"""Base analyst service that retrieves context from the knowledge layer."""

from __future__ import annotations

from typing import Any

from ...knowledge.indexing import KnowledgeIndexer
from ...knowledge.repository import DatasetName, KnowledgeRepository
from ...knowledge.retriever import KnowledgeRetriever, VectorRetrieverBackend


class KnowledgeBackedAnalystService:
    """Shared service base for analysts that depend on the knowledge layer."""

    analyst_name = "knowledge_backed_analyst"
    default_datasets: tuple[DatasetName, ...] = ("foundation", "dynamic")
    default_k = 4

    def __init__(
        self,
        repository: KnowledgeRepository | None = None,
        retriever: KnowledgeRetriever | None = None,
        backend: VectorRetrieverBackend | None = None,
    ) -> None:
        self.repository = repository or KnowledgeRepository()
        self.indexer = KnowledgeIndexer(self.repository)
        resolved_backend = backend or self.indexer.build_local_index(self.default_datasets)
        self.retriever = retriever or KnowledgeRetriever(self.repository, backend=resolved_backend)

    def default_metadata_filter(self) -> dict[str, Any]:
        """Return the analyst-specific metadata filter."""
        return {}

    def build_query(self, subject: str, extra_context: str | None = None) -> str:
        """Build a retrieval query from the current task input."""
        parts = [subject.strip()]
        if extra_context:
            parts.append(extra_context.strip())
        return " ".join(part for part in parts if part)

    def build_metadata_filter(
        self,
        *,
        symbol: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge default and call-specific metadata filters."""
        merged_filter = dict(self.default_metadata_filter())
        if symbol:
            merged_filter["symbol"] = symbol
        if metadata_filter:
            merged_filter.update(metadata_filter)
        return merged_filter

    def retrieve_context(
        self,
        query: str,
        *,
        datasets: tuple[DatasetName, ...] | None = None,
        symbol: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
        k: int | None = None,
    ) -> list[Any]:
        """Fetch knowledge documents relevant to the current analysis task."""
        selected_datasets = datasets or self.default_datasets
        merged_filter = self.build_metadata_filter(
            symbol=symbol,
            metadata_filter=metadata_filter,
        )
        return self.retriever.search(
            query,
            datasets=selected_datasets,
            k=k or self.default_k,
            metadata_filter=merged_filter or None,
        )

    def analyze(
        self,
        subject: str,
        *,
        extra_context: str | None = None,
        datasets: tuple[DatasetName, ...] | None = None,
        symbol: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
        k: int | None = None,
    ) -> dict[str, Any]:
        """Return a structured analysis payload with retrieved context."""
        selected_datasets = datasets or self.default_datasets
        query = self.build_query(subject, extra_context=extra_context)
        documents = self.retrieve_context(
            query,
            datasets=selected_datasets,
            symbol=symbol,
            metadata_filter=metadata_filter,
            k=k,
        )
        return {
            "analyst": self.analyst_name,
            "subject": subject,
            "query": query,
            "datasets": list(selected_datasets),
            "document_count": len(documents),
            "documents": [self.serialize_document(document) for document in documents],
        }

    def serialize_document(self, document: Any) -> dict[str, Any]:
        """Convert a retrieved document into a service-friendly payload."""
        metadata = dict(getattr(document, "metadata", {}))
        return {
            "title": metadata.get("title", ""),
            "text": getattr(document, "page_content", ""),
            "metadata": metadata,
        }


class GraphAnalystService(KnowledgeBackedAnalystService):
    """Retrieve cross-cutting context used for relationship and workflow analysis."""

    analyst_name = "graph_analyst"
    default_datasets = ("foundation", "dynamic")

    def build_query(self, subject: str, extra_context: str | None = None) -> str:
        base_query = super().build_query(subject, extra_context=extra_context)
        return f"{base_query} relationships dependencies workflow context".strip()
