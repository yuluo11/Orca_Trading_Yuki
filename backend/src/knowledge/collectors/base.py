"""Shared contracts for dynamic knowledge collectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..ingest import BatchIngestSummary, KnowledgeIngestor
from ..record import KnowledgeMetadata
from ..repository import DatasetName


@dataclass(slots=True)
class CollectedKnowledgeItem:
    """A normalized knowledge item ready for optional ingestion."""

    name: str
    text: str
    metadata: KnowledgeMetadata = field(default_factory=dict)
    dataset: DatasetName = "dynamic"


class KnowledgeCollector(Protocol):
    """Collector interface for any source that can produce knowledge items."""

    def collect(self) -> list[CollectedKnowledgeItem]:
        """Collect normalized knowledge items from the underlying source."""
        ...


def compact_text(text: str) -> str:
    """Normalize whitespace while preserving readable sentence boundaries."""
    return " ".join(text.split())


def metadata_without_none(metadata: dict[str, Any]) -> KnowledgeMetadata:
    """Drop empty metadata values before a record enters the knowledge base."""
    return {
        key: value
        for key, value in metadata.items()
        if value is not None and value != ""
    }


def ingest_collected_items(
    ingestor: KnowledgeIngestor,
    items: list[CollectedKnowledgeItem],
) -> BatchIngestSummary:
    """Ingest normalized collector items through the shared ingest pipeline."""
    outcomes = [
        ingestor.ingest_text_with_outcome(
            item.dataset,
            item.name,
            item.text,
            metadata=item.metadata,
        )
        for item in items
    ]
    return BatchIngestSummary(outcomes=outcomes)
