"""Adapter protocol shared by the scripted and local model adapters."""

from __future__ import annotations

from typing import Any, Protocol


# Adapter contract: workload code can select a model path without trusting it.
class Adapter(Protocol):
    """A model adapter that never receives decrypted credentials or tool handles."""

    name: str
    label: str

    def generate(self, prompt: str, *, sources: tuple[tuple[str, str], ...], trace: Any | None = None) -> str:
        """Return raw answer text for a bounded prompt and its sourced context."""
        ...
