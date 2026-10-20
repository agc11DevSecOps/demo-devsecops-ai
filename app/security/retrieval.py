"""Deterministic vector retrieval controls for approved offline documents."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any


# The fixed embedding is deterministic and exists only for the synthetic demo.
_VECTOR_DIM = 32
_SOURCE_ID = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_TRUSTED_WRITER = "trusted"

# This is the reviewed corpus used by both the workload and the optional MCP
# server. It is intentionally small and safe, but follows the same admission
# boundary as a production ingestion path: provenance is checked before a
# document can reach the vector index.
APPROVED_DOCUMENTS: tuple[tuple[str, str, str], ...] = (
    ("rollback-runbook", _TRUSTED_WRITER, "Rollback procedure: revert the release and drain traffic."),
    ("payments-runbook", _TRUSTED_WRITER, "Payments deployment runbook: use a blue/green rollout with a canary."),
    ("escalation-runbook", _TRUSTED_WRITER, "Escalation procedure: page the payments on-call owner after failed health checks."),
)


def admitted_documents(documents: tuple[tuple[str, str, str], ...] = APPROVED_DOCUMENTS) -> tuple[tuple[str, str], ...]:
    """Return only schema-valid documents from the approved writer.

    Callers must admit each document before indexing it. An unknown or
    untrusted writer is rejected rather than silently becoming searchable.
    """
    admitted: list[tuple[str, str]] = []
    seen: set[str] = set()
    for source_id, writer, text in documents:
        if (
            not isinstance(source_id, str)
            or _SOURCE_ID.fullmatch(source_id) is None
            or source_id in seen
            or writer != _TRUSTED_WRITER
            or not isinstance(text, str)
            or not text.strip()
            or len(text) > 2_048
        ):
            raise ValueError("unadmitted_document")
        seen.add(source_id)
        admitted.append((source_id, text))
    if not admitted:
        raise ValueError("empty_admitted_corpus")
    return tuple(admitted)


def _embedding(text: str, dim: int = _VECTOR_DIM) -> list[float]:
    """Return a deterministic bag-of-tokens embedding for the demo."""
    vector = [0.0] * dim
    for token in re.findall(r"[a-z0-9]+", text.casefold()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        vector[int.from_bytes(digest[:4], "big") % dim] += 1.0
    norm = math.sqrt(sum(component * component for component in vector))
    return [component / norm for component in vector] if norm else vector


# Qdrant is optional; callers must fail closed when it is unavailable.
def _vector_available() -> bool:
    try:
        import qdrant_client  # noqa: F401
    except ImportError:
        return False
    return True


def _vector_index(documents: list[tuple[str, str]]) -> Any:
    from qdrant_client import QdrantClient, models

    client = QdrantClient(":memory:")
    client.create_collection("docs", vectors_config=models.VectorParams(size=_VECTOR_DIM, distance=models.Distance.COSINE))
    client.upsert(
        "docs",
        points=[
            models.PointStruct(id=index, vector=_embedding(text), payload={"writer": writer, "text": text})
            for index, (writer, text) in enumerate(documents)
        ],
    )
    return client


def _vector_search(client: Any, query: str, *, writer: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
    from qdrant_client import models

    condition = (
        models.Filter(must=[models.FieldCondition(key="writer", match=models.MatchValue(value=writer))]) if writer else None
    )
    points = client.query_points("docs", query=_embedding(query), limit=limit, query_filter=condition).points
    return [dict(point.payload or {}) for point in points]
