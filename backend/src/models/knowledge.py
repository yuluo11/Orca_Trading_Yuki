"""Typed document and evidence contracts shared across knowledge-backed layers."""

from __future__ import annotations

from typing import Any, TypedDict


class KnowledgeDocument(TypedDict, total=False):
    """Serialized knowledge document passed across services and agents."""

    title: str
    text: str
    metadata: dict[str, Any]


class KnowledgeEvidenceItem(TypedDict, total=False):
    """Compact evidence block derived from a serialized knowledge document."""

    source_type: str
    title: str
    content: str
    metadata: dict[str, Any]


class RankedKnowledgeDocument(KnowledgeDocument, total=False):
    """Knowledge document enriched with retrieval fit and match metadata."""

    fit: str
    match_reasons: list[str]
