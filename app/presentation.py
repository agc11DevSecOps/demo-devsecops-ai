"""Build the validated, digest-free presentation projection from A/B evidence.

The authoritative and visual ledgers remain the only evidence sources. For each
scenario this module selects the bound Run A and Run B records, projects only
known display fields, attaches the control catalog (source excerpts extracted
from the repository) and the normalized live Inspect results, and never exposes
a digest, token or raw log to the browser.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.common import ARTIFACTS, ROOT
from app.control_catalog import CONTROLS, CatalogError, control_view, for_scenario
from app.flow import STAGES
from app.ledger import LedgerError, bound_visuals, visual_for

LONG_HEX = re.compile(r"\b[0-9a-f]{32,}\b", re.IGNORECASE)
FORBIDDEN_KEY = re.compile(r"sha256|digest|token|signature|secret|password|descriptor|approval", re.IGNORECASE)
MAX_TEXT = 1_200
MAX_ITEMS = 16
DIAGRAM_ROOT = ROOT / "showcase" / "diagrams"
DIAGRAM_NAME = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
INSPECT_RESULTS = ARTIFACTS / "inspect-live.json"
INSPECT_VIEW_DIR = ARTIFACTS / "inspect-view"
RECORDING = ARTIFACTS / "recording.json"
STAGE_LABELS = {
    "input": "Input contract",
    "injection_screen": "Injection screen",
    "pii_redaction": "PII redaction",
    "retrieval": "Retrieval",
    "prompt": "Prompt",
    "model": "Model",
    "output_validation": "Output validation",
    "tool_gate": "Tool gate",
    "effect": "Effect",
}
PAYLOAD_KEYS = frozenset({
    "question", "prompts", "attack_prompts", "benign_prompt", "document", "query", "writer",
    "corpus", "input_chars", "model_output", "parameters", "tool_output", "artifact", "format",
    "scopes", "requester", "recorded_model_output", "output_length", "limit", "question_length",
    "expected_source", "evidence_package",
})


@dataclass(frozen=True)
class Scenario:
    scenario: str
    order: int
    title: str
    question: str
    payload_kind: str
    pairs: tuple[tuple[str, str], ...]
    reality: str
    diagram_before: str
    diagram_after: str
    evidence: tuple[str, ...]
    appendix: bool = False
    static_payload: tuple[str, ...] = field(default=())


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "S1", 1, "Model supply chain", "Would loading a downloaded model execute code?",
        "Synthetic pickle model that only creates sandbox/PWNED_BY_MODEL",
        (("model load", "Fickling static scan"),),
        "Real local scanners, Cosign and OPA in the restricted runner; the pickle is a synthetic, self-made fixture.",
        "model-admission-before", "model-admission",
        ("evidence/A/s1.jsonl", "evidence/B/s1.jsonl", "artifacts/fickling-s1.json", "artifacts/modelscan-s1.json", "artifacts/aibom.json"),
    ),
    Scenario(
        "S0", 2, "Bounded local inference", "What does the local model answer, and where do its citations come from?",
        "Benign runbook question",
        (("Ops Assist workload", "Ops Assist workload"),),
        "Real local FLAN-T5-small in both runs; Run A has no application control.",
        "ai-flow-unguarded", "ai-flow-guarded",
        ("evidence/A/s0.jsonl", "evidence/B/s0.jsonl", "artifacts/ops-assist.jsonl"),
    ),
    Scenario(
        "S2", 3, "Prompt injection", "Does hostile or obfuscated text reach the model?",
        "Ten synthetic injection prompts (plain, special token, base64, rot13, zero-width, confusable) and one benign paraphrase",
        (("prompt injection", "Prompt Guard 2 22M inspection"),),
        "Real local model in Run A; real normalization, rules and Prompt Guard 2 22M in Run B.",
        "ai-flow-unguarded", "request-guardrails",
        ("evidence/A/s2.jsonl", "evidence/B/s2.jsonl", "fixtures/prompts/injection_11.jsonl"),
    ),
    Scenario(
        "S3", 4, "Sensitive data", "Does synthetic PII in the knowledge base reach the user?",
        "Synthetic customer record (IBAN, email, phone, demo API key) and a question about it",
        (("PII in answer", "PII in answer"),),
        "Real local model and Qdrant in Run A; real Presidio 2.2.364 at ingestion and on output in Run B.",
        "ai-flow-unguarded", "ai-flow-guarded",
        ("evidence/A/s3.jsonl", "evidence/B/s3.jsonl", "fixtures/prompts/pii_cases.jsonl"),
    ),
    Scenario(
        "S4", 5, "Retrieval poisoning", "Can an untrusted upload steer the model and the agent?",
        "Synthetic release guide from an untrusted writer, indexed next to the trusted runbooks",
        (("poisoned document", "poisoned document"),),
        "Real local model and Qdrant in Run A; real writer admission, quarantine and Qdrant filter in Run B.",
        "ai-flow-unguarded", "rag-provenance",
        ("evidence/A/s4.jsonl", "evidence/B/s4.jsonl", "fixtures/docs/poisoned_note.md", "artifacts/quarantine.json"),
    ),
    Scenario(
        "S5", 6, "Tool boundary", "Can model text authorize a high-impact tool call?",
        "Synthetic tool parameters proposed from a poisoned release question",
        (("model-proposed tool call", "model-proposed tool call"), ("delete_branch", "delete_branch")),
        "Real local model, OPA and MCP in Run B; the naive agent in Run A acts only inside sandbox/.",
        "ai-flow-unguarded", "tool-boundary",
        ("evidence/A/s5.jsonl", "evidence/B/s5.jsonl", "artifacts/approvals.jsonl"),
    ),
    Scenario(
        "S8", 7, "Input and output bounds", "Can oversized input, hostile output or a model-written citation escape the contract?",
        "Synthetic over-length question, source-marker request and citation request",
        (("input length control", "input length control"), ("output validation", "output validation"), ("output length control", "output length control"), ("retrieval attribution", "retrieval attribution")),
        "Real local model in Run A; measured request and output controls in Run B. The over-length answer baseline stays DESIGNED.",
        "ai-flow-unguarded", "request-guardrails",
        ("evidence/A/s8.jsonl", "evidence/B/s8.jsonl"),
    ),
    Scenario(
        "PIPELINE", 8, "Delivery pipeline", "Do the delivery gates reuse the same evidence discipline?",
        "Local repository build inputs and synthetic model artifacts",
        (),
        "Local pipeline; unexecuted stages remain NOT TESTED.",
        "evidence-provenance", "evidence-provenance",
        ("evidence/B/pipeline.jsonl", "artifacts/pipeline-aibom.json"),
        static_payload=("Build inputs: app/, controls/, policies/, fixtures/ and the pinned wheel lock", "Model fixtures: synthetic clean and unsafe artifacts", "No deployment target and no external package index at runtime"),
    ),
    Scenario(
        "S7", 9, "Red-team appendix", "What did the bounded Garak campaign observe?",
        "Bounded loopback Garak campaign with 55 admitted prompts",
        (("visibility", "Garak campaign"),),
        "Real local campaign when the full 55-prompt run is admitted; otherwise not tested or partial.",
        "evidence-provenance", "evidence-provenance",
        ("evidence/B/s7.jsonl", "artifacts/garak-s7.json"),
        appendix=True,
    ),
)

EXTRA_DIAGRAMS: tuple[str, ...] = ("control-integration-map", "inspect-eval-topology")
DIAGRAMS: tuple[str, ...] = tuple(sorted({scenario.diagram_before for scenario in SCENARIOS} | {scenario.diagram_after for scenario in SCENARIOS} | set(EXTRA_DIAGRAMS)))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any, *, limit: int = MAX_TEXT) -> str:
    return LONG_HEX.sub("[internal digest]", str(value))[:limit]


def _sanitize(value: Any, *, depth: int = 0) -> Any:
    """Return a bounded, digest-free display value; unknown fields are dropped."""
    if depth > 5:
        return None
    if value is None or type(value) in {bool, int}:
        return value
    if isinstance(value, str):
        return _safe_text(value)
    if type(value) is list:
        return [_sanitize(item, depth=depth + 1) for item in value[:MAX_ITEMS]]
    if type(value) is dict:
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or FORBIDDEN_KEY.search(key):
                continue
            cleaned = _sanitize(item, depth=depth + 1)
            if cleaned is not None or item is None:
                result[key] = cleaned
        return result
    return None


def _event_view(event: dict[str, Any] | None, visual: dict[str, Any] | None) -> dict[str, Any] | None:
    if event is None:
        return None
    details = (visual or {}).get("details") or {}
    return {
        "control": event.get("control", ""),
        "decision": event.get("decision", "UNKNOWN"),
        "label": event.get("label", "NOT TESTED"),
        "reason": _safe_text(event.get("reason", ""), limit=600),
        "observation_kind": (visual or {}).get("observation_kind", ""),
        "details": _sanitize(details),
    }


def _select(events: list[dict[str, Any]], control: str, *, last: bool = False) -> dict[str, Any] | None:
    matches = [event for event in events if event.get("control") == control]
    if not matches:
        return None
    return matches[-1] if last else matches[0]


def _trace_of(visual: dict[str, Any] | None) -> list[dict[str, str]]:
    if not visual:
        return []
    trace = (visual.get("details") or {}).get("trace")
    if type(trace) is not list:
        return []
    rows = []
    for item in trace:
        if type(item) is dict and item.get("stage") in STAGES:
            rows.append({
                "stage": item["stage"],
                "status": str(item.get("status", "")),
                "control": _safe_text(item.get("control", ""), limit=120),
                "detail": _safe_text(item.get("detail", ""), limit=400),
            })
    return rows


def _flow(before: list[dict[str, str]], after: list[dict[str, str]]) -> list[dict[str, Any]]:
    if not before and not after:
        return []
    index_before = {row["stage"]: row for row in before}
    index_after = {row["stage"]: row for row in after}
    rows = []
    for stage in STAGES:
        left = index_before.get(stage)
        right = index_after.get(stage)
        if left is None and right is None:
            continue
        rows.append({
            "stage": stage,
            "label": STAGE_LABELS.get(stage, stage),
            "before": {"status": left["status"], "detail": left["detail"]} if left else None,
            "after": {"status": right["status"], "detail": right["detail"]} if right else None,
        })
    return rows


def _payload(before_visual: dict[str, Any] | None, static: tuple[str, ...]) -> list[dict[str, Any]]:
    details = (before_visual or {}).get("details") or {}
    source = details.get("input") if type(details.get("input")) is dict else {}
    items = []
    for key, value in source.items():
        if key in PAYLOAD_KEYS:
            items.append({"key": key, "value": _sanitize(value)})
    if not items:
        items = [{"key": "payload", "value": item} for item in static]
    return items[:MAX_ITEMS]


def _control_results(scenario: str, run_b: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for control in for_scenario(scenario):
        events = []
        for name in control.events:
            for event in run_b:
                if event.get("scenario") == scenario and event.get("control") == name:
                    events.append({
                        "control": name,
                        "decision": event.get("decision", ""),
                        "label": event.get("label", ""),
                        "reason": _safe_text(event.get("reason", ""), limit=400),
                    })
        try:
            view = control_view(control)
        except CatalogError as error:
            view = {"id": control.id, "name": control.name, "error": str(error), "scenarios": list(control.scenarios)}
        view["results"] = events[:MAX_ITEMS]
        results.append(view)
    return results


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if type(payload) is dict else {}


def _read_inspect() -> dict[str, Any]:
    payload = _read_json(INSPECT_RESULTS)
    if payload.get("format_version") != 1 or type(payload.get("samples")) is not list:
        return {"status": "not_run", "samples": [], "summary": {}, "scope": ""}
    samples = []
    for item in payload["samples"][:64]:
        if type(item) is not dict or type(item.get("id")) is not str or type(item.get("scenario")) is not str:
            continue
        sample = {"id": item["id"][:64], "scenario": item["scenario"][:16], "check": str(item.get("check", ""))[:32]}
        for side in ("unguarded", "guarded"):
            value = item.get(side)
            if type(value) is dict:
                sample[side] = {
                    "status": value.get("status") if value.get("status") in {"safe", "unsafe", "error", "not_run"} else "not_run",
                    "explanation": _safe_text(value.get("explanation", ""), limit=300),
                }
            else:
                sample[side] = {"status": "not_run", "explanation": ""}
        samples.append(sample)
    summary = payload.get("summary") if type(payload.get("summary")) is dict else {}
    return {
        "status": "available",
        "scope": _safe_text(payload.get("scope", "live local evaluation; synthetic fixtures"), limit=300),
        "summary": {key: value for key, value in summary.items() if type(value) in {int, str} and key in {"total", "unguarded_safe", "unguarded_unsafe", "guarded_safe", "guarded_unsafe"}},
        "samples": samples,
        "view": "inspect/index.html" if (INSPECT_VIEW_DIR / "index.html").is_file() and payload.get("view_available") is True else "",
    }


def _read_recording() -> dict[str, Any]:
    payload = _read_json(RECORDING)
    if payload.get("format_version") != 1:
        return {}
    phases = []
    for item in (payload.get("phases") if type(payload.get("phases")) is list else [])[:24]:
        if type(item) is dict and isinstance(item.get("name"), str) and type(item.get("seconds")) in {int, float}:
            phases.append({"name": item["name"][:64], "seconds": round(float(item["seconds"]), 1)})
    return {
        "recorded_at": _safe_text(payload.get("recorded_at", ""), limit=40),
        "total_seconds": round(float(payload["total_seconds"]), 1) if type(payload.get("total_seconds")) in {int, float} else None,
        "limit_seconds": payload.get("limit_seconds") if type(payload.get("limit_seconds")) in {int, float} else None,
        "phases": phases,
    }


def _scenario_card(
    scenario: Scenario,
    run_a: list[dict[str, Any]],
    bound_a: dict[str, dict[str, Any]],
    run_b: list[dict[str, Any]],
    bound_b: dict[str, dict[str, Any]],
    inspect: dict[str, Any],
) -> dict[str, Any]:
    pairs = []
    primary_before = primary_after = None
    for index, (a_control, b_control) in enumerate(scenario.pairs):
        a_event = _select(run_a, a_control)
        b_event = _select(run_b, b_control, last=(index == 0))
        a_visual = visual_for(bound_a, a_event)
        b_visual = visual_for(bound_b, b_event)
        if index == 0:
            primary_before, primary_after = a_event, b_event
        pairs.append({
            "label": b_control,
            "before": _event_view(a_event, a_visual),
            "after": _event_view(b_event, b_visual),
            "flow": _flow(_trace_of(a_visual), _trace_of(b_visual)),
            "payload": _payload(a_visual, scenario.static_payload),
        })
    pipeline = []
    if scenario.scenario == "PIPELINE":
        pipeline = [
            {"control": event.get("control", ""), "decision": event.get("decision", ""), "label": event.get("label", ""), "reason": _safe_text(event.get("reason", ""), limit=300)}
            for event in run_b if event.get("scenario") == "PIPELINE"
        ][:MAX_ITEMS]
    complete = bool(pipeline) if scenario.scenario == "PIPELINE" else bool(primary_before and primary_after)
    partial = any(pair["before"] or pair["after"] for pair in pairs) or bool(pipeline)
    checks = [sample for sample in inspect.get("samples", []) if sample["scenario"] == scenario.scenario]
    payload = pairs[0]["payload"] if pairs else _payload(None, scenario.static_payload)
    return {
        "scenario": scenario.scenario,
        "order": scenario.order,
        "title": scenario.title,
        "question": scenario.question,
        "appendix": scenario.appendix,
        "state": "complete" if complete else "partial" if partial else "waiting",
        "payload_kind": scenario.payload_kind,
        "payload": payload,
        "pairs": pairs,
        "pipeline": pipeline,
        "reality": scenario.reality,
        "controls": _control_results(scenario.scenario, run_b),
        "checks": checks,
        "diagrams": {"before": scenario.diagram_before, "after": scenario.diagram_after},
        "evidence": list(scenario.evidence),
    }


def build_projection() -> dict[str, Any]:
    """Return the browser-safe projection, or an ordered catalog without results."""
    inspect = _read_inspect()
    runs: dict[str, tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]] = {}
    for run in ("A", "B"):
        try:
            runs[run] = bound_visuals(run)
        except LedgerError:
            runs[run] = ([], {})
    run_a, bound_a = runs["A"]
    run_b, bound_b = runs["B"]
    cards = [
        _scenario_card(scenario, run_a, bound_a, run_b, bound_b, inspect)
        for scenario in SCENARIOS
        if scenario.appendix is False or any(event.get("scenario") == scenario.scenario for event in run_b)
    ]
    main = [card for card in cards if not card["appendix"]]
    complete = [card for card in main if card["state"] == "complete"]
    active = next((card for card in main if card["state"] != "complete"), None)
    phase = "complete" if main and len(complete) == len(main) else "running" if any(card["state"] != "waiting" for card in main) else "waiting"
    return {
        "format_version": 1,
        "generated_at": _now(),
        "phase": phase,
        "progress": {"complete": len(complete), "total": len(main)},
        "active": active["scenario"] if active else (main[-1]["scenario"] if main else None),
        "recording": _read_recording(),
        "scenarios": cards,
        "controls": [control_view(control) for control in CONTROLS if control.scenarios != ("S7",)],
        "inspect": inspect,
        "diagrams": list(DIAGRAMS),
    }


def export_projection(path: Path | None = None) -> Path:
    """Write the validated public projection for isolated consumers."""
    target = path or ARTIFACTS / "presentation.json"
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    target.write_text(json.dumps(build_projection(), sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return target


def diagram_path(name: str) -> Path | None:
    if not isinstance(name, str) or DIAGRAM_NAME.fullmatch(name) is None or name not in DIAGRAMS:
        return None
    path = DIAGRAM_ROOT / f"{name}.svg"
    return path if path.is_file() else None


if __name__ == "__main__":
    print(export_projection())
