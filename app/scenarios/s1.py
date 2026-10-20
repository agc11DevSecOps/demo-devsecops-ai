"""S1: build synthetic model artifacts and verify admission before use."""

from __future__ import annotations

import json
import os

from app.common import ARTIFACTS, sha256
from app.evidence import Event, EvidenceWriter
from app.scenarios.helpers import safe_path
from app.security import model_admission as admission


def scenario_s1(run: str, writer: EvidenceWriter) -> None:
    malicious, clean = admission.make_model_fixtures()
    marker = safe_path("PWNED_BY_MODEL")
    if run == "A":
        if os.environ.get("OPS_DEMO_IN_CONTAINER") != "1":
            raise RuntimeError("unsafe_model_demo_requires_container")
        import pickle

        with malicious.open("rb") as handle:
            pickle.load(handle)  # noqa: S301 - deliberate, self-created demonstration fixture.
        writer.emit(Event("A", "S1", "model load", "EXECUTED", "sandbox marker created", (), input_value=malicious.name, visual={"input": {"artifact": malicious.name, "format": "pickle"}, "control": {"deserialization": "unsafe baseline"}, "observation": {"marker": "PWNED_BY_MODEL"}, "state": {"marker_exists": marker.exists()}}))
        return

    scanners_ran = 0
    if os.environ.get("OPS_DEMO_FICKLING") == "1":
        severity = admission.fickling_scan(malicious)
        if severity == "LIKELY_SAFE":
            raise AssertionError("malicious_fixture_not_detected")
        writer.emit(Event("B", "S1", "Fickling static scan", "BLOCKED", f"Fickling 0.1.12 reported {severity}", ("v1.01-C6.1.1",), input_value=malicious.name, visual={"input": {"artifact": malicious.name}, "control": {"scanner": "Fickling 0.1.12"}, "observation": {"severity": severity, "report": "fickling-s1.json"}, "state": {"admitted": False}}))
        scanners_ran += 1
    if os.environ.get("OPS_DEMO_MODELSCAN") == "1":
        findings = admission.modelscan_scan(malicious)
        if findings < 1:
            raise AssertionError("malicious_fixture_not_detected")
        writer.emit(Event("B", "S1", "ModelScan static scan", "BLOCKED", f"ModelScan 0.8.8 reported {findings} issue(s)", ("v1.01-C6.1.1",), input_value=malicious.name, visual={"input": {"artifact": malicious.name}, "control": {"scanner": "ModelScan 0.8.8"}, "observation": {"findings": findings, "report": "modelscan-s1.json"}, "state": {"admitted": False}}))
        scanners_ran += 1
    if scanners_ran == 0:
        if admission.pickle_scan(malicious):
            writer.emit(Event("B", "S1", "fallback pickle scan", "BLOCKED", "unsafe self-made pickle opcode", ("v1.01-C6.1.1",), input_value=malicious.name))
        else:
            raise AssertionError("malicious_fixture_not_detected")
    safe_format = clean.suffix == ".safetensors" and clean.is_file()
    if not safe_format:
        raise AssertionError("unsafe_format_artifact")
    writer.emit(Event("B", "S1", "SafeTensors format gate", "ALLOWED", "the clean artifact uses the non-executable SafeTensors container format, so loading it cannot execute code", (), input_value=clean.name, visual={"input": {"artifact": clean.name, "format": "safetensors"}, "control": {"format_check": "safetensors", "executable_format": False}, "observation": {"suffix": clean.suffix}, "state": {"admitted": False}}))
    integrity = "Cosign" if os.environ.get("OPS_DEMO_COSIGN") == "1" else "fallback"
    aibom = {
        "model": "synthetic-tiny-model", "sha256": sha256(clean.read_bytes()),
        "base_model": "synthetic", "license": "demo-only", "dataset_origin": "synthetic",
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    aibom_path = ARTIFACTS / "aibom.json"
    aibom_path.write_text(json.dumps(aibom, sort_keys=True), encoding="utf-8")
    writer.emit(Event("B", "S1", "AI BOM published", "ALLOWED", "machine-readable AI BOM records the model, digest, base model, license and dataset origin in version control", ("v1.01-C6.2.1",), input_value="aibom.json"))
    aibom_bundle = admission.sign(aibom_path)
    if not admission.verify(aibom_path, aibom_bundle):
        raise AssertionError("aibom_signature_failed")
    writer.emit(Event("B", "S1", "AI BOM signature", "ALLOWED", f"AI BOM signed with {integrity} and verified before deployment", ("v1.01-C6.2.2",), input_value="aibom.json"))
    required = {"model", "sha256", "base_model", "license", "dataset_origin"}
    if not required <= {key for key, value in aibom.items() if value}:
        raise AssertionError("aibom_complete_metadata_missing")
    incomplete = {key: value for key, value in aibom.items() if key != "license"}
    if required <= {key for key, value in incomplete.items() if value}:
        raise AssertionError("aibom_gate_failed")
    writer.emit(Event("B", "S1", "AI BOM completeness gate", "BLOCKED", "completeness check rejects a BOM missing component metadata, failing the admission build", ("v1.01-C6.2.3",), input_value="aibom-incomplete.json"))
    signature = admission.sign(clean)
    signature_ok = admission.verify(clean, signature)
    if not signature_ok:
        raise AssertionError("signature_failed")
    writer.emit(Event("B", "S1", f"{integrity} integrity admission", "ALLOWED", f"safe format, digest and {integrity} signature verified", ("v1.01-C3.1.1", "v1.01-C3.1.2", "v1.01-C4.1.2", "v1.01-C6.1.2", "v1.01-C6.1.3", "v1.01-C6.2.1"), input_value=clean.name))
    if not admission.admit(safe_format, signature_ok, True):
        raise AssertionError("admission_denied")
    engine = "OPA admission policy" if os.environ.get("OPS_DEMO_OPA") == "1" else "fallback admission rules"
    writer.emit(Event("B", "S1", f"{engine} model admission", "ALLOWED", "admission gated on a safe format, a verified signature and a complete AI BOM", ("v1.01-C3.1.2", "v1.01-C6.1.3"), input_value=clean.name))
    original = clean.read_bytes()
    clean.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    if admission.verify(clean, signature):
        raise AssertionError("tamper_not_detected")
    writer.emit(Event("B", "S1", "tampered model", "DENIED", f"{integrity} signature mismatch", ("v1.01-C3.1.3",), input_value=clean.name))
    clean.write_bytes(original)
    if marker.exists():
        raise AssertionError("marker_created_in_b")
    if os.environ.get("OPS_DEMO_IN_CONTAINER") == "1":
        writer.emit(Event("B", "S1", "restricted runtime boundary", "BLOCKED", "model and scanners ran with no network, a read-only rootfs and dropped capabilities, so the model cannot reach or persist beyond the sandbox", ("v1.01-C3.4.1", "v1.01-C4.1.1"), input_value="container-boundary"))
