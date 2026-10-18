"""Deterministic Tier 0 adapter: exercises the control path without a model."""

from __future__ import annotations


class ScriptedAdapter:
    name = "scripted-contract-adapter"
    label = "SCRIPTED"

    def generate(self, prompt: str, *, sources: tuple[tuple[str, str], ...]) -> str:
        from app.workload import _generate_scripted

        return _generate_scripted(sources)
