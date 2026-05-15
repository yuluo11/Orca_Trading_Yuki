"""Unified retrieval entrypoint for knowledge-base access."""

from collections.abc import Sequence
from typing import Any, Protocol

from .documents import load_dataset_documents
from .repository import DatasetName, KnowledgeRepository


class VectorRetrieverBackend(Protocol):
    """Protocol for vector-backed retrieval implementations."""

    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> list[Any]:
        """Return documents similar to the provided query."""


class KnowledgeRetriever:
    """Provide a single retrieval interface over project knowledge sources."""

    def __init__(
        self,
        repository: KnowledgeRepository,
        backend: VectorRetrieverBackend | None = None,
    ) -> None:
        self.repository = repository
        self.backend = backend

    def load_documents(self, dataset: DatasetName) -> list[Any]:
        """Load all processed documents for a single dataset."""
        return load_dataset_documents(self.repository, dataset)

    def load_all_documents(self, datasets: Sequence[DatasetName] | None = None) -> list[Any]:
        """Load documents for one or more datasets."""
        selected_datasets = tuple(datasets or ("foundation", "dynamic"))
        documents: list[Any] = []
        for dataset in selected_datasets:
            documents.extend(self.load_documents(dataset))
        return documents

    def search(
        self,
        query: str,
        *,
        datasets: Sequence[DatasetName] | None = None,
        k: int = 4,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Search knowledge documents through the configured backend or local fallback."""
        if self.backend is not None:
            search_kwargs: dict[str, Any] = {}
            if metadata_filter:
                search_kwargs["filter"] = metadata_filter
            return self.backend.similarity_search(query, k=k, **search_kwargs)

        return self._fallback_search(
            query,
            datasets=datasets,
            k=k,
            metadata_filter=metadata_filter,
        )

    def _fallback_search(
        self,
        query: str,
        *,
        datasets: Sequence[DatasetName] | None,
        k: int,
        metadata_filter: dict[str, Any] | None,
    ) -> list[Any]:
        """Run a lightweight local search when no vector backend is configured."""
        query_terms = {term for term in query.lower().split() if term}
        scored_documents: list[tuple[int, Any]] = []

        for document in self.load_all_documents(datasets):
            if not self._matches_metadata_filter(document.metadata, metadata_filter):
                continue

            haystack = " ".join(
                str(value)
                for value in (
                    document.page_content,
                    document.metadata.get("title", ""),
                    " ".join(document.metadata.get("tags", [])),
                    document.metadata.get("symbol", ""),
                    document.metadata.get("topic", ""),
                    document.metadata.get("category", ""),
                )
            ).lower()

            score = sum(1 for term in query_terms if term in haystack)
            if score > 0:
                scored_documents.append((score, document))

        scored_documents.sort(key=lambda item: item[0], reverse=True)
        return [document for _, document in scored_documents[:k]]

    def _matches_metadata_filter(
        self,
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
