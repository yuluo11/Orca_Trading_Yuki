"""Framework-neutral knowledge route handlers.

These functions are intentionally plain Python so a future FastAPI, Flask, or
desktop UI adapter can call them without moving domain logic into HTTP code.
"""

from __future__ import annotations

from typing import Any

from ..app import collect_rss_feed_knowledge, collect_web_page_knowledge
from ..knowledge.collectors import CollectedKnowledgeItem, HtmlFetcher
from ..knowledge.collector_service import RSSFeedCollectionResult, WebPageCollectionResult
from ..knowledge.ingest import BatchIngestSummary
from ..knowledge.repository import DatasetName, KnowledgeRepository


def collect_web_page_payload(
    payload: dict[str, Any],
    *,
    repository: KnowledgeRepository | None = None,
    fetcher: HtmlFetcher | None = None,
) -> dict[str, Any]:
    """Collect a web page from an API-style request payload."""
    result = collect_web_page_knowledge(
        url=_required_string(payload, "url"),
        persist=bool(payload.get("persist", False)),
        dataset=_dataset(payload.get("dataset", "dynamic")),
        category=_optional_string(payload.get("category")) or "web_page",
        symbol=_optional_string(payload.get("symbol")),
        topic=_optional_string(payload.get("topic")),
        title=_optional_string(payload.get("title")),
        repository=repository,
        fetcher=fetcher,
    )
    return _serialize_collection_result(result)


def collect_rss_feed_payload(
    payload: dict[str, Any],
    *,
    repository: KnowledgeRepository | None = None,
    fetcher: HtmlFetcher | None = None,
) -> dict[str, Any]:
    """Collect RSS/Atom feed entries from an API-style request payload."""
    result = collect_rss_feed_knowledge(
        feed_url=_required_string(payload, "feed_url"),
        persist=bool(payload.get("persist", False)),
        dataset=_dataset(payload.get("dataset", "dynamic")),
        category=_optional_string(payload.get("category")) or "news",
        symbol=_optional_string(payload.get("symbol")),
        topic=_optional_string(payload.get("topic")),
        max_items=int(payload.get("max_items", 10)),
        repository=repository,
        fetcher=fetcher,
    )
    return _serialize_collection_result(result)


def _serialize_collection_result(
    result: WebPageCollectionResult | RSSFeedCollectionResult,
) -> dict[str, Any]:
    return {
        "mode": result.mode,
        "persisted": result.persisted,
        "extraContext": result.as_extra_context(),
        "items": [_serialize_item(item) for item in result.items],
        "ingest": _serialize_ingest_summary(result.ingest_summary),
    }


def _serialize_item(item: CollectedKnowledgeItem) -> dict[str, Any]:
    return {
        "name": item.name,
        "text": item.text,
        "metadata": dict(item.metadata),
    }


def _serialize_ingest_summary(summary: BatchIngestSummary | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    paths = [str(outcome.record_path) for outcome in summary.outcomes]
    return {
        "paths": paths,
        "count": summary.imported_count,
        "createdCount": summary.created_count,
        "updatedCount": summary.updated_count,
        "skippedCount": summary.skipped_count,
        "indexed": any(outcome.index_snapshot_path for outcome in summary.outcomes),
    }


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = _optional_string(payload.get(key))
    if value is None:
        raise ValueError(f"Missing required string field: {key}")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dataset(value: Any) -> DatasetName:
    if value not in {"foundation", "dynamic"}:
        raise ValueError("dataset must be either 'foundation' or 'dynamic'")
    return value
