"""Shared, dependency-free primitives for the offline Ops Copilot laboratory.

This module deliberately contains no scenario, model, browser, or external-tool
logic. Higher layers use it for fixed paths, canonical serialization, and input
validation so they agree on what constitutes the same piece of evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


# Runtime paths are fixed by default and can only be relocated by the container.
ROOT = Path(__file__).resolve().parents[1]
SANDBOX = Path(os.environ.get("OPS_DEMO_SANDBOX", ROOT / "sandbox"))
EVIDENCE = Path(os.environ.get("OPS_DEMO_EVIDENCE", ROOT / "evidence"))
VISUAL_EVIDENCE = EVIDENCE / "visual"
ARTIFACTS = Path(os.environ.get("OPS_DEMO_ARTIFACTS", ROOT / "artifacts"))
FIXTURES = Path(os.environ.get("OPS_DEMO_FIXTURES", ROOT / "fixtures"))

# Evidence contracts accept only these declared labels and AISVS identifiers.
MAX_TEXT = 8_192
LABELS = frozenset({"MEASURED", "RECORDED", "SCRIPTED", "DESIGNED", "NOT TESTED", "PARTIAL"})
AISVS_ID = re.compile(r"^v1\.01-C(?:[1-9]|1[0-2])\.\d+\.\d+$")


def sha256(value: bytes | str) -> str:
    """Return the stable digest used to bind evidence without storing raw input."""
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def canonical(value: dict[str, Any]) -> bytes:
    """Serialize a JSON object deterministically before it is signed or hashed."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def safe_sandbox_path(relative: str) -> Path:
    """Resolve repository-owned scenario paths and reject sandbox escapes."""
    candidate = (SANDBOX / relative).resolve()
    root = SANDBOX.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("sandbox_path_escape")
    return candidate
