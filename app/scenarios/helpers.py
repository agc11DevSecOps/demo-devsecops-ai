"""Small, fixed-path helpers shared by the scenario handlers."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from app.common import safe_sandbox_path
from app.lab import branches, execute_a_tool, fixture_document, load_jsonl, save_branches, write_text

__all__ = ["branches", "execute_a_tool", "fixture_document", "fixture_prompts", "load_jsonl", "mcp_available", "mcp_call", "safe_path", "save_branches", "write_text"]


def safe_path(relative: str) -> Path:
    """Resolve a constant scenario-relative path beneath the sandbox."""
    return safe_sandbox_path(relative)


def fixture_prompts(relative: str) -> list[str]:
    return [record["prompt"] for record in load_jsonl(relative)]


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
