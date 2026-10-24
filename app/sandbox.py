"""Sandbox lifecycle for the demo runs.

The reset boundary recreates fixed repository state and, unless preserved,
clears generated evidence. Nothing outside ``sandbox/`` and the evidence
directories is removed.
"""

from __future__ import annotations

import json
import shutil

from app.common import ARTIFACTS, EVIDENCE, SANDBOX, VISUAL_EVIDENCE, safe_sandbox_path


def _write_text(path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def reset(*, clear_evidence: bool = True) -> None:
    """Restore fixed sandbox state and optionally clear generated evidence."""
    from app.workload import reset_rate_limiter

    reset_rate_limiter()
    preserved_evidence = {
        path.relative_to(EVIDENCE): path.read_bytes()
        for path in EVIDENCE.rglob("*.jsonl")
    } if not clear_evidence else {}
    shutil.rmtree(SANDBOX, ignore_errors=True)
    SANDBOX.mkdir(mode=0o700, exist_ok=True)
    for run in ("A", "B"):
        directory = EVIDENCE / run
        directory.mkdir(parents=True, exist_ok=True)
        if clear_evidence:
            for path in directory.glob("*.jsonl"):
                path.unlink()
    if clear_evidence:
        shutil.rmtree(VISUAL_EVIDENCE, ignore_errors=True)
    else:
        for relative, data in preserved_evidence.items():
            path = EVIDENCE / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    # Supporting artifacts (Garak aggregate, approvals, scanner reports) are part
    # of the evidence surface, so preserve them when evidence is preserved.
    preserved = {
        path.name: path.read_bytes()
        for path in ARTIFACTS.glob("*")
        if not clear_evidence and path.is_file()
    }
    shutil.rmtree(ARTIFACTS, ignore_errors=True)
    # A bind mount at this path survives removal of SANDBOX in the container.
    ARTIFACTS.mkdir(mode=0o700, exist_ok=True)
    for name, data in preserved.items():
        (ARTIFACTS / name).write_bytes(data)
    _write_text(safe_sandbox_path("repo/branches.json"), json.dumps(["main", "release/2.4", "feature/x", "stale/old"]))
    _write_text(safe_sandbox_path("model/signing.key"), "demo-only-integrity-key\n")
