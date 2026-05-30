from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.knowledge.repository import KnowledgeRepository
from backend.src.routes.knowledge import collect_rss_feed_payload, collect_web_page_payload


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


if __name__ == "__main__":
    unittest.main()
