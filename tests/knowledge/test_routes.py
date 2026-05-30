from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.knowledge.repository import KnowledgeRepository
from backend.src.routes.knowledge import (
    collect_rss_feed_payload,
    collect_web_page_payload,
    get_processed_record_payload,
    list_processed_records_payload,
    search_knowledge_payload,
)


class KnowledgeRouteHandlerTests(unittest.TestCase):
    def test_collect_web_page_payload_returns_context_response(self) -> None:
        response = collect_web_page_payload(
            {
                "url": "https://example.com/nvda",
                "symbol": "NVDA",
                "title": "Manual title",
            },
            fetcher=lambda url: "<html><body>Context-only web note.</body></html>",
        )

        self.assertEqual("context_only", response["mode"])
        self.assertFalse(response["persisted"])
        self.assertIsNone(response["ingest"])
        self.assertEqual("NVDA", response["items"][0]["metadata"]["symbol"])
        self.assertIn("Context-only web note.", response["extraContext"])

    def test_collect_rss_feed_payload_persists_records(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))

            response = collect_rss_feed_payload(
                {
                    "feed_url": "https://example.com/feed.xml",
                    "persist": True,
                    "symbol": "NVDA",
                    "max_items": 1,
                },
                repository=repository,
                fetcher=lambda url: """
                    <rss version="2.0">
                      <channel>
                        <item>
                          <title>NVDA risk update</title>
                          <link>https://example.com/nvda-risk</link>
                          <description>Risk budget should stay bounded.</description>
                        </item>
                      </channel>
                    </rss>
                """,
            )

            self.assertEqual("persist", response["mode"])
            self.assertTrue(response["persisted"])
            self.assertEqual(1, response["ingest"]["count"])
            self.assertEqual(1, len(repository.load_all_processed_records("dynamic")))

    def test_list_get_and_search_processed_records_payloads(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            collect_rss_feed_payload(
                {
                    "feed_url": "https://example.com/feed.xml",
                    "persist": True,
                    "symbol": "NVDA",
                    "max_items": 1,
                },
                repository=repository,
                fetcher=lambda url: """
                    <rss version="2.0">
                      <channel>
                        <item>
                          <title>NVDA catalyst confirmation</title>
                          <link>https://example.com/nvda-confirmation</link>
                          <description>Confirmation improved while event fade risk stayed bounded.</description>
                        </item>
                      </channel>
                    </rss>
                """,
            )

            listed = list_processed_records_payload(
                {"dataset": "dynamic"},
                repository=repository,
            )
            record_name = listed["records"][0]["name"]
            loaded = get_processed_record_payload(
                {"dataset": "dynamic", "name": record_name},
                repository=repository,
            )
            search = search_knowledge_payload(
                {
                    "query": "NVDA catalyst confirmation",
                    "datasets": ["dynamic"],
                    "metadata_filter": {"symbol": "NVDA"},
                },
                repository=repository,
            )

        self.assertEqual(1, listed["count"])
        self.assertNotIn("text", listed["records"][0])
        self.assertIn("Confirmation improved", loaded["text"])
        self.assertEqual(1, search["count"])
        self.assertEqual("NVDA", search["documents"][0]["metadata"]["symbol"])


if __name__ == "__main__":
    unittest.main()
