"""Thin FastAPI gateway over the bounded Ops Assist workload.

The gateway is a transport adapter only: it validates the HTTP envelope, applies
a constant-time optional bearer token, forwards the request to
:func:`app.workload.handle_payload` and never turns model output into an
authorization decision. It binds to loopback by default and exposes no docs,
OpenAPI schema or CORS surface.
"""

from __future__ import annotations

import hmac
import json
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.workload import MAX_BODY_BYTES, handle_payload

SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}
_METRICS: dict[str, int] = {}


def _blocked(status_code: int, code: str) -> JSONResponse:
    return JSONResponse({"decision": "BLOCKED", "code": code}, status_code=status_code, headers=SECURITY_HEADERS)


def _authorized(request: Request) -> bool:
    token = os.environ.get("OPS_DEMO_GATEWAY_TOKEN")
    if not token:
        return True
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    return scheme.lower() == "bearer" and hmac.compare_digest(value, token)


def create_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/healthz")
    async def healthz() -> PlainTextResponse:
        return PlainTextResponse("ok", headers=SECURITY_HEADERS)

    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        lines = [f'ops_assist_gateway_requests_total{{outcome="{name}"}} {count}' for name, count in sorted(_METRICS.items())]
        return PlainTextResponse("\n".join(lines) + "\n", headers=SECURITY_HEADERS)

    @app.post("/chat")
    async def chat(request: Request) -> JSONResponse:
        if not _authorized(request):
            _bump("unauthorized")
            return _blocked(401, "unauthorized")
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            _bump("invalid_content_type")
            return _blocked(415, "invalid_content_type")
        length = request.headers.get("content-length")
        if length is None or not length.isdecimal() or int(length) > MAX_BODY_BYTES:
            _bump("invalid_body")
            return _blocked(400, "invalid_body")
        body = await request.body()
        if len(body) > MAX_BODY_BYTES:
            _bump("invalid_body")
            return _blocked(400, "invalid_body")
        try:
            payload: Any = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _bump("invalid_body")
            return _blocked(400, "invalid_body")
        status, response = handle_payload(payload)
        _bump(response.get("decision", "unknown").lower())
        return JSONResponse(response, status_code=int(status), headers=SECURITY_HEADERS)

    return app


def _bump(outcome: str) -> None:
    _METRICS[outcome] = _METRICS.get(outcome, 0) + 1


def serve() -> None:
    """Serve on loopback only; a production ingress and authenticator are out of scope."""
    import uvicorn

    host = os.environ.get("OPS_DEMO_GATEWAY_HOST", "127.0.0.1")
    port = int(os.environ.get("OPS_DEMO_GATEWAY_PORT", "8080"))
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")
