"""Manual dynamic knowledge collector."""

from __future__ import annotations

from .base import CollectedKnowledgeItem
from ..record import KnowledgeMetadata


class ManualKnowledgeCollector:
    """Wrap caller-provided text as a collected knowledge item."""

    def __init__(
        self,
        items: list[CollectedKnowledgeItem] | None = None,
        *,
        name: str | None = None,
        text: str | None = None,
        metadata: KnowledgeMetadata | None = None,
    ) -> None:
        if items is not None:
            self.items = items
            return
        if name is None or text is None:
            raise ValueError("ManualKnowledgeCollector requires items or name/text.")
        self.items = [
            CollectedKnowledgeItem(
                name=name,
                text=text,
                metadata=dict(metadata or {}),
            )
        ]

    def collect(self) -> list[CollectedKnowledgeItem]:
        """Return the provided item in collector-normalized form."""
        return self.items
