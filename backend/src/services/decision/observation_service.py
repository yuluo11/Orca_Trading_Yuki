"""Persistence helpers for postmortem-guidance usage observations."""

from __future__ import annotations

import re
from typing import Any

from ...knowledge.ingest import KnowledgeIngestor
from ...knowledge.repository import DatasetName, KnowledgeRepository
from ...models import (
    DecisionGuidanceObservationRecord,
    GuidanceObservationPersistenceResult,
    extract_decision_output_contract,
)
from .setup_taxonomy import (
    infer_primary_setup_label,
    infer_setup_labels,
    normalize_string_list as normalize_tag_list,
)


class DecisionGuidanceObservationService:
    """Persist structured records describing how decision runs used postmortem guidance."""

    def __init__(
        self,
        repository: KnowledgeRepository | None = None,
        ingestor: KnowledgeIngestor | None = None,
    ) -> None:
        self.repository = repository or KnowledgeRepository()
        self.ingestor = ingestor or KnowledgeIngestor(self.repository)

    def persist_guidance_observation(
        self,
        decision_result: dict[str, Any] | None,
        *,
        dataset: DatasetName = "dynamic",
        force: bool = False,
        record_name: str | None = None,
    ) -> GuidanceObservationPersistenceResult:
        """Persist a decision-guidance observation when applied guidance is present."""
        if not isinstance(decision_result, dict):
            return {
                "status": "skipped",
                "persisted": False,
                "reason": "decision result must be a JSON object",
            }

        applied_guidance = self._normalize_string_list(
            decision_result.get("applied_postmortem_guidance")
        )
        if not applied_guidance and not force:
            return {
                "status": "skipped",
                "persisted": False,
                "reason": "decision result does not include applied_postmortem_guidance",
            }

        record = self.build_guidance_observation_record(
            decision_result,
            dataset=dataset,
            applied_guidance=applied_guidance,
        )
        target_name = record_name or self._build_record_name(decision_result, applied_guidance)

        self._ensure_repository_ready()
        record_path = self.ingestor.ingest_text(
            dataset,
            target_name,
            record["text"],
            metadata=record["metadata"],
        )
        return {
            "status": "persisted",
            "persisted": True,
            "path": str(record_path),
            "record_name": record_path.stem,
            "title": record["metadata"].get("title", record_path.stem),
            "applied_guidance_count": len(applied_guidance),
        }

    def build_guidance_observation_record(
        self,
        decision_result: dict[str, Any],
        *,
        dataset: DatasetName,
        applied_guidance: list[str] | None = None,
    ) -> DecisionGuidanceObservationRecord:
        """Build a processed-record payload describing one decision's guidance usage."""
        contract = extract_decision_output_contract(decision_result)
        normalized_guidance = applied_guidance or self._normalize_string_list(
            contract.get("applied_postmortem_guidance")
        )
        applied_setup_labels = self._normalize_string_list(
            contract.get("applied_setup_labels")
        )
        scenario_profile = self._extract_scenario_profile(decision_result)
        reference_cases = contract.get("reference_cases", [])
        reference_titles = [
            str(item.get("title", "")).strip()
            for item in reference_cases
            if isinstance(item, dict) and str(item.get("title", "")).strip()
        ]

        subject = str(decision_result.get("subject", "")).strip() or "Unspecified decision subject"
        symbol = str(decision_result.get("symbol", "")).strip().upper()
        recommendation = str(contract.get("recommendation", "")).strip().lower() or "keep_watch"
        confidence = str(contract.get("confidence", "")).strip().lower() or "medium"
        title = f"{symbol + ' ' if symbol else ''}{subject} Guidance Observation".strip()

        sections = [
            f"Decision summary: {str(contract.get('decision_summary', '')).strip()}",
            f"Recommendation: {recommendation}",
            f"Confidence: {confidence}",
            self._render_list_section("Applied postmortem guidance", normalized_guidance),
            self._render_list_section("Applied setup labels", applied_setup_labels),
            self._render_text_section("Rationale", contract.get("rationale")),
            self._render_list_section("Reference cases", reference_titles),
            self._render_text_section(
                "Case fit assessment", contract.get("case_fit_assessment")
            ),
        ]
        text = "\n\n".join(section for section in sections if section).strip()

        setup_labels = infer_setup_labels(scenario_profile)
        primary_setup_label = infer_primary_setup_label(scenario_profile)
        metadata = {
            "source": "decision_guidance_observation",
            "title": title,
            "category": "decision_guidance_observation",
            "tags": self._build_tags(symbol, recommendation, normalized_guidance),
            "symbol": symbol,
            "topic": "decision-guidance-usage",
            "recommendation": recommendation,
            "confidence": confidence,
            "applied_guidance": normalized_guidance,
            "applied_guidance_count": len(normalized_guidance),
            "applied_setup_labels": applied_setup_labels,
            "applied_setup_label_count": len(applied_setup_labels),
            "reference_case_titles": reference_titles,
            "market_regime": str(scenario_profile.get("market_regime", "")).strip().lower(),
            "analyst_alignment": str(scenario_profile.get("analyst_alignment", "")).strip().lower(),
            "signal_tags": self._normalize_string_list(scenario_profile.get("signal_tags")),
            "risk_tags": self._normalize_string_list(scenario_profile.get("risk_tags")),
            "timing_tags": self._normalize_string_list(scenario_profile.get("timing_tags")),
            "portfolio_state_tags": self._normalize_string_list(
                scenario_profile.get("portfolio_state_tags")
            ),
            "setup_labels": setup_labels,
            "primary_setup_label": primary_setup_label,
            "dataset": dataset,
        }
        return {"text": text, "metadata": metadata}

    def _ensure_repository_ready(self) -> None:
        """Create the repository layout and initialize the manifest if needed."""
        self.repository.ensure_structure()
        if self.repository.manifest_exists():
            return
        self.repository.save_manifest(
            {
                "version": "0.1.0",
                "description": "Placeholder manifest for the project knowledge base.",
                "datasets": {
                    "foundation": {"raw": [], "processed": []},
                    "dynamic": {"raw": [], "processed": []},
                },
                "indexes": [],
            }
        )

    def _build_record_name(
        self,
        decision_result: dict[str, Any],
        applied_guidance: list[str],
    ) -> str:
        """Build a deterministic record name for persisted guidance observations."""
        symbol = str(decision_result.get("symbol", "")).strip().lower()
        trade_date = str(decision_result.get("trade_date", "")).strip()
        date_part = trade_date.split("T", 1)[0].replace("-", "_")
        subject = str(decision_result.get("subject", "")).strip().lower()

        name_parts = ["decision_guidance_observation"]
        if symbol:
            name_parts.append(symbol)
        if date_part:
            name_parts.append(date_part)
        if subject:
            name_parts.append(subject)
        if applied_guidance:
            name_parts.append(applied_guidance[0])

        raw_name = "_".join(name_parts)
        normalized = re.sub(r"[^a-z0-9]+", "_", raw_name.lower()).strip("_")
        return normalized or "decision_guidance_observation"

    def _normalize_string_list(self, value: Any) -> list[str]:
        """Normalize optional model output into a non-empty string list."""
        if isinstance(value, list):
            normalized = [str(item).strip() for item in value if str(item).strip()]
            return normalized
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _extract_scenario_profile(self, decision_result: dict[str, Any]) -> dict[str, Any]:
        """Extract a scenario profile from the decision output when available."""
        decision_context = decision_result.get("decision_context")
        if isinstance(decision_context, dict):
            scenario_profile = decision_context.get("scenario_profile")
            if isinstance(scenario_profile, dict):
                return scenario_profile
        scenario_profile = decision_result.get("scenario_profile")
        if isinstance(scenario_profile, dict):
            return scenario_profile
        return {}

    def _render_list_section(self, title: str, values: list[str]) -> str:
        """Render a simple bullet-list section."""
        if not values:
            return ""
        return f"{title}:\n" + "\n".join(f"- {value}" for value in values)

    def _render_text_section(self, title: str, value: Any) -> str:
        """Render a single text section."""
        normalized = str(value or "").strip()
        if not normalized:
            return ""
        return f"{title}: {normalized}"

    def _build_tags(
        self,
        symbol: str,
        recommendation: str,
        applied_guidance: list[str],
    ) -> list[str]:
        """Build stable metadata tags for later observation analysis."""
        tags = ["decision_guidance_observation", recommendation]
        if symbol:
            tags.append(symbol.lower())
        if applied_guidance:
            tags.append("postmortem_guidance_applied")
        seen: set[str] = set()
        normalized_tags: list[str] = []
        for tag in tags:
            normalized = str(tag).strip().lower().replace(" ", "_")
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            normalized_tags.append(normalized)
        return normalized_tags
