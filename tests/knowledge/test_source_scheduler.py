from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.knowledge.repository import KnowledgeRepository
from backend.src.knowledge.source_governance import DataSourceRule, DynamicSourceGovernancePolicy
from backend.src.knowledge.source_scheduler import DynamicKnowledgeCrawlScheduler, to_iso
from backend.src.routes.knowledge import (
    list_dynamic_sources_payload,
    register_dynamic_source_payload,
    run_due_dynamic_sources_payload,
)


RSS_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>NVDA scheduled catalyst update</title>
      <link>https://schedule.example.com/nvda-catalyst</link>
      <description>Scheduled crawl captured catalyst and event fade context.</description>
    </item>
  </channel>
</rss>
"""


def build_policy() -> DynamicSourceGovernancePolicy:
    return DynamicSourceGovernancePolicy(
        rules=(
            DataSourceRule(
                name="scheduled_test_feed",
                domains=("schedule.example.com",),
                source_types=("rss_feed",),
                default_category="news",
                reliability="high",
                min_refresh_interval_minutes=45,
            ),
        ),
        allow_unregistered_sources=False,
    )


class DynamicKnowledgeCrawlSchedulerTests(unittest.TestCase):
    def test_register_source_persists_schedule_and_uses_governance_defaults(self) -> None:
        now = datetime(2026, 5, 18, 8, 0, tzinfo=UTC)
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            scheduler = DynamicKnowledgeCrawlScheduler(
                repository=repository,
                source_policy=build_policy(),
            )

            source = scheduler.register_source(
                source_id="nvda_feed",
                source_type="rss_feed",
                url="https://schedule.example.com/feed.xml",
                symbol="NVDA",
                now=now,
            )
            loaded_sources = scheduler.list_sources()

        self.assertEqual("nvda_feed", source.source_id)
        self.assertEqual("scheduled_test_feed", source.source_rule)
        self.assertEqual(45, source.refresh_interval_minutes)
        self.assertEqual(1, len(loaded_sources))
        self.assertEqual("nvda_feed", loaded_sources[0].source_id)

    def test_run_due_sources_collects_and_updates_schedule_state(self) -> None:
        now = datetime(2026, 5, 18, 8, 0, tzinfo=UTC)
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            scheduler = DynamicKnowledgeCrawlScheduler(
                repository=repository,
                source_policy=build_policy(),
            )
            scheduler.register_source(
                source_id="nvda_feed",
                source_type="rss_feed",
                url="https://schedule.example.com/feed.xml",
                symbol="NVDA",
                next_run_at=to_iso(now),
                now=now,
            )

            results = scheduler.run_due_sources(
                now=now,
                fetchers={"nvda_feed": lambda url: RSS_XML},
            )
            updated_source = scheduler.list_sources()[0]
            records = repository.load_all_processed_records("dynamic")
            not_due_results = scheduler.run_due_sources(
                now=now,
                fetchers={"nvda_feed": lambda url: RSS_XML},
            )

        self.assertEqual(1, len(results))
        self.assertEqual("success", results[0].status)
        self.assertEqual(1, results[0].collected_count)
        self.assertEqual(1, results[0].imported_count)
        self.assertEqual("success", updated_source.last_status)
        self.assertEqual(0, updated_source.consecutive_failures)
        self.assertEqual(1, len(records))
        self.assertEqual([], not_due_results)

    def test_failed_crawl_updates_error_and_retry_time(self) -> None:
        now = datetime(2026, 5, 18, 8, 0, tzinfo=UTC)
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            scheduler = DynamicKnowledgeCrawlScheduler(
                repository=repository,
                source_policy=build_policy(),
            )
            scheduler.register_source(
                source_id="broken_feed",
                source_type="rss_feed",
                url="https://schedule.example.com/broken.xml",
                next_run_at=to_iso(now),
                now=now,
            )

            result = scheduler.run_source(
                "broken_feed",
                now=now,
                fetcher=lambda url: (_ for _ in ()).throw(RuntimeError("feed timeout")),
                force=True,
            )
            updated_source = scheduler.list_sources()[0]

        self.assertEqual("failed", result.status)
        self.assertIn("feed timeout", result.error)
        self.assertEqual("failed", updated_source.last_status)
        self.assertEqual(1, updated_source.consecutive_failures)
        self.assertIn("feed timeout", updated_source.last_error)
        self.assertIsNotNone(updated_source.next_run_at)

    def test_route_handlers_register_list_and_run_due_sources(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            registered = register_dynamic_source_payload(
                {
                    "source_id": "route_feed",
                    "source_type": "rss_feed",
                    "url": "https://schedule.example.com/feed.xml",
                    "symbol": "NVDA",
                    "max_items": 1,
                },
                repository=repository,
                source_policy=build_policy(),
            )
            listed = list_dynamic_sources_payload({}, repository=repository)
            run_result = run_due_dynamic_sources_payload(
                {},
                repository=repository,
                source_policy=build_policy(),
                fetchers={"route_feed": lambda url: RSS_XML},
            )

        self.assertEqual("route_feed", registered["sourceId"])
        self.assertEqual(1, listed["count"])
        self.assertEqual(1, run_result["count"])
        self.assertEqual("success", run_result["results"][0]["status"])


if __name__ == "__main__":
    unittest.main()
