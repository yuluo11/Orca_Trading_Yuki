from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.app import collect_rss_feed_knowledge, collect_web_page_knowledge
from backend.src.knowledge.repository import KnowledgeRepository


class KnowledgeCollectorAppEntryTests(unittest.TestCase):
    def test_collect_web_page_knowledge_persists_dynamic_record(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))

            result = collect_web_page_knowledge(
                url="https://example.com/nvda",
                persist=True,
                symbol="NVDA",
                repository=repository,
                fetcher=lambda url: "<html><title>NVDA catalyst</title><body>Fresh context.</body></html>",
            )

            self.assertTrue(result.persisted)
            self.assertEqual("persist", result.mode)
            self.assertEqual(1, result.ingest_summary.imported_count)
            self.assertEqual(1, len(repository.load_all_processed_records("dynamic")))

    def test_collect_rss_feed_knowledge_returns_context_only(self) -> None:
        result = collect_rss_feed_knowledge(
            feed_url="https://example.com/feed.xml",
            max_items=1,
            fetcher=lambda url: """
                <rss version="2.0">
                  <channel>
                    <item>
                      <title>NVDA catalyst update</title>
                      <link>https://example.com/nvda</link>
                      <description>Guidance remains supportive.</description>
                    </item>
                  </channel>
                </rss>
            """,
        )

        self.assertFalse(result.persisted)
        self.assertEqual("context_only", result.mode)
        self.assertIn("Guidance remains supportive.", result.as_extra_context())


if __name__ == "__main__":
    unittest.main()
