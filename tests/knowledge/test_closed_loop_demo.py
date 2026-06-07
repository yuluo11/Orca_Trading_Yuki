from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.examples.knowledge_closed_loop_demo import run_demo
from backend.src.models import ALLOWED_DECISION_RECOMMENDATIONS


class KnowledgeClosedLoopDemoTests(unittest.TestCase):
    def test_dynamic_knowledge_closed_loop_demo_runs(self) -> None:
        with TemporaryDirectory() as tmpdir:
            result = run_demo(Path(tmpdir))

        self.assertEqual("success", result["crawl"]["status"])
        self.assertEqual("demo_rss_feed", result["crawl"]["source_id"])
        self.assertEqual(1, result["crawl"]["items"])
        self.assertEqual(1, result["crawl"]["ingested"])
        self.assertEqual(1, result["search"]["count"])
        self.assertIn("NVDA catalyst", result["search"]["top_title"])
        self.assertGreaterEqual(result["analyst"]["document_count"], 1)
        self.assertIn(result["decision"]["recommendation"], ALLOWED_DECISION_RECOMMENDATIONS)
        self.assertTrue(result["reflection"]["persisted"])
        self.assertGreaterEqual(result["processed_record_count"], 2)
        self.assertTrue(result["index_files"])


if __name__ == "__main__":
    unittest.main()
