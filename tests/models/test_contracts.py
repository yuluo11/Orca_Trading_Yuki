from __future__ import annotations

import unittest

from backend.src.models import (
    AnalystOrchestrationResult,
    AnalystResult,
    DecisionContext,
    DecisionMemoryRecord,
    DecisionRealizationResult,
    DecisionOutput,
    GuidanceObservationSummary,
    GuidancePriorsSummary,
    KnowledgeDocument,
    KnowledgeEvidenceItem,
    RankedKnowledgeDocument,
    ReflectionContext,
    ReflectionOutput,
    ReflectionProfile,
    ReflectionReferenceCase,
    ReflectionPersistenceRunResult,
)


class ModelContractTests(unittest.TestCase):
    def test_contract_modules_are_importable(self) -> None:
        analyst_result: AnalystResult = {
            "analyst": "market_analyst",
            "summary": "Constructive setup.",
            "signals": ["Momentum support"],
            "risks": ["Valuation risk"],
            "confidence": "medium",
        }
        analyst_document: KnowledgeDocument = {
            "title": "Analyst support doc",
            "text": "Supportive context for the analyst.",
            "metadata": {"category": "news"},
        }
        evidence_item: KnowledgeEvidenceItem = {
            "source_type": "knowledge_base",
            "title": "NVDA prior postmortem",
            "content": "Prior postmortem text.",
            "metadata": {"category": "decision_memory"},
        }
        ranked_document: RankedKnowledgeDocument = {
            "title": "NVDA prior postmortem",
            "text": "Prior postmortem text.",
            "metadata": {"category": "decision_memory"},
            "fit": "medium",
            "match_reasons": ["Similar setup"],
        }
        analyst_result["documents"] = [analyst_document]
        analyst_result["evidence"] = [evidence_item]
        orchestration: AnalystOrchestrationResult = {
            "subject": "NVIDIA constructive reset",
            "overall_summary": "Signals are constructive.",
            "overall_confidence": "medium",
            "key_signals": ["Momentum support"],
            "portfolio_risks": ["Valuation risk"],
            "cross_analyst_observations": ["Coverage remains mixed."],
            "analyst_results": [analyst_result],
        }
        decision: DecisionOutput = {
            "subject": "NVIDIA constructive reset",
            "recommendation": "keep_watch",
            "confidence": "medium",
        }
        decision_context: DecisionContext = {
            "agent": "decision_advisory",
            "subject": "NVIDIA constructive reset",
            "datasets": ["dynamic"],
            "document_count": 1,
            "validation_summary": {
                "total_candidates": 1,
                "valid_candidates": 1,
                "invalid_candidates": 0,
            },
            "documents": [ranked_document],
            "evidence": [evidence_item],
            "guidance_priors": {
                "datasets": ["dynamic"],
                "symbol": "NVDA",
                "total_observations": 1,
                "top_guidance": [{"label": "Wait for confirmation.", "count": 1}],
                "summary": "For NVDA, recurring applied guidance has emphasized waiting for confirmation.",
            },
        }
        decision["decision_context"] = decision_context
        candidate_memory: DecisionMemoryRecord = {
            "text": "Postmortem notes and reusable lessons for the setup.",
            "metadata": {
                "title": "NVDA constructive reset Postmortem",
                "category": "decision_memory",
                "memory_type": "decision_postmortem",
                "source_type": "internal",
                "subject": "NVIDIA constructive reset",
                "recommendation": "keep_watch",
                "confidence": "medium",
                "dataset": "dynamic",
            },
        }
        reflection: ReflectionOutput = {
            "subject": "NVIDIA constructive reset",
            "reflection_summary": "The review suggests bounded reuse.",
            "lessons": ["Wait for stronger confirmation."],
            "future_adjustments": ["Keep timing thresholds tighter."],
            "candidate_memory": candidate_memory,
        }
        reflection_profile: ReflectionProfile = {
            "symbol": "NVDA",
            "recommendation": "keep_watch",
            "decision_confidence": "medium",
            "outcome_label": "mixed",
            "market_regime": "event_driven",
            "portfolio_state_tags": ["existing_position"],
        }
        reflection_reference_case: ReflectionReferenceCase = {
            "title": "NVDA prior postmortem",
            "memory_type": "decision_postmortem",
            "fit": "medium",
            "why_relevant": "Similar setup.",
        }
        reflection_context: ReflectionContext = {
            "agent": "reflection_agent",
            "subject": "NVIDIA constructive reset",
            "symbol": "NVDA",
            "query": "NVDA constructive reset recommendation keep_watch",
            "reflection_profile": reflection_profile,
            "datasets": ["dynamic"],
            "document_count": 1,
            "documents": [ranked_document],
            "historical_cases": [ranked_document],
            "evidence": [evidence_item],
            "original_decision": decision,
            "analyst_summary": {
                "overall_summary": "Signals are constructive.",
                "overall_confidence": "medium",
            },
            "realized_outcome": {"outcome_label": "mixed", "summary": "realized_pnl_pct 1.8"},
            "execution_summary": {"entry_date": "2026-05-21"},
            "outcome_metrics": {"realized_pnl_pct": 1.8},
            "exit_context": {"exit_reason": "trimmed into strength"},
            "post_trade_validation": {"is_valid": True, "errors": [], "warnings": []},
            "post_trade_completeness": {"status": "complete", "completeness_score": 1.0},
            "candidate_memory_seed": {"title": "NVDA constructive reset Postmortem"},
        }
        reflection["reference_cases"] = [reflection_reference_case]
        reflection["reflection_context"] = reflection_context
        observation_summary: GuidanceObservationSummary = {
            "dataset": "dynamic",
            "total_observations": 2,
            "top_guidance": [{"label": "Wait for confirmation.", "count": 2}],
        }
        guidance_priors: GuidancePriorsSummary = {
            "datasets": ["dynamic"],
            "symbol": "NVDA",
            "total_observations": 2,
            "top_guidance": [{"label": "Wait for confirmation.", "count": 2}],
            "summary": "For NVDA, recurring applied guidance has emphasized waiting for confirmation.",
        }
        workflow_result: DecisionRealizationResult = {
            "subject": "NVIDIA constructive reset",
            "symbol": "NVDA",
            "analyst": orchestration,
            "decision": decision,
        }
        reflection_run: ReflectionPersistenceRunResult = {
            "reflection": reflection,
            "persistence": {
                "persisted": True,
                "status": "persisted",
                "record_name": "nvda_postmortem",
            },
        }

        self.assertEqual("market_analyst", orchestration["analyst_results"][0]["analyst"])
        self.assertEqual("keep_watch", decision["recommendation"])
        self.assertEqual(1, decision["decision_context"]["validation_summary"]["valid_candidates"])
        self.assertEqual("medium", decision["decision_context"]["documents"][0]["fit"])
        self.assertEqual("decision_memory", reflection["candidate_memory"]["metadata"]["category"])
        self.assertEqual("mixed", reflection["reflection_context"]["reflection_profile"]["outcome_label"])
        self.assertEqual("decision_postmortem", reflection["reference_cases"][0]["memory_type"])
        self.assertEqual(2, observation_summary["top_guidance"][0]["count"])
        self.assertEqual("NVDA", guidance_priors["symbol"])
        self.assertEqual(
            "knowledge_base",
            orchestration["analyst_results"][0]["evidence"][0]["source_type"],
        )
        self.assertEqual("keep_watch", workflow_result["decision"]["recommendation"])
        self.assertTrue(reflection_run["persistence"]["persisted"])
        self.assertTrue(reflection["lessons"])


if __name__ == "__main__":
    unittest.main()
