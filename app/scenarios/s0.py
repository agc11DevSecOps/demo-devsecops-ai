"""S0: run the read-only workload or its labelled deterministic adapter."""

from __future__ import annotations

import os

from app.evidence import Event, EvidenceWriter
from app.scenarios.helpers import fixture_prompts


def scenario_s0(run: str, writer: EvidenceWriter) -> None:
    prompts = fixture_prompts("prompts/benign_10.jsonl")
    if len(prompts) != 10:
        raise AssertionError("fixture_count")
    if run == "B" and os.environ.get("OPS_DEMO_WORKLOAD") == "1":
        from app.workload import assist

        response = assist({
            "request_id": "s0-workload",
            "requester": "synthetic-operator",
            "question": "What is the rollback procedure?",
        })
        if response.label != "MEASURED" or not response.citations:
            raise AssertionError("workload_not_measured")
        writer.emit(Event(
            "B",
            "S0",
            "Ops Assist workload",
            response.decision,
            f"{response.model} returned a bounded answer from a hash-verified SafeTensors model with {len(response.citations)} verified citation(s)",
            (),
            response.label,
            input_value="What is the rollback procedure?",
            visual={
                "input": {"question": "What is the rollback procedure?"},
                "control": {"adapter": response.model, "mode": "local", "format": "safetensors", "verification": "sha256 per model file"},
                "observation": {"answer": response.answer, "citations": [item.source_id for item in response.citations]},
                "state": {"proposed_action": "none", "decision": response.decision},
            },
        ))
        return
    reason = "10/10 answered" if run == "A" else "10/10 answered, 0 false positives"
    writer.emit(Event(run, "S0", "baseline", "ALLOWED", reason, (), "SCRIPTED", input_value="\n".join(prompts), visual={"input": {"prompts": prompts}, "control": {"adapter": "scripted-contract-adapter"}, "observation": {"answered": 10}, "state": {"decision": "ALLOWED"}}))
