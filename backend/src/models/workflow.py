"""Typed top-level workflow payload contracts exposed by app entrypoints."""

from __future__ import annotations

from typing import Any, TypedDict

from .analyst import AnalystOrchestrationResult
from .decision import DecisionOutput
from .observation import (
    GuidanceObservationPersistenceResult,
    GuidanceObservationSummary,
    GuidancePriorsSummary,
)
from .reflection import ReflectionOutput, ReflectionPersistenceResult


class ReflectionPersistenceRunResult(TypedDict, total=False):
    """Combined result returned after reflection plus optional persistence."""

    reflection: ReflectionOutput
    persistence: ReflectionPersistenceResult


class DecisionRealizationResult(TypedDict, total=False):
    """Top-level result returned after analyst orchestration and decision synthesis."""

    subject: str
    symbol: str | None
    trade_date: str | None
    portfolio_context: dict[str, Any] | None
    analyst: AnalystOrchestrationResult
    decision: DecisionOutput


__all__ = [
    "DecisionRealizationResult",
    "GuidanceObservationPersistenceResult",
    "GuidanceObservationSummary",
    "GuidancePriorsSummary",
    "ReflectionPersistenceRunResult",
]
