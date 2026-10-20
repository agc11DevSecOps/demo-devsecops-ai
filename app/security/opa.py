"""Small, fail-closed wrapper around the pinned offline OPA binary."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

_MAX_OPA_OUTPUT = 65_536


def evaluate(policy: Path, query: str, request: dict[str, Any]) -> bool:
    """Evaluate a fixed Rego policy offline; any error fails closed to ``False``."""
    body = json.dumps(request, sort_keys=True, separators=(",", ":"))
    environment = {"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin"}
    try:
        result = subprocess.run(
            ["opa", "eval", "--format", "json", "--stdin-input", "--data", str(policy), query],
            input=body.encode("utf-8"),
            check=False,
            cwd="/tmp",
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        if result.returncode != 0 or len(result.stdout) > _MAX_OPA_OUTPUT:
            return False
        payload = json.loads(result.stdout)
        value = payload["result"][0]["expressions"][0]["value"]
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, IndexError, TypeError):
        return False
    return value is True
