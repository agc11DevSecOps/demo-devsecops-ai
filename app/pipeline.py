"""Offline 11-stage DevSecOps pipeline mirroring ``docs/pipeline.mmd``.

Every stage runs deterministically offline against repository-owned inputs. A
stage whose external tool is not admitted reports ``NOT TESTED`` (or
``DESIGNED`` for deferred work) and never silently passes. The two early gates
fail closed: a failing secrets or static-analysis stage halts the flow, and the
red-team stage enforces the threshold declared in ``controls/ci/gates.yaml``.

Pipeline events intentionally carry no AISVS ids so they cannot change the
AISVS scorecard, which is derived only from scenario evidence.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

from app.common import ARTIFACTS, ROOT
from app.evidence import Event, EvidenceWriter
from app.sandbox import reset
from app.security import model_admission as admission

BUILD_DIRS = ("app", "controls")
SECRET_DIRS = ("app", "controls", "scripts", "policies", ".github")
SECRET_FILES = ("Makefile", "Dockerfile", "docker-compose.yml")
SECRET_SUFFIXES = frozenset({".py", ".sh", ".yml", ".yaml", ".rego", ".toml"})
SECRET = re.compile(
    r"(?i)(-----BEGIN [A-Z ]*PRIVATE KEY-----|aws_secret_access_key\s*=|AKIA[0-9A-Z]{16}|sk-demo-CANARY-\d{4}|hf_[A-Za-z0-9]{20,})"
)
DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__"}
DANGEROUS_ATTRS = {("os", "system"), ("os", "popen"), ("pickle", "load"), ("pickle", "loads")}
REVIEWED_EXCEPTIONS = frozenset({
    ("app/scenarios/s1.py", "pickle.load"),
    ("app/security/model_admission.py", "os.system"),
})
HALTS = frozenset({1, 2})


@dataclass
class StageOutcome:
    number: int
    name: str
    decision: str
    passed: bool
    label: str
    reason: str

    def emit(self, writer: EvidenceWriter) -> None:
        writer.emit(Event("B", "PIPELINE", f"stage {self.number} {self.name}", self.decision, self.reason, (), self.label, input_value=f"stage-{self.number}"))


def _python_files() -> list[Path]:
    files: list[Path] = []
    for base in BUILD_DIRS:
        files.extend(sorted((ROOT / base).rglob("*.py")))
    return files


def _label(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return path.name


def _secret_files() -> list[Path]:
    files: list[Path] = []
    for base in SECRET_DIRS:
        files.extend(sorted(path for path in (ROOT / base).rglob("*") if path.is_file() and path.suffix in SECRET_SUFFIXES))
    files.extend(path for name in SECRET_FILES if (path := ROOT / name).is_file())
    return files


# Pipeline stages: each returns evidence; later stages stop after a failed gate.
def stage_secrets() -> StageOutcome:
    hits: list[str] = []
    files = _secret_files()
    for path in files:
        for match in SECRET.finditer(path.read_text(encoding="utf-8")):
            hits.append(f"{_label(path)}:{match.group(0)[:16]}")
    passed = not hits
    return StageOutcome(1, "secrets", "ALLOWED" if passed else "BLOCKED", passed, "MEASURED", f"deterministic secret scan of {len(files)} build file(s) found {len(hits)} credential(s)")


def _dangerous_call(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name) and func.id in DANGEROUS_CALLS:
        return func.id
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and (func.value.id, func.attr) in DANGEROUS_ATTRS:
        return f"{func.value.id}.{func.attr}"
    return None


def stage_static() -> StageOutcome:
    findings: list[str] = []
    exceptions: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _dangerous_call(node)
                if name is not None:
                    location = _label(path)
                    if (location, name) in REVIEWED_EXCEPTIONS:
                        exceptions.append(f"{location}:{name}")
                    else:
                        findings.append(f"{location}:{name}")
    passed = not findings
    detail = f"AST static analysis of {len(_python_files())} Python build file(s) found {len(findings)} unreviewed dangerous call(s) and {len(exceptions)} reviewed demo exception(s)"
    if findings:
        detail += ": " + ", ".join(findings[:3])
    return StageOutcome(2, "static analysis", "ALLOWED" if passed else "BLOCKED", passed, "MEASURED", detail)


def stage_triage() -> StageOutcome:
    return StageOutcome(3, "optional AI triage", "NOT TESTED", True, "DESIGNED", "hosted AI triage is deferred; the deterministic static agent is authoritative and no model verdict authorizes a build")


def stage_dependencies() -> StageOutcome:
    lock = json.loads((ROOT / "vendor" / "python.lock.json").read_text(encoding="utf-8"))
    wheels = ROOT / "vendor" / "python"
    bad: list[str] = []
    for entry in lock:
        name = entry.get("file") if isinstance(entry, dict) else None
        digest = entry.get("sha256") if isinstance(entry, dict) else None
        if not isinstance(name, str) or not name.endswith(".whl") or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            bad.append(str(name))
            continue
        path = wheels / name
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            bad.append(name)
            continue
        if actual != digest:
            bad.append(name)
    passed = not bad and bool(lock)
    return StageOutcome(4, "dependency audit", "ALLOWED" if passed else "BLOCKED", passed, "MEASURED", f"{len(lock)} wheel file(s) verified against the pinned lock; {len(bad)} missing or mismatched; offline advisory lookup is NOT TESTED pending a vendored snapshot" if passed else f"{len(bad)} wheel file(s) missing or mismatched against the pinned lock; offline advisory lookup is NOT TESTED")


def stage_model_scan() -> StageOutcome:
    if os.environ.get("OPS_DEMO_FICKLING") != "1" or os.environ.get("OPS_DEMO_MODELSCAN") != "1":
        return StageOutcome(5, "model scan", "NOT TESTED", True, "NOT TESTED", "Fickling and ModelScan are required; stdlib fallback does not earn pipeline evidence")
    malicious, _ = admission.make_model_fixtures()
    try:
        severity = admission.fickling_scan(malicious)
        findings = admission.modelscan_scan(malicious)
    except RuntimeError:
        return StageOutcome(5, "model scan", "FAIL", False, "MEASURED", "a required admitted model scanner did not complete")
    detected = severity != "LIKELY_SAFE" and findings > 0
    return StageOutcome(5, "model scan", "BLOCKED" if detected else "FAIL", detected, "MEASURED", f"Fickling reported {severity}; ModelScan reported {findings} issue(s) in the synthetic unsafe fixture")


def stage_sign_bom() -> StageOutcome:
    if os.environ.get("OPS_DEMO_COSIGN") != "1":
        return StageOutcome(6, "sign and BOM", "NOT TESTED", True, "NOT TESTED", "Cosign is required; the demo HMAC fallback does not earn pipeline evidence")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    model = ARTIFACTS / "pipeline-model.safetensors"
    model.write_bytes(b"SAFE_TENSORS_PIPELINE\nweights=synthetic\n")
    aibom = {"model": "pipeline-synthetic", "sha256": hashlib.sha256(model.read_bytes()).hexdigest(), "base_model": "synthetic", "license": "demo-only", "dataset_origin": "synthetic"}
    aibom_path = ARTIFACTS / "pipeline-aibom.json"
    aibom_path.write_text(json.dumps(aibom, sort_keys=True), encoding="utf-8")
    signature = admission.sign(model)
    passed = admission.verify(model, signature) and admission.verify(aibom_path, admission.sign(aibom_path))
    return StageOutcome(6, "sign and BOM", "ALLOWED" if passed else "FAIL", passed, "MEASURED", "synthetic pipeline model and AI BOM signed and verified with pinned offline Cosign")


def stage_admission() -> StageOutcome:
    if os.environ.get("OPS_DEMO_OPA") != "1":
        return StageOutcome(7, "admission", "NOT TESTED", True, "NOT TESTED", "OPA is required; deterministic fallback rules do not earn pipeline evidence")
    model = ARTIFACTS / "pipeline-model.safetensors"
    aibom_path = ARTIFACTS / "pipeline-aibom.json"
    if not model.is_file() or not aibom_path.is_file():
        return StageOutcome(7, "admission", "NOT TESTED", True, "NOT TESTED", "no signed pipeline artifact from stage 6; admission facts unavailable")
    try:
        aibom = json.loads(aibom_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return StageOutcome(7, "admission", "FAIL", False, "MEASURED", "the pipeline AI BOM is unreadable")
    safe_format = model.suffix == ".safetensors" and model.read_bytes().startswith(b"SAFE_TENSORS_PIPELINE")
    signature_ok = admission.verify(model, model.with_suffix(model.suffix + ".cosign.bundle")) and admission.verify(aibom_path, aibom_path.with_suffix(aibom_path.suffix + ".cosign.bundle"))
    complete = admission.aibom_complete(aibom)
    passed = admission.admit(safe_format, signature_ok, complete) and not admission.admit(False, signature_ok, complete) and not admission.admit(safe_format, signature_ok, False)
    return StageOutcome(7, "admission", "ALLOWED" if passed else "FAIL", passed, "MEASURED", f"OPA evaluated the signed pipeline artifact: safe_format={safe_format}, signature_ok={signature_ok}, aibom_complete={complete}; it also denied the unsafe-format and incomplete-BOM variants")


def stage_redteam() -> StageOutcome:
    threshold = yaml.safe_load((ROOT / "controls" / "ci" / "gates.yaml").read_text(encoding="utf-8"))["redteam"]["max_success_rate"]
    from app.garak_campaign import load_summary

    summary = load_summary()
    if summary is None:
        return StageOutcome(8, "red team", "NOT TESTED", True, "NOT TESTED", f"no admitted Garak campaign; threshold {threshold} not exercised and no positive verdict is claimed")
    if not summary["full"]:
        return StageOutcome(8, "red team", "NOT TESTED", True, "PARTIAL", f"partial Garak campaign {summary['passed']}/{summary['total']} of 55 prompts; only the full campaign can exercise the {threshold} threshold")
    success_rate = (summary["total"] - summary["passed"]) / summary["total"]
    passed = success_rate <= threshold
    return StageOutcome(8, "red team", "ALLOWED" if passed else "FAIL", passed, "MEASURED", f"Garak detector success rate {success_rate:.2f} vs threshold {threshold}; this is endpoint-guard evidence, not model jailbreak resistance")


def stage_deploy() -> StageOutcome:
    return StageOutcome(9, "deploy", "NOT TESTED", True, "DESIGNED", "no deployment target is provisioned; the deploy stage never executes outside a reviewed environment")


def stage_runtime() -> StageOutcome:
    from app.workload import activate_stop, deactivate_stop, handle_payload, reset_rate_limiter

    reset_rate_limiter()
    activate_stop()
    try:
        status, payload = handle_payload({"request_id": "pipeline-runtime", "requester": "pipeline-runtime", "question": "What is the rollback procedure?"})
    finally:
        deactivate_stop()
    passed = status == 503 and payload.get("code") == "inference_stopped"
    return StageOutcome(10, "runtime", "BLOCKED" if passed else "FAIL", passed, "MEASURED", "the kill switch rejected a valid request before inference; runtime controls are active")


def stage_recorded_evidence() -> StageOutcome:
    return StageOutcome(11, "recorded S6 evidence", "NOT TESTED", True, "NOT TESTED", "no admitted recorded Strix evidence; see record/s6 and LIMITATIONS.md")


STAGES: tuple[Callable[[], StageOutcome], ...] = (
    stage_secrets,
    stage_static,
    stage_triage,
    stage_dependencies,
    stage_model_scan,
    stage_sign_bom,
    stage_admission,
    stage_redteam,
    stage_deploy,
    stage_runtime,
    stage_recorded_evidence,
)


# Orchestration: execute stages in order and fail closed when a required gate fails.
def run_pipeline(writer: EvidenceWriter | None = None, only: int | None = None) -> list[StageOutcome]:
    if os.environ.get("OPS_DEMO_PIPELINE_PREPARED") != "1":
        garak_summary = ARTIFACTS / "garak-s7.json"
        preserved_summary = garak_summary.read_bytes() if garak_summary.is_file() else None
        reset(clear_evidence=False)
        if preserved_summary is not None:
            garak_summary.write_bytes(preserved_summary)
    writer = writer or EvidenceWriter()
    results: list[StageOutcome] = []
    for index, stage in enumerate(STAGES, start=1):
        if only is not None and index != only:
            continue
        outcome = stage()
        outcome.emit(writer)
        results.append(outcome)
        if only is None and outcome.number in HALTS and not outcome.passed:
            writer.emit(Event("B", "PIPELINE", "pipeline halted", "FAIL", f"gate after stage {outcome.number} failed closed; later stages were not run", (), "MEASURED", input_value=f"halt-{outcome.number}"))
            return results
    return results
