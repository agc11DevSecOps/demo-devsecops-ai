"""Create and serve validated, local-only visual assurance bundles."""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app.common import ARTIFACTS, EVIDENCE, ROOT, SANDBOX, sha256
from app.ledger import (
    HEX_DIGEST,
    LedgerError,
    bound_visuals,
    hash_file,
    load_events as _ledger_load_events,
    load_visual_events as _ledger_load_visual_events,
    visual_for,
)
from app.presentation import DIAGRAMS, build_projection, diagram_path

SHOWCASE_ROOT = ROOT / "record" / "showcase-runs"
ASSET_ROOT = ROOT / "showcase"
INSPECT_VIEW = ARTIFACTS / "inspect-view"
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
NONCE = re.compile(r"^[A-Za-z0-9-]{8,48}$")
# The first three names are legacy audit assets retained in bundles frozen
# before the recorded viewer replaced the old dashboard. New bundles do not
# copy them; the allow-list only keeps old bundles verifiable.
ALLOWED_EXACT = frozenset({
    "index.html", "app.js", "style.css",
    "present.html", "present.js", "present.css",
    "manifest.json", "observations.json", "dossier.json", "challenge.json", "trace.json",
    "response.json", "replay.json", "presentation.json", "recording.json",
}) | frozenset(f"diagram-{name}.svg" for name in DIAGRAMS)
ALLOWED_PREFIXES = ("inspect/",)
ASSET_FILES = {"present.html": "present.html", "present.js": "present.js", "present.css": "present.css"}
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript",
    ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml",
    ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".map": "application/json",
    ".png": "image/png", ".ico": "image/x-icon",
}
STRICT_CSP = "default-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'; connect-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'; worker-src 'self'"
VIEWER_CSP_FILE = "content-security-policy.json"
MAX_VIEW_FILE = 64 * 1024 * 1024


class ShowcaseError(ValueError):
    """A bounded, non-sensitive showcase error suitable for a CLI message."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or RUN_ID.fullmatch(run_id) is None:
        raise ShowcaseError("invalid_showcase_run_id")
    return run_id


def _bundle_dir(run_id: str) -> Path:
    safe_id = _validate_run_id(run_id)
    root = SHOWCASE_ROOT.resolve()
    candidate = (root / safe_id).resolve()
    if root not in candidate.parents:
        raise ShowcaseError("showcase_path_escape")
    return candidate


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ShowcaseError("invalid_showcase_json") from error
    if type(value) is not dict:
        raise ShowcaseError("invalid_showcase_json")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


# Ledger wrappers: keep the historical private names for existing callers/tests.
def _load_events(run: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    try:
        return _ledger_load_events(run)
    except LedgerError as error:
        raise ShowcaseError(str(error)) from error


def _load_visual_events(run: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        return _ledger_load_visual_events(run, events)
    except LedgerError as error:
        raise ShowcaseError(str(error)) from error


def _live_observations() -> dict[str, Any]:
    """Return only validated evidence currently available for the live display."""
    runs: dict[str, list[dict[str, Any]]] = {}
    visual_runs: dict[str, list[dict[str, Any]]] = {}
    for run in ("A", "B"):
        try:
            runs[run], _ = _load_events(run)
            visual_runs[run] = _load_visual_events(run, runs[run])
        except ShowcaseError as error:
            if str(error) == f"missing_evidence_{run.lower()}":
                runs[run] = []
                visual_runs[run] = []
            else:
                raise
    return {"format_version": 1, "generated_at": _utcnow(), "runs": runs, "visual_runs": visual_runs}


# Immutable bundle construction: snapshot only validated data and fixed assets.
def _copy_assets(bundle: Path) -> None:
    for filename, source_name in ASSET_FILES.items():
        source = ASSET_ROOT / source_name
        if not source.is_file():
            raise ShowcaseError("showcase_assets_unavailable")
        shutil.copyfile(source, bundle / filename)
    for name in DIAGRAMS:
        source = diagram_path(name)
        if source is None:
            raise ShowcaseError("showcase_diagram_unavailable")
        shutil.copyfile(source, bundle / f"diagram-{name}.svg")


def _copy_inspect_view(bundle: Path) -> None:
    """Copy the scanned Inspect View bundle when the live evaluation produced one."""
    if not INSPECT_VIEW.is_dir():
        return
    target = bundle / "inspect"
    shutil.copytree(INSPECT_VIEW, target)
    for path in target.rglob("*"):
        if path.is_symlink():
            raise ShowcaseError("showcase_inspect_symlink")
        if path.is_file() and path.stat().st_size > MAX_VIEW_FILE:
            raise ShowcaseError("showcase_inspect_oversized")


def _bundle_files(bundle: Path) -> dict[str, str]:
    return {
        str(path.relative_to(bundle)): hash_file(path)
        for path in sorted(bundle.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }


def _manifest(bundle: Path, *, source_evidence: dict[str, str]) -> dict[str, Any]:
    return {
        "format_version": 1,
        "created_at": _utcnow(),
        "source_evidence_sha256": source_evidence,
        "assets_sha256": _bundle_files(bundle),
    }


def _write_manifest(bundle: Path, *, source_evidence: dict[str, str]) -> None:
    _write_json(bundle / "manifest.json", _manifest(bundle, source_evidence=source_evidence))


def create_bundle(run_id: str | None = None) -> str:
    """Snapshot validated A/B evidence into a new static bundle."""
    run_id = run_id or f"showcase-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    bundle = _bundle_dir(run_id)
    if bundle.exists():
        raise ShowcaseError("showcase_bundle_exists")
    events_a, hashes_a = _load_events("A")
    events_b, hashes_b = _load_events("B")
    visual_a = _load_visual_events("A", events_a)
    visual_b = _load_visual_events("B", events_b)
    bundle.mkdir(mode=0o700, parents=True)
    try:
        _write_json(bundle / "observations.json", {"format_version": 1, "generated_at": _utcnow(), "runs": {"A": events_a, "B": events_b}})
        _write_json(bundle / "dossier.json", {"format_version": 1, "generated_at": _utcnow(), "runs": {"A": visual_a, "B": visual_b}})
        _write_json(bundle / "presentation.json", build_projection())
        if (ARTIFACTS / "recording.json").is_file():
            shutil.copyfile(ARTIFACTS / "recording.json", bundle / "recording.json")
        _copy_inspect_view(bundle)
        _copy_assets(bundle)
        _write_manifest(bundle, source_evidence={**hashes_a, **hashes_b})
    except Exception:
        shutil.rmtree(bundle, ignore_errors=True)
        raise
    return run_id


# Optional local-model challenge: accept only the fixed synthetic nonce contract.
def _load_challenge(bundle: Path) -> dict[str, Any]:
    challenge = _read_json(bundle / "challenge.json")
    if set(challenge) != {"format_version", "created_at", "nonce", "question", "source_document_sha256"} or challenge.get("format_version") != 1:
        raise ShowcaseError("invalid_challenge")
    nonce = challenge.get("nonce")
    question = challenge.get("question")
    digest = challenge.get("source_document_sha256")
    if not isinstance(nonce, str) or NONCE.fullmatch(nonce) is None or question != _question(nonce) or not isinstance(digest, str) or digest != sha256(_source_document(nonce)):
        raise ShowcaseError("invalid_challenge")
    return challenge


def _question(nonce: str) -> str:
    return f"What is the approved showcase token {nonce}?"


def _source_document(nonce: str) -> str:
    return f"Approved showcase token: {nonce}\nThis is a synthetic, ephemeral RAG challenge source.\n"


def _write_challenge_source(nonce: str) -> None:
    root = SANDBOX.resolve()
    path = SANDBOX / "showcase-challenge.txt"
    if path.parent.resolve() != root:
        raise ShowcaseError("challenge_source_path_escape")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(_source_document(nonce))
    except OSError as error:
        raise ShowcaseError("challenge_source_write_failed") from error


def create_challenge(run_id: str, nonce: str | None = None) -> str:
    """Create a synthetic nonce source without accepting arbitrary document text."""
    bundle = _bundle_dir(run_id)
    if not bundle.is_dir():
        raise ShowcaseError("showcase_bundle_missing")
    if (bundle / "challenge.json").exists():
        raise ShowcaseError("showcase_challenge_exists")
    nonce = nonce or secrets.token_hex(8)
    if not isinstance(nonce, str) or NONCE.fullmatch(nonce) is None:
        raise ShowcaseError("invalid_showcase_nonce")
    document = _source_document(nonce)
    challenge = {
        "format_version": 1,
        "created_at": _utcnow(),
        "nonce": nonce,
        "question": _question(nonce),
        "source_document_sha256": sha256(document),
    }
    _write_json(bundle / "challenge.json", challenge)
    _write_manifest(bundle, source_evidence=_read_json(bundle / "manifest.json").get("source_evidence_sha256", {}))
    return nonce


def _trace_payload(trace: Any) -> dict[str, Any]:
    payload = trace.payload()
    if payload.get("format_version") != 1 or payload.get("mode") != "local":
        raise ShowcaseError("invalid_generation_trace")
    return payload


def run_challenge(run_id: str) -> str:
    """Run the challenge exclusively through the verified local workload."""
    bundle = _bundle_dir(run_id)
    challenge = _load_challenge(bundle)
    _write_challenge_source(challenge["nonce"])
    from app.workload import GenerationTrace, WorkloadError, assist

    trace = GenerationTrace()
    try:
        response = assist({"request_id": "showcase-nonce", "requester": "showcase", "question": challenge["question"]}, mode="local", trace=trace, challenge=True)
    except WorkloadError as error:
        raise ShowcaseError(error.code) from error
    result = {
        "format_version": 1,
        "decision": response.decision,
        "label": response.label,
        "model": response.model,
        "answer": response.answer,
        "answer_sha256": sha256(response.answer),
        "citations": [citation.source_id for citation in response.citations],
        "nonce_match": response.answer.strip() == challenge["nonce"],
    }
    _write_json(bundle / "trace.json", _trace_payload(trace))
    _write_json(bundle / "response.json", result)
    _write_manifest(bundle, source_evidence=_read_json(bundle / "manifest.json").get("source_evidence_sha256", {}))
    return "MATCH" if result["nonce_match"] else "MISMATCH"


def replay_challenge(run_id: str) -> str:
    """Repeat local inference and compare the actual deterministic trace."""
    bundle = _bundle_dir(run_id)
    challenge = _load_challenge(bundle)
    expected = _read_json(bundle / "trace.json")
    _write_challenge_source(challenge["nonce"])
    from app.workload import GenerationTrace, WorkloadError, assist

    trace = GenerationTrace()
    try:
        response = assist({"request_id": "showcase-replay", "requester": "showcase-replay", "question": challenge["question"]}, mode="local", trace=trace, challenge=True)
    except WorkloadError as error:
        raise ShowcaseError(error.code) from error
    actual = _trace_payload(trace)
    fields = ("model", "prompt_sha256", "source_digests", "input_token_ids", "output_token_ids", "raw_output_sha256", "validated_output_sha256")
    matched = all(expected.get(field) == actual.get(field) for field in fields)
    replay = {
        "format_version": 1,
        "replayed_at": _utcnow(),
        "status": "MATCH" if matched else "MISMATCH",
        "compared_fields": list(fields),
        "answer_sha256": sha256(response.answer),
        "trace": actual,
    }
    _write_json(bundle / "replay.json", replay)
    _write_manifest(bundle, source_evidence=_read_json(bundle / "manifest.json").get("source_evidence_sha256", {}))
    return replay["status"]


# Read-only serving: verify every declared asset before exposing it on loopback.
def _allowed(name: str) -> bool:
    if name in ALLOWED_EXACT:
        return True
    return any(name.startswith(prefix) and ".." not in name and "\\" not in name for prefix in ALLOWED_PREFIXES)


def verify_bundle(run_id: str, *, require_complete: bool = False) -> None:
    """Verify every declared non-manifest asset before exposing a bundle."""
    bundle = _bundle_dir(run_id)
    manifest = _read_json(bundle / "manifest.json")
    if manifest.get("format_version") != 1 or type(manifest.get("assets_sha256")) is not dict:
        raise ShowcaseError("invalid_showcase_manifest")
    declared = manifest["assets_sha256"]
    if not declared or "manifest.json" in declared:
        raise ShowcaseError("invalid_showcase_manifest")
    for filename, digest in declared.items():
        if not isinstance(filename, str) or not isinstance(digest, str) or HEX_DIGEST.fullmatch(digest) is None:
            raise ShowcaseError("invalid_showcase_manifest")
        if not _allowed(filename):
            raise ShowcaseError("invalid_showcase_manifest")
        path = bundle / filename
        if not path.is_file() or hash_file(path) != digest:
            raise ShowcaseError("showcase_bundle_tampered")
    if require_complete:
        presentation = _read_json(bundle / "presentation.json")
        if presentation.get("phase") != "complete":
            raise ShowcaseError("showcase_bundle_incomplete")


def _viewer_csp(bundle: Path) -> str:
    """Read the Content-Security-Policy shipped with the Inspect View dist."""
    path = bundle / "inspect" / VIEWER_CSP_FILE
    if not path.is_file():
        return STRICT_CSP
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return STRICT_CSP
    if type(payload) is not dict or payload.get("version") != 1 or type(payload.get("directives")) is not dict:
        return STRICT_CSP
    parts = []
    for name, sources in payload["directives"].items():
        if name == "frame-ancestors" or not isinstance(name, str) or not isinstance(sources, list):
            continue
        if any(not isinstance(source, str) or not source or any(not 0x21 <= ord(char) <= 0x7E or char in ";," for char in source) for source in sources):
            return STRICT_CSP
        parts.append(" ".join([name, *sources]))
    if not parts:
        return STRICT_CSP
    parts.append("frame-ancestors 'none'")
    return "; ".join(parts)


class _ShowcaseHandler(BaseHTTPRequestHandler):
    """Serve only predeclared static bundle assets from loopback."""

    server_version = "VisualAssurance/1"
    sys_version = ""
    bundle: Path
    csp: str = STRICT_CSP

    def do_GET(self) -> None:  # noqa: N802
        requested = self.path.split("?", 1)[0]
        filename = "present.html" if requested == "/" else requested.removeprefix("/")
        if not _allowed(filename) or ".." in filename or "\\" in filename:
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain; charset=utf-8")
            return
        path = self.bundle / filename
        if not path.is_file():
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain; charset=utf-8")
            return
        content_type = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        csp = _viewer_csp(self.bundle) if filename.startswith("inspect/") else self.csp
        self._send(HTTPStatus.OK, path.read_bytes(), content_type, csp)

    def do_POST(self) -> None:  # noqa: N802
        self._send(HTTPStatus.METHOD_NOT_ALLOWED, b"method not allowed", "text/plain; charset=utf-8")

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _send(self, status: HTTPStatus, body: bytes, content_type: str, csp: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", csp or self.csp)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)


def serve_bundle(run_id: str, port: int = 8090, *, require_complete: bool = False) -> None:
    if not isinstance(port, int) or not 1024 <= port <= 65535:
        raise ShowcaseError("invalid_showcase_port")
    verify_bundle(run_id, require_complete=require_complete)
    bundle = _bundle_dir(run_id)
    handler = type("ShowcaseHandler", (_ShowcaseHandler,), {"bundle": bundle, "csp": _viewer_csp(bundle)})
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"Recorded presentation: http://127.0.0.1:{server.server_address[1]}/ (read-only; Ctrl-C to stop)", flush=True)
        server.serve_forever()


class _LiveShowcaseHandler(BaseHTTPRequestHandler):
    """Expose fixed UI assets and a validated, read-only evidence view."""

    server_version = "VisualAssuranceLive/1"
    sys_version = ""
    static_files = {
        "/": "present.html", "/present.js": "present.js", "/present.css": "present.css",
    }

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in {"/live/observations.json"}:
            try:
                body = _canonical_json(_live_observations())
            except ShowcaseError:
                self._send(HTTPStatus.SERVICE_UNAVAILABLE, b'{"code":"evidence_unavailable"}', "application/json")
                return
            self._send(HTTPStatus.OK, body, "application/json")
            return
        if path in {"/presentation.json", "/live/presentation.json"}:
            try:
                body = _canonical_json(build_projection())
            except ShowcaseError:
                self._send(HTTPStatus.SERVICE_UNAVAILABLE, b'{"code":"presentation_unavailable"}', "application/json")
                return
            self._send(HTTPStatus.OK, body, "application/json")
            return
        if path.startswith("/diagram-") and path.endswith(".svg"):
            name = path.removeprefix("/diagram-").removesuffix(".svg")
            asset = diagram_path(name)
            if asset is None:
                self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain; charset=utf-8")
                return
            self._send(HTTPStatus.OK, asset.read_bytes(), "image/svg+xml")
            return
        if path.startswith("/inspect/"):
            name = path.removeprefix("/inspect/")
            target = (INSPECT_VIEW / name).resolve()
            if INSPECT_VIEW.resolve() not in target.parents or not target.is_file():
                self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain; charset=utf-8")
                return
            self._send(HTTPStatus.OK, target.read_bytes(), CONTENT_TYPES.get(target.suffix.lower(), "application/octet-stream"), _viewer_csp(INSPECT_VIEW))
            return
        filename = self.static_files.get(path)
        if filename is None:
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain; charset=utf-8")
            return
        asset = ASSET_ROOT / filename
        if not asset.is_file():
            self._send(HTTPStatus.SERVICE_UNAVAILABLE, b"assets unavailable", "text/plain; charset=utf-8")
            return
        self._send(HTTPStatus.OK, asset.read_bytes(), CONTENT_TYPES.get(asset.suffix.lower(), "application/octet-stream"))

    def do_POST(self) -> None:  # noqa: N802
        self._send(HTTPStatus.METHOD_NOT_ALLOWED, b"method not allowed", "text/plain; charset=utf-8")

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _send(self, status: HTTPStatus, body: bytes, content_type: str, csp: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", csp or STRICT_CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)


def _canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def serve_live(port: int = 8091) -> None:
    """Serve the read-only live evidence display only on loopback."""
    if not isinstance(port, int) or not 1024 <= port <= 65535:
        raise ShowcaseError("invalid_showcase_port")
    with ThreadingHTTPServer(("127.0.0.1", port), _LiveShowcaseHandler) as server:
        actual_port = server.server_address[1]
        print(f"Visual Assurance Live: http://127.0.0.1:{actual_port}/ (read-only; Ctrl-C to stop)", flush=True)
        server.serve_forever()
