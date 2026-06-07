from __future__ import annotations

import unittest

from backend.src.knowledge.foundation import (
    directions_conflict,
    normalize_foundation_metadata,
    validate_foundation_metadata,
)


class FoundationKnowledgeSchemaTests(unittest.TestCase):
    def test_normalize_foundation_metadata_adds_static_schema_defaults(self) -> None:
        metadata = {
            "category": "Risk Framework",
            "applies_to": "Decision Agent, Position Sizing",
            "valid_when": [" Setup has invalidation ", "setup has invalidation"],
        }

        normalize_foundation_metadata(metadata)

        self.assertEqual("risk_framework", metadata["foundation_category"])
        self.assertEqual("principle", metadata["principle_type"])
        self.assertEqual("medium", metadata["priority"])
        self.assertEqual("active", metadata["status"])
        self.assertEqual(["decision agent", "position sizing"], metadata["applies_to"])
        self.assertEqual(["setup has invalidation"], metadata["valid_when"])
        self.assertEqual([], validate_foundation_metadata(metadata))

    def test_validate_foundation_metadata_reports_unknown_static_values(self) -> None:
        metadata = {
            "foundation_category": "unknown_category",
            "principle_type": "rule",
            "priority": "urgent",
            "status": "active",
            "rule_direction": "neutral",
        }

        issues = validate_foundation_metadata(metadata)

        self.assertIn("invalid_foundation_category", issues)
        self.assertIn("invalid_priority", issues)

    def test_directions_conflict_detects_opposing_rule_directions(self) -> None:
        self.assertTrue(directions_conflict("allow", "block"))
        self.assertTrue(directions_conflict("increase", "reduce"))
        self.assertFalse(directions_conflict("observe", "neutral"))


if __name__ == "__main__":
    unittest.main()
