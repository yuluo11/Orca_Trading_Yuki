"""Manual collector used to seed dynamic knowledge without a live data source."""

from __future__ import annotations

from .base import CollectedKnowledgeItem


class ManualKnowledgeCollector:
    """Return caller-provided knowledge items in collector form."""

    def __init__(self, items: list[CollectedKnowledgeItem]) -> None:
        self.items = list(items)

    def collect(self) -> list[CollectedKnowledgeItem]:
        """Return the manually supplied knowledge items."""
        return list(self.items)
