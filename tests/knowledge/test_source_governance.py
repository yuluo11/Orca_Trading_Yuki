from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.knowledge.collector_service import KnowledgeCollectorService
from backend.src.knowledge.repository import KnowledgeRepository
from backend.src.knowledge.source_governance import (
    DataSourceRule,
    DynamicSourceGovernancePolicy,
    SourceGovernanceError,
)
from backend.src.routes.knowledge import collect_rss_feed_payload


RSS_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>NVDA first source governed item</title>
      <link>https://trusted.example.com/nvda-first</link>
      <description>First item should pass governance.</description>
    </item>
    <item>
      <title>NVDA second source governed item</title>
      <link>https://trusted.example.com/nvda-second</link>
      <description>Second item should be capped by policy.</description>
    </item>
  </channel>
</rss>
"""


class SourceGovernanceTests(unittest.TestCase):
    def test_source_rule_enriches_metadata_and_caps_feed_items(self) -> None:
        policy = DynamicSourceGovernancePolicy(
            rules=(
                DataSourceRule(
                    name="trusted_news_feed",
                    domains=("trusted.example.com",),
                    source_types=("rss_feed",),
                    default_category="news",
                    reliability="high",
                    trust_score=0.95,
                    max_items_per_collect=1,
                    min_refresh_interval_minutes=30,
                ),
            )
        )
        service = KnowledgeCollectorService(source_policy=policy)

        result = service.collect_rss_feed(
            "https://trusted.example.com/feed.xml",
            max_items=10,
            fetcher=lambda url: RSS_XML,
        )

        self.assertEqual(1, len(result.items))
        metadata = result.items[0].metadata
        self.assertEqual("trusted_news_feed", metadata["source_rule"])
        self.assertEqual("trusted.example.com", metadata["source_domain"])
        self.assertEqual("high", metadata["reliability"])
        self.assertEqual(0.95, metadata["source_trust_score"])
        self.assertEqual(30, metadata["source_min_refresh_interval_minutes"])

    def test_source_rule_can_constrain_url_paths(self) -> None:
        policy = DynamicSourceGovernancePolicy(
            rules=(
                DataSourceRule(
                    name="filing_articles_only",
                    domains=("trusted.example.com",),
                    allowed_path_prefixes=("/markets/",),
                    blocked_path_keywords=("sponsored",),
                ),
            )
        )

        decision = policy.evaluate(
            "https://trusted.example.com/markets/nvda-update",
            source_type="web_page",
            category="news",
        )

        self.assertEqual("filing_articles_only", decision.rule_name)
        self.assertGreater(decision.trust_score, 0)
        with self.assertRaises(SourceGovernanceError):
            policy.evaluate(
                "https://trusted.example.com/blog/nvda-update",
                source_type="web_page",
                category="news",
            )
        with self.assertRaises(SourceGovernanceError):
            policy.evaluate(
                "https://trusted.example.com/markets/sponsored-nvda-update",
                source_type="web_page",
                category="news",
            )

    def test_blocked_source_is_rejected_before_fetch(self) -> None:
        policy = DynamicSourceGovernancePolicy(blocked_domains=("blocked.example.com",))
        service = KnowledgeCollectorService(source_policy=policy)
        fetch_calls: list[str] = []

        with self.assertRaises(SourceGovernanceError):
            service.collect_web_page(
                "https://blocked.example.com/article",
                fetcher=lambda url: fetch_calls.append(url) or "<html />",
            )

        self.assertEqual([], fetch_calls)

    def test_route_handler_accepts_injected_source_policy(self) -> None:
        policy = DynamicSourceGovernancePolicy(
            rules=(
                DataSourceRule(
                    name="approved_route_feed",
                    domains=("route.example.com",),
                    source_types=("rss_feed",),
                    reliability="high",
                ),
            ),
            allowed_domains=("route.example.com",),
            allow_unregistered_sources=False,
        )
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            response = collect_rss_feed_payload(
                {
                    "feed_url": "https://route.example.com/feed.xml",
                    "persist": True,
                    "max_items": 1,
                },
                repository=repository,
                source_policy=policy,
                fetcher=lambda url: RSS_XML,
            )
            record = repository.load_all_processed_records("dynamic")[0]

        self.assertTrue(response["persisted"])
        self.assertEqual("approved_route_feed", record["metadata"]["source_rule"])
        self.assertEqual("high", record["metadata"]["reliability"])

    def test_unregistered_source_can_be_disallowed(self) -> None:
        policy = DynamicSourceGovernancePolicy(allow_unregistered_sources=False)
        service = KnowledgeCollectorService(source_policy=policy)

        with self.assertRaises(SourceGovernanceError):
            service.collect_rss_feed(
                "https://unknown.example.net/feed.xml",
                fetcher=lambda url: RSS_XML,
            )


if __name__ == "__main__":
    unittest.main()
