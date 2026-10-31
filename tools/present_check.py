"""Render a verified showcase bundle in local Chrome and retain visual evidence.

This build-time checker accepts only a validated showcase run identifier. It
starts the repository's loopback-only server, checks every presentation deep
link for known rendering failures, and captures the rendered pages and SVGs.
It never executes a scenario, model, tool, or user-supplied browser command.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from app.common import ARTIFACTS, ROOT, sha256
from app.presentation import DIAGRAMS
from app.showcase import ShowcaseError, _validate_run_id, verify_bundle

CHROME = Path.home() / ".cache/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-linux64/chrome-headless-shell"
FORBIDDEN_DOM = ("[object HTML", "Diagram could not be loaded")
EXPECTED_TEXT = {
    ("S1", "payload"): "STACK_GLOBAL",
    ("S3", "after"): "IBAN_CODE",
    ("S4", "payload"): "SYSTEM NOTE",
}
STEPS = ("payload", "before", "control", "after", "result")


class PresentationCheckError(RuntimeError):
    """A deterministic local presentation check failure."""


def _port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_server(url: str) -> None:
    for _ in range(50):
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise PresentationCheckError("showcase_server_unavailable")


def _chrome(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    if not CHROME.is_file():
        raise PresentationCheckError("chrome_headless_shell_unavailable")
    return subprocess.run(
        [str(CHROME), "--headless", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=3000", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _dom(url: str) -> str:
    result = _chrome(["--dump-dom", url])
    if result.returncode != 0:
        raise PresentationCheckError("chrome_dom_failed")
    return result.stdout


def _assert_dom(dom: str, expected: str = "") -> None:
    if any(value in dom for value in FORBIDDEN_DOM):
        raise PresentationCheckError("presentation_dom_failure")
    if expected and expected not in dom:
        raise PresentationCheckError("presentation_expected_text_missing")


def _capture(url: str, output: Path) -> None:
    result = _chrome(["--window-size=1440,900", f"--screenshot={output}", url])
    if result.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise PresentationCheckError("chrome_screenshot_failed")


def _safe_name(*parts: str) -> str:
    return "-".join(part.lower().replace("_", "-") for part in parts)


def _write_receipt(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(run_id: str) -> Path:
    run_id = _validate_run_id(run_id)
    verify_bundle(run_id, require_complete=True)
    bundle = ROOT / "record" / "showcase-runs" / run_id
    projection = json.loads((bundle / "presentation.json").read_text(encoding="utf-8"))
    if type(projection.get("scenarios")) is not list:
        raise PresentationCheckError("presentation_projection_invalid")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ARTIFACTS / "present-check" / f"{run_id}-{timestamp}"
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    port = _port()
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        [sys.executable, "-m", "app.cli", "showcase-serve", "--showcase-run-id", run_id, "--port", str(port)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    checked: list[str] = []
    try:
        _wait_for_server(f"{base}/present.html")
        for card in projection["scenarios"]:
            scenario = card.get("scenario")
            if not isinstance(scenario, str):
                raise PresentationCheckError("presentation_scenario_invalid")
            for step in STEPS:
                url = f"{base}/present.html#{scenario}/{step}"
                expected = EXPECTED_TEXT.get((scenario, step), "")
                _assert_dom(_dom(url), expected)
                _capture(url, output / f"{_safe_name(scenario, step)}.png")
                checked.append(f"{scenario}/{step}")
        for name in DIAGRAMS:
            url = f"{base}/diagram-{name}.svg"
            _capture(url, output / f"diagram-{name}.png")
            checked.append(f"diagram/{name}")
        inspect = projection.get("inspect") if type(projection.get("inspect")) is dict else {}
        logs = inspect.get("logs") if type(inspect.get("logs")) is dict else {}
        samples = inspect.get("samples") if type(inspect.get("samples")) is list else []
        if inspect.get("view") and logs.get("guarded") and samples:
            sample_id = samples[0].get("id") if type(samples[0]) is dict else ""
            if not isinstance(sample_id, str) or not sample_id:
                raise PresentationCheckError("inspect_sample_invalid")
            inspect_url = f"{base}/{inspect['view']}#/logs/{logs['guarded']}/samples/sample/{sample_id}/1"
            _assert_dom(_dom(inspect_url), sample_id)
            _capture(inspect_url, output / "inspect-deep-link.png")
            checked.append(f"inspect/{sample_id}/1")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
    receipt = {
        "format_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": "tools/present_check.py",
        "chrome": str(CHROME),
        "bundle": run_id,
        "bundle_manifest_sha256": sha256((bundle / "manifest.json").read_text(encoding="utf-8")),
        "input_sensitivity": "synthetic, validated showcase bundle only",
        "result": "PASS",
        "checked": checked,
    }
    _write_receipt(output / "receipt.json", receipt)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--showcase-run-id", required=True)
    args = parser.parse_args()
    try:
        print(run(args.showcase_run_id))
    except (PresentationCheckError, ShowcaseError, OSError, ValueError) as error:
        print(f"presentation check failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
