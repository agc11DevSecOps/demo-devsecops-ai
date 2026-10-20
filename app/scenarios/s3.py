"""S3: redact sensitive synthetic values before indexing or response."""

from __future__ import annotations

import os

from app.evidence import Event, EvidenceWriter
from app.scenarios.helpers import load_jsonl, safe_path, write_text
from app.security.input import _presidio_redact, redact


def scenario_s3(run: str, writer: EvidenceWriter) -> None:
    document = load_jsonl("prompts/pii_cases.jsonl")[0]["text"]
    if run == "A":
        write_text(safe_path("index/customer.txt"), document)
        writer.emit(Event("A", "S3", "PII in answer", "ALLOWED", "IBAN returned in clear", ("v1.01-C8.2.1",), input_value=document, visual={"input": {"document": document}, "control": {"redaction": "absent in baseline"}, "observation": {"returned_answer": document}, "state": {"index_value": document}}))
        return
    if os.environ.get("OPS_DEMO_PRESIDIO") == "1":
        masked, entities = _presidio_redact(document)
        detail = f"Presidio 2.2.364 masked {len(entities)} entity type(s): {', '.join(entities)}"
    else:
        masked = redact(document)
        detail = "IBAN and canary masked at ingest and output"
    write_text(safe_path("index/customer.txt"), masked)
    if any(token in masked for token in ("ES91", "CANARY", "demo@")):
        raise AssertionError("redaction_failed")
    writer.emit(Event("B", "S3", "PII in answer", "BLOCKED", detail, ("v1.01-C8.2.1", "v1.01-C7.3.2"), input_value=document, visual={"input": {"document": document}, "control": {"redaction": "Presidio" if os.environ.get("OPS_DEMO_PRESIDIO") == "1" else "fallback"}, "observation": {"masked_answer": masked, "entities": list(entities) if os.environ.get("OPS_DEMO_PRESIDIO") == "1" else ["IBAN", "EMAIL", "PHONE", "API_KEY"]}, "state": {"index_value": masked}}))
