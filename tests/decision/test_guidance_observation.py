from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.src.knowledge.ingest import KnowledgeIngestor
from backend.src.knowledge.repository import KnowledgeRepository
from backend.src.services.decision import (
    DecisionGuidanceObservationAnalyticsService,
    DecisionGuidanceObservationService,
)


def initialize_repository(repository: KnowledgeRepository) -> None:
    repository.ensure_structure()
    repository.save_manifest(
        {
            "version": "0.1.0",
            "description": "Test manifest",
            "datasets": {
                "foundation": {"raw": [], "processed": []},
                "dynamic": {"raw": [], "processed": []},
            },
            "indexes": [],
        }
    )


class DecisionGuidanceObservationServiceTests(unittest.TestCase):
    def test_persist_guidance_observation_skips_without_applied_guidance(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            service = DecisionGuidanceObservationService(repository=repository)

            result = service.persist_guidance_observation(
                {
                    "subject": "NVIDIA momentum rebound review",
                    "symbol": "NVDA",
                    "trade_date": "2026-05-20",
                    "recommendation": "keep_watch",
                }
            )

            self.assertFalse(result["persisted"])
            self.assertEqual("skipped", result["status"])

    def test_persist_guidance_observation_writes_processed_record(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            service = DecisionGuidanceObservationService(repository=repository)

            decision_result = {
                "subject": "NVIDIA momentum rebound review",
                "symbol": "NVDA",
                "trade_date": "2026-05-20",
                "decision_summary": "The setup remains watchful because the rebound still looks fragile.",
                "recommendation": "keep_watch",
                "confidence": "medium",
                "rationale": "A retrieved postmortem lesson argues for stronger confirmation first.",
                "case_fit_assessment": "A medium-fit postmortem offered bounded caution.",
                "reference_cases": [
                    {
                        "title": "Momentum Rebound Postmortem",
                        "fit": "medium",
                        "memory_type": "decision_postmortem",
                        "why_relevant": "Similar rebound profile.",
                    }
                ],
                "applied_postmortem_guidance": [
                    "Require stronger confirmation before adding to an extended move."
                ],
                "applied_setup_labels": ["event_momentum"],
                "decision_context": {
                    "scenario_profile": {
                        "market_regime": "event_driven",
                        "analyst_alignment": "mixed",
                        "signal_tags": ["momentum"],
                        "risk_tags": ["event_fade"],
                        "timing_tags": ["short_term"],
                        "portfolio_state_tags": ["no_position"],
                    }
                },
            }

            result = service.persist_guidance_observation(decision_result)

            self.assertTrue(result["persisted"])
            self.assertEqual("persisted", result["status"])
            record_path = Path(result["path"])
            self.assertTrue(record_path.exists())

            payload = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual("decision_guidance_observation", payload["metadata"]["category"])
            self.assertEqual("dynamic", payload["metadata"]["dataset"])
            self.assertEqual("event_driven", payload["metadata"]["market_regime"])
            self.assertEqual(["momentum"], payload["metadata"]["signal_tags"])
            self.assertEqual("event_momentum", payload["metadata"]["primary_setup_label"])
            self.assertEqual(["event_momentum"], payload["metadata"]["applied_setup_labels"])
            self.assertIn("Applied setup labels:", payload["text"])
            self.assertIn("Applied postmortem guidance:", payload["text"])

            manifest = repository.load_manifest()
            processed_entries = manifest["datasets"]["dynamic"]["processed"]
            self.assertTrue(
                any(entry["name"] == result["record_name"] for entry in processed_entries)
            )

    def test_summarize_observations_reports_top_guidance_and_breakdowns(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            persistence = DecisionGuidanceObservationService(repository=repository)
            analytics = DecisionGuidanceObservationAnalyticsService(repository=repository)

            persistence.persist_guidance_observation(
                {
                    "subject": "NVIDIA momentum rebound review",
                    "symbol": "NVDA",
                    "trade_date": "2026-05-20",
                    "decision_summary": "Watchful stance while rebound remains fragile.",
                    "recommendation": "keep_watch",
                    "confidence": "medium",
                    "rationale": "A postmortem lesson argues for stronger confirmation.",
                    "case_fit_assessment": "A medium-fit postmortem offered caution.",
                    "reference_cases": [{"title": "Momentum Rebound Postmortem"}],
                    "applied_postmortem_guidance": [
                        "Require stronger confirmation before adding to an extended move."
                    ],
                    "applied_setup_labels": ["event_momentum"],
                    "decision_context": {
                        "scenario_profile": {
                            "market_regime": "event_driven",
                            "signal_tags": ["momentum"],
                            "risk_tags": ["event_fade"],
                            "timing_tags": ["short_term"],
                        }
                    },
                }
            )
            persistence.persist_guidance_observation(
                {
                    "subject": "NVIDIA constructive reset",
                    "symbol": "NVDA",
                    "trade_date": "2026-05-21",
                    "decision_summary": "Measured add only after confirmation.",
                    "recommendation": "consider_buy",
                    "confidence": "medium",
                    "rationale": "The same guidance still argues for staged sizing.",
                    "case_fit_assessment": "Partial fit to prior rebound lesson.",
                    "reference_cases": [{"title": "Momentum Rebound Postmortem"}],
                    "applied_postmortem_guidance": [
                        "Require stronger confirmation before adding to an extended move."
                    ],
                    "applied_setup_labels": ["event_momentum"],
                    "decision_context": {
                        "scenario_profile": {
                            "market_regime": "event_driven",
                            "signal_tags": ["momentum"],
                            "risk_tags": ["event_fade"],
                            "timing_tags": ["short_term"],
                        }
                    },
                }
            )
            persistence.persist_guidance_observation(
                {
                    "subject": "Utilities defensive rotation",
                    "symbol": "XLU",
                    "trade_date": "2026-05-22",
                    "decision_summary": "Reduce exposure into weakening momentum.",
                    "recommendation": "consider_reduce",
                    "confidence": "medium",
                    "rationale": "A separate lesson warns that failed bounces fade quickly.",
                    "case_fit_assessment": "High-fit defensive postmortem.",
                    "reference_cases": [{"title": "Defensive Rotation Postmortem"}],
                    "applied_postmortem_guidance": [
                        "Treat failed rebound persistence as a reason to lower confidence."
                    ],
                    "applied_setup_labels": ["defensive_drawdown"],
                    "decision_context": {
                        "scenario_profile": {
                            "market_regime": "risk_off",
                            "signal_tags": ["momentum"],
                            "risk_tags": ["drawdown_risk"],
                            "timing_tags": ["short_term"],
                        }
                    },
                }
            )

            summary = analytics.summarize_observations(top_n=3)

            self.assertEqual(3, summary["total_observations"])
            self.assertEqual(
                "Require stronger confirmation before adding to an extended move.",
                summary["top_guidance"][0]["label"],
            )
            self.assertEqual(2, summary["top_guidance"][0]["count"])
            self.assertTrue(
                any(
                    item["label"] == "NVDA" and item["count"] == 2
                    for item in summary["symbol_breakdown"]
                )
            )
            self.assertTrue(
                any(
                    item["label"] == "keep_watch" and item["count"] == 1
                    for item in summary["recommendation_breakdown"]
                )
            )
            self.assertTrue(
                any(
                    item["label"] == "Momentum Rebound Postmortem" and item["count"] == 2
                    for item in summary["top_reference_cases"]
                )
            )
            self.assertTrue(
                any(
                    item["label"] == "event_momentum" and item["count"] == 2
                    for item in summary["top_applied_setup_labels"]
                )
            )
            self.assertTrue(
                any(
                    item["label"] == "event_momentum" and item["count"] == 2
                    for item in summary["top_setup_labels"]
                )
            )

    def test_summarize_guidance_priors_filters_by_symbol_and_builds_summary(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            persistence = DecisionGuidanceObservationService(repository=repository)
            analytics = DecisionGuidanceObservationAnalyticsService(repository=repository)

            persistence.persist_guidance_observation(
                {
                    "subject": "NVIDIA momentum rebound review",
                    "symbol": "NVDA",
                    "trade_date": "2026-05-20",
                    "decision_summary": "Watchful stance while rebound remains fragile.",
                    "recommendation": "keep_watch",
                    "confidence": "medium",
                    "rationale": "A postmortem lesson argues for stronger confirmation.",
                    "case_fit_assessment": "A medium-fit postmortem offered caution.",
                    "reference_cases": [{"title": "Momentum Rebound Postmortem"}],
                    "applied_postmortem_guidance": [
                        "Require stronger confirmation before adding to an extended move."
                    ],
                    "applied_setup_labels": ["event_momentum"],
                    "decision_context": {
                        "scenario_profile": {
                            "market_regime": "event_driven",
                            "signal_tags": ["momentum"],
                            "risk_tags": ["event_fade"],
                            "timing_tags": ["short_term"],
                        }
                    },
                }
            )
            persistence.persist_guidance_observation(
                {
                    "subject": "NVIDIA constructive reset",
                    "symbol": "NVDA",
                    "trade_date": "2026-05-21",
                    "decision_summary": "Measured add only after confirmation.",
                    "recommendation": "consider_buy",
                    "confidence": "medium",
                    "rationale": "The same guidance still argues for staged sizing.",
                    "case_fit_assessment": "Partial fit to prior rebound lesson.",
                    "reference_cases": [{"title": "Momentum Rebound Postmortem"}],
                    "applied_postmortem_guidance": [
                        "Require stronger confirmation before adding to an extended move."
                    ],
                    "applied_setup_labels": ["event_momentum"],
                    "decision_context": {
                        "scenario_profile": {
                            "market_regime": "event_driven",
                            "signal_tags": ["momentum"],
                            "risk_tags": ["event_fade"],
                            "timing_tags": ["short_term"],
                        }
                    },
                }
            )
            persistence.persist_guidance_observation(
                {
                    "subject": "Utilities defensive rotation",
                    "symbol": "XLU",
                    "trade_date": "2026-05-22",
                    "decision_summary": "Reduce exposure into weakening momentum.",
                    "recommendation": "consider_reduce",
                    "confidence": "medium",
                    "rationale": "A separate lesson warns that failed bounces fade quickly.",
                    "case_fit_assessment": "High-fit defensive postmortem.",
                    "reference_cases": [{"title": "Defensive Rotation Postmortem"}],
                    "applied_postmortem_guidance": [
                        "Treat failed rebound persistence as a reason to lower confidence."
                    ],
                    "applied_setup_labels": ["defensive_drawdown"],
                    "decision_context": {
                        "scenario_profile": {
                            "market_regime": "risk_off",
                            "signal_tags": ["momentum"],
                            "risk_tags": ["drawdown_risk"],
                            "timing_tags": ["short_term"],
                        }
                    },
                }
            )

            priors = analytics.summarize_guidance_priors(
                datasets=("dynamic",),
                symbol="NVDA",
                top_n=2,
            )

            self.assertEqual("NVDA", priors["symbol"])
            self.assertEqual(2, priors["total_observations"])
            self.assertEqual(
                "Require stronger confirmation before adding to an extended move.",
                priors["top_guidance"][0]["label"],
            )
            self.assertEqual(2, priors["top_guidance"][0]["count"])
            self.assertIn("For NVDA", priors["summary"])
            self.assertIn("keep_watch", priors["summary"])
            self.assertNotIn("XLU", priors["summary"])
            self.assertEqual("event_momentum", priors["top_applied_setup_labels"][0]["label"])

    def test_summarize_guidance_priors_can_filter_by_setup_profile(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            persistence = DecisionGuidanceObservationService(repository=repository)
            analytics = DecisionGuidanceObservationAnalyticsService(repository=repository)

            persistence.persist_guidance_observation(
                {
                    "subject": "NVIDIA momentum rebound review",
                    "symbol": "NVDA",
                    "trade_date": "2026-05-20",
                    "decision_summary": "Watchful stance while rebound remains fragile.",
                    "recommendation": "keep_watch",
                    "confidence": "medium",
                    "rationale": "A postmortem lesson argues for stronger confirmation.",
                    "case_fit_assessment": "A medium-fit postmortem offered caution.",
                    "reference_cases": [{"title": "Momentum Rebound Postmortem"}],
                    "applied_postmortem_guidance": [
                        "Require stronger confirmation before adding to an extended move."
                    ],
                    "applied_setup_labels": ["event_momentum"],
                    "decision_context": {
                        "scenario_profile": {
                            "market_regime": "event_driven",
                            "signal_tags": ["momentum"],
                            "risk_tags": ["event_fade"],
                            "timing_tags": ["short_term"],
                        }
                    },
                }
            )
            persistence.persist_guidance_observation(
                {
                    "subject": "Software catalyst follow-up",
                    "symbol": "MSFT",
                    "trade_date": "2026-05-21",
                    "decision_summary": "Wait for stronger confirmation after the gap.",
                    "recommendation": "keep_watch",
                    "confidence": "medium",
                    "rationale": "The same event-driven lesson remains relevant.",
                    "case_fit_assessment": "Similar catalyst and fade risk.",
                    "reference_cases": [{"title": "Catalyst Fade Postmortem"}],
                    "applied_postmortem_guidance": [
                        "Require stronger confirmation before adding to an extended move."
                    ],
                    "applied_setup_labels": ["event_momentum"],
                    "decision_context": {
                        "scenario_profile": {
                            "market_regime": "event_driven",
                            "signal_tags": ["momentum"],
                            "risk_tags": ["event_fade"],
                            "timing_tags": ["short_term"],
                        }
                    },
                }
            )
            persistence.persist_guidance_observation(
                {
                    "subject": "Utilities defensive rotation",
                    "symbol": "XLU",
                    "trade_date": "2026-05-22",
                    "decision_summary": "Reduce exposure into weakening momentum.",
                    "recommendation": "consider_reduce",
                    "confidence": "medium",
                    "rationale": "A separate lesson warns that failed bounces fade quickly.",
                    "case_fit_assessment": "High-fit defensive postmortem.",
                    "reference_cases": [{"title": "Defensive Rotation Postmortem"}],
                    "applied_postmortem_guidance": [
                        "Treat failed rebound persistence as a reason to lower confidence."
                    ],
                    "applied_setup_labels": ["defensive_drawdown"],
                    "decision_context": {
                        "scenario_profile": {
                            "market_regime": "risk_off",
                            "signal_tags": ["momentum"],
                            "risk_tags": ["drawdown_risk"],
                            "timing_tags": ["short_term"],
                        }
                    },
                }
            )

            priors = analytics.summarize_guidance_priors(
                datasets=("dynamic",),
                scenario_profile={
                    "market_regime": "event_driven",
                    "signal_tags": ["momentum"],
                    "risk_tags": ["event_fade"],
                    "timing_tags": ["short_term"],
                },
                top_n=2,
            )

            self.assertIsNone(priors["symbol"])
            self.assertEqual("event_driven", priors["market_regime"])
            self.assertEqual("event_momentum", priors["primary_setup_label"])
            self.assertEqual(2, priors["total_observations"])
            self.assertEqual(
                "Require stronger confirmation before adding to an extended move.",
                priors["top_guidance"][0]["label"],
            )
            self.assertEqual("event_momentum", priors["top_applied_setup_labels"][0]["label"])
            self.assertIn("event_driven", priors["summary"])

    def test_summarize_setup_outcome_priors_reports_cautionary_setup_bias(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            analytics = DecisionGuidanceObservationAnalyticsService(repository=repository)
            initialize_repository(repository)
            ingestor = KnowledgeIngestor(repository)

            ingestor.ingest_text(
                "dynamic",
                "nvda_event_momentum_failed",
                "A postmortem on an event-driven momentum setup that failed after weak follow-through.",
                metadata={
                    "source": "internal_reflection",
                    "source_type": "internal",
                    "title": "NVDA Event Momentum Failure",
                    "category": "decision_memory",
                    "memory_type": "decision_postmortem",
                    "symbol": "NVDA",
                    "subject": "NVIDIA momentum rebound review",
                    "topic": "decision-memory",
                    "recommendation": "keep_watch",
                    "confidence": "medium",
                    "market_regime": "event_driven",
                    "analyst_alignment": "mixed",
                    "setup_labels": ["event_momentum"],
                    "primary_setup_label": "event_momentum",
                    "signal_tags": ["momentum", "news_catalyst"],
                    "risk_tags": ["event_fade"],
                    "timing_tags": ["short_term"],
                    "outcome_label": "failed",
                    "quality_score": 0.8,
                    "dataset": "dynamic",
                },
            )
            ingestor.ingest_text(
                "dynamic",
                "nvda_event_momentum_mixed",
                "A second postmortem on a similar event setup that delivered only mixed follow-through.",
                metadata={
                    "source": "internal_reflection",
                    "source_type": "internal",
                    "title": "NVDA Event Momentum Mixed Outcome",
                    "category": "decision_memory",
                    "memory_type": "decision_postmortem",
                    "symbol": "NVDA",
                    "subject": "NVIDIA constructive reset",
                    "topic": "decision-memory",
                    "recommendation": "keep_watch",
                    "confidence": "medium",
                    "market_regime": "event_driven",
                    "analyst_alignment": "mixed",
                    "setup_labels": ["event_momentum"],
                    "primary_setup_label": "event_momentum",
                    "signal_tags": ["momentum"],
                    "risk_tags": ["event_fade"],
                    "timing_tags": ["short_term"],
                    "outcome_label": "mixed",
                    "quality_score": 0.75,
                    "dataset": "dynamic",
                },
            )
            ingestor.ingest_text(
                "dynamic",
                "xlu_defensive_worked",
                "A defensive drawdown postmortem that worked as expected.",
                metadata={
                    "source": "internal_reflection",
                    "source_type": "internal",
                    "title": "XLU Defensive Drawdown Worked",
                    "category": "decision_memory",
                    "memory_type": "decision_postmortem",
                    "symbol": "XLU",
                    "subject": "Utilities defensive rotation",
                    "topic": "decision-memory",
                    "recommendation": "consider_reduce",
                    "confidence": "medium",
                    "market_regime": "risk_off",
                    "analyst_alignment": "aligned",
                    "setup_labels": ["defensive_drawdown"],
                    "primary_setup_label": "defensive_drawdown",
                    "signal_tags": ["momentum"],
                    "risk_tags": ["drawdown_risk"],
                    "timing_tags": ["short_term"],
                    "outcome_label": "worked",
                    "quality_score": 0.8,
                    "dataset": "dynamic",
                },
            )

            summary = analytics.summarize_setup_outcome_priors(
                datasets=("dynamic",),
                scenario_profile={
                    "market_regime": "event_driven",
                    "signal_tags": ["momentum", "news_catalyst"],
                    "risk_tags": ["event_fade"],
                    "timing_tags": ["short_term"],
                },
                top_n=3,
            )

            self.assertEqual("event_momentum", summary["primary_setup_label"])
            self.assertEqual(2, summary["reviewed_observations"])
            self.assertEqual("cautionary", summary["outcome_bias"])
            self.assertEqual("failed", summary["outcome_breakdown"][0]["label"])
            self.assertTrue(
                any(
                    item["label"] == "keep_watch" and item["count"] == 2
                    for item in summary["recommendation_breakdown"]
                )
            )
            self.assertIn("event_momentum", summary["summary"])
            self.assertIn("cautionary", summary["summary"])

    def test_summarize_setup_recommendation_outcomes_groups_results_by_recommendation(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repository = KnowledgeRepository(data_root=Path(tmpdir))
            analytics = DecisionGuidanceObservationAnalyticsService(repository=repository)
            initialize_repository(repository)
            ingestor = KnowledgeIngestor(repository)

            ingestor.ingest_text(
                "dynamic",
                "nvda_event_keep_watch_failed",
                "A watchful event-driven setup that later failed on weak follow-through.",
                metadata={
                    "source": "internal_reflection",
                    "source_type": "internal",
                    "title": "NVDA Keep Watch Failed",
                    "category": "decision_memory",
                    "memory_type": "decision_postmortem",
                    "symbol": "NVDA",
                    "subject": "NVIDIA momentum rebound review",
                    "topic": "decision-memory",
                    "recommendation": "keep_watch",
                    "confidence": "medium",
                    "market_regime": "event_driven",
                    "analyst_alignment": "mixed",
                    "setup_labels": ["event_momentum"],
                    "primary_setup_label": "event_momentum",
                    "signal_tags": ["momentum", "news_catalyst"],
                    "risk_tags": ["event_fade"],
                    "timing_tags": ["short_term"],
                    "outcome_label": "failed",
                    "quality_score": 0.8,
                    "dataset": "dynamic",
                },
            )
            ingestor.ingest_text(
                "dynamic",
                "nvda_event_keep_watch_mixed",
                "A second watchful event-driven setup that produced only mixed follow-through.",
                metadata={
                    "source": "internal_reflection",
                    "source_type": "internal",
                    "title": "NVDA Keep Watch Mixed",
                    "category": "decision_memory",
                    "memory_type": "decision_postmortem",
                    "symbol": "NVDA",
                    "subject": "NVIDIA constructive reset",
                    "topic": "decision-memory",
                    "recommendation": "keep_watch",
                    "confidence": "medium",
                    "market_regime": "event_driven",
                    "analyst_alignment": "mixed",
                    "setup_labels": ["event_momentum"],
                    "primary_setup_label": "event_momentum",
                    "signal_tags": ["momentum"],
                    "risk_tags": ["event_fade"],
                    "timing_tags": ["short_term"],
                    "outcome_label": "mixed",
                    "quality_score": 0.75,
                    "dataset": "dynamic",
                },
            )
            ingestor.ingest_text(
                "dynamic",
                "nvda_event_consider_buy_worked",
                "A more constructive event-driven setup that worked after confirmation held.",
                metadata={
                    "source": "internal_reflection",
                    "source_type": "internal",
                    "title": "NVDA Consider Buy Worked",
                    "category": "decision_memory",
                    "memory_type": "decision_postmortem",
                    "symbol": "NVDA",
                    "subject": "NVIDIA post-reset confirmation",
                    "topic": "decision-memory",
                    "recommendation": "consider_buy",
                    "confidence": "medium",
                    "market_regime": "event_driven",
                    "analyst_alignment": "aligned",
                    "setup_labels": ["event_momentum"],
                    "primary_setup_label": "event_momentum",
                    "signal_tags": ["momentum", "news_catalyst"],
                    "risk_tags": ["event_fade"],
                    "timing_tags": ["short_term"],
                    "outcome_label": "worked",
                    "quality_score": 0.82,
                    "dataset": "dynamic",
                },
            )
            ingestor.ingest_text(
                "dynamic",
                "xlu_defensive_reduce_worked",
                "A defensive drawdown setup that resolved as expected.",
                metadata={
                    "source": "internal_reflection",
                    "source_type": "internal",
                    "title": "XLU Defensive Reduce Worked",
                    "category": "decision_memory",
                    "memory_type": "decision_postmortem",
                    "symbol": "XLU",
                    "subject": "Utilities defensive rotation",
                    "topic": "decision-memory",
                    "recommendation": "consider_reduce",
                    "confidence": "medium",
                    "market_regime": "risk_off",
                    "analyst_alignment": "aligned",
                    "setup_labels": ["defensive_drawdown"],
                    "primary_setup_label": "defensive_drawdown",
                    "signal_tags": ["momentum"],
                    "risk_tags": ["drawdown_risk"],
                    "timing_tags": ["short_term"],
                    "outcome_label": "worked",
                    "quality_score": 0.8,
                    "dataset": "dynamic",
                },
            )

            summary = analytics.summarize_setup_recommendation_outcomes(
                datasets=("dynamic",),
                scenario_profile={
                    "market_regime": "event_driven",
                    "signal_tags": ["momentum", "news_catalyst"],
                    "risk_tags": ["event_fade"],
                    "timing_tags": ["short_term"],
                },
                top_n=3,
            )

            self.assertEqual("event_momentum", summary["primary_setup_label"])
            self.assertEqual(3, summary["total_records"])
            self.assertEqual("keep_watch", summary["recommendation_outcomes"][0]["recommendation"])
            self.assertEqual(2, summary["recommendation_outcomes"][0]["total_observations"])
            self.assertEqual("cautionary", summary["recommendation_outcomes"][0]["outcome_bias"])
            self.assertEqual("consider_buy", summary["recommendation_outcomes"][1]["recommendation"])
            self.assertEqual("worked", summary["recommendation_outcomes"][1]["dominant_outcome"])
            self.assertIn("keep_watch has most often led to failed outcomes", summary["summary"])
            self.assertIn("consider_buy has most often led to worked outcomes", summary["summary"])


if __name__ == "__main__":
    unittest.main()
