"""Base contracts for dynamic knowledge collectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..ingest import BatchIngestSummary, IngestOutcome, KnowledgeIngestor
from ..record import KnowledgeMetadata
from ..repository import DatasetName


@dataclass(slots=True)
class CollectedKnowledgeItem:
    """One collector-normalized knowledge item ready for ingestion."""

    name: str
    text: str
    metadata: KnowledgeMetadata = field(default_factory=dict)
    dataset: DatasetName = "dynamic"


class KnowledgeCollector(Protocol):
    """Protocol implemented by concrete knowledge collectors."""

    def collect(self) -> list[CollectedKnowledgeItem]:
        """Return normalized items collected from one source."""


def ingest_collected_items(
    ingestor: KnowledgeIngestor,
    items: list[CollectedKnowledgeItem],
) -> BatchIngestSummary:
    """Ingest collector output through the existing knowledge ingest pipeline."""
    outcomes: list[IngestOutcome] = []
    for item in items:
        outcomes.append(
            ingestor.ingest_text_with_outcome(
                item.dataset,
                item.name,
                item.text,
                metadata=item.metadata,
            )
        )
    return BatchIngestSummary(outcomes)
