"""Retrieval controls: provenance-scoped vector retrieval and quarantine."""

from app.demo import (  # noqa: F401
    _vector_available as vector_available,
    _vector_index as vector_index,
    _vector_search as vector_search,
)

__all__ = ["vector_available", "vector_index", "vector_search"]
