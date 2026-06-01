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
    foundation_schema_version: str
    foundation_category: str
    principle_type: str
    applies_to: list[str]
    valid_when: list[str]
    invalid_when: list[str]
    priority: str
    status: str
    rule_direction: str
    owner_defined: bool
    rule_id: str
    conflicts_with: list[str]
    reliability: KnowledgeReliability
    time_sensitivity: KnowledgeTimeSensitivity
    dataset: KnowledgeDataset


class ProcessedKnowledgeRecord(TypedDict):
    """Canonical structure for a processed knowledge record."""

    text: str
    metadata: KnowledgeMetadata
