from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.app import collect_web_page_knowledge
from backend.src.knowledge.repository import KnowledgeRepository


class KnowledgeCollectorAppEntryTests(unittest.TestCase):
    def test_collect_web_page_knowledge_can_persist_dynamic_record(self) -> None:
        html = """
        <html>
          <head><title>NVIDIA URL note</title></head>
          <body><article><p>NVIDIA URL note should enter dynamic knowledge.</p></article></body>
        </html>
        """
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))

            result = collect_web_page_knowledge(
                url="https://example.com/nvidia-url-note",
                persist=True,
                category="news",
                symbol="NVDA",
                repository=repository,
                fetcher=lambda url: html,
            )
            processed_paths = repository.list_processed_record_paths("dynamic")

        self.assertTrue(result.persisted)
        self.assertEqual("persist", result.mode)
        self.assertEqual(1, result.ingest_summary.imported_count)
        self.assertEqual(1, len(processed_paths))


if __name__ == "__main__":
    unittest.main()
