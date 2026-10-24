"""Validated access to the authoritative and visual evidence ledgers.

The authoritative record stores input hashes only. The visual record is a
separate, bounded channel bound to its authoritative event by ``event_sha256``.
Nothing here grants authority: every record is untrusted input until it passes
this contract.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.common import EVIDENCE, sha256

RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
EVENT_KEYS = frozenset({"format_version", "timestamp", "run", "scenario", "control", "decision", "reason", "label", "input_sha256", "aisvs_ids"})
VISUAL_EVENT_KEYS = frozenset({"format_version", "timestamp", "run", "scenario", "control", "decision", "label", "reason", "input_sha256", "aisvs_ids", "observation_kind", "details", "event_sha256"})
MAX_EVENTS = 512
MAX_TEXT = 4_096


class LedgerError(ValueError):
    """A bounded, non-sensitive ledger error suitable for a CLI message."""


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(event: dict[str, Any]) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"))


def validate_event(record: Any, run: str) -> dict[str, Any]:
    if type(record) is not dict or set(record) != EVENT_KEYS:
        raise LedgerError("invalid_evidence_record")
    if record.get("format_version") != 1 or record.get("run") != run:
        raise LedgerError("invalid_evidence_record")
    if not all(isinstance(record.get(key), str) and len(record[key]) <= MAX_TEXT for key in ("timestamp", "scenario", "control", "decision", "reason", "label", "input_sha256")):
        raise LedgerError("invalid_evidence_record")
    if HEX_DIGEST.fullmatch(record["input_sha256"]) is None:
        raise LedgerError("invalid_evidence_record")
    if type(record["aisvs_ids"]) is not list or not all(isinstance(item, str) and len(item) <= 32 for item in record["aisvs_ids"]):
        raise LedgerError("invalid_evidence_record")
    return record


def load_events(run: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    directory = EVIDENCE / run
    paths = sorted(directory.glob("*.jsonl"))
    if not paths:
        raise LedgerError(f"missing_evidence_{run.lower()}")
    events: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}
    for path in paths:
        hashes[f"{run}/{path.name}"] = hash_file(path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise LedgerError("invalid_evidence_record") from error
        for line in lines:
            try:
                events.append(validate_event(json.loads(line), run))
            except json.JSONDecodeError as error:
                raise LedgerError("invalid_evidence_record") from error
    if not events or len(events) > MAX_EVENTS:
        raise LedgerError("invalid_evidence_count")
    return events, hashes


def validate_visual_value(value: Any, *, depth: int = 0) -> None:
    if depth > 5:
        raise LedgerError("invalid_visual_evidence")
    if value is None or type(value) in {bool, int}:
        return
    if isinstance(value, str):
        if len(value) > MAX_TEXT:
            raise LedgerError("invalid_visual_evidence")
        return
    if type(value) is list:
        if len(value) > 48:
            raise LedgerError("invalid_visual_evidence")
        for item in value:
            validate_visual_value(item, depth=depth + 1)
        return
    if type(value) is dict:
        if len(value) > 32 or any(not isinstance(key, str) or re.fullmatch(r"[a-z][a-z0-9_]{0,47}", key) is None for key in value):
            raise LedgerError("invalid_visual_evidence")
        for item in value.values():
            validate_visual_value(item, depth=depth + 1)
        return
    raise LedgerError("invalid_visual_evidence")


def load_visual_events(run: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    directory = EVIDENCE / "visual" / run
    paths = sorted(directory.glob("*.jsonl"))
    if not paths:
        return []
    source_hashes = {sha256(canonical(event)) for event in events}
    visual: list[dict[str, Any]] = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise LedgerError("invalid_visual_evidence") from error
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise LedgerError("invalid_visual_evidence") from error
            if type(record) is not dict or set(record) != VISUAL_EVENT_KEYS or record.get("format_version") != 1 or record.get("run") != run:
                raise LedgerError("invalid_visual_evidence")
            if not all(isinstance(record.get(key), str) and len(record[key]) <= MAX_TEXT for key in ("timestamp", "scenario", "control", "decision", "label", "reason", "input_sha256", "event_sha256")):
                raise LedgerError("invalid_visual_evidence")
            if HEX_DIGEST.fullmatch(record["input_sha256"]) is None or HEX_DIGEST.fullmatch(record["event_sha256"]) is None or record["event_sha256"] not in source_hashes:
                raise LedgerError("invalid_visual_evidence")
            if record.get("observation_kind") not in {"fixture", "observed"} or type(record.get("aisvs_ids")) is not list or type(record.get("details")) is not dict:
                raise LedgerError("invalid_visual_evidence")
            validate_visual_value(record["details"])
            visual.append(record)
    if len(visual) > MAX_EVENTS:
        raise LedgerError("invalid_visual_evidence")
    return visual


def bound_visuals(run: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return authoritative events and the visuals bound to them by digest."""
    try:
        events, _ = load_events(run)
        visuals = load_visual_events(run, events)
    except LedgerError:
        return [], {}
    by_hash = {sha256(canonical(event)): event for event in events}
    bound: dict[str, dict[str, Any]] = {}
    for visual in visuals:
        event = by_hash.get(visual.get("event_sha256", ""))
        if event is None:
            continue
        if event.get("run") != run or event.get("scenario") != visual.get("scenario") or event.get("control") != visual.get("control"):
            continue
        bound[visual["event_sha256"]] = {"event": event, "visual": visual}
    return events, bound


def visual_for(bound: dict[str, dict[str, Any]], event: dict[str, Any] | None) -> dict[str, Any] | None:
    if event is None:
        return None
    return bound.get(sha256(canonical(event)), {}).get("visual")
