"""Service layer for collecting and optionally ingesting dynamic knowledge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .collectors import (
    CollectedKnowledgeItem,
    HtmlFetcher,
    RSSNewsCollector,
    WebPageCollector,
    ingest_collected_items,
)
from .ingest import BatchIngestSummary, KnowledgeIngestor
from .repository import DatasetName, KnowledgeRepository
from .source_governance import (
    DEFAULT_DYNAMIC_SOURCE_GOVERNANCE,
    DynamicSourceGovernancePolicy,
    SourceGovernanceDecision,
)

CollectionMode = Literal["context_only", "persist"]


@dataclass(slots=True)
class WebPageCollectionResult:
    """Result returned after collecting a single web page."""

    mode: CollectionMode
    items: list[CollectedKnowledgeItem]
    ingest_summary: BatchIngestSummary | None = None

    @property
    def persisted(self) -> bool:
        return self.ingest_summary is not None

    def as_extra_context(self, *, max_chars: int = 4000) -> str:
        """Render collected items for immediate analyst/decision context."""
        return render_collected_item_context(self.items, max_chars=max_chars)


@dataclass(slots=True)
class RSSFeedCollectionResult:
    """Result returned after collecting RSS/Atom feed entries."""

    mode: CollectionMode
    items: list[CollectedKnowledgeItem]
    ingest_summary: BatchIngestSummary | None = None

    @property
    def persisted(self) -> bool:
        return self.ingest_summary is not None

    def as_extra_context(self, *, max_chars: int = 4000) -> str:
        """Render collected items for immediate analyst/decision context."""
        return render_collected_item_context(self.items, max_chars=max_chars)


class KnowledgeCollectorService:
    """Coordinate dynamic collectors with the persistent knowledge base."""

    def __init__(
        self,
        repository: KnowledgeRepository | None = None,
        ingestor: KnowledgeIngestor | None = None,
        source_policy: DynamicSourceGovernancePolicy | None = None,
    ) -> None:
        self.repository = repository or KnowledgeRepository()
        self.ingestor = ingestor or KnowledgeIngestor(self.repository)
        self.source_policy = source_policy or DEFAULT_DYNAMIC_SOURCE_GOVERNANCE

    def collect_web_page(
        self,
        url: str,
        *,
        persist: bool = False,
        dataset: DatasetName = "dynamic",
        category: str = "web_page",
        symbol: str | None = None,
        topic: str | None = None,
        title: str | None = None,
        fetcher: HtmlFetcher | None = None,
    ) -> WebPageCollectionResult:
        """Collect a page either as extra context or as persisted knowledge."""
        governance = self.source_policy.evaluate(
            url,
            source_type="web_page",
            category=category,
        )
        collector = WebPageCollector(
            url=url,
            dataset=dataset,
            category=governance.category,
            symbol=symbol,
            topic=topic,
            title=title,
            fetcher=fetcher,
        )
        items = self._apply_governance_metadata(collector.collect(), governance)
        if not persist:
            return WebPageCollectionResult(mode="context_only", items=items)

        summary = self._ingest_items(dataset, items)
        return WebPageCollectionResult(mode="persist", items=items, ingest_summary=summary)

    def collect_rss_feed(
        self,
        feed_url: str,
        *,
        persist: bool = False,
        dataset: DatasetName = "dynamic",
        category: str = "news",
        symbol: str | None = None,
        topic: str | None = None,
        max_items: int = 10,
        fetcher: HtmlFetcher | None = None,
    ) -> RSSFeedCollectionResult:
        """Collect RSS/Atom entries either as context or persisted knowledge."""
        governance = self.source_policy.evaluate(
            feed_url,
            source_type="rss_feed",
            category=category,
        )
        effective_max_items = max_items
        if governance.max_items_per_collect is not None:
            effective_max_items = min(max_items, governance.max_items_per_collect)

        collector = RSSNewsCollector(
            feed_url=feed_url,
            dataset=dataset,
            category=governance.category,
            symbol=symbol,
            topic=topic,
            max_items=effective_max_items,
            fetcher=fetcher,
        )
        items = self._apply_governance_metadata(collector.collect(), governance)
        if not persist:
            return RSSFeedCollectionResult(mode="context_only", items=items)

        summary = self._ingest_items(dataset, items)
        return RSSFeedCollectionResult(mode="persist", items=items, ingest_summary=summary)

    def _ingest_items(
        self,
        dataset: DatasetName,
        items: list[CollectedKnowledgeItem],
    ) -> BatchIngestSummary:
        normalized_items = [
            CollectedKnowledgeItem(
                name=item.name,
                text=item.text,
                metadata=item.metadata,
                dataset=dataset,
            )
            for item in items
        ]
        return ingest_collected_items(self.ingestor, normalized_items)

    def _apply_governance_metadata(
        self,
        items: list[CollectedKnowledgeItem],
        governance: SourceGovernanceDecision,
    ) -> list[CollectedKnowledgeItem]:
        """Attach source governance metadata to collected records."""
        governed_items: list[CollectedKnowledgeItem] = []
        governance_metadata = governance.metadata()
        for item in items:
            metadata = dict(item.metadata)
            metadata.update(
                {
                    key: value
                    for key, value in governance_metadata.items()
                    if value is not None and value != ""
                }
            )
            metadata["category"] = governance.category
            metadata["reliability"] = governance.reliability
            metadata["time_sensitivity"] = governance.time_sensitivity
            governed_items.append(
                CollectedKnowledgeItem(
                    name=item.name,
                    text=item.text,
                    metadata=metadata,
                    dataset=item.dataset,
                )
            )
        return governed_items


def render_collected_item_context(
    items: list[CollectedKnowledgeItem],
    *,
    max_chars: int = 4000,
) -> str:
    """Render collected items into a bounded context block for agents."""
    blocks = []
    for item in items:
        title = item.metadata.get("title") or item.name
        source_url = item.metadata.get("source_url")
        header = f"[Collected Knowledge] {title}"
        if source_url:
            header = f"{header}\nSource: {source_url}"
        blocks.append(f"{header}\n{item.text}")

    rendered = "\n\n".join(blocks).strip()
    if len(rendered) <= max_chars:
        return rendered
    return rendered[: max(0, max_chars - 3)].rstrip() + "..."
