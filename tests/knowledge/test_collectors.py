from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.knowledge.collectors import (
    CollectedKnowledgeItem,
    ManualKnowledgeCollector,
    WebPageCollector,
    extract_web_page_text,
    ingest_collected_items,
)
from backend.src.knowledge.collector_service import KnowledgeCollectorService
from backend.src.knowledge.ingest import KnowledgeIngestor
from backend.src.knowledge.policy import KnowledgePolicy
from backend.src.knowledge.repository import KnowledgeRepository


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
        self.assertEqual("https://example.com/markets/nvidia-event-update", item.metadata["source_url"])
        self.assertIn("fade risk", item.text)
        self.assertNotIn("navigation", item.text.lower())

    def test_web_page_collector_can_feed_existing_ingest_pipeline(self) -> None:
        html = """
        <html>
          <head><title>NVIDIA event update</title></head>
          <body>
            <article>
              <p>NVIDIA event momentum remains active while fade risk is still present.</p>
            </article>
          </body>
        </html>
        """
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            ingestor = KnowledgeIngestor(repository)
            collector = WebPageCollector(
                "https://example.com/nvda-event-update",
                symbol="NVDA",
                category="news",
                fetcher=lambda url: html,
            )

            summary = ingest_collected_items(ingestor, collector.collect())
            processed_paths = repository.list_processed_record_paths("dynamic")
            record = repository.load_processed_record("dynamic", processed_paths[0].stem)

        self.assertEqual(1, summary.imported_count)
        self.assertEqual("https://example.com/nvda-event-update", record["metadata"]["source_url"])
        self.assertEqual("NVDA", record["metadata"]["symbol"])

    def test_extract_web_page_text_falls_back_to_readable_body_text(self) -> None:
        extracted = extract_web_page_text(
            "<html><body><p>Readable text should survive extraction for downstream ingest.</p></body></html>"
        )

        self.assertEqual("", extracted.title)
        self.assertIn("Readable text should survive", extracted.text)

    def test_collector_service_can_return_web_page_as_context_only(self) -> None:
        html = """
        <html>
          <head><title>Context only update</title></head>
          <body><article><p>Temporary context should be available without persistence.</p></article></body>
        </html>
        """
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            service = KnowledgeCollectorService(repository=repository)

            result = service.collect_web_page(
                "https://example.com/context-only",
                fetcher=lambda url: html,
            )
            processed_paths = repository.list_processed_record_paths("dynamic")

        self.assertFalse(result.persisted)
        self.assertEqual("context_only", result.mode)
        self.assertEqual(1, len(result.items))
        self.assertEqual([], processed_paths)
        self.assertIn("Context only update", result.as_extra_context())
        self.assertIn("Temporary context", result.as_extra_context())

    def test_collector_service_can_persist_web_page_to_dynamic_knowledge(self) -> None:
        html = """
        <html>
          <head><title>Persisted URL update</title></head>
          <body><article><p>Persisted URL context should become dynamic knowledge.</p></article></body>
        </html>
        """
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            service = KnowledgeCollectorService(repository=repository)

            result = service.collect_web_page(
                "https://example.com/persisted-url-update",
                persist=True,
                symbol="NVDA",
                category="news",
                fetcher=lambda url: html,
            )
            processed_paths = repository.list_processed_record_paths("dynamic")
            record = repository.load_processed_record("dynamic", processed_paths[0].stem)

        self.assertTrue(result.persisted)
        self.assertEqual("persist", result.mode)
        self.assertEqual(1, result.ingest_summary.imported_count)
        self.assertEqual("NVDA", record["metadata"]["symbol"])
        self.assertEqual("news", record["metadata"]["category"])

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
