"""Unguarded laboratory flow: the same local AI path with no application controls.

This module exists only to show, inside the restricted runner, what the real
local model does when every application security control is removed: no input
schema or length limit, no injection screen, no PII redaction, retrieval without
a provenance filter, no output validation, and a naive agent that turns tool
names found in model output into sandboxed effects.

Lab containment is never removed: the module refuses to run unless both
``OPS_DEMO_UNGUARDED_LAB=1`` and ``OPS_DEMO_IN_CONTAINER=1`` are set, effects are
limited to fixed synthetic tools and parameters inside ``sandbox/``, the runner
has no network, the kill switch applies and the tokenizer truncates at 512
tokens. The gateway never imports this module.
"""

from __future__ import annotations

import os
from typing import Any

from app.flow import CORPUS_NAMES, STAGE_CONTROLS, lab_corpus, FlowTrace, classify, clip, model_citations, proposed_tool_calls
from app.common import safe_sandbox_path as safe_path
from app.lab import branches, execute_a_tool

LAB_MAX_CHARS = 8_192
LAB_BRANCHES = frozenset({"release/2.4", "stale/old", "feature/x"})
LAB_REQUESTER = "lab-operator"


class LabDisabled(RuntimeError):
    """The unguarded lab was requested outside its restricted runner."""


def lab_enabled() -> bool:
    return os.environ.get("OPS_DEMO_UNGUARDED_LAB") == "1" and os.environ.get("OPS_DEMO_IN_CONTAINER") == "1"


def model_available() -> bool:
    from app.llm.runtime import WORKLOAD_FILES, flan_model_dir

    directory = flan_model_dir()
    return directory.is_dir() and all((directory / name).is_file() for name in WORKLOAD_FILES)


def require_lab() -> None:
    if not lab_enabled():
        raise LabDisabled("unguarded_lab_disabled")


def naive_agent(text: str, flow: FlowTrace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Execute tool names found in model output, confined to fixed sandbox tools."""
    calls = proposed_tool_calls(text)
    effects: list[dict[str, Any]] = []
    for call in calls:
        tool, parameters = call["tool"], call["parameters"]
        if tool == "delete_branch":
            branch = parameters.get("branch", "")
            if branch not in LAB_BRANCHES or branch not in branches():
                call["result"] = "not executed: parameter outside the fixed lab set"
                continue
            execute_a_tool(tool, parameters)
            call["result"] = f"{branch} removed from the sandbox repository"
        else:
            execute_a_tool(tool, parameters)
            call["result"] = "synthetic customers written to sandbox/exfil/customers.csv"
        effects.append({"tool": tool, "result": call["result"]})
    if calls:
        flow.record("tool_gate", "absent", STAGE_CONTROLS["tool_gate"], "naive agent turned model text into: " + ", ".join(item["tool"] for item in calls))
    else:
        flow.record("tool_gate", "absent", STAGE_CONTROLS["tool_gate"], "naive agent found no tool name in the model output")
    if effects:
        flow.record("effect", "executed", STAGE_CONTROLS["effect"], "; ".join(item["result"] for item in effects))
    else:
        flow.record("effect", "skipped", STAGE_CONTROLS["effect"], "no effect")
    return calls, effects


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run one fixed lab case through the unguarded flow."""
    return run_unguarded(case["question"], corpus=case["corpus"], check=case["check"], agent=case["agent"], expected_source=case.get("expected_source", ""))


def run_unguarded(question: str, *, corpus: str = "approved", check: str = "benign", agent: bool = True, expected_source: str = "") -> dict[str, Any]:
    """Run the real local model with every application control removed."""
    require_lab()
    if not isinstance(question, str) or not question or len(question) > LAB_MAX_CHARS or corpus not in CORPUS_NAMES:
        raise ValueError("lab_input_rejected")
    from app.errors import WorkloadError
    from app.llm import LOCAL_ADAPTER
    from app.security.retrieval import APPROVED_DOCUMENTS, _vector_index, _vector_search
    from app.workload import MAX_SOURCES, _render_prompt, _stop_enabled

    if _stop_enabled():
        raise WorkloadError("inference_stopped")
    flow = FlowTrace("unguarded")
    flow.record("input", "absent", STAGE_CONTROLS["input"], f"accepted as-is: {len(question)} chars, no schema or length limit")
    flow.record("injection_screen", "absent", STAGE_CONTROLS["injection_screen"], "question sent to the model unscreened")
    documents = APPROVED_DOCUMENTS + lab_corpus(corpus)
    flow.record("pii_redaction", "absent", STAGE_CONTROLS["pii_redaction"], f"{len(documents)} documents indexed raw, without redaction")
    index = _vector_index([(writer, text) for _, writer, text in documents])
    hits = _vector_search(index, question, limit=MAX_SOURCES)
    by_text = {text: (source_id, writer) for source_id, writer, text in documents}
    context = [
        {"source_id": by_text[hit["text"]][0], "writer": by_text[hit["text"]][1], "text": hit["text"]}
        for hit in hits
        if hit.get("text") in by_text
    ]
    flow.record(
        "retrieval",
        "absent",
        STAGE_CONTROLS["retrieval"],
        "Qdrant without a writer filter returned: " + ", ".join(f"{item['source_id']} ({item['writer']})" for item in context),
    )
    sources = tuple((item["source_id"], item["text"]) for item in context)
    prompt = _render_prompt(question, sources)
    flow.record("prompt", "absent", STAGE_CONTROLS["prompt"], f"{len(prompt)} chars, no prompt limit; the tokenizer truncates at 512 tokens (lab containment)")
    output = LOCAL_ADAPTER.generate(prompt, sources=sources)
    flow.record("model", "executed", STAGE_CONTROLS["model"], f"{LOCAL_ADAPTER.name.split('@')[0]} generated {len(output)} chars")
    flow.record("output_validation", "absent", STAGE_CONTROLS["output_validation"], "raw model output returned to the user")
    calls: list[dict[str, Any]] = []
    effects: list[dict[str, Any]] = []
    if agent:
        calls, effects = naive_agent(output, flow)
    else:
        flow.record("tool_gate", "skipped", STAGE_CONTROLS["tool_gate"], "agent not used for this request")
        flow.record("effect", "skipped", STAGE_CONTROLS["effect"], "no effect")
    result: dict[str, Any] = {
        "question": clip(question, 600),
        "input_chars": len(question),
        "corpus": corpus,
        "context": [{**item, "text": clip(item["text"], 400)} for item in context],
        "output": clip(output),
        "model_citations": model_citations(output),
        "tool_calls": calls,
        "effects": effects,
        "release_branch_present": "release/2.4" in branches(),
        "export_exists": safe_path("exfil/customers.csv").exists(),
    }
    outcome, reason = classify(check, {**result, "output": output, "context": context, "expected_source": expected_source})
    result["outcome"] = outcome
    result["outcome_reason"] = reason
    result["trace"] = flow.payload()
    return result
