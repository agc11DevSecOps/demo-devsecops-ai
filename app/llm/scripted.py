"""Deterministic Tier 0 adapter: exercises the control path without a model."""

from __future__ import annotations

from typing import Any

from app.llm import runtime


# Deterministic test double: this path is always labelled SCRIPTED in evidence.
class ScriptedAdapter:
    name = "scripted-contract-adapter"
    label = "SCRIPTED"

    def generate(self, prompt: str, *, sources: tuple[tuple[str, str], ...], trace: Any | None = None) -> str:
        return runtime.generate_scripted(sources)
