"""Tool schemas, quotas, and the only authorization boundary for tool actions.

Tool outputs are untrusted data as well: callers must validate and screen them
before forwarding anything to a model. No model output can authorize an action.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from app.common import ROOT, canonical, sha256
from app.security.input import INJECTION
from app.security import opa

TOOL_SCHEMAS: dict[str, frozenset[str]] = {
    "read_ticket": frozenset({"ticket_id"}),
    "search_docs": frozenset({"query"}),
    "delete_branch": frozenset({"repo", "branch"}),
    "export_customers": frozenset({"format"}),
}

OUTPUT_SCHEMAS: dict[str, frozenset[str]] = {
    "read_ticket": frozenset({"ticket_id", "status", "summary"}),
    "search_docs": frozenset({"query", "results"}),
    "delete_branch": frozenset({"repo", "branch", "result"}),
    "export_customers": frozenset({"format", "path"}),
}

TOOL_SCOPES: dict[str, str] = {
    "read_ticket": "docs:read",
    "search_docs": "docs:read",
    "delete_branch": "repo:write",
    "export_customers": "data:export",
}

TOOL_QUOTA: dict[str, int] = {
    "read_ticket": 20,
    "search_docs": 20,
    "delete_branch": 1,
    "export_customers": 1,
}


def descriptor_digest(tool: str, description: str) -> str:
    """Pin a tool name, description, and declared parameter fields."""
    if tool not in TOOL_SCHEMAS or len(description) > 512 or INJECTION.search(description):
        raise ValueError("invalid_descriptor")
    return sha256(canonical({"tool": tool, "description": description, "fields": sorted(TOOL_SCHEMAS[tool])}))


@dataclass
class Grant:
    """A single-use grant bound to one exact tool call."""

    tool: str
    parameters_sha256: str
    descriptor_sha256: str
    requester: str
    used: bool = False


class ToolQuota:
    """Per-run, per-tool invocation budget that contains runaway tool use."""

    def __init__(self, limits: dict[str, int] | None = None) -> None:
        self._limits = dict(limits or TOOL_QUOTA)
        self._used: dict[str, int] = {}

    def reserve(self, tool: str) -> bool:
        if tool not in self._limits:
            raise ValueError("invalid_tool")
        if self._used.get(tool, 0) >= self._limits[tool]:
            return False
        self._used[tool] = self._used.get(tool, 0) + 1
        return True


# Policy decision: descriptors, scopes, grants, and OPA/fallback rules.
def fallback_authorize(action: str, descriptor_ok: bool, grant_valid: bool) -> bool:
    """Deterministic stdlib fallback used when the OPA binary is not requested."""
    if not descriptor_ok:
        return False
    if action in {"read_ticket", "search_docs"}:
        return True
    return action == "delete_branch" and grant_valid


def opa_authorize(action: str, descriptor_ok: bool, grant_valid: bool) -> bool:
    """Authorize a tool action through the pinned OPA binary and fixed policy."""
    return opa.evaluate(
        ROOT / "policies" / "tool_boundary.rego",
        "data.ops.copilot.allow",
        {"action": action, "context": {"descriptor_ok": bool(descriptor_ok), "grant_valid": bool(grant_valid)}},
    )


class ToolBoundary:
    def __init__(self, *, policy_available: bool = True) -> None:
        self.policy_available = policy_available
        self.descriptions = {
            "read_ticket": "Read one synthetic ticket.",
            "search_docs": "Search approved synthetic documents.",
            "delete_branch": "Delete one named branch from the synthetic repository.",
            "export_customers": "Export synthetic customers to sandbox only.",
        }
        self.pins = {name: descriptor_digest(name, description) for name, description in self.descriptions.items()}

    def validate(self, tool: str, parameters: dict[str, Any]) -> None:
        if tool not in TOOL_SCHEMAS or type(parameters) is not dict or set(parameters) != TOOL_SCHEMAS[tool]:
            raise ValueError("invalid_tool_parameters")
        if any(not isinstance(item, str) or not item or len(item) > 128 for item in parameters.values()):
            raise ValueError("invalid_tool_parameters")
        if tool == "delete_branch" and (parameters["repo"] != "demo-app" or parameters["branch"] not in {"release/2.4", "stale/old"}):
            raise ValueError("invalid_tool_parameters")
        if tool == "export_customers" and parameters["format"] != "csv":
            raise ValueError("invalid_tool_parameters")

    def list_tools(self, scopes: frozenset[str]) -> tuple[str, ...]:
        """Return only the tools permitted by the caller's authorized scopes."""
        return tuple(sorted(name for name, scope in TOOL_SCOPES.items() if scope in scopes))

    def validate_output(self, tool: str, output: Any) -> dict[str, Any]:
        """Reject any tool output that does not match its declared output schema."""
        if tool not in OUTPUT_SCHEMAS or type(output) is not dict or set(output) != OUTPUT_SCHEMAS[tool]:
            raise ValueError("invalid_tool_output")
        return output

    def screen_output(self, tool: str, output: Any) -> dict[str, Any]:
        """Screen tool output for indirect prompt injection before it is consumed."""
        if INJECTION.search(json.dumps(output, sort_keys=True)):
            raise ValueError("tool_output_injection")
        return output

    def decide(self, tool: str, parameters: dict[str, Any], requester: str, grant: Grant | None = None) -> str:
        self.validate(tool, parameters)
        if not self.policy_available:
            return "DENIED"
        descriptor_ok = descriptor_digest(tool, self.descriptions[tool]) == self.pins[tool]
        if grant is not None:
            valid = (
                grant.tool == tool and grant.requester == requester and not grant.used
                and grant.parameters_sha256 == sha256(canonical(parameters))
                and grant.descriptor_sha256 == self.pins[tool]
            )
            if not valid:
                return "DENIED"
        grant_valid = grant is not None
        if os.environ.get("OPS_DEMO_OPA") == "1":
            authorized = opa_authorize(tool, descriptor_ok, grant_valid)
        else:
            authorized = fallback_authorize(tool, descriptor_ok, grant_valid)
        if not authorized:
            return "DENIED"
        if grant is not None:
            grant.used = True
            return "REVIEW" if tool == "delete_branch" else "DENIED"
        return "ALLOWED"
