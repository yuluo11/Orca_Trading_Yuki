"""Index construction utilities for the project knowledge base."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from .documents import load_dataset_documents
from .repository import DatasetName, KnowledgeRepository

VectorBackendKind = Literal["auto", "local", "persisted_token", "langchain_inmemory"]


@dataclass(frozen=True, slots=True)
class VectorBackendConfig:
    """Configuration for choosing a knowledge retrieval backend."""

    kind: VectorBackendKind = "auto"
    index_name: str | None = None


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


def _build_term_counts(text: str) -> dict[str, int]:
    """Build raw term counts for BM25-style sparse retrieval."""
    counts: dict[str, int] = {}
    for term in _tokenize(text):
        counts[term] = counts.get(term, 0) + 1
    return counts


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
        return [document for document, _ in self.similarity_search_with_scores(query, k=k, **kwargs)]

    def similarity_search_with_scores(
        self,
        query: str,
        k: int = 4,
        **kwargs: Any,
    ) -> list[tuple[Any, float]]:
        """Run local search and keep scores for evaluation/debugging."""
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
        return [(document, float(score)) for score, document in scored_documents[:k]]


class PersistedTokenVectorIndex:
    """Persistent sparse token-vector backend compatible with the retriever interface."""

    def __init__(self, entries: Sequence[dict[str, Any]]) -> None:
        self.entries = list(entries)
        self.document_count = len(self.entries)
        self.average_document_length = self._average_document_length()
        self.document_frequencies = self._document_frequencies()

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs: Any,
    ) -> list[Any]:
        """Run cosine-style sparse-vector retrieval over persisted entries."""
        return [
            document
            for document, _ in self.similarity_search_with_scores(query, k=k, **kwargs)
        ]

    def similarity_search_with_scores(
        self,
        query: str,
        k: int = 4,
        **kwargs: Any,
    ) -> list[tuple[Any, float]]:
        """Run hybrid sparse-vector retrieval and return result scores."""
        metadata_filter = kwargs.get("filter")
        query_terms = _tokenize(query)
        query_weights = _build_term_weights(query)
        scored_entries: list[tuple[float, dict[str, Any]]] = []

        for entry in self.entries:
            metadata = entry.get("metadata", {})
            if not _matches_metadata_filter(metadata, metadata_filter):
                continue

            score = self._hybrid_score(entry, query_terms=query_terms, query_weights=query_weights)
            if score > 0:
                scored_entries.append((score, entry))

        scored_entries.sort(key=lambda item: item[0], reverse=True)
        return [
            (_entry_to_document(entry), score)
            for score, entry in scored_entries[:k]
        ]

    def _hybrid_score(
        self,
        entry: dict[str, Any],
        *,
        query_terms: list[str],
        query_weights: dict[str, float],
    ) -> float:
        """Combine cosine similarity, BM25-style term ranking, and metadata boosts."""
        cosine_score = _cosine_similarity(query_weights, entry.get("term_weights", {}))
        bm25_score = self._bm25_score(entry, query_terms)
        phrase_score = _phrase_boost(entry, query_terms)
        metadata_score = _metadata_boost(entry, query_terms)
        return cosine_score + bm25_score + phrase_score + metadata_score

    def _bm25_score(self, entry: dict[str, Any], query_terms: list[str]) -> float:
        term_counts = _entry_term_counts(entry)
        if not term_counts or not query_terms or self.document_count == 0:
            return 0.0

        document_length = int(entry.get("document_length") or sum(term_counts.values()) or 1)
        average_length = self.average_document_length or 1.0
        k1 = 1.5
        b = 0.75
        score = 0.0
        for term in set(query_terms):
            frequency = term_counts.get(term, 0)
            if frequency == 0:
                continue
            document_frequency = self.document_frequencies.get(term, 0)
            idf = math.log(1 + (self.document_count - document_frequency + 0.5) / (document_frequency + 0.5))
            denominator = frequency + k1 * (1 - b + b * document_length / average_length)
            score += idf * (frequency * (k1 + 1)) / denominator
        return score

    def _average_document_length(self) -> float:
        lengths = [
            int(entry.get("document_length") or sum(_entry_term_counts(entry).values()))
            for entry in self.entries
        ]
        lengths = [length for length in lengths if length > 0]
        if not lengths:
            return 0.0
        return sum(lengths) / len(lengths)

    def _document_frequencies(self) -> dict[str, int]:
        frequencies: dict[str, int] = {}
        for entry in self.entries:
            for term in _entry_term_counts(entry):
                frequencies[term] = frequencies.get(term, 0) + 1
        return frequencies


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

    def build_configured_backend(
        self,
        config: VectorBackendConfig | None = None,
        *,
        datasets: Sequence[DatasetName] | None = None,
        embeddings: Any | None = None,
    ) -> Any:
        """Build a retrieval backend from a small backend config."""
        resolved_config = config or VectorBackendConfig()
        if resolved_config.kind == "auto":
            return self.load_or_build_default_backend(datasets)
        if resolved_config.kind == "local":
            return self.build_local_index(datasets)
        if resolved_config.kind == "persisted_token":
            if resolved_config.index_name:
                try:
                    return self.load_persisted_token_vector_index(resolved_config.index_name)
                except FileNotFoundError:
                    pass
            return self.build_persisted_token_vector_index(datasets)
        if resolved_config.kind == "langchain_inmemory":
            if embeddings is None:
                raise ValueError("embeddings are required for langchain_inmemory backend")
            return self.build_inmemory_vector_store(embeddings, datasets)
        raise ValueError(f"Unsupported vector backend kind: {resolved_config.kind}")

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
    term_counts = _build_term_counts(haystack)
    return {
        "page_content": page_content,
        "metadata": metadata,
        "term_counts": term_counts,
        "document_length": sum(term_counts.values()),
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


def _entry_term_counts(entry: dict[str, Any]) -> dict[str, int]:
    counts = entry.get("term_counts")
    if isinstance(counts, dict):
        return {str(term): int(count) for term, count in counts.items()}
    weights = entry.get("term_weights", {})
    if isinstance(weights, dict):
        return {str(term): 1 for term in weights}
    return {}


def _phrase_boost(entry: dict[str, Any], query_terms: list[str]) -> float:
    if len(query_terms) < 2:
        return 0.0
    query_phrase = " ".join(query_terms)
    haystack = _entry_haystack(entry)
    if query_phrase and query_phrase in haystack:
        return 1.0
    adjacent_pairs = zip(query_terms, query_terms[1:])
    return sum(0.15 for left, right in adjacent_pairs if f"{left} {right}" in haystack)


def _metadata_boost(entry: dict[str, Any], query_terms: list[str]) -> float:
    if not query_terms:
        return 0.0
    metadata = dict(entry.get("metadata", {}))
    weighted_fields = (
        ("title", 0.4),
        ("symbol", 0.3),
        ("topic", 0.2),
        ("category", 0.1),
    )
    score = 0.0
    for field_name, weight in weighted_fields:
        value = str(metadata.get(field_name, "")).lower()
        if not value:
            continue
        score += sum(weight for term in set(query_terms) if term in value)
    return score


def _entry_haystack(entry: dict[str, Any]) -> str:
    metadata = dict(entry.get("metadata", {}))
    return " ".join(
        str(value)
        for value in (
            entry.get("page_content", ""),
            metadata.get("title", ""),
            metadata.get("symbol", ""),
            metadata.get("topic", ""),
            metadata.get("category", ""),
        )
    ).lower()
