"""Small, fixed-path helpers shared by the scenario handlers."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.common import FIXTURES, safe_sandbox_path


def safe_path(relative: str) -> Path:
    """Resolve a constant scenario-relative path beneath the sandbox."""
    return safe_sandbox_path(relative)


def write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


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


def fixture_prompts(relative: str) -> list[str]:
    return [record["prompt"] for record in load_jsonl(relative)]


def fixture_document(relative: str) -> str:
    return (FIXTURES / relative).read_text(encoding="utf-8").strip()


def branches() -> list[str]:
    return json.loads(safe_path("repo/branches.json").read_text(encoding="utf-8"))


def save_branches(values: list[str]) -> None:
    write_text(safe_path("repo/branches.json"), json.dumps(values))


def execute_a_tool(tool: str, parameters: dict[str, str]) -> None:
    """Model the unsafe baseline's unbounded tool effects inside the sandbox."""
    if tool == "delete_branch":
        save_branches([branch for branch in branches() if branch != parameters["branch"]])
    elif tool == "export_customers":
        write_text(safe_path("exfil/customers.csv"), "id,name\n1,Synthetic Customer\n")


def mcp_available() -> bool:
    try:
        import mcp  # noqa: F401
    except ImportError:
        return False
    return True


def mcp_call(tool: str, arguments: dict[str, str]) -> tuple[tuple[str, ...], str]:
    """Call a tool on the local stdio MCP server and return its tool list and text."""
    import asyncio

    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp_server"])

    async def go() -> tuple[tuple[str, ...], str]:
        async with Client(params) as client:
            listed = await client.list_tools()
            result = await client.call_tool(tool, arguments)
            text = result.content[0].text if result.content else ""
            return tuple(item.name for item in listed.tools), text

    return asyncio.run(go())
