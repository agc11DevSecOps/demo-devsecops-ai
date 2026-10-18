"""Tier 1 offline adapter over the pinned local FLAN-T5-small safetensors model."""

from __future__ import annotations

FLAN_T5_SMALL_REVISION = "0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab"


class LocalAdapter:
    name = f"google/flan-t5-small@{FLAN_T5_SMALL_REVISION}"
    label = "MEASURED"

    def generate(self, prompt: str, *, sources: tuple[tuple[str, str], ...]) -> str:
        from app.workload import _generate_local

        return _generate_local(prompt)
