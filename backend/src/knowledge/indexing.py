"""Index construction utilities for the project knowledge base."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .documents import load_dataset_documents
from .repository import DatasetName, KnowledgeRepository


def _tokenize(text: str) -> list[str]:
    """Tokenize text into simple lowercase word terms."""
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token]


def _build_term_weights(text: str) -> dict[str, float]:
    """Build normalized sparse term weights for a text payload."""
    terms = _tokenize(text)
    if not terms:
        return {}

    counts: dict[str, int] = {}
    for term in terms:
        counts[term] = counts.get(term, 0) + 1

    total = float(len(terms))
    return {
        term: count / total
        for term, count in counts.items()
    }


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    """Compute cosine similarity between sparse vectors."""
    if not left or not right:
        return 0.0

    dot = sum(value * right.get(term, 0.0) for term, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


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


class PersistedTokenVectorIndex:
    """Persistent sparse token-vector backend compatible with the retriever interface."""

    def __init__(self, entries: Sequence[dict[str, Any]]) -> None:
        self.entries = list(entries)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs: Any,
    ) -> list[Any]:
        """Run cosine-style sparse-vector retrieval over persisted entries."""
        metadata_filter = kwargs.get("filter")
        query_weights = _build_term_weights(query)
        scored_entries: list[tuple[float, dict[str, Any]]] = []

        for entry in self.entries:
            metadata = entry.get("metadata", {})
            if not _matches_metadata_filter(metadata, metadata_filter):
                continue

            score = _cosine_similarity(query_weights, entry.get("term_weights", {}))
            if score > 0:
                scored_entries.append((score, entry))

        scored_entries.sort(key=lambda item: item[0], reverse=True)
        return [_entry_to_document(entry) for _, entry in scored_entries[:k]]


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

    def load_or_build_default_backend(
        self,
        datasets: Sequence[DatasetName] | None = None,
    ) -> LocalVectorIndex | PersistedTokenVectorIndex:
        """Prefer dataset auto-index snapshots, filling gaps from live documents."""
        selected_datasets = tuple(datasets or ("foundation", "dynamic"))
        persisted_entries: list[dict[str, Any]] = []

        for dataset in selected_datasets:
            try:
                backend = self.load_persisted_token_vector_index(f"{dataset}_auto_index")
                persisted_entries.extend(backend.entries)
            except FileNotFoundError:
                persisted_entries.extend(
                    _document_to_index_entry(document)
                    for document in self.load_documents((dataset,))
                )

        return PersistedTokenVectorIndex(persisted_entries)

    def build_persisted_token_vector_index(
        self,
        datasets: Sequence[DatasetName] | None = None,
    ) -> PersistedTokenVectorIndex:
        """Build a persistent sparse token-vector index for local semantic retrieval."""
        documents = self.load_documents(datasets)
        entries = [_document_to_index_entry(document) for document in documents]
        return PersistedTokenVectorIndex(entries)

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

    def save_persisted_token_vector_index(
        self,
        name: str,
        *,
        datasets: Sequence[DatasetName] | None = None,
    ) -> Path:
        """Persist a sparse token-vector backend to disk."""
        selected_datasets = tuple(datasets or ("foundation", "dynamic"))
        index = self.build_persisted_token_vector_index(selected_datasets)
        snapshot_path = self.repository.indexes / f"{name}.json"
        snapshot = {
            "name": name,
            "backend": "persisted_token_vector",
            "datasets": list(selected_datasets),
            "document_count": len(index.entries),
            "documents": index.entries,
        }
        self.repository.indexes.mkdir(parents=True, exist_ok=True)
        with snapshot_path.open("w", encoding="utf-8") as file:
            json.dump(snapshot, file, ensure_ascii=False, indent=2)
        return snapshot_path

    def load_persisted_token_vector_index(self, name: str) -> PersistedTokenVectorIndex:
        """Load a sparse token-vector backend from disk."""
        snapshot_path = self.repository.indexes / f"{name}.json"
        with snapshot_path.open("r", encoding="utf-8") as file:
            snapshot = json.load(file)
        entries = snapshot.get("documents", [])
        if not isinstance(entries, list):
            raise ValueError(f"Persisted index {snapshot_path} must contain a document list")
        return PersistedTokenVectorIndex(entries)


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


def _document_to_index_entry(document: Any) -> dict[str, Any]:
    """Convert a document into a persisted sparse-vector entry."""
    metadata = dict(getattr(document, "metadata", {}))
    page_content = str(getattr(document, "page_content", ""))
    haystack = " ".join(
        str(value)
        for value in (
            page_content,
            metadata.get("title", ""),
            " ".join(metadata.get("tags", [])),
            metadata.get("symbol", ""),
            metadata.get("topic", ""),
            metadata.get("category", ""),
        )
    )
    return {
        "page_content": page_content,
        "metadata": metadata,
        "term_weights": _build_term_weights(haystack),
    }


def _entry_to_document(entry: dict[str, Any]) -> Any:
    """Convert a persisted sparse-vector entry back into a document object."""
    try:
        from langchain_core.documents import Document
    except ModuleNotFoundError:
        from .documents import LocalDocument

        return LocalDocument(
            page_content=str(entry.get("page_content", "")),
            metadata=dict(entry.get("metadata", {})),
        )

    return Document(
        page_content=str(entry.get("page_content", "")),
        metadata=dict(entry.get("metadata", {})),
    )
