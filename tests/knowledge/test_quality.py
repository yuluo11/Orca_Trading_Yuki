from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.knowledge.ingest import KnowledgeIngestor
from backend.src.knowledge.quality import KnowledgeQualityAuditor
from backend.src.knowledge.repository import KnowledgeRepository
from backend.src.routes.knowledge import audit_knowledge_payload


class KnowledgeQualityAuditTests(unittest.TestCase):
    def test_quality_audit_passes_clean_foundation_records(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            KnowledgeIngestor(repository).ingest_text(
                "foundation",
                "nvda_foundation_note",
                "NVDA foundation note contains enough durable context for retrieval.",
                metadata={"category": "research"},
            )

            summary = KnowledgeQualityAuditor(repository).audit(datasets=("foundation",))

        self.assertTrue(summary.passed)
        self.assertEqual(1, summary.record_count)
        self.assertEqual(0, summary.error_count)

    def test_quality_audit_reports_dynamic_metadata_gaps(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            KnowledgeIngestor(repository).ingest_text(
                "dynamic",
                "nvda_dynamic_note",
                "NVDA dynamic note has content but lacks source metadata fields.",
                metadata={"symbol": "NVDA", "category": "news"},
            )

            summary = audit_knowledge_payload(
                {"dataset": "dynamic", "dynamic_max_age_days": 9999},
                repository=repository,
            )

        self.assertTrue(summary["passed"])
        self.assertGreater(summary["warningCount"], 0)
        codes = {issue["code"] for issue in summary["issues"]}
        self.assertIn("missing_source_url", codes)
        self.assertIn("missing_published_at", codes)

    def test_quality_audit_reports_foundation_schema_and_conflict_warnings(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            ingestor = KnowledgeIngestor(repository)
            ingestor.ingest_text(
                "foundation",
                "allow_breakout_rule",
                "Breakout entries may be allowed when trend and confirmation align.",
                metadata={
                    "foundation_category": "setup_playbook",
                    "topic": "breakout entry",
                    "applies_to": ["decision_agent"],
                    "valid_when": ["trend confirmation aligns"],
                    "rule_direction": "allow",
                    "rule_id": "allow_breakout",
                },
            )
            ingestor.ingest_text(
                "foundation",
                "block_breakout_rule",
                "Breakout entries should be blocked when the same setup context is overextended.",
                metadata={
                    "foundation_category": "setup_playbook",
                    "topic": "breakout entry",
                    "applies_to": ["decision_agent"],
                    "valid_when": ["trend confirmation aligns"],
                    "rule_direction": "block",
                    "rule_id": "block_breakout",
                    "conflicts_with": ["missing_rule"],
                },
            )

            summary = KnowledgeQualityAuditor(repository).audit(datasets=("foundation",))

        self.assertTrue(summary.passed)
        codes = {issue.code for issue in summary.issues}
        self.assertIn("potential_static_conflict", codes)
        self.assertIn("unknown_conflict_reference", codes)


if __name__ == "__main__":
    unittest.main()
