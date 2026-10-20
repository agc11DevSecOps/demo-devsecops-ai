"""Local FLAN-T5 generation and the deterministic scripted fallback.

Moving the runtime here keeps model loading independent from the workload
module, so adapters no longer import the workload they are called from.
"""

from __future__ import annotations

import functools
import hashlib
import os
import time
from pathlib import Path
from typing import Any

from app.common import ROOT
from app.errors import WorkloadError

from http import HTTPStatus

# Pinned local artifacts: every file hash is verified before the model loads.
WORKLOAD_FILES = {
    "config.json": "439aa0fecf5a5546a1def68b1fc45e538e2c94528ce805378daf091e2bf6e4de",
    "generation_config.json": "f5a1c7e2be8092018d8835128987edf0111637dd98e90599cc80310fef75d95a",
    "model.safetensors": "495fa51e204676f1a857a9fc13c4c89f3f5ba9f480b898cebca02add25e6d749",
    "special_tokens_map.json": "5c87151ef0f72a99d1f766a4c418bd2a1f90aaa30a8e22fe5eca9641daebb64f",
    "spiece.model": "d60acb128cf7b7f2536e8f38a5b18a05535c9e14c7a355904270e15b0945ea86",
    "tokenizer.json": "fe2ebbbbde2985be723e0ce18217853e4020c5e9d35bd07be2c27ab9d3ead57a",
    "tokenizer_config.json": "fcde0f79bffda3688119c94330866a8fbf8de20ae65a8c492c9bd47c704655a0",
}


def flan_model_dir() -> Path:
    """Return the configured local model directory, never a remote identifier."""
    configured = os.environ.get("OPS_DEMO_WORKLOAD_MODEL")
    return Path(configured) if configured else ROOT / "vendor" / "models" / "flan-t5-small"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


@functools.lru_cache(maxsize=1)
def _flan_generator() -> tuple[Any, Any, Any]:
    """Load only the reviewed local safetensors model and never contact a hub."""
    model_dir = flan_model_dir()
    if not model_dir.is_dir() or any(
        not (model_dir / filename).is_file() or _sha256_file(model_dir / filename) != expected
        for filename, expected in WORKLOAD_FILES.items()
    ):
        raise WorkloadError("workload_model_unavailable", HTTPStatus.SERVICE_UNAVAILABLE)
    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        torch.set_num_threads(1)
        tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True, use_fast=True, trust_remote_code=False)
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_dir,
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
        )
        model.eval()
    except Exception as error:  # Model/parser failures are not exposed to callers.
        raise WorkloadError("workload_model_unavailable", HTTPStatus.SERVICE_UNAVAILABLE) from error
    return tokenizer, model, torch


def generate_local(prompt: str, *, trace: Any | None = None) -> str:
    """Generate bounded text locally and record trace data without trusting it."""
    tokenizer, model, torch = _flan_generator()
    try:
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        started = time.monotonic()
        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=96, do_sample=False, num_beams=1)
        if trace is not None:
            trace.token_ids(inputs["input_ids"][0].tolist(), output[0].tolist(), int((time.monotonic() - started) * 1_000))
        return tokenizer.decode(output[0], skip_special_tokens=True).strip()
    except Exception as error:
        raise WorkloadError("workload_inference_failed", HTTPStatus.SERVICE_UNAVAILABLE) from error


def generate_scripted(sources: tuple[tuple[str, str], ...]) -> str:
    """Return deterministic text that exercises the control path without a model."""
    return f"According to {sources[0][0]}, {sources[0][1]}"
