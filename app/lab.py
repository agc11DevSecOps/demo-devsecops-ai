"""Fixed fixture loading and sandbox-only synthetic tool effects.

Shared by the scenario handlers, the unguarded lab and the evaluation target.
Every path is repository-owned or resolved beneath the sandbox.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.common import FIXTURES, safe_sandbox_path


def load_jsonl(relative: str) -> list[dict[str, Any]]:
    """Load a reviewed, repository-owned fixture corpus (one JSON object per line)."""
    path = FIXTURES / relative
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if type(record) is not dict or not isinstance(record.get("id"), str):
            raise ValueError("invalid_fixture_record")
        records.append(record)
    if not records:
        raise ValueError("empty_fixture")
    return records


def fixture_document(relative: str) -> str:
    return (FIXTURES / relative).read_text(encoding="utf-8").strip()


def write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def branches() -> list[str]:
    return json.loads(safe_sandbox_path("repo/branches.json").read_text(encoding="utf-8"))


def save_branches(values: list[str]) -> None:
    write_text(safe_sandbox_path("repo/branches.json"), json.dumps(values))


def execute_a_tool(tool: str, parameters: dict[str, str]) -> None:
    """Model the unsafe baseline's unbounded tool effects inside the sandbox."""
    if tool == "delete_branch":
        save_branches([branch for branch in branches() if branch != parameters["branch"]])
    elif tool == "export_customers":
        write_text(safe_sandbox_path("exfil/customers.csv"), "id,name\n1,Synthetic Customer\n")
