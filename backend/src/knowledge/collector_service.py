"""Service entry points for collecting knowledge from external inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .collectors import CollectedKnowledgeItem, WebPageCollector, ingest_collected_items
from .collectors.web_page import HtmlFetcher
from .ingest import BatchIngestSummary, KnowledgeIngestor
from .repository import DatasetName, KnowledgeRepository


CollectionMode = Literal["context_only", "persist"]


@dataclass(slots=True)
class WebPageCollectionResult:
    """Result returned after collecting a user-provided web page."""

    mode: CollectionMode
    items: list[CollectedKnowledgeItem]
    ingest_summary: BatchIngestSummary | None = None

    @property
    def persisted(self) -> bool:
        return self.ingest_summary is not None

    def as_extra_context(self, *, max_chars: int = 4000) -> str:
        """Render collected items as compact context for analyst or decision tasks."""
        context_blocks = [render_collected_item_context(item) for item in self.items]
        context = "\n\n".join(block for block in context_blocks if block).strip()
        if len(context) <= max_chars:
            return context
        return context[: max_chars - 3].rstrip() + "..."


class KnowledgeCollectorService:
    """Coordinate collectors with the existing knowledge ingest pipeline."""

    def __init__(
        self,
        repository: KnowledgeRepository | None = None,
        ingestor: KnowledgeIngestor | None = None,
    ) -> None:
        self.repository = repository or KnowledgeRepository()
        self.ingestor = ingestor or KnowledgeIngestor(self.repository)

    def collect_web_page(
        self,
        url: str,
        *,
        persist: bool = False,
        dataset: DatasetName = "dynamic",
        category: str = "web_page",
        symbol: str | None = None,
        topic: str | None = None,
        fetcher: HtmlFetcher | None = None,
    ) -> WebPageCollectionResult:
        """Collect a single URL as temporary context or persist it to dynamic knowledge."""
        collector = WebPageCollector(
            url,
            dataset=dataset,
            category=category,
            symbol=symbol,
            topic=topic,
            fetcher=fetcher,
        )
        items = collector.collect()
        if not persist:
            return WebPageCollectionResult(mode="context_only", items=items)

        return WebPageCollectionResult(
            mode="persist",
            items=items,
            ingest_summary=ingest_collected_items(self.ingestor, items),
        )


def render_collected_item_context(item: CollectedKnowledgeItem) -> str:
    """Render one collected item into an agent-friendly context block."""
    metadata = dict(item.metadata or {})
    header_parts = [
        str(metadata.get("title", "")).strip() or item.name,
        str(metadata.get("source_url") or metadata.get("source") or "").strip(),
        str(metadata.get("symbol", "")).strip().upper(),
        str(metadata.get("category", "")).strip().lower(),
    ]
    header = " | ".join(part for part in header_parts if part)
    text = " ".join(item.text.split())
    return f"[Collected context] {header}\n{text}".strip()
