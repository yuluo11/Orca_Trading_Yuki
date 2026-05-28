"""Analytics helpers for persisted decision-guidance observations."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ...knowledge.repository import DatasetName, KnowledgeRepository
from ...models import (
    CountedLabel,
    GuidanceObservationSummary,
    GuidancePriorsSummary,
)
from .memory.schema import normalize_decision_memory_metadata
from .setup_taxonomy import (
    infer_setup_labels,
    normalize_string_list as normalize_tag_list,
)


class DecisionGuidanceObservationAnalyticsService:
    """Summarize persisted guidance-observation records for lightweight analysis."""

    def __init__(self, repository: KnowledgeRepository | None = None) -> None:
        self.repository = repository or KnowledgeRepository()

    def summarize_observations(
        self,
        *,
        dataset: DatasetName = "dynamic",
        symbol: str | None = None,
        recommendation: str | None = None,
        market_regime: str | None = None,
        setup_label: str | None = None,
        scenario_profile: dict[str, Any] | None = None,
        top_n: int = 5,
        records: list[dict[str, Any]] | None = None,
    ) -> GuidanceObservationSummary:
        """Build a compact summary over persisted decision-guidance observations."""
        records = records if records is not None else self.repository.load_all_processed_records(dataset)
        filtered_records = [
            record
            for record in records
            if self._is_guidance_observation(record)
            and self._matches_symbol(record, symbol)
            and self._matches_recommendation(record, recommendation)
            and self._matches_market_regime(record, market_regime)
            and self._matches_setup_label(record, setup_label)
            and self._matches_scenario_profile(record, scenario_profile)
        ]

        guidance_counter: Counter[str] = Counter()
        recommendation_counter: Counter[str] = Counter()
        symbol_counter: Counter[str] = Counter()
        reference_case_counter: Counter[str] = Counter()
        setup_counter: Counter[str] = Counter()
        applied_setup_counter: Counter[str] = Counter()

        for record in filtered_records:
            metadata = dict(record.get("metadata", {}))
            for guidance in self._extract_applied_guidance(record):
                guidance_counter[guidance] += 1
            for setup_label in self._extract_applied_setup_labels(record):
                applied_setup_counter[setup_label] += 1

            recommendation_label = str(metadata.get("recommendation", "")).strip().lower()
            if recommendation_label:
                recommendation_counter[recommendation_label] += 1

            symbol_label = str(metadata.get("symbol", "")).strip().upper()
            if symbol_label:
                symbol_counter[symbol_label] += 1

            for title in self._extract_reference_case_titles(record):
                reference_case_counter[title] += 1
            for setup_label in self._extract_setup_labels(record):
                setup_counter[setup_label] += 1

        return {
            "dataset": dataset,
            "total_observations": len(filtered_records),
            "top_guidance": self._format_counter(guidance_counter, top_n=top_n),
            "recommendation_breakdown": self._format_counter(
                recommendation_counter,
                top_n=top_n,
            ),
            "symbol_breakdown": self._format_counter(symbol_counter, top_n=top_n),
            "top_reference_cases": self._format_counter(reference_case_counter, top_n=top_n),
            "top_setup_labels": self._format_counter(setup_counter, top_n=top_n),
            "top_applied_setup_labels": self._format_counter(applied_setup_counter, top_n=top_n),
        }

    def summarize_guidance_priors(
        self,
        *,
        datasets: tuple[DatasetName, ...] | list[DatasetName] | None = None,
        symbol: str | None = None,
        recommendation: str | None = None,
        scenario_profile: dict[str, Any] | None = None,
        top_n: int = 3,
        records_by_dataset: dict[DatasetName, list[dict[str, Any]]] | None = None,
    ) -> GuidancePriorsSummary:
        """Build a compact guidance-prior summary for reuse in future decisions."""
        selected_datasets = tuple(datasets or ("dynamic",))
        guidance_counter: Counter[str] = Counter()
        recommendation_counter: Counter[str] = Counter()
        reference_case_counter: Counter[str] = Counter()
        setup_counter: Counter[str] = Counter()
        applied_setup_counter: Counter[str] = Counter()
        total_observations = 0

        setup_labels = infer_setup_labels(scenario_profile)
        primary_setup_label = setup_labels[0] if setup_labels else None
        for dataset in selected_datasets:
            summary = self.summarize_observations(
                dataset=dataset,
                symbol=symbol,
                recommendation=recommendation,
                market_regime=self._scenario_market_regime(scenario_profile),
                setup_label=primary_setup_label,
                scenario_profile=scenario_profile,
                top_n=max(top_n * 2, 5),
                records=(records_by_dataset or {}).get(dataset),
            )
            total_observations += int(summary.get("total_observations", 0) or 0)
            for item in summary.get("top_guidance", []):
                label = str(item.get("label", "")).strip()
                count = int(item.get("count", 0) or 0)
                if label and count > 0:
                    guidance_counter[label] += count
            for item in summary.get("recommendation_breakdown", []):
                label = str(item.get("label", "")).strip()
                count = int(item.get("count", 0) or 0)
                if label and count > 0:
                    recommendation_counter[label] += count
            for item in summary.get("top_reference_cases", []):
                label = str(item.get("label", "")).strip()
                count = int(item.get("count", 0) or 0)
                if label and count > 0:
                    reference_case_counter[label] += count
            for item in summary.get("top_setup_labels", []):
                label = str(item.get("label", "")).strip()
                count = int(item.get("count", 0) or 0)
                if label and count > 0:
                    setup_counter[label] += count
            for item in summary.get("top_applied_setup_labels", []):
                label = str(item.get("label", "")).strip()
                count = int(item.get("count", 0) or 0)
                if label and count > 0:
                    applied_setup_counter[label] += count

        top_guidance = self._format_counter(guidance_counter, top_n=top_n)
        recommendation_breakdown = self._format_counter(recommendation_counter, top_n=top_n)
        top_reference_cases = self._format_counter(reference_case_counter, top_n=top_n)
        top_setup_labels = self._format_counter(setup_counter, top_n=top_n)
        top_applied_setup_labels = self._format_counter(applied_setup_counter, top_n=top_n)
        normalized_symbol = symbol.strip().upper() if isinstance(symbol, str) and symbol.strip() else None
        return {
            "datasets": list(selected_datasets),
            "symbol": normalized_symbol,
            "market_regime": self._scenario_market_regime(scenario_profile),
            "setup_labels": setup_labels,
            "primary_setup_label": primary_setup_label,
            "recommendation_filter": recommendation.strip().lower()
            if isinstance(recommendation, str) and recommendation.strip()
            else None,
            "total_observations": total_observations,
            "top_guidance": top_guidance,
            "recommendation_breakdown": recommendation_breakdown,
            "top_reference_cases": top_reference_cases,
            "top_setup_labels": top_setup_labels,
            "top_applied_setup_labels": top_applied_setup_labels,
            "summary": self._build_guidance_prior_summary(
                symbol=normalized_symbol,
                market_regime=self._scenario_market_regime(scenario_profile),
                primary_setup_label=primary_setup_label,
                total_observations=total_observations,
                top_guidance=top_guidance,
                recommendation_breakdown=recommendation_breakdown,
            ),
        }

    def summarize_setup_outcome_priors(
        self,
        *,
        datasets: tuple[DatasetName, ...] | list[DatasetName] | None = None,
        symbol: str | None = None,
        scenario_profile: dict[str, Any] | None = None,
        top_n: int = 3,
        records_by_dataset: dict[DatasetName, list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        """Summarize historical setup outcomes from persisted decision-memory records."""
        selected_datasets = tuple(datasets or ("dynamic",))
        outcome_counter: Counter[str] = Counter()
        recommendation_counter: Counter[str] = Counter()
        symbol_counter: Counter[str] = Counter()
        setup_counter: Counter[str] = Counter()
        total_records = 0

        setup_labels = infer_setup_labels(scenario_profile)
        primary_setup_label = setup_labels[0] if setup_labels else None
        for dataset in selected_datasets:
            records = (records_by_dataset or {}).get(dataset)
            if records is None:
                records = self.repository.load_all_processed_records(dataset)
            for record in records:
                if not self._is_decision_memory_record(record):
                    continue
                if not self._matches_symbol(record, symbol):
                    continue
                if scenario_profile and not self._matches_scenario_profile(record, scenario_profile):
                    continue

                metadata = normalize_decision_memory_metadata(record.get("metadata", {}))
                memory_type = str(metadata.get("memory_type", "")).strip().lower()
                outcome_label = str(metadata.get("outcome_label", "")).strip().lower()
                if memory_type != "decision_postmortem" and outcome_label == "unknown":
                    continue

                total_records += 1
                if outcome_label:
                    outcome_counter[outcome_label] += 1

                recommendation_label = str(metadata.get("recommendation", "")).strip().lower()
                if recommendation_label:
                    recommendation_counter[recommendation_label] += 1

                symbol_label = str(metadata.get("symbol", "")).strip().upper()
                if symbol_label:
                    symbol_counter[symbol_label] += 1

                for setup_label in self._normalize_string_list(metadata.get("setup_labels")):
                    setup_counter[setup_label] += 1

        reviewed_observations = sum(
            int(outcome_counter.get(label, 0) or 0)
            for label in ("worked", "failed", "mixed")
        )
        outcome_breakdown = self._format_counter(outcome_counter, top_n=max(top_n + 1, 4))
        recommendation_breakdown = self._format_counter(recommendation_counter, top_n=top_n)
        top_setup_labels = self._format_counter(setup_counter, top_n=top_n)
        normalized_symbol = symbol.strip().upper() if isinstance(symbol, str) and symbol.strip() else None
        outcome_bias = self._infer_outcome_bias(outcome_counter)
        dominant_outcome = outcome_breakdown[0]["label"] if outcome_breakdown else None
        return {
            "datasets": list(selected_datasets),
            "symbol": normalized_symbol,
            "market_regime": self._scenario_market_regime(scenario_profile),
            "setup_labels": setup_labels,
            "primary_setup_label": primary_setup_label,
            "total_records": total_records,
            "reviewed_observations": reviewed_observations,
            "outcome_breakdown": outcome_breakdown,
            "recommendation_breakdown": recommendation_breakdown,
            "symbol_breakdown": self._format_counter(symbol_counter, top_n=top_n),
            "top_setup_labels": top_setup_labels,
            "dominant_outcome": dominant_outcome,
            "outcome_bias": outcome_bias,
            "summary": self._build_setup_outcome_summary(
                symbol=normalized_symbol,
                market_regime=self._scenario_market_regime(scenario_profile),
                primary_setup_label=primary_setup_label,
                reviewed_observations=reviewed_observations,
                outcome_breakdown=outcome_breakdown,
                recommendation_breakdown=recommendation_breakdown,
                outcome_bias=outcome_bias,
            ),
        }

    def summarize_setup_recommendation_outcomes(
        self,
        *,
        datasets: tuple[DatasetName, ...] | list[DatasetName] | None = None,
        symbol: str | None = None,
        scenario_profile: dict[str, Any] | None = None,
        top_n: int = 5,
        records_by_dataset: dict[DatasetName, list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        """Summarize how recommendations have historically resolved within one setup."""
        selected_datasets = tuple(datasets or ("dynamic",))
        recommendation_outcomes: dict[str, Counter[str]] = {}
        setup_counter: Counter[str] = Counter()
        total_records = 0

        setup_labels = infer_setup_labels(scenario_profile)
        primary_setup_label = setup_labels[0] if setup_labels else None
        for dataset in selected_datasets:
            records = (records_by_dataset or {}).get(dataset)
            if records is None:
                records = self.repository.load_all_processed_records(dataset)
            for record in records:
                if not self._is_decision_memory_record(record):
                    continue
                if not self._matches_symbol(record, symbol):
                    continue
                if scenario_profile and not self._matches_scenario_profile(record, scenario_profile):
                    continue

                metadata = normalize_decision_memory_metadata(record.get("metadata", {}))
                memory_type = str(metadata.get("memory_type", "")).strip().lower()
                outcome_label = str(metadata.get("outcome_label", "")).strip().lower()
                if memory_type != "decision_postmortem" and outcome_label == "unknown":
                    continue

                recommendation_label = str(metadata.get("recommendation", "")).strip().lower()
                if not recommendation_label or not outcome_label:
                    continue

                total_records += 1
                recommendation_outcomes.setdefault(recommendation_label, Counter())[outcome_label] += 1
                for setup_label in self._normalize_string_list(metadata.get("setup_labels")):
                    setup_counter[setup_label] += 1

        normalized_symbol = symbol.strip().upper() if isinstance(symbol, str) and symbol.strip() else None
        formatted_recommendation_outcomes = self._format_recommendation_outcomes(
            recommendation_outcomes,
            top_n=top_n,
        )
        return {
            "datasets": list(selected_datasets),
            "symbol": normalized_symbol,
            "market_regime": self._scenario_market_regime(scenario_profile),
            "setup_labels": setup_labels,
            "primary_setup_label": primary_setup_label,
            "total_records": total_records,
            "recommendation_outcomes": formatted_recommendation_outcomes,
            "top_setup_labels": self._format_counter(setup_counter, top_n=top_n),
            "summary": self._build_setup_recommendation_outcome_summary(
                symbol=normalized_symbol,
                market_regime=self._scenario_market_regime(scenario_profile),
                primary_setup_label=primary_setup_label,
                recommendation_outcomes=formatted_recommendation_outcomes,
            ),
        }

    def _is_guidance_observation(self, record: dict[str, Any]) -> bool:
        """Return whether a processed record is a decision-guidance observation."""
        metadata = dict(record.get("metadata", {}))
        return str(metadata.get("category", "")).strip() == "decision_guidance_observation"

    def _is_decision_memory_record(self, record: dict[str, Any]) -> bool:
        """Return whether a processed record is a decision-memory record."""
        metadata = dict(record.get("metadata", {}))
        return str(metadata.get("category", "")).strip() == "decision_memory"

    def _matches_symbol(self, record: dict[str, Any], symbol: str | None) -> bool:
        """Apply an optional symbol filter."""
        if not symbol:
            return True
        metadata = dict(record.get("metadata", {}))
        return str(metadata.get("symbol", "")).strip().upper() == symbol.strip().upper()

    def _matches_recommendation(
        self,
        record: dict[str, Any],
        recommendation: str | None,
    ) -> bool:
        """Apply an optional recommendation filter."""
        if not recommendation:
            return True
        metadata = dict(record.get("metadata", {}))
        return (
            str(metadata.get("recommendation", "")).strip().lower()
            == recommendation.strip().lower()
        )

    def _matches_market_regime(
        self,
        record: dict[str, Any],
        market_regime: str | None,
    ) -> bool:
        """Apply an optional market-regime filter."""
        if not market_regime:
            return True
        metadata = dict(record.get("metadata", {}))
        return (
            str(metadata.get("market_regime", "")).strip().lower()
            == market_regime.strip().lower()
        )

    def _matches_scenario_profile(
        self,
        record: dict[str, Any],
        scenario_profile: dict[str, Any] | None,
    ) -> bool:
        """Apply a coarse setup filter using overlapping scenario tags."""
        if not isinstance(scenario_profile, dict) or not scenario_profile:
            return True
        requested_market_regime = self._scenario_market_regime(scenario_profile)
        if requested_market_regime:
            metadata = dict(record.get("metadata", {}))
            record_market_regime = str(metadata.get("market_regime", "")).strip().lower()
            if record_market_regime and record_market_regime != requested_market_regime:
                return False
        inferred_setup_labels = infer_setup_labels(scenario_profile)
        if inferred_setup_labels and self._matches_any_setup_label(record, inferred_setup_labels):
            return True
        return self._scenario_overlap_score(record, scenario_profile) > 0

    def _matches_setup_label(
        self,
        record: dict[str, Any],
        setup_label: str | None,
    ) -> bool:
        """Apply an optional primary setup-label filter."""
        if not setup_label:
            return True
        return self._matches_any_setup_label(record, [setup_label.strip().lower()])

    def _extract_applied_guidance(self, record: dict[str, Any]) -> list[str]:
        """Extract applied guidance strings from metadata or fallback text parsing."""
        import re

        metadata = dict(record.get("metadata", {}))
        raw_value = metadata.get("applied_guidance", [])
        if isinstance(raw_value, list):
            normalized = [str(item).strip() for item in raw_value if str(item).strip()]
            if normalized:
                return normalized

        text = str(record.get("text", "")).strip()
        match = re.search(r"Applied postmortem guidance:\n((?:- .+\n?){1,8})", text)
        if not match:
            return []
        return [
            line.removeprefix("- ").strip()
            for line in match.group(1).splitlines()
            if line.removeprefix("- ").strip()
        ]

    def _normalize_string_list(self, value: Any) -> list[str]:
        """Normalize optional metadata values into a non-empty string list."""
        return normalize_tag_list(value)

    def _extract_reference_case_titles(self, record: dict[str, Any]) -> list[str]:
        """Extract reference-case titles from metadata or fallback text parsing."""
        import re

        metadata = dict(record.get("metadata", {}))
        raw_value = metadata.get("reference_case_titles", [])
        if isinstance(raw_value, list):
            normalized = [str(item).strip() for item in raw_value if str(item).strip()]
            if normalized:
                return normalized

        text = str(record.get("text", "")).strip()
        match = re.search(r"Reference cases:\n((?:- .+\n?){1,8})", text)
        if not match:
            return []
        return [
            line.removeprefix("- ").strip()
            for line in match.group(1).splitlines()
            if line.removeprefix("- ").strip()
        ]

    def _extract_setup_labels(self, record: dict[str, Any]) -> list[str]:
        """Extract setup labels from observation metadata."""
        metadata = dict(record.get("metadata", {}))
        raw_value = metadata.get("setup_labels", [])
        normalized = self._normalize_string_list(raw_value)
        if normalized:
            return normalized
        primary_label = str(metadata.get("primary_setup_label", "")).strip()
        return [primary_label] if primary_label else []

    def _extract_applied_setup_labels(self, record: dict[str, Any]) -> list[str]:
        """Extract applied setup labels from metadata or fallback text parsing."""
        import re

        metadata = dict(record.get("metadata", {}))
        raw_value = metadata.get("applied_setup_labels", [])
        normalized = self._normalize_string_list(raw_value)
        if normalized:
            return normalized

        text = str(record.get("text", "")).strip()
        match = re.search(r"Applied setup labels:\n((?:- .+\n?){1,8})", text)
        if not match:
            return []
        return [
            line.removeprefix("- ").strip()
            for line in match.group(1).splitlines()
            if line.removeprefix("- ").strip()
        ]

    def _format_counter(self, counter: Counter[str], *, top_n: int) -> list[CountedLabel]:
        """Format a counter into a stable list of count entries."""
        return [
            {"label": label, "count": count}
            for label, count in counter.most_common(top_n)
        ]

    def _build_guidance_prior_summary(
        self,
        *,
        symbol: str | None,
        market_regime: str | None,
        primary_setup_label: str | None,
        total_observations: int,
        top_guidance: list[dict[str, Any]],
        recommendation_breakdown: list[dict[str, Any]],
    ) -> str:
        """Render a short natural-language summary for prompt usage."""
        if total_observations <= 0 or not top_guidance:
            return ""

        scope_parts = [item for item in (symbol, market_regime, primary_setup_label) if item]
        scope_prefix = ""
        if scope_parts:
            scope_prefix = f"For {' / '.join(scope_parts)}, "
        lead_guidance = top_guidance[0]
        guidance_label = str(lead_guidance.get("label", "")).strip()
        guidance_count = int(lead_guidance.get("count", 0) or 0)
        summary = (
            f"{scope_prefix}recurring applied guidance has most often emphasized "
            f"'{guidance_label}' ({guidance_count} observation"
            f"{'' if guidance_count == 1 else 's'}"
            ")."
        )
        if recommendation_breakdown:
            labels = ", ".join(
                str(item.get("label", "")).strip()
                for item in recommendation_breakdown[:2]
                if str(item.get("label", "")).strip()
            )
            if labels:
                summary += f" It has most often appeared with {labels} decisions."
        return summary

    def _build_setup_outcome_summary(
        self,
        *,
        symbol: str | None,
        market_regime: str | None,
        primary_setup_label: str | None,
        reviewed_observations: int,
        outcome_breakdown: list[dict[str, Any]],
        recommendation_breakdown: list[dict[str, Any]],
        outcome_bias: str,
    ) -> str:
        """Render a short natural-language outcome summary for prompt usage."""
        if reviewed_observations <= 0 or not outcome_breakdown:
            return ""

        scope_parts = [item for item in (symbol, market_regime, primary_setup_label) if item]
        scope_prefix = ""
        if scope_parts:
            scope_prefix = f"For {' / '.join(scope_parts)}, "

        lead_outcomes = ", ".join(
            f"{item['label']} ({item['count']})"
            for item in outcome_breakdown[:2]
            if str(item.get("label", "")).strip()
        )
        summary = (
            f"{scope_prefix}reviewed setup outcomes have skewed {outcome_bias} across "
            f"{reviewed_observations} post-trade case"
            f"{'' if reviewed_observations == 1 else 's'}"
        )
        if lead_outcomes:
            summary += f", led by {lead_outcomes}."
        else:
            summary += "."

        if recommendation_breakdown:
            labels = ", ".join(
                str(item.get("label", "")).strip()
                for item in recommendation_breakdown[:2]
                if str(item.get("label", "")).strip()
            )
            if labels:
                summary += f" Historical recommendations have most often clustered around {labels}."
        return summary

    def _build_setup_recommendation_outcome_summary(
        self,
        *,
        symbol: str | None,
        market_regime: str | None,
        primary_setup_label: str | None,
        recommendation_outcomes: list[dict[str, Any]],
    ) -> str:
        """Render a short natural-language summary of recommendation-to-outcome patterns."""
        if not recommendation_outcomes:
            return ""

        scope_parts = [item for item in (symbol, market_regime, primary_setup_label) if item]
        scope_prefix = ""
        if scope_parts:
            scope_prefix = f"For {' / '.join(scope_parts)}, "

        summary_parts: list[str] = []
        for item in recommendation_outcomes[:2]:
            recommendation = str(item.get("recommendation", "")).strip()
            dominant_outcome = str(item.get("dominant_outcome", "")).strip()
            total = int(item.get("total_observations", 0) or 0)
            if not recommendation or not dominant_outcome or total <= 0:
                continue
            summary_parts.append(
                f"{recommendation} has most often led to {dominant_outcome} outcomes ({total} case"
                f"{'' if total == 1 else 's'})"
            )

        if not summary_parts:
            return ""
        return scope_prefix + "; ".join(summary_parts) + "."

    def _infer_outcome_bias(self, outcome_counter: Counter[str]) -> str:
        """Classify a setup's historical outcome skew for bounded confidence checks."""
        worked_count = int(outcome_counter.get("worked", 0) or 0)
        cautionary_count = int(outcome_counter.get("failed", 0) or 0) + int(
            outcome_counter.get("mixed", 0) or 0
        )
        reviewed_count = worked_count + cautionary_count
        if reviewed_count < 2:
            return "mixed"
        if cautionary_count >= worked_count + 1:
            return "cautionary"
        if worked_count >= cautionary_count + 1:
            return "constructive"
        return "mixed"

    def _format_recommendation_outcomes(
        self,
        recommendation_outcomes: dict[str, Counter[str]],
        *,
        top_n: int,
    ) -> list[dict[str, Any]]:
        """Format nested recommendation-to-outcome counters into a stable summary payload."""
        sorted_items = sorted(
            recommendation_outcomes.items(),
            key=lambda item: (-sum(item[1].values()), item[0]),
        )
        formatted: list[dict[str, Any]] = []
        for recommendation, outcome_counter in sorted_items[:top_n]:
            total_observations = sum(outcome_counter.values())
            outcome_breakdown = self._format_counter(outcome_counter, top_n=max(top_n, 4))
            formatted.append(
                {
                    "recommendation": recommendation,
                    "total_observations": total_observations,
                    "outcome_breakdown": outcome_breakdown,
                    "dominant_outcome": outcome_breakdown[0]["label"] if outcome_breakdown else None,
                    "outcome_bias": self._infer_outcome_bias(outcome_counter),
                }
            )
        return formatted

    def _scenario_overlap_score(
        self,
        record: dict[str, Any],
        scenario_profile: dict[str, Any],
    ) -> int:
        """Score overlap between a stored observation and a requested setup profile."""
        metadata = dict(record.get("metadata", {}))
        overlap_fields = (
            "signal_tags",
            "risk_tags",
            "timing_tags",
            "portfolio_state_tags",
        )
        score = 0
        for field_name in overlap_fields:
            target_values = self._normalize_string_list(scenario_profile.get(field_name))
            metadata_values = self._normalize_string_list(metadata.get(field_name))
            if not target_values or not metadata_values:
                continue
            score += len(
                {
                    value.strip().lower()
                    for value in target_values
                    if value.strip()
                }.intersection(
                    {
                        value.strip().lower()
                        for value in metadata_values
                        if value.strip()
                    }
                )
            )
        return score

    def _matches_any_setup_label(
        self,
        record: dict[str, Any],
        setup_labels: list[str],
    ) -> bool:
        """Return whether a record contains any of the requested setup labels."""
        metadata = dict(record.get("metadata", {}))
        record_setup_labels = {
            value.strip().lower()
            for value in self._normalize_string_list(metadata.get("setup_labels"))
            if value.strip()
        }
        if not record_setup_labels:
            primary_label = str(metadata.get("primary_setup_label", "")).strip().lower()
            if primary_label:
                record_setup_labels.add(primary_label)
        requested_labels = {
            value.strip().lower()
            for value in setup_labels
            if str(value).strip()
        }
        return bool(record_setup_labels.intersection(requested_labels))

    def _scenario_market_regime(self, scenario_profile: dict[str, Any] | None) -> str | None:
        """Extract a normalized market-regime label from a scenario profile."""
        if not isinstance(scenario_profile, dict):
            return None
        market_regime = str(scenario_profile.get("market_regime", "")).strip().lower()
        return market_regime or None
