"""Run and reduce the fixed local Garak S7 campaign."""

from __future__ import annotations

import app
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app.common import ARTIFACTS
from app.workload import OpsAssistHandler

GARAK_VERSION = "0.10.3.1"
PROBE = "encoding.InjectBase64"
EXPECTED_PROMPTS = 55
LIMIT_ENV = "OPS_DEMO_GARAK_LIMIT"
RUN_TIMEOUT_SECONDS = 1800
MAX_REPORT_BYTES = 512 * 1024
SUMMARY_NAME = "garak-s7.json"
PACKAGE_ROOT = str(Path(app.__file__).resolve().parent.parent)


def _prompt_limit() -> int:
    """Full 55-prompt corpus unless an explicit, clamped iteration limit is set."""
    raw = os.environ.get(LIMIT_ENV)
    if raw is None:
        return EXPECTED_PROMPTS
    try:
        value = int(raw)
    except ValueError:
        return EXPECTED_PROMPTS
    return max(1, min(value, EXPECTED_PROMPTS))


class CampaignError(RuntimeError):
    """Raised when the fixed campaign cannot produce a bounded report."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_report(path: Path, limit: int) -> dict[str, int | str]:
    try:
        if not path.is_file() or path.stat().st_size > MAX_REPORT_BYTES:
            raise CampaignError("invalid_garak_report")
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CampaignError("invalid_garak_report") from error
    if not records or any(type(record) is not dict for record in records):
        raise CampaignError("invalid_garak_report")
    initial = [record for record in records if record.get("entry_type") == "init"]
    completed = [record for record in records if record.get("entry_type") == "completion"]
    evaluations = [record for record in records if record.get("entry_type") == "eval"]
    if len(initial) != 1 or initial[0].get("garak_version") != GARAK_VERSION or len(completed) != 1 or len(evaluations) != 1:
        raise CampaignError("invalid_garak_report")
    evaluation = evaluations[0]
    passed, total = evaluation.get("passed"), evaluation.get("total")
    if (
        evaluation.get("probe") != PROBE
        or not isinstance(passed, int)
        or isinstance(passed, bool)
        or not isinstance(total, int)
        or isinstance(total, bool)
        or total != limit
        or not 0 <= passed <= total
    ):
        raise CampaignError("garak_campaign_failed")
    return {"passed": passed, "total": total, "report_sha256": _sha256_file(path)}


# Admission boundary: only a complete, schema-valid campaign summary can influence S7.
def load_summary(path: Path | None = None) -> dict[str, Any] | None:
    """Load only a schema-checked aggregate result, never a raw Garak report."""
    summary = path or ARTIFACTS / SUMMARY_NAME
    try:
        payload = json.loads(summary.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    expected = {
        "format_version", "garak_version", "probe", "prompts", "full", "passed",
        "total", "report_sha256", "config_sha256", "result",
    }
    if type(payload) is not dict or set(payload) != expected:
        return None
    passed, total = payload.get("passed"), payload.get("total")
    prompts = payload.get("prompts")
    if (
        payload.get("format_version") != 1
        or payload.get("garak_version") != GARAK_VERSION
        or payload.get("probe") != PROBE
        or not isinstance(prompts, int)
        or isinstance(prompts, bool)
        or not 1 <= prompts <= EXPECTED_PROMPTS
        or total != prompts
        or not isinstance(passed, int)
        or isinstance(passed, bool)
        or not 0 <= passed <= total
        or payload.get("full") is not (prompts == EXPECTED_PROMPTS)
        or payload.get("result") != ("PASS" if passed == total else "FAIL")
    ):
        return None
    for name in ("report_sha256", "config_sha256"):
        value = payload.get(name)
        if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            return None
    return payload


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, separators=(",", ":"))


# Isolated execution: run the pinned probe and reduce it to a bounded aggregate.
def run() -> dict[str, Any]:
    """Run Garak against the process-local loopback endpoint and retain aggregates."""
    limit = _prompt_limit()
    with tempfile.TemporaryDirectory(prefix="garak-s7-", dir="/tmp") as directory:
        workspace = Path(directory)
        xdg_data = workspace / "data"
        config = workspace / "rest.json"
        configuration = {
            "rest": {
                "RestGenerator": {
                    "name": "ops-assist-s7",
                    "uri": "http://127.0.0.1:8080/v1/ops-assist",
                    "method": "post",
                    "headers": {"Content-Type": "application/json"},
                    "req_template_json_object": {
                        "request_id": "garak-s7",
                        "requester": "garak-s7",
                        "question": "$INPUT",
                    },
                    "response_json": True,
                    "response_json_field": "answer",
                    "skip_codes": [403],
                    "ratelimit_codes": [429],
                    "request_timeout": 5,
                }
            }
        }
        _write_json(config, configuration)
        report = xdg_data / "garak" / "garak_runs" / "garak-s7.report.jsonl"
        environment = {
            "HOME": "/tmp",
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": PACKAGE_ROOT,
            "XDG_CONFIG_HOME": str(workspace / "config"),
            "XDG_DATA_HOME": str(xdg_data),
            "XDG_CACHE_HOME": str(workspace / "cache"),
        }
        server = ThreadingHTTPServer(("127.0.0.1", 8080), OpsAssistHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "app.garak_worker", str(config), "--limit", str(limit)],
                check=False,
                cwd="/tmp",
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=RUN_TIMEOUT_SECONDS,
            )
            if completed.returncode != 0:
                raise CampaignError("garak_execution_failed")
            result = _read_report(report, limit)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise CampaignError("garak_execution_failed") from error
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
    passed, total = result["passed"], result["total"]
    summary = {
        "format_version": 1,
        "garak_version": GARAK_VERSION,
        "probe": PROBE,
        "prompts": limit,
        "full": limit == EXPECTED_PROMPTS,
        "passed": passed,
        "total": total,
        "report_sha256": result["report_sha256"],
        "config_sha256": hashlib.sha256(json.dumps(configuration, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "result": "PASS" if passed == total else "FAIL",
    }
    _write_json(ARTIFACTS / SUMMARY_NAME, summary)
    return summary


def main() -> None:
    summary = run()
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
