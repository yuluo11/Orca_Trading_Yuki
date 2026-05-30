"""Persistent scheduler for dynamic knowledge source crawls."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import json
import re
from typing import Any, Literal

from .collector_service import KnowledgeCollectorService
from .collectors import HtmlFetcher
from .repository import DatasetName, KnowledgeRepository
from .source_governance import (
    DEFAULT_DYNAMIC_SOURCE_GOVERNANCE,
    DynamicSourceGovernancePolicy,
    SourceGovernanceDecision,
    SourceType,
)

CrawlStatus = Literal["never_run", "success", "failed", "skipped"]


@dataclass(slots=True)
class ScheduledKnowledgeSource:
    """A persisted dynamic source subscription."""

    source_id: str
    source_type: SourceType
    url: str
    dataset: DatasetName = "dynamic"
    category: str = "news"
    enabled: bool = True
    symbol: str | None = None
    topic: str | None = None
    title: str | None = None
    max_items: int = 10
    refresh_interval_minutes: int = 60
    next_run_at: str | None = None
    last_run_at: str | None = None
    last_success_at: str | None = None
    last_status: CrawlStatus = "never_run"
    last_error: str | None = None
    consecutive_failures: int = 0
    source_rule: str | None = None
    source_domain: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(slots=True)
class CrawlRunResult:
    """Outcome of one scheduled crawl run."""

    source_id: str
    status: CrawlStatus
    collected_count: int = 0
    imported_count: int = 0
    skipped_count: int = 0
    error: str | None = None
    ran_at: str | None = None
    next_run_at: str | None = None


class DynamicSourceScheduleStore:
    """Persist scheduled dynamic sources under the knowledge manifest directory."""

    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository
        self.path = repository.manifests / "dynamic_source_schedule.json"

    def load_sources(self) -> list[ScheduledKnowledgeSource]:
        """Load all scheduled sources from disk."""
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        sources = payload.get("sources", [])
        if not isinstance(sources, list):
            raise ValueError(f"Schedule file {self.path} must contain a sources list")
        return [ScheduledKnowledgeSource(**source) for source in sources]

    def save_sources(self, sources: list[ScheduledKnowledgeSource]) -> None:
        """Write scheduled sources to disk."""
        self.repository.manifests.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": utc_now_iso(),
            "sources": [asdict(source) for source in sources],
        }
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)


class DynamicKnowledgeCrawlScheduler:
    """Register sources, find due crawls, and execute scheduled collections."""

    def __init__(
        self,
        repository: KnowledgeRepository | None = None,
        *,
        source_policy: DynamicSourceGovernancePolicy | None = None,
        collector_service: KnowledgeCollectorService | None = None,
        store: DynamicSourceScheduleStore | None = None,
    ) -> None:
        self.repository = repository or KnowledgeRepository()
        self.source_policy = source_policy or DEFAULT_DYNAMIC_SOURCE_GOVERNANCE
        self.collector_service = collector_service or KnowledgeCollectorService(
            repository=self.repository,
            source_policy=self.source_policy,
        )
        self.store = store or DynamicSourceScheduleStore(self.repository)

    def register_source(
        self,
        *,
        source_type: SourceType,
        url: str,
        source_id: str | None = None,
        dataset: DatasetName = "dynamic",
        category: str = "news",
        enabled: bool = True,
        symbol: str | None = None,
        topic: str | None = None,
        title: str | None = None,
        max_items: int = 10,
        refresh_interval_minutes: int | None = None,
        next_run_at: str | None = None,
        now: datetime | None = None,
    ) -> ScheduledKnowledgeSource:
        """Create or update one scheduled source."""
        current_time = now or datetime.now(UTC)
        governance = self.source_policy.evaluate(url, source_type=source_type, category=category)
        resolved_interval = (
            refresh_interval_minutes
            or governance.min_refresh_interval_minutes
            or 60
        )
        resolved_id = source_id or build_source_id(source_type, url)
        source = ScheduledKnowledgeSource(
            source_id=resolved_id,
            source_type=source_type,
            url=url,
            dataset=dataset,
            category=governance.category,
            enabled=enabled,
            symbol=symbol,
            topic=topic,
            title=title,
            max_items=max_items,
            refresh_interval_minutes=resolved_interval,
            next_run_at=next_run_at or to_iso(current_time),
            source_rule=governance.rule_name,
            source_domain=governance.domain,
            created_at=to_iso(current_time),
            updated_at=to_iso(current_time),
        )
        sources = [
            existing
            for existing in self.store.load_sources()
            if existing.source_id != resolved_id
        ]
        sources.append(source)
        sources.sort(key=lambda item: item.source_id)
        self.store.save_sources(sources)
        return source

    def list_sources(self, *, include_disabled: bool = True) -> list[ScheduledKnowledgeSource]:
        """Return scheduled sources, optionally hiding disabled entries."""
        sources = self.store.load_sources()
        if include_disabled:
            return sources
        return [source for source in sources if source.enabled]

    def due_sources(self, *, now: datetime | None = None) -> list[ScheduledKnowledgeSource]:
        """Return enabled sources whose next_run_at has passed."""
        current_time = now or datetime.now(UTC)
        return [
            source
            for source in self.store.load_sources()
            if source.enabled and is_due(source, current_time)
        ]

    def run_due_sources(
        self,
        *,
        now: datetime | None = None,
        fetchers: dict[str, HtmlFetcher] | None = None,
    ) -> list[CrawlRunResult]:
        """Run all due sources and persist their updated schedule state."""
        current_time = now or datetime.now(UTC)
        due_ids = {source.source_id for source in self.due_sources(now=current_time)}
        results: list[CrawlRunResult] = []
        for source_id in due_ids:
            results.append(
                self.run_source(
                    source_id,
                    now=current_time,
                    fetcher=(fetchers or {}).get(source_id),
                    force=True,
                )
            )
        return results

    def run_source(
        self,
        source_id: str,
        *,
        now: datetime | None = None,
        fetcher: HtmlFetcher | None = None,
        force: bool = False,
    ) -> CrawlRunResult:
        """Run one source by id and update its persisted status."""
        current_time = now or datetime.now(UTC)
        sources = self.store.load_sources()
        source = find_source(sources, source_id)
        if source is None:
            raise KeyError(f"Scheduled source not found: {source_id}")

        if not source.enabled:
            result = CrawlRunResult(
                source_id=source.source_id,
                status="skipped",
                error="Source is disabled.",
                ran_at=to_iso(current_time),
                next_run_at=source.next_run_at,
            )
            return result

        if not force and not is_due(source, current_time):
            return CrawlRunResult(
                source_id=source.source_id,
                status="skipped",
                error="Source is not due yet.",
                ran_at=to_iso(current_time),
                next_run_at=source.next_run_at,
            )

        try:
            collection = self._collect_source(source, fetcher=fetcher)
        except Exception as error:  # noqa: BLE001 - failures are scheduler state.
            updated = mark_failed(source, error, current_time)
            self._replace_source(sources, updated)
            return CrawlRunResult(
                source_id=source.source_id,
                status="failed",
                error=str(error),
                ran_at=updated.last_run_at,
                next_run_at=updated.next_run_at,
            )

        imported_count = (
            collection.ingest_summary.imported_count
            if collection.ingest_summary
            else 0
        )
        skipped_count = (
            collection.ingest_summary.skipped_count
            if collection.ingest_summary
            else 0
        )
        updated = mark_success(source, current_time)
        self._replace_source(sources, updated)
        return CrawlRunResult(
            source_id=source.source_id,
            status="success",
            collected_count=len(collection.items),
            imported_count=imported_count,
            skipped_count=skipped_count,
            ran_at=updated.last_run_at,
            next_run_at=updated.next_run_at,
        )

    def _collect_source(
        self,
        source: ScheduledKnowledgeSource,
        *,
        fetcher: HtmlFetcher | None,
    ) -> Any:
        if source.source_type == "rss_feed":
            return self.collector_service.collect_rss_feed(
                source.url,
                persist=True,
                dataset=source.dataset,
                category=source.category,
                symbol=source.symbol,
                topic=source.topic,
                max_items=source.max_items,
                fetcher=fetcher,
            )
        if source.source_type == "web_page":
            return self.collector_service.collect_web_page(
                source.url,
                persist=True,
                dataset=source.dataset,
                category=source.category,
                symbol=source.symbol,
                topic=source.topic,
                title=source.title,
                fetcher=fetcher,
            )
        raise ValueError(f"Unsupported source_type: {source.source_type}")

    def _replace_source(
        self,
        sources: list[ScheduledKnowledgeSource],
        updated_source: ScheduledKnowledgeSource,
    ) -> None:
        updated_sources = [
            updated_source if source.source_id == updated_source.source_id else source
            for source in sources
        ]
        self.store.save_sources(updated_sources)


def find_source(
    sources: list[ScheduledKnowledgeSource],
    source_id: str,
) -> ScheduledKnowledgeSource | None:
    """Find a source by id."""
    for source in sources:
        if source.source_id == source_id:
            return source
    return None


def is_due(source: ScheduledKnowledgeSource, now: datetime) -> bool:
    """Return whether a source is due at the provided time."""
    if source.next_run_at is None:
        return True
    return parse_iso(source.next_run_at) <= now


def mark_success(
    source: ScheduledKnowledgeSource,
    now: datetime,
) -> ScheduledKnowledgeSource:
    """Return a source updated after a successful run."""
    next_run = now + timedelta(minutes=source.refresh_interval_minutes)
    return ScheduledKnowledgeSource(
        **{
            **asdict(source),
            "last_run_at": to_iso(now),
            "last_success_at": to_iso(now),
            "last_status": "success",
            "last_error": None,
            "consecutive_failures": 0,
            "next_run_at": to_iso(next_run),
            "updated_at": to_iso(now),
        }
    )


def mark_failed(
    source: ScheduledKnowledgeSource,
    error: Exception,
    now: datetime,
) -> ScheduledKnowledgeSource:
    """Return a source updated after a failed run."""
    backoff_minutes = max(source.refresh_interval_minutes, min(1440, 15 * (source.consecutive_failures + 1)))
    next_run = now + timedelta(minutes=backoff_minutes)
    return ScheduledKnowledgeSource(
        **{
            **asdict(source),
            "last_run_at": to_iso(now),
            "last_status": "failed",
            "last_error": str(error),
            "consecutive_failures": source.consecutive_failures + 1,
            "next_run_at": to_iso(next_run),
            "updated_at": to_iso(now),
        }
    )


def build_source_id(source_type: SourceType, url: str) -> str:
    """Build a stable source id from source type and URL."""
    normalized = re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")
    return f"{source_type}_{normalized}"[:120]


def parse_iso(value: str) -> datetime:
    """Parse scheduler timestamps."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def to_iso(value: datetime) -> str:
    """Render scheduler timestamps as UTC ISO strings."""
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_now_iso() -> str:
    """Return current UTC timestamp."""
    return to_iso(datetime.now(UTC))
