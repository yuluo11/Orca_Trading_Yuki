from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.knowledge.collector_service import KnowledgeCollectorService
from backend.src.knowledge.collectors import (
    CollectedKnowledgeItem,
    ManualKnowledgeCollector,
    RSSNewsCollector,
    WebPageCollectionError,
    WebPageCollector,
    extract_web_page_text,
    ingest_collected_items,
    parse_feed_items,
)
from backend.src.knowledge.ingest import KnowledgeIngestor
from backend.src.knowledge.policy import KnowledgePolicy
from backend.src.knowledge.repository import KnowledgeRepository


RSS_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Market Feed</title>
    <item>
      <title>NVDA rebound faces fade risk</title>
      <link>https://example.com/nvda-fade</link>
      <description>Momentum improved, but event fade risk remains active.</description>
      <pubDate>Mon, 18 May 2026 08:00:00 GMT</pubDate>
    </item>
    <item>
      <title>TSLA volume expands</title>
      <link>https://example.com/tsla-volume</link>
      <description>Volume confirmation improved.</description>
    </item>
  </channel>
</rss>
"""


ATOM_XML = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Macro pressure cools risk appetite</title>
    <link href="https://example.com/macro-risk" />
    <summary>Rates pressure weighed on growth exposure.</summary>
    <updated>2026-05-18T09:00:00Z</updated>
  </entry>
</feed>
"""


class KnowledgeCollectorTests(unittest.TestCase):
    def test_manual_collector_ingests_dynamic_items_and_refreshes_index(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            policy = KnowledgePolicy()
            policy.indexing.rebuild_after_processed_updates = True
            policy.indexing.snapshot_enabled = True
            ingestor = KnowledgeIngestor(repository, policy=policy)
            collector = ManualKnowledgeCollector(
                [
                    CollectedKnowledgeItem(
                        name="nvda_event_news_manual",
                        text="NVIDIA event momentum remains active while fade risk is still present.",
                        metadata={
                            "source": "manual_dynamic_seed",
                            "title": "NVDA Event News Manual",
                            "category": "news",
                            "symbol": "NVDA",
                            "topic": "event momentum",
                            "reliability": "medium",
                            "time_sensitivity": "high",
                        },
                    )
                ]
            )

            summary = ingest_collected_items(ingestor, collector.collect())
            record = repository.load_processed_record("dynamic", "nvda_event_news_manual")
            index_path = repository.indexes / "dynamic_auto_index.json"
            index_exists = index_path.exists()

        self.assertEqual(1, summary.imported_count)
        self.assertEqual("dynamic", record["metadata"]["dataset"])
        self.assertEqual("news", record["metadata"]["category"])
        self.assertEqual("NVDA", record["metadata"]["symbol"])
        self.assertTrue(index_exists)

    def test_web_page_collector_extracts_single_url_into_dynamic_item(self) -> None:
        html = """
        <html>
          <head>
            <title>NVIDIA event update</title>
            <meta name="author" content="Market Desk" />
            <meta property="article:published_time" content="2026-05-31T01:00:00Z" />
            <style>.hidden { display: none; }</style>
          </head>
          <body>
            <nav>This navigation should not become knowledge.</nav>
            <article>
              <h1>NVIDIA event update</h1>
              <p>NVIDIA shares held momentum after a product event, while analysts debated fade risk.</p>
              <p>Volume remained elevated and follow-through confirmation was still incomplete.</p>
            </article>
          </body>
        </html>
        """
        collector = WebPageCollector(
            "https://example.com/markets/nvidia-event-update",
            symbol="NVDA",
            category="news",
            fetcher=lambda url: html,
        )

        items = collector.collect()

        self.assertEqual(1, len(items))
        item = items[0]
        self.assertEqual("dynamic", item.dataset)
        self.assertEqual("NVIDIA event update", item.metadata["title"])
        self.assertEqual("NVDA", item.metadata["symbol"])
        self.assertEqual("news", item.metadata["category"])
        self.assertEqual("Market Desk", item.metadata["author"])
        self.assertEqual("2026-05-31T01:00:00Z", item.metadata["published_at"])
        self.assertEqual("primary_content", item.metadata["extraction_method"])
        self.assertEqual("https://example.com/markets/nvidia-event-update", item.metadata["source_url"])
        self.assertIn("fade risk", item.text)
        self.assertNotIn("navigation", item.text.lower())

    def test_web_page_collector_rejects_non_http_urls(self) -> None:
        collector = WebPageCollector("file:///tmp/local.html", fetcher=lambda url: "<html />")

        with self.assertRaises(WebPageCollectionError):
            collector.collect()

    def test_extract_web_page_text_returns_title_and_body(self) -> None:
        extracted = extract_web_page_text(
            "<html><title>Setup</title><body><h1>Headline</h1><p>Body text.</p></body></html>"
        )

        self.assertEqual("Setup", extracted.title)
        self.assertIn("Headline Body text.", extracted.text)

    def test_extract_web_page_text_prefers_article_and_meta_description(self) -> None:
        extracted = extract_web_page_text(
            """
            <html>
              <head>
                <script type="application/ld+json">
                  {
                    "@type": "NewsArticle",
                    "headline": "NVDA article title",
                    "description": "Article summary for search snippets.",
                    "author": {"name": "Research Desk"},
                    "datePublished": "2026-05-31T02:30:00Z"
                  }
                </script>
              </head>
              <body>
                <aside>Subscribe now and share this page.</aside>
                <div class="related">Related links should not dominate extraction.</div>
                <article>
                  <h1>NVDA article title</h1>
                  <p>Fresh AI infrastructure commentary supported the catalyst setup.</p>
                  <p>Event fade risk still needs confirmation before position sizing.</p>
                </article>
                <footer>Boilerplate footer should be skipped.</footer>
              </body>
            </html>
            """
        )

        self.assertEqual("NVDA article title", extracted.title)
        self.assertEqual("Article summary for search snippets.", extracted.description)
        self.assertEqual("Research Desk", extracted.author)
        self.assertEqual("2026-05-31T02:30:00Z", extracted.published_at)
        self.assertEqual("primary_content", extracted.extraction_method)
        self.assertIn("AI infrastructure commentary", extracted.text)
        self.assertIn("Event fade risk", extracted.text)
        self.assertNotIn("Subscribe now", extracted.text)
        self.assertNotIn("footer", extracted.text.lower())

    def test_extract_web_page_text_closes_primary_container_scope(self) -> None:
        extracted = extract_web_page_text(
            """
            <html>
              <body>
                <div class="main-content">
                  <p>Primary market commentary has enough detail to be selected as content.</p>
                  <p>It includes catalyst context, risk framing, and confirmation notes.</p>
                </div>
                <div class="related">Related sidebar should stay outside the primary extraction.</div>
              </body>
            </html>
            """
        )

        self.assertEqual("primary_content", extracted.extraction_method)
        self.assertIn("Primary market commentary", extracted.text)
        self.assertNotIn("Related sidebar", extracted.text)

    def test_rss_news_collector_parses_feed_items(self) -> None:
        collector = RSSNewsCollector(
            "https://example.com/feed.xml",
            symbol="NVDA",
            topic="semiconductor catalyst",
            max_items=1,
            fetcher=lambda url: RSS_XML,
        )

        items = collector.collect()

        self.assertEqual(1, len(items))
        self.assertEqual("dynamic", items[0].dataset)
        self.assertIn("fade risk", items[0].text)
        self.assertEqual("news", items[0].metadata["category"])
        self.assertEqual("NVDA", items[0].metadata["symbol"])
        self.assertEqual("https://example.com/nvda-fade", items[0].metadata["source_url"])

    def test_parse_feed_items_supports_atom_entries(self) -> None:
        items = parse_feed_items(ATOM_XML)

        self.assertEqual(1, len(items))
        self.assertEqual("Macro pressure cools risk appetite", items[0]["title"])
        self.assertEqual("https://example.com/macro-risk", items[0]["link"])
        self.assertIn("Rates pressure", items[0]["summary"])

    def test_collector_service_can_return_web_page_as_context_only(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            service = KnowledgeCollectorService(repository=repository)

            result = service.collect_web_page(
                "https://example.com/context-only",
                fetcher=lambda url: (
                    "<html><head><title>Context only update</title></head>"
                    "<body><article><p>Temporary context should be available without persistence.</p>"
                    "</article></body></html>"
                ),
            )

            self.assertFalse(result.persisted)
            self.assertEqual("context_only", result.mode)
            self.assertEqual([], repository.list_processed_record_paths("dynamic"))
            self.assertIn("Temporary context", result.as_extra_context())

    def test_collector_service_can_persist_web_page(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            service = KnowledgeCollectorService(repository=repository)

            result = service.collect_web_page(
                "https://example.com/nvda",
                persist=True,
                symbol="NVDA",
                fetcher=lambda url: "<html><title>NVDA</title><body>Dynamic context.</body></html>",
            )

            self.assertTrue(result.persisted)
            self.assertEqual(1, result.ingest_summary.imported_count)
            self.assertEqual(1, len(repository.load_all_processed_records("dynamic")))
            self.assertIn("Dynamic context.", result.as_extra_context())

    def test_collector_service_can_persist_rss_feed(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            service = KnowledgeCollectorService(repository=repository)

            result = service.collect_rss_feed(
                "https://example.com/feed.xml",
                persist=True,
                symbol="NVDA",
                max_items=2,
                fetcher=lambda url: RSS_XML,
            )

            self.assertTrue(result.persisted)
            self.assertEqual(2, result.ingest_summary.imported_count)
            self.assertEqual(2, len(repository.load_all_processed_records("dynamic")))
            self.assertIn("NVDA rebound", result.as_extra_context())

    def test_collection_result_context_can_be_limited_for_prompt_usage(self) -> None:
        result = KnowledgeCollectorService().collect_web_page(
            "https://example.com/long-context",
            fetcher=lambda url: (
                "<html><head><title>Long context</title></head><body>"
                "<p>" + ("context " * 200) + "</p>"
                "</body></html>"
            ),
        )

        context = result.as_extra_context(max_chars=120)

        self.assertLessEqual(len(context), 120)
        self.assertTrue(context.endswith("..."))


if __name__ == "__main__":
    unittest.main()
