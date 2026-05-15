"""Index construction utilities for the project knowledge base."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .documents import load_dataset_documents
from .repository import DatasetName, KnowledgeRepository


class LocalVectorIndex:
    """Lightweight in-memory backend compatible with the retriever interface."""

    def __init__(self, documents: Sequence[Any]) -> None:
        self.documents = list(documents)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs: Any,
    ) -> list[Any]:
        """Run a simple term-overlap search over indexed documents."""
        metadata_filter = kwargs.get("filter")
        query_terms = {term for term in query.lower().split() if term}
        scored_documents: list[tuple[int, Any]] = []

        for document in self.documents:
            metadata = getattr(document, "metadata", {})
            if not _matches_metadata_filter(metadata, metadata_filter):
                continue

            haystack = " ".join(
                str(value)
                for value in (
                    getattr(document, "page_content", ""),
                    metadata.get("title", ""),
                    " ".join(metadata.get("tags", [])),
                    metadata.get("symbol", ""),
                    metadata.get("topic", ""),
                    metadata.get("category", ""),
                )
            ).lower()

            score = sum(1 for term in query_terms if term in haystack)
            if score > 0:
                scored_documents.append((score, document))

        scored_documents.sort(key=lambda item: item[0], reverse=True)
        return [document for _, document in scored_documents[:k]]


class KnowledgeIndexer:
    """Build index backends from processed knowledge records."""

    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository

    def load_documents(self, datasets: Sequence[DatasetName] | None = None) -> list[Any]:
        """Load processed knowledge records as document objects."""
        selected_datasets = tuple(datasets or ("foundation", "dynamic"))
        documents: list[Any] = []
        for dataset in selected_datasets:
            documents.extend(load_dataset_documents(self.repository, dataset))
        return documents

    def build_local_index(self, datasets: Sequence[DatasetName] | None = None) -> LocalVectorIndex:
        """Build a lightweight local index for immediate use or testing."""
        return LocalVectorIndex(self.load_documents(datasets))

    def build_inmemory_vector_store(
        self,
        embeddings: Any,
        datasets: Sequence[DatasetName] | None = None,
    ) -> Any:
        """Build a LangChain in-memory vector store when dependencies are installed."""
        try:
            from langchain_core.vectorstores import InMemoryVectorStore
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "langchain_core is required to build an in-memory vector store backend"
            ) from error

        vector_store = InMemoryVectorStore(embedding=embeddings)
        vector_store.add_documents(self.load_documents(datasets))
        return vector_store

    def save_index_snapshot(
        self,
        name: str,
        *,
        datasets: Sequence[DatasetName] | None = None,
        document_count: int | None = None,
    ) -> Path:
        """Persist a small snapshot describing an index build."""
        selected_datasets = tuple(datasets or ("foundation", "dynamic"))
        snapshot_path = self.repository.indexes / f"{name}.json"
        snapshot = {
            "name": name,
            "datasets": list(selected_datasets),
            "document_count": document_count
            if document_count is not None
            else len(self.load_documents(selected_datasets)),
        }
        self.repository.indexes.mkdir(parents=True, exist_ok=True)
        with snapshot_path.open("w", encoding="utf-8") as file:
            json.dump(snapshot, file, ensure_ascii=False, indent=2)
        return snapshot_path


def _matches_metadata_filter(
    metadata: dict[str, Any],
    metadata_filter: dict[str, Any] | None,
) -> bool:
    """Apply exact-match filtering over document metadata."""
    if not metadata_filter:
        return True

    for key, expected_value in metadata_filter.items():
        actual_value = metadata.get(key)
        if actual_value != expected_value:
            return False
    return True
