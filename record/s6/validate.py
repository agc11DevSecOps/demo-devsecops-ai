"""Validate a recorded S6 evidence package without executing its contents."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.demo import AISVS_ID


REQUIRED = {"format_version", "label", "tool", "tool_version", "model", "recorded_at", "scope", "media_sha256", "findings"}


def validate(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) != REQUIRED:
        raise ValueError("invalid_s6_manifest_schema")
    if data["format_version"] != 1 or data["label"] != "RECORDED" or data["tool"] != "Strix":
        raise ValueError("invalid_s6_manifest_identity")
    if not all(isinstance(data[field], str) and data[field] for field in ("tool_version", "model", "recorded_at", "scope")):
        raise ValueError("invalid_s6_manifest_metadata")
    if not isinstance(data["media_sha256"], str) or len(data["media_sha256"]) != 64:
        raise ValueError("invalid_s6_media_hash")
    if not isinstance(data["findings"], list):
        raise ValueError("invalid_s6_findings")
    for finding in data["findings"]:
        if type(finding) is not dict or set(finding) != {"run", "finding_id", "aisvs_ids", "status"}:
            raise ValueError("invalid_s6_finding")
        if finding["run"] not in {"A", "B"} or finding["status"] not in {"confirmed", "residual", "blocked"}:
            raise ValueError("invalid_s6_finding")
        if not isinstance(finding["finding_id"], str) or not finding["finding_id"]:
            raise ValueError("invalid_s6_finding")
        if not isinstance(finding["aisvs_ids"], list) or any(AISVS_ID.fullmatch(item) is None for item in finding["aisvs_ids"]):
            raise ValueError("invalid_s6_finding")
    return data


def verify_media(manifest: dict[str, Any], media: Path) -> bool:
    return hashlib.sha256(media.read_bytes()).hexdigest() == manifest["media_sha256"]
