"""Human-approval tokens cryptographically bound to an exact tool call.

An approval binds the tool, its canonicalized parameters, the requester and the
pinned descriptor digest. Tokens are HMAC-signed with a key that is isolated from
the agent, so a model or tool cannot mint or widen its own approval.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from app.demo import ARTIFACTS, _safe_path, canonical, sha256

DEFAULT_TTL_SECONDS = 300
FIELDS = ("tool", "parameters", "requester", "descriptor_sha256", "expires_at")


def _key() -> bytes:
    configured = os.environ.get("OPS_DEMO_APPROVAL_KEY")
    if configured:
        return configured.encode("utf-8")
    path = _safe_path("model/signing.key")
    if not path.is_file():
        raise ValueError("approval_key_unavailable")
    return path.read_bytes()


def _sign(body: str) -> str:
    return hmac.new(_key(), body.encode("ascii"), hashlib.sha256).hexdigest()


def issue(tool: str, parameters: dict[str, Any], requester: str, descriptor_sha256: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    payload = {
        "tool": tool,
        "parameters": parameters,
        "requester": requester,
        "descriptor_sha256": descriptor_sha256,
        "expires_at": int(time.time()) + ttl_seconds,
    }
    body = base64.urlsafe_b64encode(canonical(payload)).decode("ascii")
    return f"{body}.{_sign(body)}"


def verify(token: str, *, tool: str, parameters: dict[str, Any], requester: str, descriptor_sha256: str) -> bool:
    try:
        body, signature = token.split(".")
        payload = json.loads(base64.urlsafe_b64decode(body.encode("ascii")))
    except (ValueError, json.JSONDecodeError):
        return False
    if type(payload) is not dict or set(payload) != set(FIELDS):
        return False
    if not hmac.compare_digest(_sign(body), signature):
        return False
    if payload["expires_at"] < int(time.time()):
        return False
    return (
        payload["tool"] == tool
        and payload["parameters"] == parameters
        and payload["requester"] == requester
        and payload["descriptor_sha256"] == descriptor_sha256
    )


def record_decision(approver: str, tool: str, parameters: dict[str, Any], descriptor_sha256: str, decision: str) -> None:
    """Append an immutable, hash-only audit record for a human approval action."""
    if decision not in {"approved", "denied"}:
        raise ValueError("invalid_approval_decision")
    record = {
        "format_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "approval_decision",
        "approver_sha256": sha256(approver),
        "tool": tool,
        "parameters_sha256": sha256(canonical(parameters)),
        "descriptor_sha256": descriptor_sha256,
        "decision": decision,
    }
    path = ARTIFACTS / "approvals.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
