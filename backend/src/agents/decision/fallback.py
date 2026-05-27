"""Fallback and helper methods for advisory decision synthesis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...services.decision.setup_taxonomy import infer_setup_labels
from .base_agent import ALLOWED_CONFIDENCE

if TYPE_CHECKING:
    from .base_agent import DecisionTask


class DecisionFallbackMixin:
    """Mixin supplying fallback logic and portfolio-context helpers."""

    def _fallback_recommendation(self, task: DecisionTask) -> str:
        """Generate a conservative recommendation when no model output is available."""
        portfolio_context = task.portfolio_context or {}
        current_position = self._find_symbol_position(portfolio_context, task.symbol)
        current_weight = self._extract_position_weight(current_position)
        max_weight = self._extract_max_single_name_pct(portfolio_context)
        cash_pct = self._extract_percent(portfolio_context.get("cash_pct"))
        has_conflict = self._has_material_conflict(task.cross_analyst_observations)
        confidence = self._normalize_confidence(task.overall_confidence)

        if current_weight is not None and max_weight is not None and current_weight > max_weight:
            return "consider_reduce"
        if not task.key_signals:
            return "no_trade"
        if has_conflict:
            return "keep_watch"
        if (
            current_weight is not None
            and max_weight is not None
            and current_weight >= max_weight * 0.9
        ):
            return "hold"
        if current_weight is None and confidence == "high" and (cash_pct is None or cash_pct >= 5):
            return "consider_buy"
        if current_weight is None and cash_pct is not None and cash_pct < 5:
            return "keep_watch"
        if confidence == "high":
            return "hold"
        return "keep_watch"

    def _fallback_position_impact(
        self,
        task: DecisionTask,
        recommendation: str,
    ) -> str:
        """Describe portfolio impact using current holdings when available."""
        portfolio_context = task.portfolio_context or {}
        current_position = self._find_symbol_position(portfolio_context, task.symbol)
        current_weight = self._extract_position_weight(current_position)
        cash_pct = self._extract_percent(portfolio_context.get("cash_pct"))
        max_weight = self._extract_max_single_name_pct(portfolio_context)

        if task.symbol and current_weight is not None:
            if recommendation == "consider_reduce":
                return (
                    f"The current {task.symbol} position is about {current_weight:.1f}% and the "
                    "advisory stance favors reducing exposure rather than adding to it."
                )
            if recommendation == "hold":
                return (
                    f"The current {task.symbol} position is about {current_weight:.1f}% and the "
                    "advisory stance is to maintain that exposure for now."
                )
            return (
                f"The current {task.symbol} position is about {current_weight:.1f}% and the "
                "advisory stance does not support immediate resizing."
            )

        if task.symbol and recommendation == "consider_buy":
            if cash_pct is not None and max_weight is not None:
                return (
                    f"No existing {task.symbol} position was identified. With cash near "
                    f"{cash_pct:.1f}% and a single-name limit near {max_weight:.1f}%, the "
                    "current setup supports considering a measured new position rather than a full-size entry."
                )
            if cash_pct is not None:
                return (
                    f"No existing {task.symbol} position was identified. Cash is about "
                    f"{cash_pct:.1f}%, so the setup can be treated as a measured add candidate."
                )
            return (
                f"No existing {task.symbol} position was identified, and the current setup "
                "supports only a measured initial exposure rather than an aggressive entry."
            )

        if task.symbol and recommendation in {"keep_watch", "no_trade"}:
            base = f"No existing {task.symbol} position was identified."
            if cash_pct is not None:
                return (
                    f"{base} Cash is about {cash_pct:.1f}%, but the current setup does not yet "
                    "justify adding new exposure."
                )
            return f"{base} The current setup does not yet justify adding new exposure."

        if task.symbol and recommendation == "hold" and max_weight is not None:
            return (
                f"Any future exposure to {task.symbol} should stay mindful of the single-name "
                f"limit near {max_weight:.1f}%."
            )

        return (
            "The current advisory stance is not expected to materially change portfolio exposure "
            "until stronger confirmation appears."
        )

    def _fallback_timing_decision(
        self,
        task: DecisionTask,
        recommendation: str,
    ) -> str:
        """Provide a bounded view on timing rather than an execution instruction."""
        scenario_profile = self._scenario_profile_from_task(task)
        cash_pct = self._extract_percent((task.portfolio_context or {}).get("cash_pct"))
        if recommendation == "consider_reduce":
            return "Current conditions support reviewing exposure now rather than waiting for a stronger risk signal."
        if recommendation == "consider_buy":
            if "near_local_high" in scenario_profile.get("timing_tags", []):
                return "The setup is constructive, but because it looks extended, any new exposure should wait for confirmation or be sized in gradually."
            return "The setup is constructive enough to consider a measured entry now, provided exposure is staged rather than rushed."
        if self._has_material_conflict(task.cross_analyst_observations):
            return "Waiting for clearer analyst alignment is preferable before changing exposure."
        if "near_local_high" in scenario_profile.get("timing_tags", []):
            return "The setup looks extended, so waiting for better confirmation or a less stretched entry is preferable."
        if cash_pct is not None and cash_pct < 5:
            return "Limited cash makes immediate action less attractive, so timing should improve only if conviction strengthens meaningfully."
        if self._normalize_confidence(task.overall_confidence) == "high":
            return "The setup is actionable only in a measured way, with preference for staged decision-making over urgency."
        return "The current setup is better treated as a watchlist decision than an immediate portfolio action."

    def _fallback_action_conditions(
        self,
        task: DecisionTask,
        recommendation: str,
    ) -> list[str]:
        """List the conditions that would strengthen the advisory stance."""
        conditions = [
            "Keep the recommendation bounded to current analyst evidence and any matching decision-memory cases.",
        ]
        if task.key_signals:
            conditions.append(
                f"Act only if the leading signals remain intact: {', '.join(task.key_signals[:2])}."
            )
        cash_pct = self._extract_percent((task.portfolio_context or {}).get("cash_pct"))
        max_weight = self._extract_max_single_name_pct(task.portfolio_context or {})
        if max_weight is not None and task.symbol:
            conditions.append(
                f"Any exposure change should remain within the single-name limit near {max_weight:.1f}%."
            )
        if recommendation == "consider_buy" and cash_pct is not None:
            conditions.append(
                f"Keep enough liquidity after any entry; current cash is about {cash_pct:.1f}%."
            )
        if recommendation in {"keep_watch", "no_trade"}:
            conditions.append(
                "Look for stronger cross-analyst confirmation before upgrading the stance."
            )
        return conditions

    def _fallback_no_action_reasons(
        self,
        task: DecisionTask,
        recommendation: str,
    ) -> list[str]:
        """Explain why the current stance is still constrained."""
        reasons: list[str] = []
        if recommendation in {"keep_watch", "no_trade", "hold"}:
            reasons.append("Current evidence does not yet justify a more aggressive portfolio change.")
        if self._has_material_conflict(task.cross_analyst_observations):
            reasons.append(
                "Cross-analyst alignment is not strong enough to support a higher-conviction action."
            )
        cash_pct = self._extract_percent((task.portfolio_context or {}).get("cash_pct"))
        if recommendation != "consider_buy" and cash_pct is not None and cash_pct < 5:
            reasons.append(
                "Available cash is limited, which reduces flexibility for adding new exposure."
            )
        current_weight = self._extract_position_weight(
            self._find_symbol_position(task.portfolio_context or {}, task.symbol)
        )
        max_weight = self._extract_max_single_name_pct(task.portfolio_context or {})
        if (
            recommendation == "hold"
            and current_weight is not None
            and max_weight is not None
            and current_weight >= max_weight * 0.9
        ):
            reasons.append("Current exposure is already close to the single-name limit.")
        if task.portfolio_risks:
            reasons.append(f"Key risks remain active: {', '.join(task.portfolio_risks[:2])}.")
        if not reasons:
            reasons.append("The current stance remains advisory and conditional rather than execution-oriented.")
        return reasons

    def _fallback_reference_cases(
        self,
        decision_context: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Convert retrieved decision-memory documents into compact reference case records."""
        reference_cases: list[dict[str, str]] = []
        for document in decision_context.get("documents", [])[:3]:
            metadata = dict(document.get("metadata", {}))
            reference_cases.append(
                {
                    "title": str(document.get("title", "")).strip() or "Untitled decision case",
                    "memory_type": str(metadata.get("memory_type", "decision_case")).strip()
                    or "decision_case",
                    "fit": str(document.get("fit") or metadata.get("fit") or "medium").strip().lower()
                    or "medium",
                    "why_relevant": "; ".join(document.get("match_reasons", [])[:2])
                    or str(metadata.get("subject", "")).strip()
                    or "Retrieved as a potentially similar decision-memory case.",
                }
            )
        return reference_cases

    def _fallback_postmortem_lessons(
        self,
        decision_context: dict[str, Any],
    ) -> list[str]:
        """Return compact lesson strings extracted from retrieved postmortem memories."""
        lessons: list[str] = []
        for item in decision_context.get("postmortem_lessons", [])[:3]:
            if not isinstance(item, dict):
                continue
            lesson = str(item.get("lesson", "")).strip()
            if lesson:
                lessons.append(lesson)
        return lessons

    def _fallback_guidance_priors(
        self,
        decision_context: dict[str, Any],
    ) -> list[str]:
        """Return recurring guidance strings from historical guidance observations."""
        priors = dict(decision_context.get("guidance_priors", {}))
        guidance_items = priors.get("top_guidance", [])
        if not isinstance(guidance_items, list):
            return []
        lessons: list[str] = []
        for item in guidance_items[:2]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip()
            count = int(item.get("count", 0) or 0)
            if not label:
                continue
            if count > 1:
                lessons.append(f"{label} (seen {count} times in prior decisions)")
            else:
                lessons.append(label)
        return lessons

    def _fallback_applied_setup_labels(
        self,
        decision_context: dict[str, Any],
    ) -> list[str]:
        """Return the most relevant setup labels used by the current recommendation."""
        labels: list[str] = []
        for label in infer_setup_labels(decision_context.get("scenario_profile", {})):
            if label not in labels:
                labels.append(label)
        for document in decision_context.get("documents", [])[:2]:
            if not isinstance(document, dict):
                continue
            metadata = dict(document.get("metadata", {}))
            for raw_label in metadata.get("setup_labels", [])[:2] if isinstance(metadata.get("setup_labels", []), list) else []:
                label = str(raw_label).strip().lower()
                if label and label not in labels:
                    labels.append(label)
            primary_label = str(metadata.get("primary_setup_label", "")).strip().lower()
            if primary_label and primary_label not in labels:
                labels.append(primary_label)
        return labels[:3]

    def _fallback_setup_outcome_priors(
        self,
        decision_context: dict[str, Any],
    ) -> str:
        """Return a short setup-outcome summary when historical postmortems are informative."""
        priors = dict(decision_context.get("setup_outcome_priors", {}))
        reviewed_observations = int(priors.get("reviewed_observations", 0) or 0)
        if reviewed_observations < 2:
            return ""

        outcome_breakdown = priors.get("outcome_breakdown", [])
        if not isinstance(outcome_breakdown, list) or not outcome_breakdown:
            return ""

        scope_parts = [
            item
            for item in (
                str(priors.get("symbol") or "").strip().upper() or None,
                str(priors.get("market_regime", "")).strip().lower() or None,
                str(priors.get("primary_setup_label", "")).strip().lower() or None,
            )
            if item
        ]
        scope_prefix = f"For {' / '.join(scope_parts)}, " if scope_parts else ""
        dominant_outcomes = ", ".join(
            f"{item['label']} ({item['count']})"
            for item in outcome_breakdown[:2]
            if isinstance(item, dict) and str(item.get("label", "")).strip()
        )
        if not dominant_outcomes:
            return ""
        return (
            f"{scope_prefix}historical postmortem outcomes for this setup have most often been "
            f"{dominant_outcomes}."
        )

    def _fallback_setup_recommendation_outcome_priors(
        self,
        decision_context: dict[str, Any],
        *,
        recommendation: str,
    ) -> str:
        """Return a short summary for how the current recommendation resolved in similar setups."""
        priors = dict(decision_context.get("setup_recommendation_outcome_priors", {}))
        recommendation_outcomes = priors.get("recommendation_outcomes", [])
        if not isinstance(recommendation_outcomes, list) or not recommendation_outcomes:
            return ""

        matched_item = self._matching_recommendation_outcome_item(
            recommendation_outcomes,
            recommendation=recommendation,
        )
        if not matched_item:
            return ""

        total_observations = int(matched_item.get("total_observations", 0) or 0)
        dominant_outcome = str(matched_item.get("dominant_outcome", "")).strip().lower()
        if total_observations < 2 or not dominant_outcome:
            return ""

        scope_parts = [
            item
            for item in (
                str(priors.get("symbol") or "").strip().upper() or None,
                str(priors.get("market_regime", "")).strip().lower() or None,
                str(priors.get("primary_setup_label", "")).strip().lower() or None,
            )
            if item
        ]
        scope_prefix = f"For {' / '.join(scope_parts)}, " if scope_parts else ""
        return (
            f"{scope_prefix}{recommendation} has historically resolved most often as "
            f"{dominant_outcome} across {total_observations} similar case"
            f"{'' if total_observations == 1 else 's'}."
        )

    def _fallback_case_fit_assessment(
        self,
        reference_cases: list[dict[str, str]],
    ) -> str:
        """Summarize how well retrieved reference cases match the current setup."""
        if not reference_cases:
            return (
                "No matching decision-memory cases were retrieved, so the recommendation relies on "
                "current analyst synthesis only."
            )

        fits = [str(case.get("fit", "low")).strip().lower() for case in reference_cases]
        if any(fit == "high" for fit in fits):
            return (
                "At least one reference case shows high scenario fit, but it remains supporting "
                "context rather than an instruction to copy."
            )
        if any(fit == "medium" for fit in fits):
            return (
                "Reference cases show partial scenario fit and were used to frame similarities and "
                "differences, not to force a decision."
            )
        return (
            "The retrieved reference cases have weak scenario fit, so they mainly serve as a "
            "confidence check rather than a directional guide."
        )

    def _fallback_confidence(
        self,
        task: DecisionTask,
        *,
        decision_context: dict[str, Any],
        recommendation: str,
    ) -> tuple[str, str]:
        """Apply bounded confidence adjustments using historical guidance and outcomes."""
        base_confidence = self._normalize_confidence(task.overall_confidence)
        note_parts: list[str] = []

        priors = dict(decision_context.get("guidance_priors", {}))
        total_observations = int(priors.get("total_observations", 0) or 0)
        recommendation_breakdown = priors.get("recommendation_breakdown", [])
        if total_observations >= 2 and isinstance(recommendation_breakdown, list) and recommendation_breakdown:
            dominant_item = recommendation_breakdown[0]
            if isinstance(dominant_item, dict):
                dominant_recommendation = str(dominant_item.get("label", "")).strip().lower()
                dominant_count = int(dominant_item.get("count", 0) or 0)
                if dominant_count >= 2 and self._is_confidence_conflict(
                    recommendation=recommendation,
                    dominant_recommendation=dominant_recommendation,
                ):
                    symbol = str(priors.get("symbol") or task.symbol or "").strip().upper()
                    market_regime = str(priors.get("market_regime", "")).strip().lower()
                    scope_parts = [item for item in (symbol, market_regime) if item]
                    scope_prefix = f"For {' / '.join(scope_parts)}, " if scope_parts else ""
                    note_parts.append(
                        f"{scope_prefix}recurring guidance has more often accompanied "
                        f"{dominant_recommendation} decisions ({dominant_count} observations), so "
                        "confidence stays one step lower."
                    )

        setup_outcome_priors = dict(decision_context.get("setup_outcome_priors", {}))
        reviewed_observations = int(setup_outcome_priors.get("reviewed_observations", 0) or 0)
        outcome_bias = str(setup_outcome_priors.get("outcome_bias", "")).strip().lower()
        if reviewed_observations >= 2 and self._is_outcome_prior_conflict(
            recommendation=recommendation,
            outcome_bias=outcome_bias,
        ):
            scope_parts = [
                item
                for item in (
                    str(setup_outcome_priors.get("symbol") or task.symbol or "").strip().upper() or None,
                    str(setup_outcome_priors.get("market_regime", "")).strip().lower() or None,
                    str(setup_outcome_priors.get("primary_setup_label", "")).strip().lower() or None,
                )
                if item
            ]
            scope_prefix = f"For {' / '.join(scope_parts)}, " if scope_parts else ""
            note_parts.append(
                f"{scope_prefix}reviewed postmortem outcomes for this setup have skewed "
                f"{outcome_bias} across {reviewed_observations} cases, so confidence stays one "
                "step lower."
            )

        recommendation_outcome_priors = dict(
            decision_context.get("setup_recommendation_outcome_priors", {})
        )
        matched_recommendation_outcome = self._matching_recommendation_outcome_item(
            recommendation_outcome_priors.get("recommendation_outcomes", []),
            recommendation=recommendation,
        )
        if isinstance(matched_recommendation_outcome, dict):
            total_recommendation_observations = int(
                matched_recommendation_outcome.get("total_observations", 0) or 0
            )
            recommendation_outcome_bias = str(
                matched_recommendation_outcome.get("outcome_bias", "")
            ).strip().lower()
            if total_recommendation_observations >= 2 and self._is_recommendation_outcome_prior_conflict(
                recommendation=recommendation,
                outcome_bias=recommendation_outcome_bias,
            ):
                scope_parts = [
                    item
                    for item in (
                        str(recommendation_outcome_priors.get("symbol") or task.symbol or "").strip().upper() or None,
                        str(recommendation_outcome_priors.get("market_regime", "")).strip().lower() or None,
                        str(recommendation_outcome_priors.get("primary_setup_label", "")).strip().lower() or None,
                    )
                    if item
                ]
                scope_prefix = f"For {' / '.join(scope_parts)}, " if scope_parts else ""
                note_parts.append(
                    f"{scope_prefix}{recommendation} has historically resolved in a more "
                    f"{recommendation_outcome_bias} way across {total_recommendation_observations} "
                    "similar cases, so confidence stays one step lower."
                )

        if not note_parts:
            return base_confidence, ""

        adjusted_confidence = self._downgrade_confidence(base_confidence)
        if adjusted_confidence == base_confidence:
            return base_confidence, ""
        return adjusted_confidence, " ".join(note_parts)

    def _normalize_string_list(self, value: Any, *, fallback: list[str]) -> list[str]:
        """Normalize a model value into a non-empty list of strings."""
        if isinstance(value, list):
            normalized = [str(item).strip() for item in value if str(item).strip()]
            return normalized or fallback
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return fallback

    def _normalize_reference_cases(
        self,
        value: Any,
        *,
        fallback: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Normalize model output into the reference-case schema."""
        if not isinstance(value, list):
            return fallback

        normalized_cases: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            memory_type = str(item.get("memory_type", "decision_case")).strip() or "decision_case"
            fit = str(item.get("fit", "medium")).strip().lower() or "medium"
            if fit not in {"high", "medium", "low"}:
                fit = "medium"
            why_relevant = (
                str(item.get("why_relevant", "")).strip()
                or "Returned by the decision-memory retrieval layer."
            )
            normalized_cases.append(
                {
                    "title": title,
                    "memory_type": memory_type,
                    "fit": fit,
                    "why_relevant": why_relevant,
                }
            )
        return normalized_cases or fallback

    def _normalize_confidence(self, value: Any) -> str:
        """Normalize confidence labels into the supported set."""
        confidence = str(value or "low").strip().lower()
        if confidence not in ALLOWED_CONFIDENCE:
            return "low"
        return confidence

    def _downgrade_confidence(self, confidence: str) -> str:
        """Lower confidence by one step while staying within the supported set."""
        if confidence == "high":
            return "medium"
        if confidence == "medium":
            return "low"
        return "low"

    def _is_confidence_conflict(
        self,
        *,
        recommendation: str,
        dominant_recommendation: str,
    ) -> bool:
        """Return whether recurring recommendation history conflicts with the current stance."""
        if recommendation == "consider_buy":
            return dominant_recommendation in {"keep_watch", "hold", "no_trade", "consider_reduce"}
        if recommendation == "consider_reduce":
            return dominant_recommendation in {"consider_buy", "hold"}
        return False

    def _matching_recommendation_outcome_item(
        self,
        recommendation_outcomes: list[dict[str, Any]],
        *,
        recommendation: str,
    ) -> dict[str, Any] | None:
        """Return the summary entry for the current recommendation when available."""
        target_recommendation = str(recommendation).strip().lower()
        for item in recommendation_outcomes:
            if not isinstance(item, dict):
                continue
            item_recommendation = str(item.get("recommendation", "")).strip().lower()
            if item_recommendation == target_recommendation:
                return item
        return None

    def _is_outcome_prior_conflict(
        self,
        *,
        recommendation: str,
        outcome_bias: str,
    ) -> bool:
        """Return whether historical setup outcomes argue for lower confidence."""
        if recommendation == "consider_buy":
            return outcome_bias == "cautionary"
        if recommendation == "consider_reduce":
            return outcome_bias == "constructive"
        return False

    def _is_recommendation_outcome_prior_conflict(
        self,
        *,
        recommendation: str,
        outcome_bias: str,
    ) -> bool:
        """Return whether recommendation-specific historical outcomes argue for lower confidence."""
        if recommendation == "consider_buy":
            return outcome_bias == "cautionary"
        if recommendation == "consider_reduce":
            return outcome_bias == "constructive"
        return False

    def summarize_portfolio_context(self, portfolio_context: dict[str, Any] | None) -> str:
        """Summarize portfolio inputs into a compact prompt/debug string."""
        if not isinstance(portfolio_context, dict) or not portfolio_context:
            return ""

        positions = portfolio_context.get("positions")
        position_count = len(positions) if isinstance(positions, list) else 0
        cash_pct = self._extract_percent(portfolio_context.get("cash_pct"))
        max_weight = self._extract_max_single_name_pct(portfolio_context)
        summary_parts = [f"positions={position_count}"]
        if cash_pct is not None:
            summary_parts.append(f"cash_pct={cash_pct:.1f}")
        if max_weight is not None:
            summary_parts.append(f"max_single_name_pct={max_weight:.1f}")
        return ", ".join(summary_parts)

    def _scenario_profile_from_task(self, task: DecisionTask) -> dict[str, Any]:
        """Infer lightweight timing cues directly from the task."""
        combined = " ".join(
            [task.subject, task.extra_context or "", task.overall_summary, *task.cross_analyst_observations]
        ).lower()
        timing_tags: list[str] = []
        if any(keyword in combined for keyword in ("high", "extended", "stretched", "overbought")):
            timing_tags.append("near_local_high")
        if any(keyword in combined for keyword in ("event", "earnings", "guidance", "catalyst")):
            timing_tags.append("event_window")
        return {"timing_tags": timing_tags}

    def _find_symbol_position(
        self,
        portfolio_context: dict[str, Any],
        symbol: str | None,
    ) -> dict[str, Any] | None:
        """Return the current position object for the requested symbol if present."""
        if not symbol:
            return None
        positions = portfolio_context.get("positions", [])
        if not isinstance(positions, list):
            return None
        target_symbol = symbol.strip().upper()
        for position in positions:
            if not isinstance(position, dict):
                continue
            if str(position.get("symbol", "")).strip().upper() == target_symbol:
                return position
        return None

    def _extract_position_weight(self, position: dict[str, Any] | None) -> float | None:
        """Extract a normalized percent weight from a position object."""
        if not isinstance(position, dict):
            return None
        for field_name in ("weight_pct", "weight"):
            value = self._extract_percent(position.get(field_name))
            if value is not None:
                return value
        return None

    def _extract_max_single_name_pct(self, portfolio_context: dict[str, Any]) -> float | None:
        """Extract the active single-name position limit if one is available."""
        direct_value = self._extract_percent(portfolio_context.get("max_single_name_pct"))
        if direct_value is not None:
            return direct_value
        position_limits = portfolio_context.get("position_limits")
        if isinstance(position_limits, dict):
            return self._extract_percent(position_limits.get("max_single_name_pct"))
        return None

    def _extract_percent(self, value: Any) -> float | None:
        """Parse numeric percent-like values into floats."""
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            normalized = value.strip().rstrip("%")
            if not normalized:
                return None
            try:
                return float(normalized)
            except ValueError:
                return None
        return None

    def _has_material_conflict(self, observations: list[str]) -> bool:
        """Detect obvious cross-analyst disagreement from observation strings."""
        conflict_markers = ("disagree", "conflict", "mixed", "diverge", "uncertain")
        for observation in observations:
            normalized = observation.lower()
            if any(marker in normalized for marker in conflict_markers):
                return True
        return False
