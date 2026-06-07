from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
import unittest
from unittest.mock import patch

from backend.src.knowledge.repository import KnowledgeRepository


class FakeHTTPException(Exception):
    def __init__(self, *, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class FakeFastAPI:
    def __init__(self, **metadata: object) -> None:
        self.metadata = metadata
        self.routes: dict[tuple[str, str], object] = {}

    def get(self, path: str):
        return self._register("GET", path)

    def post(self, path: str):
        return self._register("POST", path)

    def _register(self, method: str, path: str):
        def decorator(func):
            self.routes[(method, path)] = func
            return func

        return decorator


def fake_fastapi_module() -> ModuleType:
    module = ModuleType("fastapi")
    module.FastAPI = FakeFastAPI
    module.HTTPException = FakeHTTPException
    return module


class KnowledgeApiAdapterTests(unittest.TestCase):
    def test_create_knowledge_api_registers_expected_routes(self) -> None:
        with patch.dict(sys.modules, {"fastapi": fake_fastapi_module()}):
            from backend.src.api.knowledge_api import create_knowledge_api

            app = create_knowledge_api()

        self.assertEqual(
            "Orca Trading Yuki Knowledge API",
            app.metadata["title"],
        )
        self.assertIn(("GET", "/health"), app.routes)
        self.assertIn(("POST", "/knowledge/search"), app.routes)
        self.assertIn(("POST", "/knowledge/sources/run-due"), app.routes)
        self.assertEqual(
            {"status": "ok", "service": "knowledge-api"},
            app.routes[("GET", "/health")](),
        )

    def test_knowledge_api_delegates_to_framework_neutral_handlers(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))

            with patch.dict(sys.modules, {"fastapi": fake_fastapi_module()}):
                from backend.src.api.knowledge_api import create_knowledge_api

                app = create_knowledge_api(
                    repository=repository,
                    rss_fetcher=lambda url: """
                        <rss version="2.0">
                          <channel>
                            <item>
                              <title>NVDA catalyst confirmation</title>
                              <link>https://example.com/nvda-confirmation</link>
                              <description>Confirmation improved while risk stayed bounded.</description>
                            </item>
                          </channel>
                        </rss>
                    """,
                )

            collect = app.routes[("POST", "/knowledge/collect/rss-feed")](
                {
                    "feed_url": "https://example.com/feed.xml",
                    "persist": True,
                    "symbol": "NVDA",
                    "max_items": 1,
                }
            )
            search = app.routes[("POST", "/knowledge/search")](
                {
                    "query": "NVDA catalyst confirmation",
                    "datasets": ["dynamic"],
                    "metadata_filter": {"symbol": "NVDA"},
                }
            )

        self.assertTrue(collect["persisted"])
        self.assertEqual(1, collect["ingest"]["count"])
        self.assertEqual(1, search["count"])
        self.assertEqual("NVDA", search["documents"][0]["metadata"]["symbol"])

    def test_knowledge_api_converts_handler_errors_to_http_errors(self) -> None:
        with patch.dict(sys.modules, {"fastapi": fake_fastapi_module()}):
            from backend.src.api.knowledge_api import create_knowledge_api

            app = create_knowledge_api()

        with self.assertRaises(FakeHTTPException) as context:
            app.routes[("POST", "/knowledge/search")]({})

        self.assertEqual(400, context.exception.status_code)
        self.assertIn("Missing required string field: query", context.exception.detail)


if __name__ == "__main__":
    unittest.main()
