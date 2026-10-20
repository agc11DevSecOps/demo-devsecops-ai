"""Write bounded AISVS and display evidence without granting any authority.

The AISVS record is the scorecard source of truth and stores input hashes only.
The separate visual record contains bounded, synthetic display values and binds
back to the exact AISVS record with a SHA-256 digest.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.common import AISVS_ID, EVIDENCE, LABELS, VISUAL_EVIDENCE, sha256


@dataclass(frozen=True)
class Event:
    """A single scenario observation that can be verified independently."""

    run: str
    scenario: str
    control: str
    decision: str
    reason: str
    aisvs_ids: tuple[str, ...]
    label: str = "MEASURED"
    input_value: str = ""
    visual: dict[str, Any] | None = None

    def record(self) -> dict[str, Any]:
        if self.run not in {"A", "B"}:
            raise ValueError("invalid_run")
        if self.label not in LABELS:
            raise ValueError("invalid_label")
        if any(AISVS_ID.fullmatch(item) is None for item in self.aisvs_ids):
            raise ValueError("invalid_aisvs_id")
        return {
            "format_version": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run": self.run,
            "scenario": self.scenario,
            "control": self.control,
            "decision": self.decision,
            "reason": self.reason,
            "label": self.label,
            "input_sha256": sha256(self.input_value),
            "aisvs_ids": list(self.aisvs_ids),
        }

    def verdict(self) -> str:
        ids = ",".join(item.removeprefix("v1.01-") for item in self.aisvs_ids) or "n/a"
        return f"[{self.run}] [{self.scenario}] [{self.label}] {self.control} -> {self.decision} :: {self.reason} (AISVS {ids})"


class EvidenceWriter:
    """Append a hash-only scorecard event and its separately bounded visual view."""

    def emit(self, event: Event) -> None:
        record = event.record()
        path = EVIDENCE / event.run / f"{event.scenario.lower()}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        self._emit_visual(event, record)
        print(event.verdict())

    # The browser receives only this constrained channel, never arbitrary logs.
    def _emit_visual(self, event: Event, record: dict[str, Any]) -> None:
        payload = visual_value(event.visual) if event.visual is not None else {
            "input": {"value": event.input_value},
            "control": {"name": event.control},
            "observation": {"decision": event.decision, "reason": event.reason},
            "state": {"decision": event.decision},
        }
        visual = {
            "format_version": 1,
            "timestamp": record["timestamp"],
            "run": event.run,
            "scenario": event.scenario,
            "control": event.control,
            "decision": event.decision,
            "label": event.label,
            "reason": event.reason,
            "input_sha256": record["input_sha256"],
            "aisvs_ids": record["aisvs_ids"],
            "observation_kind": "fixture" if event.label in {"SCRIPTED", "DESIGNED"} else "observed",
            "details": payload,
            "event_sha256": sha256(json.dumps(record, sort_keys=True, separators=(",", ":"))),
        }
        path = VISUAL_EVIDENCE / event.run / f"{event.scenario.lower()}.jsonl"
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(visual, sort_keys=True, separators=(",", ":")) + "\n")


_VISUAL_KEY = re.compile(r"^[a-z][a-z0-9_]{0,47}$")


def visual_value(value: Any, *, depth: int = 0) -> Any:
    """Accept JSON display values with strict type, size, and depth limits."""
    if depth > 4:
        raise ValueError("visual_depth")
    if value is None or type(value) in {bool, int}:
        return value
    if isinstance(value, str):
        if len(value) > 4_096:
            raise ValueError("visual_text_too_long")
        return value
    if isinstance(value, list):
        if len(value) > 32:
            raise ValueError("visual_list_too_long")
        return [visual_value(item, depth=depth + 1) for item in value]
    if type(value) is dict:
        if len(value) > 24 or any(type(key) is not str or _VISUAL_KEY.fullmatch(key) is None for key in value):
            raise ValueError("visual_object_invalid")
        return {key: visual_value(item, depth=depth + 1) for key, item in value.items()}
    raise ValueError("visual_type_invalid")
