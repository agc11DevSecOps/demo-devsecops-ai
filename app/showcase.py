"""Create and serve validated, local-only visual assurance bundles."""

from __future__ import annotations

import hashlib
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

from app.common import EVIDENCE, ROOT, SANDBOX, sha256


SHOWCASE_ROOT = ROOT / "record" / "showcase-runs"
ASSET_ROOT = ROOT / "showcase"
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
NONCE = re.compile(r"^[A-Za-z0-9-]{8,48}$")
HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
EVENT_KEYS = frozenset({"format_version", "timestamp", "run", "scenario", "control", "decision", "reason", "label", "input_sha256", "aisvs_ids"})
ALLOWED_FILES = frozenset({"index.html", "app.js", "style.css", "manifest.json", "observations.json", "dossier.json", "challenge.json", "trace.json", "response.json", "replay.json"})
VISUAL_EVENT_KEYS = frozenset({"format_version", "timestamp", "run", "scenario", "control", "decision", "label", "reason", "input_sha256", "aisvs_ids", "observation_kind", "details", "event_sha256"})
MAX_EVENTS = 256
MAX_TEXT = 4_096


class ShowcaseError(ValueError):
    """A bounded, non-sensitive showcase error suitable for a CLI message."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


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
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


# Source evidence validation: display data is never trusted without this contract.
def _validate_event(record: Any, run: str) -> dict[str, Any]:
    if type(record) is not dict or set(record) != EVENT_KEYS:
        raise ShowcaseError("invalid_evidence_record")
    if record.get("format_version") != 1 or record.get("run") != run:
        raise ShowcaseError("invalid_evidence_record")
    if not all(isinstance(record.get(key), str) and len(record[key]) <= MAX_TEXT for key in ("timestamp", "scenario", "control", "decision", "reason", "label", "input_sha256")):
        raise ShowcaseError("invalid_evidence_record")
    if HEX_DIGEST.fullmatch(record["input_sha256"]) is None:
        raise ShowcaseError("invalid_evidence_record")
    if type(record["aisvs_ids"]) is not list or not all(isinstance(item, str) and len(item) <= 32 for item in record["aisvs_ids"]):
        raise ShowcaseError("invalid_evidence_record")
    return record


def _load_events(run: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    directory = EVIDENCE / run
    paths = sorted(directory.glob("*.jsonl"))
    if not paths:
        raise ShowcaseError(f"missing_evidence_{run.lower()}")
    events: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}
    for path in paths:
        hashes[f"{run}/{path.name}"] = _hash_file(path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise ShowcaseError("invalid_evidence_record") from error
        for line in lines:
            try:
                events.append(_validate_event(json.loads(line), run))
            except json.JSONDecodeError as error:
                raise ShowcaseError("invalid_evidence_record") from error
    if not events or len(events) > MAX_EVENTS:
        raise ShowcaseError("invalid_evidence_count")
    return events, hashes


def _validate_visual_value(value: Any, *, depth: int = 0) -> None:
    if depth > 4:
        raise ShowcaseError("invalid_visual_evidence")
    if value is None or type(value) in {bool, int}:
        return
    if isinstance(value, str):
        if len(value) > MAX_TEXT:
            raise ShowcaseError("invalid_visual_evidence")
        return
    if type(value) is list:
        if len(value) > 32:
            raise ShowcaseError("invalid_visual_evidence")
        for item in value:
            _validate_visual_value(item, depth=depth + 1)
        return
    if type(value) is dict:
        if len(value) > 24 or any(not isinstance(key, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,47}", key) is None for key in value):
            raise ShowcaseError("invalid_visual_evidence")
        for item in value.values():
            _validate_visual_value(item, depth=depth + 1)
        return
    raise ShowcaseError("invalid_visual_evidence")


def _load_visual_events(run: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    directory = EVIDENCE / "visual" / run
    paths = sorted(directory.glob("*.jsonl"))
    if not paths:
        return []
    source_hashes = {sha256(json.dumps(event, sort_keys=True, separators=(",", ":"))) for event in events}
    visual: list[dict[str, Any]] = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise ShowcaseError("invalid_visual_evidence") from error
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ShowcaseError("invalid_visual_evidence") from error
            if type(record) is not dict or set(record) != VISUAL_EVENT_KEYS or record.get("format_version") != 1 or record.get("run") != run:
                raise ShowcaseError("invalid_visual_evidence")
            if not all(isinstance(record.get(key), str) and len(record[key]) <= MAX_TEXT for key in ("timestamp", "scenario", "control", "decision", "label", "reason", "input_sha256", "event_sha256")):
                raise ShowcaseError("invalid_visual_evidence")
            if HEX_DIGEST.fullmatch(record["input_sha256"]) is None or HEX_DIGEST.fullmatch(record["event_sha256"]) is None or record["event_sha256"] not in source_hashes:
                raise ShowcaseError("invalid_visual_evidence")
            if record.get("observation_kind") not in {"fixture", "observed"} or type(record.get("aisvs_ids")) is not list or type(record.get("details")) is not dict:
                raise ShowcaseError("invalid_visual_evidence")
            _validate_visual_value(record["details"])
            visual.append(record)
    if len(visual) > MAX_EVENTS:
        raise ShowcaseError("invalid_visual_evidence")
    return visual


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
    for filename in ("index.html", "app.js", "style.css"):
        source = ASSET_ROOT / filename
        if not source.is_file():
            raise ShowcaseError("showcase_assets_unavailable")
        shutil.copyfile(source, bundle / filename)


def _manifest(bundle: Path, *, source_evidence: dict[str, str]) -> dict[str, Any]:
    assets = {path.name: _hash_file(path) for path in sorted(bundle.iterdir()) if path.is_file() and path.name != "manifest.json"}
    return {
        "format_version": 1,
        "created_at": _utcnow(),
        "source_evidence_sha256": source_evidence,
        "assets_sha256": assets,
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
def verify_bundle(run_id: str) -> None:
    """Verify every declared non-manifest asset before exposing a bundle."""
    bundle = _bundle_dir(run_id)
    manifest = _read_json(bundle / "manifest.json")
    if manifest.get("format_version") != 1 or type(manifest.get("assets_sha256")) is not dict:
        raise ShowcaseError("invalid_showcase_manifest")
    declared = manifest["assets_sha256"]
    if not declared or "manifest.json" in declared or set(declared) - ALLOWED_FILES:
        raise ShowcaseError("invalid_showcase_manifest")
    for filename, digest in declared.items():
        if not isinstance(filename, str) or not isinstance(digest, str) or HEX_DIGEST.fullmatch(digest) is None:
            raise ShowcaseError("invalid_showcase_manifest")
        path = bundle / filename
        if not path.is_file() or _hash_file(path) != digest:
            raise ShowcaseError("showcase_bundle_tampered")


class _ShowcaseHandler(BaseHTTPRequestHandler):
    """Serve only predeclared static bundle assets from loopback."""

    server_version = "VisualAssurance/1"
    sys_version = ""
    bundle: Path

    def do_GET(self) -> None:  # noqa: N802
        requested = self.path.split("?", 1)[0]
        filename = "index.html" if requested == "/" else requested.removeprefix("/")
        if filename not in ALLOWED_FILES or "/" in filename or "\\" in filename:
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain; charset=utf-8")
            return
        path = self.bundle / filename
        if not path.is_file():
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain; charset=utf-8")
            return
        content_type = "application/json" if filename.endswith(".json") else "text/javascript" if filename.endswith(".js") else "text/css" if filename.endswith(".css") else "text/html; charset=utf-8"
        self._send(HTTPStatus.OK, path.read_bytes(), content_type)

    def do_POST(self) -> None:  # noqa: N802
        self._send(HTTPStatus.METHOD_NOT_ALLOWED, b"method not allowed", "text/plain; charset=utf-8")

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'; connect-src 'self'; img-src 'none'; script-src 'self'; style-src 'self'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)


def serve_bundle(run_id: str, port: int = 8090) -> None:
    if not isinstance(port, int) or not 1024 <= port <= 65535:
        raise ShowcaseError("invalid_showcase_port")
    verify_bundle(run_id)
    handler = type("ShowcaseHandler", (_ShowcaseHandler,), {"bundle": _bundle_dir(run_id)})
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        server.serve_forever()


class _LiveShowcaseHandler(BaseHTTPRequestHandler):
    """Expose fixed UI assets and a validated, read-only evidence view."""

    server_version = "VisualAssuranceLive/1"
    sys_version = ""
    static_files = {"/": "live.html", "/live.js": "live.js", "/style.css": "style.css"}

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/live/observations.json":
            try:
                body = _canonical_json(_live_observations())
            except ShowcaseError:
                self._send(HTTPStatus.SERVICE_UNAVAILABLE, b'{"code":"evidence_unavailable"}', "application/json")
                return
            self._send(HTTPStatus.OK, body, "application/json")
            return
        filename = self.static_files.get(path)
        if filename is None:
            self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain; charset=utf-8")
            return
        asset = ASSET_ROOT / filename
        if not asset.is_file():
            self._send(HTTPStatus.SERVICE_UNAVAILABLE, b"assets unavailable", "text/plain; charset=utf-8")
            return
        content_type = "text/javascript" if filename.endswith(".js") else "text/css" if filename.endswith(".css") else "text/html; charset=utf-8"
        self._send(HTTPStatus.OK, asset.read_bytes(), content_type)

    def do_POST(self) -> None:  # noqa: N802
        self._send(HTTPStatus.METHOD_NOT_ALLOWED, b"method not allowed", "text/plain; charset=utf-8")

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'; connect-src 'self'; img-src 'none'; script-src 'self'; style-src 'self'")
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
