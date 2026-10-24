"""Guarded flow: the enforced workload plus a tool gate for any model proposal.

The workload never proposes actions. To show the tool boundary in the same
flow as the unguarded lab, any tool name found in the model output is routed to
``ToolBoundary.decide``. Nothing is ever executed here: a proposal is evidence
for the gate, never authorization.
"""

from __future__ import annotations

from typing import Any

from app.flow import CORPUS_NAMES, STAGE_CONTROLS, lab_corpus, FlowTrace, clip, pii_found, proposed_tool_calls, source_marker, template_echo


def guarded_agent(text: str, requester: str, flow: FlowTrace) -> list[dict[str, Any]]:
    """Send every proposed tool call to the deterministic boundary; never execute."""
    from app.security.tool_boundary import ToolBoundary

    calls = proposed_tool_calls(text)
    if not calls:
        flow.record("tool_gate", "passed", STAGE_CONTROLS["tool_gate"], "no tool proposed by the model output")
        flow.record("effect", "skipped", STAGE_CONTROLS["effect"], "no effect")
        return []
    boundary = ToolBoundary()
    for call in calls:
        try:
            call["decision"] = boundary.decide(call["tool"], call["parameters"], requester)
        except ValueError:
            call["decision"] = "DENIED"
            call["reason"] = "parameters outside the declared schema"
    engine = "OPA" if _opa_enabled() else "fallback rules"
    flow.record("tool_gate", "denied", STAGE_CONTROLS["tool_gate"], f"{engine}: " + ", ".join(f"{item['tool']} {item['decision']}" for item in calls))
    flow.record("effect", "skipped", STAGE_CONTROLS["effect"], "no tool executed")
    return calls


def _opa_enabled() -> bool:
    import os

    return os.environ.get("OPS_DEMO_OPA") == "1"


def run_case(case: dict[str, Any], requester: str) -> dict[str, Any]:
    """Run one fixed lab case through the guarded flow."""
    return run_guarded(case["question"], corpus=case["corpus"], requester=requester, request_id=case["id"])


def run_guarded(question: str, *, corpus: str = "approved", requester: str = "lab-operator", request_id: str = "guarded-flow") -> dict[str, Any]:
    """Run the enforced workload on a fixed lab request and return its trace."""
    if corpus not in CORPUS_NAMES:
        raise ValueError("lab_input_rejected")
    from app.errors import WorkloadError
    from app.workload import assist

    flow = FlowTrace("guarded")
    result: dict[str, Any] = {"question": clip(question, 600), "input_chars": len(question), "corpus": corpus}
    try:
        response = assist(
            {"request_id": request_id, "requester": requester, "question": question},
            flow=flow,
            extra_documents=lab_corpus(corpus),
        )
    except WorkloadError as error:
        result.update({"decision": "BLOCKED", "code": error.code, "output": "", "withheld_output": flow.withheld_output, "citations": [], "tool_calls": []})
        result["quarantined"] = list(flow.quarantined)
        result["stopped_at"] = flow.stopped_at() or "input"
        result["trace"] = flow.payload()
        return result
    calls = guarded_agent(response.answer, requester, flow)
    result.update({
        "decision": response.decision,
        "code": "",
        "output": clip(response.answer),
        "withheld_output": "",
        "citations": [item.source_id for item in response.citations],
        "tool_calls": calls,
        "pii_in_output": pii_found(response.answer),
        "marker_in_output": source_marker(response.answer) or template_echo(response.answer),
        "quarantined": list(flow.quarantined),
        "stopped_at": None,
        "trace": flow.payload(),
    })
    return result
