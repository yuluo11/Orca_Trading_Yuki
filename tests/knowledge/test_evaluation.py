from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.knowledge.evaluation import (
    KnowledgeRetrievalEvaluator,
    parse_eval_case,
)
from backend.src.knowledge.ingest import KnowledgeIngestor
from backend.src.knowledge.repository import KnowledgeRepository


class KnowledgeEvaluationTests(unittest.TestCase):
    def test_parse_eval_case_keeps_user_defined_expectations(self) -> None:
        case = parse_eval_case(
            {
                "case_id": "nvda_event_fade",
                "query": "NVDA event fade risk",
                "datasets": ["dynamic"],
                "expected_symbols": ["NVDA"],
                "expected_categories": ["news"],
                "must_include_terms": ["fade", "risk"],
                "k": 3,
            }
        )

        self.assertEqual("nvda_event_fade", case.case_id)
        self.assertEqual(("dynamic",), case.datasets)
        self.assertEqual(("NVDA",), case.expected_symbols)
        self.assertEqual(("news",), case.expected_categories)
        self.assertEqual(("fade", "risk"), case.must_include_terms)

    def test_evaluator_passes_enabled_fixed_cases_and_skips_disabled_cases(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir) / "data"
            repository = KnowledgeRepository(data_root=data_root)
            ingestor = KnowledgeIngestor(repository)
            ingestor.ingest_text(
                "dynamic",
                "nvda_event_fade_note",
                "NVDA event fade risk remains active while confirmation improves.",
                metadata={"symbol": "NVDA", "category": "news"},
            )
            eval_path = data_root / "manifests" / "knowledge_eval_set.json"
            eval_path.parent.mkdir(parents=True, exist_ok=True)
            eval_path.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "case_id": "nvda_event_fade",
                                "enabled": True,
                                "query": "NVDA event fade risk",
                                "datasets": ["dynamic"],
                                "expected_symbols": ["NVDA"],
                                "expected_categories": ["news"],
                                "must_include_terms": ["fade", "risk"],
                            },
                            {
                                "case_id": "disabled_macro_case",
                                "enabled": False,
                                "query": "macro rate pressure",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            summary = KnowledgeRetrievalEvaluator(repository).evaluate_file(eval_path)

        self.assertTrue(summary.passed)
        self.assertEqual(1, summary.total_count)
        self.assertEqual(1, summary.passed_count)
        self.assertEqual(0, summary.failed_count)
        self.assertEqual(1, summary.skipped_count)
        self.assertEqual("nvda_event_fade", summary.results[0].case_id)
        self.assertGreater(summary.results[0].top_results[0]["score"], 0)

    def test_evaluator_reports_failed_fixed_expectations(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            ingestor = KnowledgeIngestor(repository)
            ingestor.ingest_text(
                "dynamic",
                "amd_generic_note",
                "AMD catalyst context improved without direct NVDA fade discussion.",
                metadata={"symbol": "AMD", "category": "news"},
            )
            case = parse_eval_case(
                {
                    "case_id": "missing_nvda",
                    "query": "AMD catalyst",
                    "datasets": ["dynamic"],
                    "expected_symbols": ["NVDA"],
                    "must_include_terms": ["fade", "risk"],
                }
            )

            summary = KnowledgeRetrievalEvaluator(repository).evaluate_cases([case])

        self.assertFalse(summary.passed)
        self.assertEqual(1, summary.failed_count)
        self.assertIn("Missing expected symbols", summary.results[0].failures[0])
        self.assertTrue(
            any("Missing required terms" in failure for failure in summary.results[0].failures)
        )


if __name__ == "__main__":
    unittest.main()
