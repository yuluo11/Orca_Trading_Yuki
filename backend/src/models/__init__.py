"""Shared typed models for backend payload contracts."""

from .analyst import AnalystOrchestrationResult, AnalystResult
from .decision import (
    DecisionContext,
    DecisionOutput,
    DecisionReferenceCase,
    MemoryPersistenceAssessment,
)
from .memory import (
    DecisionMemoryMetadata,
    DecisionMemoryRecord,
    DecisionMemoryValidationExample,
    DecisionMemoryValidationSummary,
)
from .knowledge import KnowledgeDocument, KnowledgeEvidenceItem, RankedKnowledgeDocument
from .observation import (
    CountedLabel,
    DecisionGuidanceObservationMetadata,
    DecisionGuidanceObservationRecord,
    GuidanceObservationPersistenceResult,
    GuidanceObservationSummary,
    GuidancePriorsSummary,
)
from .reflection import (
    CandidateMemorySeed,
    ExecutionSummary,
    ExitContext,
    OutcomeMetrics,
    PostTradeCompletenessResult,
    PostTradeValidationResult,
    RealizedOutcomeSummary,
    ReflectionAnalystSummary,
    ReflectionContext,
    ReflectionOutput,
    ReflectionPersistenceResult,
    ReflectionProfile,
    ReflectionReferenceCase,
)
from .workflow import DecisionRealizationResult, ReflectionPersistenceRunResult

__all__ = [
    "AnalystOrchestrationResult",
    "AnalystResult",
    "CountedLabel",
    "DecisionContext",
    "DecisionOutput",
    "DecisionGuidanceObservationMetadata",
    "DecisionGuidanceObservationRecord",
    "DecisionReferenceCase",
    "DecisionMemoryMetadata",
    "DecisionMemoryRecord",
    "DecisionMemoryValidationExample",
    "DecisionMemoryValidationSummary",
    "KnowledgeDocument",
    "KnowledgeEvidenceItem",
    "RankedKnowledgeDocument",
    "GuidanceObservationPersistenceResult",
    "GuidanceObservationSummary",
    "GuidancePriorsSummary",
    "MemoryPersistenceAssessment",
    "CandidateMemorySeed",
    "DecisionRealizationResult",
    "ExecutionSummary",
    "ExitContext",
    "OutcomeMetrics",
    "PostTradeCompletenessResult",
    "PostTradeValidationResult",
    "RealizedOutcomeSummary",
    "ReflectionAnalystSummary",
    "ReflectionContext",
    "ReflectionOutput",
    "ReflectionPersistenceRunResult",
    "ReflectionPersistenceResult",
    "ReflectionProfile",
    "ReflectionReferenceCase",
]
