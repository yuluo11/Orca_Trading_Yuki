from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from backend.src.app import (
    persist_decision_guidance_observation,
    run_decision_advisory,
    run_reflection_and_persist,
    summarize_decision_guidance_priors,
    summarize_decision_setup_outcomes,
    summarize_decision_setup_recommendation_outcomes,
)
from backend.src.knowledge.repository import KnowledgeRepository


def build_analyst_payload(*, subject: str, symbol: str, trade_date: str) -> dict[str, object]:
    """Create a compact analyst payload that maps to the event-momentum setup."""
    return {
        "subject": subject,
        "symbol": symbol,
        "trade_date": trade_date,
        "extra_context": "Event-driven semiconductor setup after guidance and momentum follow-through.",
        "overall_summary": (
            "Catalyst and momentum remain active, but timing looks mixed and the rebound may "
            "need stronger confirmation."
        ),
        "overall_confidence": "medium",
        "key_signals": [
            "news catalyst remains active",
            "momentum is still constructive",
        ],
        "portfolio_risks": [
            "event fade risk remains active",
            "valuation risk is elevated",
        ],
        "cross_analyst_observations": [
            "Signals are constructive but timing looks mixed",
            "Cross-analyst views remain uncertain around follow-through quality",
        ],
        "analyst_sequence": [
            "market_analyst",
            "news_analyst",
            "sentiment_analyst",
        ],
        "analyst_results": [
            {
                "agent_name": "market_analyst",
                "summary": "Momentum remains constructive but stretched.",
                "signals": ["momentum remains constructive"],
                "risks": ["valuation risk is elevated"],
            },
            {
                "agent_name": "news_analyst",
                "summary": "Guidance and catalyst support remain relevant.",
                "signals": ["guidance remains supportive", "catalyst remains active"],
                "risks": ["event fade risk remains active"],
            },
        ],
    }


class PostTradeLearningLoopTests(unittest.TestCase):
    def test_post_trade_learning_loop_runs_end_to_end(self) -> None:
        with TemporaryDirectory() as tmpdir, patch(
            "backend.src.app.build_default_llm_client",
            return_value=None,
        ):
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            portfolio_context = {
                "cash_pct": 14,
                "max_single_name_pct": 10,
                "positions": [],
            }

            analyst_payload_a = build_analyst_payload(
                subject="NVIDIA momentum rebound review",
                symbol="NVDA",
                trade_date="2026-05-20",
            )
            decision_a = run_decision_advisory(
                analyst_payload=analyst_payload_a,
                portfolio_context=portfolio_context,
                repository=repository,
            )

            self.assertEqual("keep_watch", decision_a["recommendation"])
            self.assertFalse(decision_a["decision_context"]["documents"])
            self.assertFalse(decision_a["applied_postmortem_guidance"])

            reflection_a = run_reflection_and_persist(
                decision_output=decision_a,
                analyst_payload=analyst_payload_a,
                portfolio_context=portfolio_context,
                execution_summary={
                    "entry_date": "2026-05-21",
                    "exit_date": "2026-05-27",
                    "holding_period_days": 6,
                },
                outcome_metrics={
                    "realized_pnl_pct": -2.8,
                    "max_drawdown_pct": -5.1,
                    "benchmark_relative_return_pct": -1.3,
                },
                exit_context={"exit_reason": "trimmed into failed rebound"},
                post_trade_notes=(
                    "Confirmation stayed weak and the rebound failed after the initial catalyst."
                ),
                repository=repository,
            )

            self.assertTrue(reflection_a["persistence"]["persisted"])
            self.assertEqual(
                "decision_postmortem",
                reflection_a["reflection"]["candidate_memory"]["metadata"]["memory_type"],
            )

            analyst_payload_b = build_analyst_payload(
                subject="NVIDIA constructive reset review",
                symbol="NVDA",
                trade_date="2026-06-03",
            )
            decision_b = run_decision_advisory(
                analyst_payload=analyst_payload_b,
                portfolio_context=portfolio_context,
                repository=repository,
            )

            self.assertEqual("keep_watch", decision_b["recommendation"])
            self.assertTrue(decision_b["decision_context"]["postmortem_lessons"])
            self.assertIn("postmortem lesson", decision_b["rationale"].lower())
            self.assertTrue(decision_b["applied_postmortem_guidance"])

            observation_b = persist_decision_guidance_observation(
                decision_result=decision_b,
                repository=repository,
            )
            self.assertTrue(observation_b["persisted"])

            reflection_b = run_reflection_and_persist(
                decision_output=decision_b,
                analyst_payload=analyst_payload_b,
                portfolio_context=portfolio_context,
                execution_summary={
                    "entry_date": "2026-06-04",
                    "exit_date": "2026-06-10",
                    "holding_period_days": 6,
                },
                outcome_metrics={
                    "realized_pnl_pct": -0.8,
                    "max_drawdown_pct": -2.4,
                    "benchmark_relative_return_pct": -0.2,
                },
                exit_context={"exit_reason": "reduced after mixed follow-through"},
                post_trade_notes=(
                    "The reset stabilized briefly but still lacked strong confirmation."
                ),
                repository=repository,
            )
            self.assertTrue(reflection_b["persistence"]["persisted"])

            analyst_payload_c = build_analyst_payload(
                subject="NVIDIA catalyst continuation check",
                symbol="NVDA",
                trade_date="2026-06-17",
            )
            decision_c = run_decision_advisory(
                analyst_payload=analyst_payload_c,
                portfolio_context=portfolio_context,
                repository=repository,
            )

            self.assertEqual("keep_watch", decision_c["recommendation"])
            self.assertGreaterEqual(
                decision_c["decision_context"]["guidance_priors"]["total_observations"],
                1,
            )
            self.assertEqual(
                2,
                decision_c["decision_context"]["setup_outcome_priors"]["reviewed_observations"],
            )
            self.assertEqual(
                "keep_watch",
                decision_c["decision_context"]["setup_recommendation_outcome_priors"][
                    "recommendation_outcomes"
                ][0]["recommendation"],
            )
            self.assertIn("recurring guidance prior", decision_c["rationale"].lower())
            self.assertIn("historical postmortem outcomes", decision_c["rationale"].lower())
            self.assertIn("historically resolved most often as", decision_c["rationale"].lower())

            guidance_priors = summarize_decision_guidance_priors(
                datasets=("dynamic",),
                symbol="NVDA",
                repository=repository,
            )
            setup_outcomes = summarize_decision_setup_outcomes(
                datasets=("dynamic",),
                symbol="NVDA",
                scenario_profile=decision_c["decision_context"]["scenario_profile"],
                repository=repository,
            )
            recommendation_outcomes = summarize_decision_setup_recommendation_outcomes(
                datasets=("dynamic",),
                symbol="NVDA",
                scenario_profile=decision_c["decision_context"]["scenario_profile"],
                repository=repository,
            )

            self.assertEqual(1, guidance_priors["total_observations"])
            self.assertEqual("event_momentum", setup_outcomes["primary_setup_label"])
            self.assertEqual("cautionary", setup_outcomes["outcome_bias"])
            self.assertEqual(
                "keep_watch",
                recommendation_outcomes["recommendation_outcomes"][0]["recommendation"],
            )
            self.assertTrue(
                recommendation_outcomes["recommendation_outcomes"][0]["outcome_breakdown"]
            )


if __name__ == "__main__":
    unittest.main()
