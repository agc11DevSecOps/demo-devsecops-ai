"""Adapter protocol shared by the scripted and local model adapters."""

from __future__ import annotations

from typing import Protocol


class Adapter(Protocol):
    """A model adapter that never receives decrypted credentials or tool handles."""

    name: str
    label: str

    def generate(self, prompt: str, *, sources: tuple[tuple[str, str], ...]) -> str:
        """Return raw answer text for a bounded prompt and its sourced context."""
        ...
