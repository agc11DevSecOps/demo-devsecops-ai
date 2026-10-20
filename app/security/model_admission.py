"""Model artifact construction, scanning, signing, and admission controls.

All demo artifacts are synthetic and remain inside ``sandbox/``. Admission is a
pure function of static checks, artifact integrity, and AI BOM metadata; model
output never participates in the decision.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import pickle
import pickletools
import shlex
import subprocess
from pathlib import Path
from typing import Any

from app.common import ARTIFACTS, ROOT, safe_sandbox_path
from app.security import opa


def malicious_command() -> str:
    """Shell command reachable only from the self-made S1 fixture."""
    marker = shlex.quote(str(safe_sandbox_path("PWNED_BY_MODEL")))
    return f"printf 'synthetic marker\\n' > {marker}"


class MaliciousFixture:
    """Self-created pickle fixture; its only payload writes the sandbox marker.

    The payload deliberately resolves to the ``os.system`` global (pickled as the
    ``posix`` module) so canonical scanners such as ModelScan and Fickling flag it
    as unsafe, while the effect stays confined to ``sandbox/``.
    """

    def __reduce__(self) -> tuple[Any, tuple[str]]:
        return os.system, (malicious_command(),)


def make_model_fixtures() -> tuple[Path, Path]:
    """Create one unsafe pickle and one clean synthetic tensor artifact."""
    incoming = safe_sandbox_path("models/incoming")
    incoming.mkdir(parents=True, exist_ok=True)
    malicious = incoming / "model_malicious.pkl"
    clean = incoming / "model_clean.safetensors"
    malicious.write_bytes(pickle.dumps(MaliciousFixture(), protocol=4))
    clean.write_bytes(b"SAFE_TENSORS_DEMO\nweights=synthetic\n")
    return malicious, clean


_UNSAFE_PICKLE_MODULES = frozenset({"os", "posix", "nt", "subprocess", "sys", "shutil", "builtins", "runpy", "importlib"})


def pickle_scan(path: Path) -> bool:
    """Narrow stdlib fallback: inspect opcodes only, never load the pickle."""
    pending: list[str] = []
    try:
        for opcode, argument, _ in pickletools.genops(path.read_bytes()):
            if opcode.name == "GLOBAL" and isinstance(argument, str):
                if argument.split(" ", 1)[0].strip() in _UNSAFE_PICKLE_MODULES:
                    return True
            elif opcode.name in {"SHORT_BINUNICODE", "BINUNICODE", "UNICODE", "STRING"} and isinstance(argument, str):
                pending = (pending + [argument])[-2:]
            elif opcode.name == "STACK_GLOBAL" and len(pending) == 2 and pending[0] in _UNSAFE_PICKLE_MODULES:
                return True
    except Exception:
        return False
    return False


def fickling_scan(path: Path) -> str:
    """Run the pinned scanner only on the fixed, sandbox-contained fixture."""
    report = ARTIFACTS / "fickling-s1.json"
    report.unlink(missing_ok=True)
    environment = {
        "HOME": "/tmp",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": "",
    }
    try:
        result = subprocess.run(
            ["fickling", "--check-safety", "--json-output", str(report), str(path)],
            check=False,
            cwd="/tmp",
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        payload = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        raise RuntimeError("fickling_scan_failed") from error
    severity = payload.get("severity") if isinstance(payload, dict) else None
    if result.returncode not in {0, 1} or not isinstance(severity, str):
        raise RuntimeError("fickling_scan_failed")
    return severity


def modelscan_scan(path: Path) -> int:
    """Run the pinned ModelScan scanner and return its issue count."""
    report = ARTIFACTS / "modelscan-s1.json"
    report.unlink(missing_ok=True)
    environment = {
        "HOME": "/tmp",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "OPENBLAS_NUM_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    try:
        result = subprocess.run(
            ["modelscan", "scan", "-p", str(path), "-r", "json", "-o", str(report)],
            check=False,
            cwd="/tmp",
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
        payload = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        raise RuntimeError("modelscan_scan_failed") from error
    summary = payload.get("summary") if isinstance(payload, dict) else None
    count = summary.get("total_issues") if isinstance(summary, dict) else None
    if result.returncode not in {0, 1} or not isinstance(count, int):
        raise RuntimeError("modelscan_scan_failed")
    return count


# Admission combines format safety, signature integrity, and AI BOM completeness.
def opa_admit(safe_format: bool, signature_ok: bool, aibom_complete: bool) -> bool:
    """Admit a model artifact through the pinned OPA binary and admission policy."""
    return opa.evaluate(
        ROOT / "policies" / "admission.rego",
        "data.ops.copilot.admission.allow",
        {"artifact": {"safe_format": bool(safe_format), "signature_ok": bool(signature_ok), "aibom_complete": bool(aibom_complete)}},
    )


def fallback_admit(safe_format: bool, signature_ok: bool, aibom_complete: bool) -> bool:
    """Deterministic stdlib admission used when the OPA binary is not requested."""
    return bool(safe_format) and bool(signature_ok) and bool(aibom_complete)


def admit(safe_format: bool, signature_ok: bool, aibom_complete: bool) -> bool:
    """Gate model admission through OPA when enabled, else the fixed fallback."""
    if os.environ.get("OPS_DEMO_OPA") == "1":
        return opa_admit(safe_format, signature_ok, aibom_complete)
    return fallback_admit(safe_format, signature_ok, aibom_complete)


# Integrity helpers: Cosign when requested, otherwise a demo-only HMAC.
_COSIGN_PASSWORD = "demo-only"
_COSIGN_ENV = {"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin", "COSIGN_PASSWORD": _COSIGN_PASSWORD}


def cosign_keypair() -> tuple[Path, Path]:
    """Generate the demo-only keypair in the sandbox if it is absent."""
    key = safe_sandbox_path("model/cosign.key")
    pub = safe_sandbox_path("model/cosign.pub")
    if key.exists() and pub.exists():
        return key, pub
    result = subprocess.run(
        ["cosign", "generate-key-pair", "--output-key-prefix", str(safe_sandbox_path("model/cosign"))],
        check=False,
        cwd="/tmp",
        env=_COSIGN_ENV,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    if result.returncode != 0 or not key.exists() or not pub.exists():
        raise RuntimeError("cosign_keygen_failed")
    return key, pub


def cosign_sign(path: Path) -> Path:
    """Sign a blob offline with the pinned Cosign binary and a local key."""
    key, _ = cosign_keypair()
    bundle = path.with_suffix(path.suffix + ".cosign.bundle")
    result = subprocess.run(
        ["cosign", "sign-blob", "--yes", "--use-signing-config=false", "--tlog-upload=false", "--key", str(key), "--bundle", str(bundle), str(path)],
        check=False,
        cwd="/tmp",
        env=_COSIGN_ENV,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    if result.returncode != 0 or not bundle.exists():
        raise RuntimeError("cosign_sign_failed")
    return bundle


def cosign_verify(path: Path, bundle: Path) -> bool:
    """Verify a blob offline; never generate keys here, fail closed instead."""
    pub = safe_sandbox_path("model/cosign.pub")
    if not bundle.exists() or not pub.exists():
        return False
    result = subprocess.run(
        ["cosign", "verify-blob", "--key", str(pub), "--bundle", str(bundle), "--insecure-ignore-tlog", str(path)],
        check=False,
        cwd="/tmp",
        env={"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    return result.returncode == 0


def sign(path: Path) -> Path:
    """Sign an artifact with Cosign when enabled, else the demo HMAC key."""
    if os.environ.get("OPS_DEMO_COSIGN") == "1":
        return cosign_sign(path)
    key = safe_sandbox_path("model/signing.key").read_bytes()
    digest = hmac.new(key, path.read_bytes(), hashlib.sha256).hexdigest()
    signature = path.with_suffix(path.suffix + ".demo-hmac")
    signature.write_text(digest, encoding="ascii")
    return signature


def verify(path: Path, signature: Path) -> bool:
    """Verify an artifact signature and fail closed on any mismatch."""
    if os.environ.get("OPS_DEMO_COSIGN") == "1":
        return cosign_verify(path, signature)
    key = safe_sandbox_path("model/signing.key").read_bytes()
    expected = hmac.new(key, path.read_bytes(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.read_text(encoding="ascii"))
