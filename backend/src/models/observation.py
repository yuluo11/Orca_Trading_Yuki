"""Typed contracts for persisted decision-guidance observations and summaries."""

from __future__ import annotations

from typing import TypedDict


class CountedLabel(TypedDict, total=False):
    """A labeled count entry used in lightweight analytics summaries."""

    label: str
    count: int


class DecisionGuidanceObservationMetadata(TypedDict, total=False):
    """Metadata stored alongside persisted guidance-observation records."""

    source: str
    title: str
    category: str
    tags: list[str]
    symbol: str
    topic: str
    recommendation: str
    confidence: str
    applied_guidance: list[str]
    applied_guidance_count: int
    reference_case_titles: list[str]
    dataset: str


class DecisionGuidanceObservationRecord(TypedDict, total=False):
    """Canonical processed record describing one guidance-usage observation."""

    text: str
    metadata: DecisionGuidanceObservationMetadata


class GuidanceObservationPersistenceResult(TypedDict, total=False):
    """Persistence outcome returned after writing a guidance observation."""

    status: str
    persisted: bool
    reason: str
    path: str
    record_name: str
    title: str
    applied_guidance_count: int


class GuidanceObservationSummary(TypedDict, total=False):
    """Aggregated analytics over persisted guidance observations."""

    dataset: str
    total_observations: int
    top_guidance: list[CountedLabel]
    recommendation_breakdown: list[CountedLabel]
    symbol_breakdown: list[CountedLabel]
    top_reference_cases: list[CountedLabel]


class GuidancePriorsSummary(TypedDict, total=False):
    """Symbol-scoped recurring guidance priors reused by the decision layer."""

    datasets: list[str]
    symbol: str | None
    recommendation_filter: str | None
    total_observations: int
    top_guidance: list[CountedLabel]
    recommendation_breakdown: list[CountedLabel]
    top_reference_cases: list[CountedLabel]
    summary: str
