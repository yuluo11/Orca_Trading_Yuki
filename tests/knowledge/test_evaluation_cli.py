from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.knowledge.evaluation_cli import run_cli
from backend.src.knowledge.ingest import KnowledgeIngestor
from backend.src.knowledge.repository import KnowledgeRepository


class KnowledgeEvaluationCliTests(unittest.TestCase):
    def test_eval_cli_runs_user_fixed_eval_set(self) -> None:
        with TemporaryDirectory() as tmpdir:
            data_root = Path(tmpdir) / "data"
            repository = KnowledgeRepository(data_root=data_root)
            KnowledgeIngestor(repository).ingest_text(
                "dynamic",
                "nvda_eval_cli_note",
                "NVDA evaluation CLI should find event fade risk context.",
                metadata={"symbol": "NVDA", "category": "news"},
            )
            eval_path = Path(tmpdir) / "eval.json"
            eval_path.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "case_id": "nvda_eval_cli",
                                "query": "NVDA event fade risk",
                                "datasets": ["dynamic"],
                                "expected_symbols": ["NVDA"],
                                "must_include_terms": ["fade", "risk"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_cli(
                [
                    "--data-root",
                    str(data_root),
                    "--eval-set",
                    str(eval_path),
                ]
            )

        self.assertTrue(result["passed"])
        self.assertEqual(1, result["passedCount"])
        self.assertEqual(str(eval_path), result["evalSetPath"])


if __name__ == "__main__":
    unittest.main()
