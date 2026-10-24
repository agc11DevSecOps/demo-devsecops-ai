"""S3: synthetic PII through the unguarded lab and through redaction controls."""

from __future__ import annotations

import os

from app.evidence import Event, EvidenceWriter
from app.flow import guarded_ready, guarded_visual, lab_cases, lab_ready, lab_visual
from app.scenarios.helpers import load_jsonl, safe_path, write_text
from app.security.input import _presidio_redact, redact


def scenario_s3(run: str, writer: EvidenceWriter) -> None:
    document = load_jsonl("prompts/pii_cases.jsonl")[0]["text"]
    if run == "A":
        write_text(safe_path("index/customer.txt"), document)
        if lab_ready():
            from app.unguarded import run_case

            result = run_case(lab_cases()["s3-pii"])
            writer.emit(Event("A", "S3", "PII in answer", "ALLOWED", f"unguarded lab: customer record indexed raw; {result['outcome']}: {result['outcome_reason']}", ("v1.01-C8.2.1",), "MEASURED", input_value=document, visual=lab_visual(result, input_extra={"document": document})))
            return
        writer.emit(Event("A", "S3", "PII in answer", "ALLOWED", "IBAN returned in clear", ("v1.01-C8.2.1",), input_value=document, visual={"input": {"document": document}, "control": {"redaction": "absent in baseline"}, "observation": {"returned_answer": document}, "state": {"index_value": document}}))
        return
    presidio = os.environ.get("OPS_DEMO_PRESIDIO") == "1"
    if presidio:
        masked, entities = _presidio_redact(document)
        detail = f"Presidio 2.2.364 masked {len(entities)} entity type(s): {', '.join(entities)}"
    else:
        masked = redact(document)
        entities = ("IBAN", "EMAIL", "PHONE", "API_KEY")
        detail = "IBAN and canary masked at ingest and output"
    write_text(safe_path("index/customer.txt"), masked)
    if any(token in masked for token in ("ES91", "CANARY", "demo@")):
        raise AssertionError("redaction_failed")
    visual = {
        "input": {"document": document},
        "control": {"redaction": "Presidio" if presidio else "fallback"},
        "observation": {"masked_answer": masked, "entities": list(entities)},
        "state": {"index_value": masked},
    }
    if guarded_ready():
        from app.flow import pii_found
        from app.guarded import run_case

        result = run_case(lab_cases()["s3-pii"], requester="s3-guarded")
        if pii_found(result.get("output", "")) or pii_found(result.get("withheld_output", "")):
            raise AssertionError("guarded_flow_leaked_pii")
        visual["observation"].update(guarded_visual(result))
        visual["trace"] = result["trace"]
    writer.emit(Event("B", "S3", "PII in answer", "BLOCKED", detail, ("v1.01-C8.2.1", "v1.01-C7.3.2"), input_value=document, visual=visual))
