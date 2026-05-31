"""Structured types for processed knowledge records."""

from typing import Literal, TypedDict

KnowledgeDataset = Literal["foundation", "dynamic"]
KnowledgeReliability = Literal["high", "medium", "low"]
KnowledgeTimeSensitivity = Literal["high", "medium", "low"]


class KnowledgeMetadata(TypedDict, total=False):
    """Metadata attached to a processed knowledge record."""

    source: str
    title: str
    created_at: str
    updated_at: str
    category: str
    tags: list[str]
    symbol: str
    topic: str
    source_url: str
    source_domain: str
    author: str
    published_at: str
    summary: str
    extraction_method: str
    content_hash: str
    content_length: int
    reliability: KnowledgeReliability
    time_sensitivity: KnowledgeTimeSensitivity
    dataset: KnowledgeDataset


class ProcessedKnowledgeRecord(TypedDict):
    """Canonical structure for a processed knowledge record."""

    text: str
    metadata: KnowledgeMetadata
