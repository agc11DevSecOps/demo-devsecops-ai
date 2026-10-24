"""Internal evaluation target for the live Inspect check.

The server accepts only the fixed synthetic samples from ``fixtures/eval`` with
their exact text, requires an ephemeral bearer token supplied through an
owner-only env file, bounds every request, resets its tmpfs sandbox before each
agent sample and returns bounded display fields without digests or the token.

It runs one side per path: ``/v1/eval/unguarded`` (the Run A lab) and
``/v1/eval/guarded`` (the enforced workload). Nothing here authorizes an action.
"""

from __future__ import annotations

import hmac
import json
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from app.flow import lab_cases
from app.sandbox import reset

MAX_BODY = 8_192
SIDES = {"unguarded", "guarded"}
CASES = {case_id: case for case_id, case in lab_cases().items()}
BY_QUESTION = {case["question"]: case for case in CASES.values()}
if len(BY_QUESTION) != len(CASES):
    raise RuntimeError("duplicate_eval_question")
_LOCK = threading.Lock()


class EvalTargetError(RuntimeError):
    """A bounded configuration error with no sensitive detail."""


def side_enabled(side: str) -> bool:
    if side == "unguarded":
        return os.environ.get("OPS_DEMO_UNGUARDED_LAB") == "1" and os.environ.get("OPS_DEMO_IN_CONTAINER") == "1"
    return os.environ.get("OPS_DEMO_WORKLOAD") == "1" and os.environ.get("OPS_DEMO_WORKLOAD_MODE") == "local"


def _reset_sandbox() -> None:
    reset(clear_evidence=False)


def run_side(side: str, case: dict[str, Any]) -> dict[str, Any]:
    """Run one fixed sample through one side and return bounded display fields."""
    if side not in SIDES:
        raise EvalTargetError("invalid_side")
    if not side_enabled(side):
        raise EvalTargetError(f"{side}_unavailable")
    if side == "unguarded":
        from app.unguarded import run_unguarded

        _reset_sandbox()
        result = run_unguarded(
            case["question"],
            corpus=case["corpus"],
            check=case["check"],
            agent=case["agent"],
            expected_source=case.get("expected_source", ""),
        )
        return {
            "format_version": 1,
            "side": side,
            "id": case["id"],
            "scenario": case["scenario"],
            "check": case["check"],
            "decision": "ALLOWED",
            "code": "",
            "output": result["output"],
            "withheld_output": "",
            "citations": result["model_citations"],
            "context_writers": [item["writer"] for item in result["context"]],
            "quarantined": [],
            "effects": [item["tool"] for item in result["effects"]],
            "outcome": result["outcome"],
            "outcome_reason": result["outcome_reason"],
            "trace": result["trace"],
        }
    from app.guarded import run_guarded

    _reset_sandbox()
    result = run_guarded(
        case["question"],
        corpus=case["corpus"],
        requester=f"eval-{case['id']}",
        request_id=f"eval-{case['id']}",
    )
    return {
        "format_version": 1,
        "side": side,
        "id": case["id"],
        "scenario": case["scenario"],
        "check": case["check"],
        "decision": result["decision"],
        "code": result.get("code", ""),
        "output": result.get("output", ""),
        "withheld_output": result.get("withheld_output", ""),
        "citations": result.get("citations", []),
        "context_writers": ["trusted"] if result["decision"] == "ALLOWED" else [],
        "quarantined": result.get("quarantined", []),
        "effects": [],
        "outcome": "",
        "outcome_reason": "",
        "trace": result["trace"],
    }


class _Handler(BaseHTTPRequestHandler):
    server_version = "EvalTarget/1"
    sys_version = ""
    token: str

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._send(HTTPStatus.OK, {"status": "ok"})
            return
        self._send(HTTPStatus.NOT_FOUND, {"code": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/v1/eval/unguarded", "/v1/eval/guarded"}:
            self._send(HTTPStatus.NOT_FOUND, {"code": "not_found"})
            return
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"code": "unauthorized"})
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._send(HTTPStatus.BAD_REQUEST, {"code": "invalid_content_type"})
            return
        length = self.headers.get("Content-Length")
        if length is None or not length.isdecimal() or int(length) > MAX_BODY:
            self._send(HTTPStatus.BAD_REQUEST, {"code": "invalid_body"})
            return
        try:
            payload = json.loads(self.rfile.read(int(length)).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send(HTTPStatus.BAD_REQUEST, {"code": "invalid_body"})
            return
        if type(payload) is not dict or set(payload) != {"input"} or not isinstance(payload["input"], str):
            self._send(HTTPStatus.BAD_REQUEST, {"code": "invalid_body"})
            return
        case = BY_QUESTION.get(payload["input"])
        if case is None:
            self._send(HTTPStatus.NOT_FOUND, {"code": "unknown_sample"})
            return
        side = self.path.rsplit("/", 1)[-1]
        try:
            with _LOCK:
                result = run_side(side, case)
        except EvalTargetError as error:
            self._send(HTTPStatus.SERVICE_UNAVAILABLE, {"code": str(error)})
            return
        except Exception:
            self._send(HTTPStatus.SERVICE_UNAVAILABLE, {"code": "evaluation_failed"})
            return
        self._send(HTTPStatus.OK, result)

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        scheme, _, value = header.partition(" ")
        return scheme.lower() == "bearer" and bool(self.token) and hmac.compare_digest(value, self.token)

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


def serve() -> None:
    """Run the evaluation target inside the internal Docker network."""
    token = os.environ.get("OPS_EVAL_TOKEN", "")
    if len(token) < 32:
        raise EvalTargetError("eval_token_unavailable")
    port_text = os.environ.get("OPS_EVAL_PORT", "8099")
    if not port_text.isdecimal() or not 1024 <= int(port_text) <= 65535:
        raise EvalTargetError("invalid_eval_port")
    if not side_enabled("unguarded") or not side_enabled("guarded"):
        raise EvalTargetError("eval_target_profile_incomplete")
    handler = type("EvalHandler", (_Handler,), {"token": token})
    server_class = type("EvalServer", (ThreadingHTTPServer,), {"request_queue_size": 128, "daemon_threads": True})
    with server_class(("0.0.0.0", int(port_text)), handler) as server:
        print(f"Evaluation target listening on :{int(port_text)}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    serve()
