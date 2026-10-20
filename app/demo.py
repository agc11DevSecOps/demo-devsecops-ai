"""Offline scenario runner for the synthetic Ops Copilot demo.

``reset`` owns the sandbox boundary; scenario handlers live in
``app.scenarios`` and the controls they exercise live in ``app.security``.
Run A models the unsafe baseline but all effects stay inside ``sandbox/``.
Run B uses deterministic validation and never treats model output, retrieval
text, or detector output as authorization.

This module only dispatches scenarios. Paths, evidence, controls, and sandbox
lifecycle are imported from their owning modules.
"""

from __future__ import annotations

from typing import Iterable

from app.evidence import EvidenceWriter
from app.scenarios import SCENARIOS


# Runner dispatch: scenario observations are evidence, never authorization.
def run(run: str, scenarios: Iterable[str] | None = None) -> None:
    if run not in {"A", "B"}:
        raise ValueError("invalid_run")
    writer = EvidenceWriter()
    for name in scenarios or SCENARIOS:
        SCENARIOS[name](run, writer)
