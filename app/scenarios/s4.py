"""S4: deterministic retrieval fixtures demonstrate provenance filtering."""

from __future__ import annotations

import json
import os

from app.common import ARTIFACTS, sha256
from app.evidence import Event, EvidenceWriter
from app.scenarios.helpers import fixture_document, safe_path, write_text
from app.security.retrieval import _vector_available, _vector_index, _vector_search, admitted_documents


def scenario_s4(run: str, writer: EvidenceWriter) -> None:
    poisoned = fixture_document("docs/poisoned_note.md")
    trusted = fixture_document("docs/rollback.md")
    query = "release rollback delete_branch export_customers"
    if run == "A":
        write_text(safe_path("index/poisoned.txt"), poisoned)
        writer.emit(Event("A", "S4", "poisoned document", "ALLOWED", "indexed and retrieved without provenance", ("v1.01-C8.2.4",), input_value=poisoned, visual={"input": {"query": query, "document": poisoned}, "control": {"provenance_filter": "absent in baseline"}, "observation": {"retrieved_writer": "untrusted-upload"}, "state": {"indexed": True}}))
        return
    immutable_metadata = {"source": "untrusted-upload", "writer_id": "external", "timestamp": "2026-10-17T00:00:00Z", "digest": sha256(poisoned)}
    (ARTIFACTS / "quarantine.json").write_text(json.dumps(immutable_metadata, sort_keys=True), encoding="utf-8")
    try:
        admitted_documents((("poisoned-note", "untrusted-upload", poisoned),))
    except ValueError as error:
        if str(error) != "unadmitted_document":
            raise
    else:
        raise AssertionError("untrusted_document_admitted")
    writer.emit(Event("B", "S4", "poisoned document", "BLOCKED", "quarantined; writer not on allow-list", ("v1.01-C12.5.4", "v1.01-C8.1.2", "v1.01-C8.1.3", "v1.01-C8.2.4", "v1.01-C8.3.3", "v1.01-C7.4.2"), input_value=poisoned, visual={"input": {"query": query, "document": poisoned}, "control": {"allowed_writer": "trusted"}, "observation": {"quarantine": immutable_metadata}, "state": {"indexed": False}}))
    if os.environ.get("OPS_DEMO_VECTOR") == "1" and _vector_available():
        index = _vector_index([("trusted", trusted), ("untrusted-upload", poisoned)])
        unfiltered = _vector_search(index, query)
        if not any(item.get("writer") == "untrusted-upload" for item in unfiltered):
            raise AssertionError("vector_recall_failed")
        writer.emit(Event("B", "S4", "forced retrieval test", "REVIEW", "Qdrant 1.19.1 returns the untrusted document when the provenance filter is disabled; S5 boundary required", ("v1.01-C9.5.3", "v1.01-C8.2.4"), input_value=poisoned, visual={"input": {"query": query}, "control": {"provenance_filter": "disabled for test"}, "observation": {"results": unfiltered}, "state": {"boundary_required": True}}))
        filtered = _vector_search(index, query, writer="trusted")
        if not filtered or any(item.get("writer") != "trusted" for item in filtered):
            raise AssertionError("provenance_filter_failed")
        writer.emit(Event("B", "S4", "provenance-filtered retrieval", "BLOCKED", f"Qdrant 1.19.1 returned {len(filtered)} trusted hit(s); the quarantined writer never enters the allow-list", ("v1.01-C8.1.2", "v1.01-C8.1.3", "v1.01-C8.2.4", "v1.01-C8.3.3"), input_value=poisoned, visual={"input": {"query": query}, "control": {"allowed_writer": "trusted"}, "observation": {"results": filtered}, "state": {"untrusted_returned": False}}))
    else:
        writer.emit(Event("B", "S4", "forced retrieval test", "REVIEW", "FILTER DISABLED FOR TEST; S5 boundary required", ("v1.01-C9.5.3",), input_value=poisoned))
