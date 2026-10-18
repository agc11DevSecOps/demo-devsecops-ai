"""Model adapter boundary for the Ops Assist workload.

Adapters translate a prompt and its retrieved sources into answer text. They are
the only place the workload selects a model, so Tier 0 (``scripted``) and Tier 1
(``local``) runs differ by adapter and not by control logic.
"""

from app.llm.base import Adapter
from app.llm.local import LocalAdapter
from app.llm.scripted import ScriptedAdapter

SCRIPTED_ADAPTER = ScriptedAdapter()
LOCAL_ADAPTER = LocalAdapter()
ADAPTERS: dict[str, Adapter] = {"scripted": SCRIPTED_ADAPTER, "local": LOCAL_ADAPTER}

__all__ = ["Adapter", "ScriptedAdapter", "LocalAdapter", "SCRIPTED_ADAPTER", "LOCAL_ADAPTER", "ADAPTERS"]
