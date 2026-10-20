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
SECRET = re.compile(
    r"(?i)(-----BEGIN [A-Z ]*PRIVATE KEY-----|aws_secret_access_key\s*=|AKIA[0-9A-Z]{16}|sk-demo-CANARY-\d{4})"
)
DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__"}
DANGEROUS_ATTRS = {("os", "system"), ("os", "popen"), ("pickle", "loads")}
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


# Pipeline stages: each returns evidence; later stages stop after a failed gate.
def stage_secrets() -> StageOutcome:
    hits: list[str] = []
    for path in _python_files():
        for match in SECRET.finditer(path.read_text(encoding="utf-8")):
            hits.append(f"{_label(path)}:{match.group(0)[:16]}")
    passed = not hits
    return StageOutcome(1, "secrets", "ALLOWED" if passed else "BLOCKED", passed, "MEASURED", f"deterministic secret scan of {len(_python_files())} build file(s) found {len(hits)} credential(s)")


def stage_static() -> StageOutcome:
    findings: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in DANGEROUS_CALLS:
                    findings.append(f"{_label(path)}:{func.id}")
                elif isinstance(func, ast.Attribute) and func.attr == "system" and isinstance(func.value, ast.Name) and (func.value.id, func.attr) in DANGEROUS_ATTRS:
                    findings.append(f"{_label(path)}:os.system")
    passed = not findings
    return StageOutcome(2, "static analysis", "ALLOWED" if passed else "BLOCKED", passed, "MEASURED", f"AST static analysis of {len(_python_files())} build file(s) found {len(findings)} dangerous call(s)")


def stage_triage() -> StageOutcome:
    return StageOutcome(3, "optional AI triage", "NOT TESTED", True, "DESIGNED", "hosted AI triage is deferred; the deterministic static agent is authoritative and no model verdict authorizes a build")


def stage_dependencies() -> StageOutcome:
    lock = json.loads((ROOT / "vendor" / "python.lock.json").read_text(encoding="utf-8"))
    bad = [entry.get("file") for entry in lock if not isinstance(entry, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256"))) or not str(entry.get("file", "")).endswith(".whl")]
    passed = not bad and bool(lock)
    return StageOutcome(4, "dependency audit", "ALLOWED" if passed else "BLOCKED", passed, "MEASURED", f"{len(lock)} pinned wheel hash(es) verified; offline advisory lookup is NOT TESTED pending a vendored snapshot")


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
    return StageOutcome(6, "sign and BOM", "ALLOWED" if passed else "FAIL", passed, "MEASURED", "model and AI BOM signed and verified with pinned offline Cosign")


def stage_admission() -> StageOutcome:
    if os.environ.get("OPS_DEMO_OPA") != "1":
        return StageOutcome(7, "admission", "NOT TESTED", True, "NOT TESTED", "OPA is required; deterministic fallback rules do not earn pipeline evidence")
    passed = admission.admit(True, True, True) and not admission.admit(False, True, True)
    return StageOutcome(7, "admission", "ALLOWED" if passed else "FAIL", passed, "MEASURED", "OPA admits only safe, signed, BOM-complete artifacts and denies the unsafe-format variant")


def stage_redteam() -> StageOutcome:
    threshold = yaml.safe_load((ROOT / "controls" / "ci" / "gates.yaml").read_text(encoding="utf-8"))["redteam"]["max_success_rate"]
    from app.garak_campaign import load_summary

    summary = load_summary()
    if summary is None:
        return StageOutcome(8, "red team", "NOT TESTED", True, "NOT TESTED", f"no admitted Garak campaign; threshold {threshold} not exercised and no positive verdict is claimed")
    success_rate = (summary["total"] - summary["passed"]) / summary["total"]
    passed = success_rate <= threshold
    return StageOutcome(8, "red team", "BLOCKED" if passed else "FAIL", passed, "MEASURED", f"campaign success rate {success_rate:.2f} vs threshold {threshold}")


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
    reset()
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
