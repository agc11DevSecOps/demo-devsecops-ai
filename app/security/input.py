"""Offline input normalization, prompt screening, and PII redaction controls."""

from __future__ import annotations

import base64
import functools
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from app.common import MAX_TEXT, ROOT


# Pattern controls use only fixed, reviewed expressions and synthetic markers.
IBAN = re.compile(r"\bES\d{2}(?:\s?\d{4}){5}\b")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"\+?\d{2,3}[ -]?\d{3}[ -]?\d{3}[ -]?\d{3}\b")
CANARY = re.compile(r"\bsk-demo-CANARY-\d{4}\b")
INJECTION = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|"
    r"print\s+(?:the\s+)?system\s+prompt|"
    r"system\s*:\s*|"
    r"<\|[^|]{1,64}\|>|"
    r"call\s+(?:delete_branch|export_customers)|"
    r"first\s+call\s+delete_branch",
    re.IGNORECASE,
)
PROMPT_GUARD_THRESHOLD = 0.5
PROMPT_GUARD_ATTACKS = 10


# Normalization exposes every inspected representation to the caller.
def normalize(text: str) -> tuple[str, tuple[str, ...]]:
    if not isinstance(text, str) or not text or len(text.encode("utf-8")) > MAX_TEXT:
        raise ValueError("invalid_input_size")
    normalized = "".join(character for character in unicodedata.normalize("NFKC", text) if unicodedata.category(character) not in {"Cf", "Cc"})
    # Narrow confusable folding covers the fixed corpus; it is not general Unicode security.
    normalized = normalized.translate(str.maketrans({"\u043e": "o", "\u041e": "O", "\u0430": "a", "\u0410": "A", "\u0435": "e", "\u0415": "E"}))
    candidates = [normalized]
    compact = re.sub(r"\s+", "", normalized)
    if 8 <= len(compact) <= 2048 and re.fullmatch(r"[A-Za-z0-9+/=]+", compact):
        try:
            decoded = base64.b64decode(compact, validate=True).decode("utf-8")
            if decoded.isprintable() and len(decoded) <= MAX_TEXT:
                candidates.append(decoded)
        except (UnicodeDecodeError, ValueError):
            pass
    rot13 = normalized.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"))
    if INJECTION.search(rot13):
        candidates.append(rot13)
    return normalized, tuple(dict.fromkeys(candidates))


# Prompt Guard loads reviewed local artifacts only and never contacts a model hub.
def _prompt_guard_model_dir() -> Path:
    override = os.environ.get("OPS_DEMO_PROMPT_GUARD_MODEL")
    return Path(override) if override else ROOT / "vendor" / "models" / "prompt-guard-2-22m"


@functools.lru_cache(maxsize=1)
def _prompt_guard_classifier() -> tuple[Any, Any, Any]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    directory = str(_prompt_guard_model_dir())
    torch.set_num_threads(1)
    tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(directory, local_files_only=True)
    model.eval()
    return tokenizer, model, torch


def _prompt_guard_scores(texts: Iterable[str]) -> tuple[float, ...]:
    tokenizer, model, torch = _prompt_guard_classifier()
    scores: list[float] = []
    with torch.no_grad():
        for text in texts:
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            logits = model(**inputs).logits
            probabilities = torch.softmax(logits, dim=-1)
            scores.append(float(probabilities[0][1]))
    return tuple(scores)


# Redaction uses deterministic fallbacks and an optional offline Presidio engine.
def redact(text: str) -> str:
    result = IBAN.sub("<IBAN>", text)
    result = EMAIL.sub("<EMAIL>", result)
    result = PHONE.sub("<PHONE>", result)
    return CANARY.sub("<API_KEY>", result)


def _presidio_redact(text: str) -> tuple[str, tuple[str, ...]]:
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_analyzer.predefined_recognizers import IbanRecognizer, PhoneRecognizer

    provider = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
    )
    # The built-in email recognizer can fetch a suffix list; this fixed recognizer cannot.
    email = PatternRecognizer(
        supported_entity="EMAIL_ADDRESS",
        patterns=[Pattern("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", 0.85)],
        supported_language="en",
    )
    api_key = PatternRecognizer(
        supported_entity="API_KEY",
        patterns=[Pattern("demo-api-key", r"\bsk-demo-CANARY-\d{4}\b", 0.9)],
        supported_language="en",
    )
    registry = RecognizerRegistry(supported_languages=["en"])
    for recognizer in (IbanRecognizer(supported_language="en"), PhoneRecognizer(supported_language="en"), email, api_key):
        registry.add_recognizer(recognizer)
    engine = AnalyzerEngine(
        registry=registry, nlp_engine=provider.create_engine(), supported_languages=["en"]
    )
    spans: list[tuple[int, int, str]] = []
    for result in sorted(engine.analyze(text=text, language="en"), key=lambda item: (item.start, -(item.end - item.start))):
        if spans and result.start < spans[-1][1]:
            continue
        spans.append((result.start, result.end, result.entity_type))
    masked = text
    for start, end, entity_type in reversed(spans):
        masked = masked[:start] + f"<{entity_type}>" + masked[end:]
    return masked, tuple(sorted({entity_type for _, _, entity_type in spans}))
