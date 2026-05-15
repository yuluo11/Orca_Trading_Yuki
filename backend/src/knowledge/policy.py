"""Default policies for knowledge cleaning, metadata, deduplication, and indexing.

This module separates:
1. Engineering defaults that can be decided now.
2. Business-facing placeholders that should be defined by the project owner later.
"""

from dataclasses import dataclass, field
from typing import Literal

from .record import KnowledgeReliability, KnowledgeTimeSensitivity
from .repository import DatasetName

DeduplicationMode = Literal["overwrite_same_name", "skip_same_text", "flag_similar_text"]
IndexRebuildMode = Literal["manual", "batch", "automatic"]


@dataclass(slots=True)
class CleaningPolicy:
    """Engineering defaults for text normalization."""

    trim_whitespace: bool = True
    collapse_extra_blank_lines: bool = True
    collapse_repeated_spaces: bool = True
    drop_empty_paragraphs: bool = True
    strip_obvious_boilerplate: bool = True
    keep_title_in_metadata: bool = True
    keep_source_in_metadata: bool = True
    keep_timestamps_in_metadata: bool = True
    chunk_during_ingest: bool = False


@dataclass(slots=True)
class MetadataPolicy:
    """Defaults for required and optional metadata behavior."""

    required_fields: tuple[str, ...] = ("dataset", "created_at", "updated_at")
    recommended_fields: tuple[str, ...] = ("source", "title", "category")
    optional_fields: tuple[str, ...] = (
        "tags",
        "symbol",
        "topic",
        "reliability",
        "time_sensitivity",
    )
    default_reliability: KnowledgeReliability = "medium"
    foundation_default_time_sensitivity: KnowledgeTimeSensitivity = "low"
    dynamic_default_time_sensitivity: KnowledgeTimeSensitivity = "high"
    infer_from_filename: bool = True
    infer_from_directory: bool = True

    def default_time_sensitivity(self, dataset: DatasetName) -> KnowledgeTimeSensitivity:
        """Return the default time sensitivity for a dataset."""
        if dataset == "foundation":
            return self.foundation_default_time_sensitivity
        return self.dynamic_default_time_sensitivity


@dataclass(slots=True)
class DeduplicationPolicy:
    """Defaults for identifying and handling duplicate records."""

    modes: tuple[DeduplicationMode, ...] = (
        "overwrite_same_name",
        "skip_same_text",
        "flag_similar_text",
    )
    exact_text_match_enabled: bool = True
    similar_text_detection_enabled: bool = False
    similar_text_threshold: float = 0.9


@dataclass(slots=True)
class IndexingPolicy:
    """Defaults for rebuilding and tracking indexes."""

    rebuild_mode: IndexRebuildMode = "manual"
    snapshot_enabled: bool = True
    rebuild_after_processed_updates: bool = False
    rebuild_after_metadata_changes: bool = True
    rebuild_after_embedding_changes: bool = True


@dataclass(slots=True)
class UserDefinedKnowledgePolicy:
    """Business-facing placeholders that should be customized by the user."""

    # Define the long-term categories you want to keep stable.
    preferred_categories: tuple[str, ...] = ()
    # Define your own reliability rubric, for example what counts as high confidence.
    reliability_rubric: dict[str, str] = field(default_factory=dict)
    # Define which content types should never enter the knowledge base.
    excluded_content_rules: tuple[str, ...] = ()
    # Define preferred source priorities, for example official filings over social media.
    source_priority: tuple[str, ...] = ()
    # Define symbol/topic naming conventions used across your project.
    symbol_conventions: tuple[str, ...] = ()
    topic_conventions: tuple[str, ...] = ()


@dataclass(slots=True)
class KnowledgePolicy:
    """Top-level policy container for the knowledge subsystem."""

    cleaning: CleaningPolicy = field(default_factory=CleaningPolicy)
    metadata: MetadataPolicy = field(default_factory=MetadataPolicy)
    deduplication: DeduplicationPolicy = field(default_factory=DeduplicationPolicy)
    indexing: IndexingPolicy = field(default_factory=IndexingPolicy)
    user_defined: UserDefinedKnowledgePolicy = field(
        default_factory=UserDefinedKnowledgePolicy
    )


DEFAULT_KNOWLEDGE_POLICY = KnowledgePolicy()
