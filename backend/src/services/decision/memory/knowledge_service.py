"""Decision-memory retrieval service for advisory synthesis."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from ....knowledge.indexing import KnowledgeIndexer
from ....knowledge.repository import DatasetName, KnowledgeRepository
from ....knowledge.retriever import KnowledgeRetriever, VectorRetrieverBackend
from ....models import (
    DecisionMemoryValidationSummary,
    GuidancePriorsSummary,
    KnowledgeEvidenceItem,
    RankedKnowledgeDocument,
)
from ..observation_analytics_service import DecisionGuidanceObservationAnalyticsService
from ..setup_taxonomy import infer_primary_setup_label, infer_setup_labels
from .schema import (
    normalize_decision_memory_metadata,
    summarize_decision_memory_validation,
    validate_decision_memory_record,
)

if TYPE_CHECKING:
    from ....agents.decision.base_agent import DecisionTask

from .ranking import DecisionRankingMixin


class DecisionKnowledgeService(DecisionRankingMixin):
    """Retrieve dynamic decision-memory records used by the advisory layer."""

    agent_name = "decision_advisory"
    default_datasets: tuple[DatasetName, ...] = ("dynamic",)
    default_k = 3

    def __init__(
        self,
        repository: KnowledgeRepository | None = None,
        retriever: KnowledgeRetriever | None = None,
        backend: VectorRetrieverBackend | None = None,
        observation_analytics: DecisionGuidanceObservationAnalyticsService | None = None,
    ) -> None:
        self.repository = repository or KnowledgeRepository()
        self.indexer = KnowledgeIndexer(self.repository)
        resolved_backend = backend or self.indexer.load_or_build_default_backend(self.default_datasets)
        self.retriever = retriever or KnowledgeRetriever(self.repository, backend=resolved_backend)
        self.observation_analytics = observation_analytics or DecisionGuidanceObservationAnalyticsService(
            self.repository
        )

    def default_metadata_filter(self) -> dict[str, Any]:
        """Restrict retrieval to decision-memory records by default."""
        return {"category": "decision_memory"}

    def build_query(self, task: "DecisionTask") -> str:
        """Build a retrieval query from the orchestrated analyst payload."""
        query_parts: list[str] = [task.subject.strip()]
        if task.symbol:
            query_parts.append(task.symbol.strip())
        if task.overall_summary:
            query_parts.append(task.overall_summary.strip())
        if task.key_signals:
            query_parts.append("signals " + " ".join(task.key_signals[:3]))
        if task.portfolio_risks:
            query_parts.append("risks " + " ".join(task.portfolio_risks[:3]))
        if task.cross_analyst_observations:
            query_parts.append("observations " + " ".join(task.cross_analyst_observations[:2]))
        if task.extra_context:
            query_parts.append(task.extra_context.strip())
        return " ".join(part for part in query_parts if part)

    def build_scenario_profile(self, task: "DecisionTask") -> dict[str, Any]:
        """Derive structured retrieval hints from the current analyst payload."""
        signal_texts = list(task.key_signals)
        risk_texts = list(task.portfolio_risks)
        for analyst_result in task.analyst_results:
            if not isinstance(analyst_result, dict):
                continue
            signal_texts.extend(str(item).strip() for item in analyst_result.get("signals", []))
            risk_texts.extend(str(item).strip() for item in analyst_result.get("risks", []))

        combined_text = " ".join(
            part
            for part in (
                task.subject,
                task.extra_context or "",
                task.overall_summary,
                " ".join(task.cross_analyst_observations),
            )
            if part
        )
        return {
            "symbol": task.symbol,
            "market_regime": self._infer_market_regime(combined_text),
            "analyst_alignment": self._infer_analyst_alignment(task),
            "signal_tags": self._extract_tags(
                signal_texts,
                tag_map={
                    "news_catalyst": ("guidance", "catalyst", "news", "headline"),
                    "sentiment_spike": ("sentiment", "hype", "attention", "buzz", "social"),
                    "momentum": ("momentum", "breakout", "trend", "acceleration"),
                    "ai_theme": ("ai", "artificial intelligence", "infrastructure"),
                    "price_extension": ("extended", "extension", "overbought", "high"),
                },
            ),
            "risk_tags": self._extract_tags(
                risk_texts,
                tag_map={
                    "crowded_trade": ("crowded", "overowned", "consensus", "crowded trade"),
                    "event_fade": ("event fade", "fade", "post catalyst", "post-catalyst"),
                    "valuation_risk": ("valuation", "expensive", "multiple", "rich"),
                    "execution_risk": ("execution", "delivery", "miss"),
                    "drawdown_risk": ("drawdown", "reversal", "pullback", "volatility"),
                },
            ),
            "timing_tags": self._extract_tags(
                [combined_text],
                tag_map={
                    "short_term": ("short-term", "near-term"),
                    "event_window": ("event", "earnings", "guidance", "catalyst"),
                    "near_local_high": ("high", "extended", "peak"),
                    "post_gap_up": ("gap", "gap-up"),
                },
            ),
            "portfolio_state_tags": self._infer_portfolio_state_tags(task),
        }

    def build_metadata_filter(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge default and caller-specific metadata filters."""
        merged_filter = dict(self.default_metadata_filter())
        if metadata_filter:
            merged_filter.update(metadata_filter)
        return merged_filter

    def retrieve_context(
        self,
        task: "DecisionTask",
        *,
        query: str,
        scenario_profile: dict[str, Any],
        guidance_priors: dict[str, Any] | None = None,
        datasets: tuple[DatasetName, ...] | None = None,
        metadata_filter: dict[str, Any] | None = None,
        k: int | None = None,
    ) -> dict[str, Any]:
        """Fetch and rank decision-memory documents for the current task."""
        selected_datasets = datasets or self.default_datasets
        merged_filter = self.build_metadata_filter(metadata_filter=metadata_filter)
        candidate_count = max((k or self.default_k) * 4, 8)

        search_candidates = self.retriever.search(
            query,
            datasets=selected_datasets,
            k=candidate_count,
            metadata_filter=merged_filter or None,
        )
        fallback_candidates = [
            document
            for document in self.retriever.load_all_documents(selected_datasets)
            if self._matches_metadata_filter(getattr(document, "metadata", {}), merged_filter)
        ]
        candidates = self._dedupe_documents([*search_candidates, *fallback_candidates])
        validations: list[dict[str, Any]] = []
        validated_candidates: list[tuple[Any, dict[str, Any]]] = []
        for candidate in candidates:
            validation = self._validate_candidate(
                candidate,
                allowed_datasets=selected_datasets,
            )
            validations.append(validation)
            if not validation["is_valid"]:
                continue
            validated_candidates.append((candidate, validation))

        ranked_documents = [
            self._build_ranked_document(
                document,
                query=query,
                scenario_profile=scenario_profile,
                guidance_priors=guidance_priors or {},
                task=task,
                validation=validation,
            )
            for document, validation in validated_candidates
        ]
        ranked_documents.sort(
            key=lambda item: (
                item["score"],
                item["fit_rank"],
                item["metadata_quality"],
            ),
            reverse=True,
        )
        return {
            "ranked_documents": ranked_documents[: k or self.default_k],
            "validation_summary": summarize_decision_memory_validation(validations),
        }

    def analyze(
        self,
        task: "DecisionTask",
        *,
        datasets: tuple[DatasetName, ...] | None = None,
        metadata_filter: dict[str, Any] | None = None,
        k: int | None = None,
    ) -> dict[str, Any]:
        """Return a structured decision-memory payload for the advisory agent."""
        selected_datasets = datasets or self.default_datasets
        query = self.build_query(task)
        scenario_profile = self.build_scenario_profile(task)
        records_by_dataset = self._load_records_by_dataset(selected_datasets)
        guidance_priors = self.collect_guidance_priors(
            task,
            datasets=selected_datasets,
            records_by_dataset=records_by_dataset,
        )
        setup_outcome_priors = self.collect_setup_outcome_priors(
            task,
            datasets=selected_datasets,
            records_by_dataset=records_by_dataset,
        )
        setup_recommendation_outcome_priors = self.collect_setup_recommendation_outcome_priors(
            task,
            datasets=selected_datasets,
            records_by_dataset=records_by_dataset,
        )
        retrieval_context = self.retrieve_context(
            task,
            query=query,
            scenario_profile=scenario_profile,
            guidance_priors=guidance_priors,
            datasets=selected_datasets,
            metadata_filter=metadata_filter,
            k=k,
        )
        return self.build_context(
            task,
            query=query,
            scenario_profile=scenario_profile,
            datasets=selected_datasets,
            ranked_documents=retrieval_context["ranked_documents"],
            validation_summary=retrieval_context["validation_summary"],
            guidance_priors=guidance_priors,
            setup_outcome_priors=setup_outcome_priors,
            setup_recommendation_outcome_priors=setup_recommendation_outcome_priors,
        )

    def build_context(
        self,
        task: "DecisionTask",
        *,
        query: str,
        scenario_profile: dict[str, Any],
        datasets: tuple[DatasetName, ...],
        ranked_documents: list[dict[str, Any]],
        validation_summary: DecisionMemoryValidationSummary,
        guidance_priors: GuidancePriorsSummary,
        setup_outcome_priors: dict[str, Any],
        setup_recommendation_outcome_priors: dict[str, Any],
    ) -> dict[str, Any]:
        """Build an agent-friendly context payload from retrieved decision records."""
        serialized_documents = [self.serialize_document(item) for item in ranked_documents]
        return {
            "agent": self.agent_name,
            "subject": task.subject,
            "symbol": task.symbol,
            "trade_date": task.trade_date,
            "query": query,
            "scenario_profile": scenario_profile,
            "datasets": list(datasets),
            "document_count": len(serialized_documents),
            "validation_summary": validation_summary,
            "documents": serialized_documents,
            "evidence": self.collect_evidence(serialized_documents),
            "postmortem_lessons": self.collect_postmortem_lessons(serialized_documents),
            "guidance_priors": guidance_priors,
            "setup_outcome_priors": setup_outcome_priors,
            "setup_recommendation_outcome_priors": setup_recommendation_outcome_priors,
        }

    def serialize_document(self, ranked_document: dict[str, Any]) -> RankedKnowledgeDocument:
        """Convert a ranked document into a decision-service friendly payload."""
        document = ranked_document["document"]
        metadata = normalize_decision_memory_metadata(getattr(document, "metadata", {}))
        metadata["retrieval_score"] = ranked_document["score"]
        metadata["fit"] = ranked_document["fit"]
        metadata["match_reasons"] = ranked_document["match_reasons"]
        metadata["validation_warnings"] = ranked_document["validation"].get("warnings", [])
        return {
            "title": metadata.get("title", ""),
            "text": getattr(document, "page_content", ""),
            "metadata": metadata,
            "fit": ranked_document["fit"],
            "match_reasons": ranked_document["match_reasons"],
        }

    def collect_evidence(
        self,
        documents: list[RankedKnowledgeDocument],
    ) -> list[KnowledgeEvidenceItem]:
        """Normalize serialized documents into compact evidence entries."""
        evidence: list[KnowledgeEvidenceItem] = []
        for document in documents:
            metadata = dict(document.get("metadata", {}))
            evidence.append(
                {
                    "source_type": metadata.get("source_type", "internal"),
                    "title": document.get("title", ""),
                    "content": self.build_excerpt(document.get("text", "")),
                    "metadata": metadata,
                    "fit": document.get("fit", metadata.get("fit", "low")),
                }
            )
        return evidence

    def collect_postmortem_lessons(self, documents: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Extract reusable lesson snippets from retrieved postmortem memories."""
        lessons: list[dict[str, str]] = []
        for document in documents:
            metadata = dict(document.get("metadata", {}))
            memory_type = str(metadata.get("memory_type", "")).strip().lower()
            if memory_type != "decision_postmortem":
                continue
            for lesson in self._extract_postmortem_sections(document):
                lessons.append(
                    {
                        "title": str(document.get("title", "")).strip() or "Untitled postmortem",
                        "fit": str(document.get("fit", metadata.get("fit", "medium"))).strip().lower()
                        or "medium",
                        "lesson": lesson,
                    }
                )
        return lessons[:4]

    def collect_guidance_priors(
        self,
        task: "DecisionTask",
        *,
        datasets: tuple[DatasetName, ...],
        records_by_dataset: dict[DatasetName, list[dict[str, Any]]] | None = None,
    ) -> GuidancePriorsSummary:
        """Summarize recurring guidance usage for the current symbol or setup."""
        scenario_profile = self.build_scenario_profile(task)
        default_empty = {
            "datasets": list(datasets),
            "symbol": None,
            "market_regime": str(scenario_profile.get("market_regime", "")).strip().lower() or None,
            "setup_labels": infer_setup_labels(scenario_profile),
            "primary_setup_label": infer_primary_setup_label(scenario_profile) or None,
            "total_observations": 0,
            "top_guidance": [],
            "recommendation_breakdown": [],
            "top_reference_cases": [],
            "summary": "",
            "scope": "none",
        }

        symbol_priors = self.observation_analytics.summarize_guidance_priors(
            datasets=datasets,
            symbol=task.symbol,
            scenario_profile=scenario_profile,
            top_n=3,
            records_by_dataset=records_by_dataset,
        )
        if task.symbol and int(symbol_priors.get("total_observations", 0) or 0) == 0:
            symbol_priors = self.observation_analytics.summarize_guidance_priors(
                datasets=datasets,
                symbol=task.symbol,
                top_n=3,
                records_by_dataset=records_by_dataset,
            )
        if int(symbol_priors.get("total_observations", 0) or 0) >= 2:
            symbol_priors["scope"] = "symbol_setup"
            return symbol_priors

        setup_priors = self.observation_analytics.summarize_guidance_priors(
            datasets=datasets,
            scenario_profile=scenario_profile,
            top_n=3,
            records_by_dataset=records_by_dataset,
        )
        if int(setup_priors.get("total_observations", 0) or 0) > int(
            symbol_priors.get("total_observations", 0) or 0
        ):
            setup_priors["scope"] = "setup"
            return setup_priors

        if int(symbol_priors.get("total_observations", 0) or 0) > 0:
            symbol_priors["scope"] = "symbol_setup"
            return symbol_priors

        return default_empty

    def collect_setup_outcome_priors(
        self,
        task: "DecisionTask",
        *,
        datasets: tuple[DatasetName, ...],
        records_by_dataset: dict[DatasetName, list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        """Summarize setup-level historical outcomes for bounded reuse in decisions."""
        scenario_profile = self.build_scenario_profile(task)
        default_empty = {
            "datasets": list(datasets),
            "symbol": None,
            "market_regime": str(scenario_profile.get("market_regime", "")).strip().lower() or None,
            "setup_labels": infer_setup_labels(scenario_profile),
            "primary_setup_label": infer_primary_setup_label(scenario_profile) or None,
            "total_records": 0,
            "reviewed_observations": 0,
            "outcome_breakdown": [],
            "recommendation_breakdown": [],
            "top_setup_labels": [],
            "dominant_outcome": None,
            "outcome_bias": "mixed",
            "summary": "",
            "scope": "none",
        }

        symbol_priors = self.observation_analytics.summarize_setup_outcome_priors(
            datasets=datasets,
            symbol=task.symbol,
            scenario_profile=scenario_profile,
            top_n=3,
            records_by_dataset=records_by_dataset,
        )
        if task.symbol and int(symbol_priors.get("reviewed_observations", 0) or 0) == 0:
            symbol_priors = self.observation_analytics.summarize_setup_outcome_priors(
                datasets=datasets,
                symbol=task.symbol,
                top_n=3,
                records_by_dataset=records_by_dataset,
            )
        if int(symbol_priors.get("reviewed_observations", 0) or 0) >= 2:
            symbol_priors["scope"] = "symbol_setup"
            return symbol_priors

        setup_priors = self.observation_analytics.summarize_setup_outcome_priors(
            datasets=datasets,
            scenario_profile=scenario_profile,
            top_n=3,
            records_by_dataset=records_by_dataset,
        )
        if int(setup_priors.get("reviewed_observations", 0) or 0) > int(
            symbol_priors.get("reviewed_observations", 0) or 0
        ):
            setup_priors["scope"] = "setup"
            return setup_priors

        if int(symbol_priors.get("reviewed_observations", 0) or 0) > 0:
            symbol_priors["scope"] = "symbol_setup"
            return symbol_priors

        return default_empty

    def collect_setup_recommendation_outcome_priors(
        self,
        task: "DecisionTask",
        *,
        datasets: tuple[DatasetName, ...],
        records_by_dataset: dict[DatasetName, list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        """Summarize recommendation-to-outcome patterns for the current setup."""
        scenario_profile = self.build_scenario_profile(task)
        default_empty = {
            "datasets": list(datasets),
            "symbol": None,
            "market_regime": str(scenario_profile.get("market_regime", "")).strip().lower() or None,
            "setup_labels": infer_setup_labels(scenario_profile),
            "primary_setup_label": infer_primary_setup_label(scenario_profile) or None,
            "total_records": 0,
            "recommendation_outcomes": [],
            "summary": "",
            "scope": "none",
        }

        symbol_priors = self.observation_analytics.summarize_setup_recommendation_outcomes(
            datasets=datasets,
            symbol=task.symbol,
            scenario_profile=scenario_profile,
            top_n=5,
            records_by_dataset=records_by_dataset,
        )
        if task.symbol and int(symbol_priors.get("total_records", 0) or 0) == 0:
            symbol_priors = self.observation_analytics.summarize_setup_recommendation_outcomes(
                datasets=datasets,
                symbol=task.symbol,
                top_n=5,
                records_by_dataset=records_by_dataset,
            )
        if int(symbol_priors.get("total_records", 0) or 0) >= 2:
            symbol_priors["scope"] = "symbol_setup"
            return symbol_priors

        setup_priors = self.observation_analytics.summarize_setup_recommendation_outcomes(
            datasets=datasets,
            scenario_profile=scenario_profile,
            top_n=5,
            records_by_dataset=records_by_dataset,
        )
        if int(setup_priors.get("total_records", 0) or 0) > int(
            symbol_priors.get("total_records", 0) or 0
        ):
            setup_priors["scope"] = "setup"
            return setup_priors

        if int(symbol_priors.get("total_records", 0) or 0) > 0:
            symbol_priors["scope"] = "symbol_setup"
            return symbol_priors

        return default_empty

    def _load_records_by_dataset(
        self,
        datasets: tuple[DatasetName, ...],
    ) -> dict[DatasetName, list[dict[str, Any]]]:
        """Load processed records once per dataset for prior analytics reuse."""
        return {
            dataset: self.repository.load_all_processed_records(dataset)
            for dataset in datasets
        }

    def build_excerpt(self, text: str, *, limit: int = 280) -> str:
        """Return a compact evidence excerpt suitable for prompts."""
        compact_text = " ".join(text.split())
        if len(compact_text) <= limit:
            return compact_text
        return compact_text[: limit - 3].rstrip() + "..."

    def _extract_tags(
        self,
        texts: list[str],
        *,
        tag_map: dict[str, tuple[str, ...]],
    ) -> list[str]:
        """Infer normalized tags from free-form analyst text."""
        combined = " ".join(text.lower() for text in texts if text)
        return [
            tag
            for tag, keywords in tag_map.items()
            if any(keyword in combined for keyword in keywords)
        ]

    def _infer_market_regime(self, text: str) -> str:
        """Infer a coarse market-regime tag from the current task text."""
        lowered = text.lower()
        if any(
            keyword in lowered
            for keyword in ("earnings", "guidance", "catalyst", "event-driven", "event")
        ):
            return "event_driven"
        if any(keyword in lowered for keyword in ("risk-off", "defensive", "drawdown", "de-risk")):
            return "risk_off"
        if any(keyword in lowered for keyword in ("range", "sideways", "mean reversion")):
            return "range_bound"
        if any(keyword in lowered for keyword in ("momentum", "trend", "breakout")):
            return "trend_following"
        return "mixed"

    def _infer_analyst_alignment(self, task: "DecisionTask") -> str:
        """Infer the degree of cross-analyst agreement."""
        conflict_markers = ("disagree", "conflict", "mixed", "diverge", "uncertain")
        observations = " ".join(task.cross_analyst_observations).lower()
        if any(marker in observations for marker in conflict_markers):
            return "conflicted"
        if str(task.overall_confidence).strip().lower() == "high":
            return "aligned"
        return "mixed"

    def _infer_portfolio_state_tags(self, task: "DecisionTask") -> list[str]:
        """Infer coarse portfolio-state tags from current holdings and limits."""
        portfolio_context = task.portfolio_context or {}
        tags: list[str] = []
        positions = portfolio_context.get("positions", [])
        if isinstance(positions, list) and positions:
            tags.append("has_positions")

        current_position = self._find_symbol_position(portfolio_context, task.symbol)
        current_weight = self._extract_position_weight(current_position)
        max_weight = self._extract_max_single_name_pct(portfolio_context)
        cash_pct = self._extract_percent(portfolio_context.get("cash_pct"))

        if current_position is not None:
            tags.append("existing_position")
        else:
            tags.append("no_position")

        if current_weight is not None and max_weight is not None:
            if current_weight > max_weight:
                tags.append("above_single_name_limit")
            elif current_weight >= max_weight * 0.9:
                tags.append("near_single_name_limit")

        if cash_pct is not None:
            if cash_pct >= 10:
                tags.append("ample_cash")
            elif cash_pct < 5:
                tags.append("limited_cash")

        return tags

    def _dedupe_documents(self, documents: Iterable[Any]) -> list[Any]:
        """Remove duplicate candidate documents while preserving first-seen order."""
        deduped: list[Any] = []
        seen_keys: set[tuple[str, str]] = set()
        for document in documents:
            metadata = dict(getattr(document, "metadata", {}))
            key = (
                str(metadata.get("title", "")).strip(),
                str(metadata.get("created_at", "")).strip(),
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(document)
        return deduped
