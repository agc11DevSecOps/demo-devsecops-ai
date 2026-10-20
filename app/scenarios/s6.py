"""S6: recorded-only scenario that makes missing external evidence visible."""

from __future__ import annotations

from app.evidence import Event, EvidenceWriter


def scenario_s6(run: str, writer: EvidenceWriter) -> None:
    writer.emit(Event(
        run,
        "S6",
        "Strix agentic campaign",
        "NOT TESTED",
        "no admitted recorded Strix evidence package is available; no campaign executed",
        (),
        "NOT TESTED",
        input_value="record/s6 admission status",
        visual={
            "input": {"evidence_package": "record/s6"},
            "control": {"external_campaign_execution": False},
            "observation": {"admitted_evidence": False},
            "state": {"decision": "NOT TESTED"},
        },
    ))
