"""Output validation and redaction before a model answer reaches the caller."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from app.errors import WorkloadError
from app.security.input import INJECTION, _presidio_redact, redact

MAX_ANSWER_CHARS = 1_200


def validate_answer(answer: Any, *, use_presidio: bool) -> str:
    """Reject malformed, oversized, or instruction-bearing model output."""
    if not isinstance(answer, str):
        raise WorkloadError("invalid_model_output", HTTPStatus.SERVICE_UNAVAILABLE)
    answer = answer.strip()
    answer = _presidio_redact(answer)[0] if use_presidio else redact(answer)
    if not answer or len(answer) > MAX_ANSWER_CHARS:
        raise WorkloadError("invalid_model_output", HTTPStatus.SERVICE_UNAVAILABLE)
    if "[SOURCE" in answer or "[QUESTION]" in answer or INJECTION.search(answer):
        raise WorkloadError("invalid_model_output", HTTPStatus.SERVICE_UNAVAILABLE)
    return answer
