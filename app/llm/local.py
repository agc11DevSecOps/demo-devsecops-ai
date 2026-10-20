"""Tier 1 offline adapter over the pinned local FLAN-T5-small safetensors model."""

from __future__ import annotations

from typing import Any

from app.llm import runtime

FLAN_T5_SMALL_REVISION = "0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab"


# Local-only adapter: the pinned runtime verifies files before generation.
class LocalAdapter:
    name = f"google/flan-t5-small@{FLAN_T5_SMALL_REVISION}"
    label = "MEASURED"

    def generate(self, prompt: str, *, sources: tuple[tuple[str, str], ...], trace: Any | None = None) -> str:
        return runtime.generate_local(prompt, trace=trace)
