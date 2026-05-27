"""Ranking and scoring helpers for decision-memory document retrieval."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from ....knowledge.repository import DatasetName
from ..setup_taxonomy import infer_setup_labels
from .schema import validate_decision_memory_record

if TYPE_CHECKING:
    from ....agents.decision.base_agent import DecisionTask


class DecisionRankingMixin:
    """Mixin supplying document scoring, ranking, and portfolio-extraction helpers."""

    def _build_ranked_document(
        self,
        document: Any,
        *,
        query: str,
        scenario_profile: dict[str, Any],
        guidance_priors: dict[str, Any],
        task: "DecisionTask",
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        """Score a candidate decision-memory document against the current task."""
        metadata = dict(validation.get("normalized_metadata", {}))
        score = 0.0
        match_reasons: list[str] = []
        primary_identity_match = False
        structured_overlap_count = 0

        text_score = self._text_overlap_score(query=query, document=document)
        score += text_score
        if text_score > 0:
            match_reasons.append("textual overlap with the current analyst synthesis")

        if task.symbol and str(metadata.get("symbol", "")).strip().upper() == task.symbol.upper():
            score += 6.0
            match_reasons.append("same symbol")
            primary_identity_match = True

        metadata_subject = str(metadata.get("subject", "")).lower()
        if task.subject and task.subject.lower() in metadata_subject:
            score += 3.0
            match_reasons.append("similar subject framing")
            primary_identity_match = True

        market_regime = str(metadata.get("market_regime", "")).strip().lower()
        if market_regime and market_regime == str(scenario_profile.get("market_regime", "")).lower():
            score += 3.0
            match_reasons.append("matching market regime")
            structured_overlap_count += 1

        analyst_alignment = str(metadata.get("analyst_alignment", "")).strip().lower()
        if analyst_alignment and analyst_alignment == str(
            scenario_profile.get("analyst_alignment", "")
        ).lower():
            score += 2.0
            match_reasons.append("similar analyst alignment")
            structured_overlap_count += 1

        signal_overlap = self._metadata_overlap(
            scenario_profile.get("signal_tags", []),
            metadata,
            field_names=("signal_tags", "tags"),
        )
        if signal_overlap:
            score += 2.0 * len(signal_overlap)
            match_reasons.append(f"shared signal tags: {', '.join(signal_overlap)}")
            structured_overlap_count += len(signal_overlap)

        risk_overlap = self._metadata_overlap(
            scenario_profile.get("risk_tags", []),
            metadata,
            field_names=("risk_tags", "tags"),
        )
        if risk_overlap:
            score += 2.0 * len(risk_overlap)
            match_reasons.append(f"shared risk tags: {', '.join(risk_overlap)}")
            structured_overlap_count += len(risk_overlap)

        timing_overlap = self._metadata_overlap(
            scenario_profile.get("timing_tags", []),
            metadata,
            field_names=("timing_tags", "tags"),
        )
        if timing_overlap:
            score += 1.5 * len(timing_overlap)
            match_reasons.append(f"shared timing tags: {', '.join(timing_overlap)}")
            structured_overlap_count += len(timing_overlap)

        portfolio_state_overlap = self._metadata_overlap(
            scenario_profile.get("portfolio_state_tags", []),
            metadata,
            field_names=("portfolio_state_tags", "tags"),
        )
        if portfolio_state_overlap:
            score += 2.5 * len(portfolio_state_overlap)
            match_reasons.append(
                f"shared portfolio state tags: {', '.join(portfolio_state_overlap)}"
            )
            structured_overlap_count += len(portfolio_state_overlap)

        setup_label_overlap = self._setup_label_overlap(scenario_profile, metadata)
        if setup_label_overlap:
            score += 3.0 * len(setup_label_overlap)
            match_reasons.append(f"shared setup labels: {', '.join(setup_label_overlap)}")
            structured_overlap_count += len(setup_label_overlap)

        source_type = str(metadata.get("source_type", "")).strip().lower()
        if source_type == "internal":
            score += 0.5

        outcome_label = str(metadata.get("outcome_label", "")).strip().lower()
        if outcome_label == "worked":
            score += 0.5

        memory_type = str(metadata.get("memory_type", "")).strip().lower()
        if memory_type == "decision_postmortem":
            score += 0.75
            match_reasons.append("postmortem memory with reusable review lessons")

        guidance_alignment_score = self._guidance_prior_alignment_score(
            document=document,
            guidance_priors=guidance_priors,
        )
        if guidance_alignment_score > 0:
            score += guidance_alignment_score
            match_reasons.append("aligned with recurring guidance priors for this symbol")

        metadata_quality = self._safe_float(metadata.get("quality_score")) or 0.0
        score += min(metadata_quality, 1.0) * 2.0

        fit = self._score_to_fit(
            score,
            primary_identity_match=primary_identity_match,
            structured_overlap_count=structured_overlap_count,
        )
        return {
            "document": document,
            "score": round(score, 3),
            "fit": fit,
            "fit_rank": {"high": 3, "medium": 2, "low": 1}[fit],
            "match_reasons": match_reasons or ["fallback decision-memory reference"],
            "metadata_quality": metadata_quality,
            "validation": validation,
        }

    def _validate_candidate(
        self,
        document: Any,
        *,
        allowed_datasets: Iterable[DatasetName] | None = None,
    ) -> dict[str, Any]:
        """Validate a candidate document before it participates in ranking."""
        record = {
            "text": getattr(document, "page_content", ""),
            "metadata": dict(getattr(document, "metadata", {})),
        }
        return validate_decision_memory_record(
            record,
            allowed_datasets=allowed_datasets,
        )

    def _text_overlap_score(self, *, query: str, document: Any) -> float:
        """Compute a small lexical overlap score for the current query."""
        stopwords = {
            "current",
            "analyst",
            "analysis",
            "evidence",
            "supports",
            "stance",
            "subject",
            "symbol",
            "setup",
            "with",
            "from",
            "that",
            "this",
            "into",
        }
        query_terms = {
            term
            for term in self._tokenize(query)
            if len(term) > 3 and term not in stopwords
        }
        metadata = dict(getattr(document, "metadata", {}))
        haystack = " ".join(
            [
                getattr(document, "page_content", ""),
                str(metadata.get("title", "")),
                str(metadata.get("subject", "")),
                " ".join(str(tag) for tag in metadata.get("tags", [])),
                " ".join(str(tag) for tag in metadata.get("signal_tags", [])),
                " ".join(str(tag) for tag in metadata.get("risk_tags", [])),
                " ".join(str(tag) for tag in metadata.get("timing_tags", [])),
            ]
        ).lower()
        haystack_terms = set(self._tokenize(haystack))
        return float(min(sum(1 for term in query_terms if term in haystack_terms), 4))

    def _guidance_prior_alignment_score(
        self,
        *,
        document: Any,
        guidance_priors: dict[str, Any],
    ) -> float:
        """Apply a small boost when a document aligns with recurring guidance priors."""
        top_guidance = guidance_priors.get("top_guidance", [])
        if not isinstance(top_guidance, list) or not top_guidance:
            return 0.0

        metadata = dict(getattr(document, "metadata", {}))
        haystack = " ".join(
            [
                getattr(document, "page_content", ""),
                str(metadata.get("title", "")),
                str(metadata.get("subject", "")),
                " ".join(str(tag) for tag in metadata.get("tags", [])),
                " ".join(str(tag) for tag in metadata.get("signal_tags", [])),
                " ".join(str(tag) for tag in metadata.get("risk_tags", [])),
            ]
        ).lower()
        haystack_terms = set(self._tokenize(haystack))

        overlap_count = 0
        for item in top_guidance[:2]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip().lower()
            if not label:
                continue
            guidance_terms = {
                term
                for term in self._tokenize(label)
                if len(term) > 4 and term not in {"before", "after", "prior", "decisions"}
            }
            overlap_count += sum(1 for term in guidance_terms if term in haystack_terms)

        if overlap_count >= 4:
            return 1.5
        if overlap_count >= 2:
            return 0.75
        return 0.0

    def _setup_label_overlap(
        self,
        scenario_profile: dict[str, Any],
        metadata: dict[str, Any],
    ) -> list[str]:
        """Return overlapping setup labels between the current setup and record metadata."""
        target_setup_labels = infer_setup_labels(scenario_profile)
        metadata_setup_labels = self._metadata_list(metadata, "setup_labels")
        primary_setup_label = str(metadata.get("primary_setup_label", "")).strip().lower()
        if primary_setup_label and primary_setup_label not in metadata_setup_labels:
            metadata_setup_labels.append(primary_setup_label)
        metadata_setup_label_set = {
            label.strip().lower()
            for label in metadata_setup_labels
            if label.strip()
        }
        return [
            label
            for label in target_setup_labels
            if label.strip().lower() in metadata_setup_label_set
        ]

    def _metadata_overlap(
        self,
        target_tags: list[str],
        metadata: dict[str, Any],
        *,
        field_names: tuple[str, ...],
    ) -> list[str]:
        """Return overlapping tags between the scenario profile and document metadata."""
        metadata_tags: set[str] = set()
        for field_name in field_names:
            raw_value = metadata.get(field_name, [])
            if isinstance(raw_value, list):
                metadata_tags.update(
                    str(item).strip().lower() for item in raw_value if str(item).strip()
                )
        return [tag for tag in target_tags if tag.lower() in metadata_tags]

    def _metadata_list(self, metadata: dict[str, Any], field_name: str) -> list[str]:
        """Normalize one metadata field into a lowercase string list."""
        raw_value = metadata.get(field_name, [])
        if isinstance(raw_value, list):
            return [str(item).strip().lower() for item in raw_value if str(item).strip()]
        if isinstance(raw_value, str) and raw_value.strip():
            return [raw_value.strip().lower()]
        return []

    def _score_to_fit(
        self,
        score: float,
        *,
        primary_identity_match: bool,
        structured_overlap_count: int,
    ) -> str:
        """Convert a numeric retrieval score into a fit label."""
        if score >= 11 and primary_identity_match and structured_overlap_count >= 2:
            return "high"
        if score >= 5:
            return "medium"
        return "low"

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase alphanumeric terms."""
        return re.findall(r"[a-z0-9_+-]+", text.lower())

    def _extract_postmortem_sections(self, document: dict[str, Any]) -> list[str]:
        """Extract lesson-like bullet points from a serialized postmortem document."""
        text = str(document.get("text", "")).strip()
        if not text:
            return []

        sections: list[str] = []
        for heading in ("Reusable lessons:", "Future adjustments:"):
            pattern = rf"{re.escape(heading)}\n((?:- .+\n?){{1,6}})"
            match = re.search(pattern, text)
            if not match:
                continue
            block = match.group(1)
            for line in block.splitlines():
                normalized = line.removeprefix("- ").strip()
                if normalized:
                    sections.append(normalized)
        return sections[:3]

    def _matches_metadata_filter(
        self,
        metadata: dict[str, Any],
        metadata_filter: dict[str, Any] | None,
    ) -> bool:
        """Apply exact-match filtering over document metadata."""
        if not metadata_filter:
            return True
        for key, expected_value in metadata_filter.items():
            if metadata.get(key) != expected_value:
                return False
        return True

    def _safe_float(self, value: Any) -> float | None:
        """Convert optional numeric-like values into floats."""
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                return None
        return None

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
        """Extract the active single-name limit if available."""
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
