"""Framework-neutral knowledge route handlers.

These functions are intentionally plain Python so a future FastAPI, Flask, or
desktop UI adapter can call them without moving domain logic into HTTP code.
"""

from __future__ import annotations

from typing import Any

from ..app import (
    build_dynamic_knowledge_scheduler,
    collect_rss_feed_knowledge,
    collect_web_page_knowledge,
)
from ..knowledge.indexing import KnowledgeIndexer
from ..knowledge.evaluation import KnowledgeRetrievalEvaluator, parse_eval_case
from ..knowledge.collectors import CollectedKnowledgeItem, HtmlFetcher
from ..knowledge.collector_service import RSSFeedCollectionResult, WebPageCollectionResult
from ..knowledge.ingest import BatchIngestSummary
from ..knowledge.repository import DatasetName, KnowledgeRepository
from ..knowledge.retriever import KnowledgeRetriever
from ..knowledge.source_scheduler import CrawlRunResult, ScheduledKnowledgeSource
from ..knowledge.source_governance import DynamicSourceGovernancePolicy


def collect_web_page_payload(
    payload: dict[str, Any],
    *,
    repository: KnowledgeRepository | None = None,
    fetcher: HtmlFetcher | None = None,
    source_policy: DynamicSourceGovernancePolicy | None = None,
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
        source_policy=source_policy,
    )
    return _serialize_collection_result(result)


def collect_rss_feed_payload(
    payload: dict[str, Any],
    *,
    repository: KnowledgeRepository | None = None,
    fetcher: HtmlFetcher | None = None,
    source_policy: DynamicSourceGovernancePolicy | None = None,
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
        source_policy=source_policy,
    )
    return _serialize_collection_result(result)


def list_processed_records_payload(
    payload: dict[str, Any],
    *,
    repository: KnowledgeRepository | None = None,
) -> dict[str, Any]:
    """List processed knowledge records for one or more datasets."""
    repo = repository or KnowledgeRepository()
    datasets = _datasets(payload.get("datasets") or payload.get("dataset") or "dynamic")
    limit = _optional_int(payload.get("limit"))
    include_text = bool(payload.get("include_text", False))

    records: list[dict[str, Any]] = []
    for dataset in datasets:
        for record_path in repo.list_processed_record_paths(dataset):
            record = repo.load_processed_record(dataset, record_path.stem)
            records.append(
                _serialize_record(
                    dataset=dataset,
                    name=record_path.stem,
                    record=record,
                    include_text=include_text,
                    path=str(record_path),
                )
            )

    records.sort(key=lambda item: item["metadata"].get("updated_at", ""), reverse=True)
    if limit is not None:
        records = records[:limit]

    return {
        "datasets": list(datasets),
        "count": len(records),
        "records": records,
    }


def get_processed_record_payload(
    payload: dict[str, Any],
    *,
    repository: KnowledgeRepository | None = None,
) -> dict[str, Any]:
    """Read one processed knowledge record by dataset and name."""
    repo = repository or KnowledgeRepository()
    dataset = _dataset(payload.get("dataset", "dynamic"))
    name = _required_string(payload, "name")
    record = repo.load_processed_record(dataset, name)
    return _serialize_record(dataset=dataset, name=name, record=record, include_text=True)


def search_knowledge_payload(
    payload: dict[str, Any],
    *,
    repository: KnowledgeRepository | None = None,
) -> dict[str, Any]:
    """Search processed knowledge with the default local vector backend."""
    repo = repository or KnowledgeRepository()
    query = _required_string(payload, "query")
    datasets = _datasets(payload.get("datasets") or payload.get("dataset") or ("foundation", "dynamic"))
    k = _optional_int(payload.get("k")) or _optional_int(payload.get("max_documents")) or 4
    metadata_filter = payload.get("metadata_filter")
    include_scores = bool(payload.get("include_scores", False))
    if metadata_filter is not None and not isinstance(metadata_filter, dict):
        raise ValueError("metadata_filter must be an object when provided")

    backend = KnowledgeIndexer(repo).load_or_build_default_backend(datasets)
    retriever = KnowledgeRetriever(repo, backend=backend)
    if include_scores:
        scored_documents = retriever.search_with_scores(
            query,
            datasets=datasets,
            k=k,
            metadata_filter=metadata_filter,
        )
        documents = [
            _serialize_document(document, score=score)
            for document, score in scored_documents
        ]
    else:
        documents = [
            _serialize_document(document)
            for document in retriever.search(
                query,
                datasets=datasets,
                k=k,
                metadata_filter=metadata_filter,
            )
        ]
    return {
        "query": query,
        "datasets": list(datasets),
        "count": len(documents),
        "documents": documents,
    }


def evaluate_knowledge_payload(
    payload: dict[str, Any],
    *,
    repository: KnowledgeRepository | None = None,
) -> dict[str, Any]:
    """Run user-fixed retrieval evaluation cases on demand."""
    repo = repository or KnowledgeRepository()
    evaluator = KnowledgeRetrievalEvaluator(repo)
    include_disabled = bool(payload.get("include_disabled", False))
    if "eval_set_path" in payload:
        summary = evaluator.evaluate_file(
            _required_string(payload, "eval_set_path"),
            include_disabled=include_disabled,
        )
        return summary.to_dict()

    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("Provide eval_set_path or a non-empty cases list")
    summary = evaluator.evaluate_cases(
        [parse_eval_case(raw_case) for raw_case in raw_cases],
        include_disabled=include_disabled,
    )
    return summary.to_dict()


def register_dynamic_source_payload(
    payload: dict[str, Any],
    *,
    repository: KnowledgeRepository | None = None,
    source_policy: DynamicSourceGovernancePolicy | None = None,
) -> dict[str, Any]:
    """Register or update a scheduled dynamic knowledge source."""
    scheduler = build_dynamic_knowledge_scheduler(
        repository=repository,
        source_policy=source_policy,
    )
    source = scheduler.register_source(
        source_id=_optional_string(payload.get("source_id")),
        source_type=_source_type(payload.get("source_type")),
        url=_required_string(payload, "url"),
        dataset=_dataset(payload.get("dataset", "dynamic")),
        category=_optional_string(payload.get("category")) or "news",
        enabled=bool(payload.get("enabled", True)),
        symbol=_optional_string(payload.get("symbol")),
        topic=_optional_string(payload.get("topic")),
        title=_optional_string(payload.get("title")),
        max_items=_optional_int(payload.get("max_items")) or 10,
        refresh_interval_minutes=_optional_int(payload.get("refresh_interval_minutes")),
        next_run_at=_optional_string(payload.get("next_run_at")),
    )
    return _serialize_scheduled_source(source)


def list_dynamic_sources_payload(
    payload: dict[str, Any],
    *,
    repository: KnowledgeRepository | None = None,
) -> dict[str, Any]:
    """List scheduled dynamic knowledge sources."""
    scheduler = build_dynamic_knowledge_scheduler(repository=repository)
    sources = scheduler.list_sources(
        include_disabled=bool(payload.get("include_disabled", True))
    )
    return {
        "count": len(sources),
        "sources": [_serialize_scheduled_source(source) for source in sources],
    }


def run_dynamic_source_payload(
    payload: dict[str, Any],
    *,
    repository: KnowledgeRepository | None = None,
    fetcher: HtmlFetcher | None = None,
    source_policy: DynamicSourceGovernancePolicy | None = None,
) -> dict[str, Any]:
    """Run one scheduled source immediately or only when it is due."""
    scheduler = build_dynamic_knowledge_scheduler(
        repository=repository,
        source_policy=source_policy,
    )
    result = scheduler.run_source(
        _required_string(payload, "source_id"),
        force=bool(payload.get("force", False)),
        fetcher=fetcher,
    )
    return _serialize_crawl_run_result(result)


def run_due_dynamic_sources_payload(
    payload: dict[str, Any],
    *,
    repository: KnowledgeRepository | None = None,
    fetchers: dict[str, HtmlFetcher] | None = None,
    source_policy: DynamicSourceGovernancePolicy | None = None,
) -> dict[str, Any]:
    """Run all currently due scheduled sources."""
    scheduler = build_dynamic_knowledge_scheduler(
        repository=repository,
        source_policy=source_policy,
    )
    results = scheduler.run_due_sources(fetchers=fetchers)
    return {
        "count": len(results),
        "results": [_serialize_crawl_run_result(result) for result in results],
    }


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


def _serialize_record(
    *,
    dataset: DatasetName,
    name: str,
    record: dict[str, Any],
    include_text: bool,
    path: str | None = None,
) -> dict[str, Any]:
    text = str(record.get("text", ""))
    payload = {
        "dataset": dataset,
        "name": name,
        "title": record.get("metadata", {}).get("title", name),
        "metadata": dict(record.get("metadata", {})),
        "excerpt": _excerpt(text),
    }
    if path is not None:
        payload["path"] = path
    if include_text:
        payload["text"] = text
    return payload


def _serialize_document(document: Any, *, score: float | None = None) -> dict[str, Any]:
    text = str(getattr(document, "page_content", ""))
    metadata = dict(getattr(document, "metadata", {}))
    payload = {
        "title": metadata.get("title", ""),
        "text": text,
        "excerpt": _excerpt(text),
        "metadata": metadata,
    }
    if score is not None:
        payload["score"] = round(score, 6)
    return payload


def _serialize_scheduled_source(source: ScheduledKnowledgeSource) -> dict[str, Any]:
    return {
        "sourceId": source.source_id,
        "sourceType": source.source_type,
        "url": source.url,
        "dataset": source.dataset,
        "category": source.category,
        "enabled": source.enabled,
        "symbol": source.symbol,
        "topic": source.topic,
        "title": source.title,
        "maxItems": source.max_items,
        "refreshIntervalMinutes": source.refresh_interval_minutes,
        "nextRunAt": source.next_run_at,
        "lastRunAt": source.last_run_at,
        "lastSuccessAt": source.last_success_at,
        "lastStatus": source.last_status,
        "lastError": source.last_error,
        "consecutiveFailures": source.consecutive_failures,
        "sourceRule": source.source_rule,
        "sourceDomain": source.source_domain,
        "createdAt": source.created_at,
        "updatedAt": source.updated_at,
    }


def _serialize_crawl_run_result(result: CrawlRunResult) -> dict[str, Any]:
    return {
        "sourceId": result.source_id,
        "status": result.status,
        "collectedCount": result.collected_count,
        "importedCount": result.imported_count,
        "skippedCount": result.skipped_count,
        "error": result.error,
        "ranAt": result.ran_at,
        "nextRunAt": result.next_run_at,
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


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    parsed = int(value)
    if parsed < 0:
        raise ValueError("integer values must be non-negative")
    return parsed


def _dataset(value: Any) -> DatasetName:
    if value not in {"foundation", "dynamic"}:
        raise ValueError("dataset must be either 'foundation' or 'dynamic'")
    return value


def _source_type(value: Any) -> str:
    if value not in {"web_page", "rss_feed"}:
        raise ValueError("source_type must be either 'web_page' or 'rss_feed'")
    return value


def _datasets(value: Any) -> tuple[DatasetName, ...]:
    if isinstance(value, str):
        return (_dataset(value),)
    if isinstance(value, (list, tuple)):
        datasets = tuple(_dataset(item) for item in value)
        if datasets:
            return datasets
    raise ValueError("datasets must be a dataset string or a non-empty list")


def _excerpt(text: str, *, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."
