"""Decision-memory retrieval service for advisory synthesis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ....knowledge.indexing import KnowledgeIndexer
from ....knowledge.repository import DatasetName, KnowledgeRepository
from ....knowledge.retriever import KnowledgeRetriever, VectorRetrieverBackend

if TYPE_CHECKING:
    from ..models.task import DecisionTask


class DecisionKnowledgeService:
    """Retrieve dynamic decision-memory records used by the advisory layer."""

    agent_name = "decision_advisory"
    default_datasets: tuple[DatasetName, ...] = ("dynamic",)
    default_k = 3

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
        """Restrict retrieval to decision-memory records by default."""
        return {"category": "decision_memory"}

    def build_query(self, task: "DecisionTask") -> str:
        """Build a retrieval query from the orchestrated analyst payload."""
        query_parts: list[str] = [task.subject.strip()]
        if task.symbol:
            query_parts.append(task.symbol.strip())
        if task.overall_summary:
            query_parts.append(task.overall_summary.strip())
        if task.key_signals:
            query_parts.append("signals " + " ".join(task.key_signals[:3]))
        if task.portfolio_risks:
            query_parts.append("risks " + " ".join(task.portfolio_risks[:3]))
        if task.cross_analyst_observations:
            query_parts.append("observations " + " ".join(task.cross_analyst_observations[:2]))
        if task.extra_context:
            query_parts.append(task.extra_context.strip())
        return " ".join(part for part in query_parts if part)

    def build_metadata_filter(
        self,
        *,
        metadata_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Merge default and caller-specific metadata filters."""
        merged_filter = dict(self.default_metadata_filter())
        if metadata_filter:
            merged_filter.update(metadata_filter)
        return merged_filter

    def retrieve_context(
        self,
        query: str,
        *,
        datasets: tuple[DatasetName, ...] | None = None,
        metadata_filter: dict[str, Any] | None = None,
        k: int | None = None,
    ) -> list[Any]:
        """Fetch decision-memory documents relevant to the current task."""
        selected_datasets = datasets or self.default_datasets
        merged_filter = self.build_metadata_filter(metadata_filter=metadata_filter)
        return self.retriever.search(
            query,
            datasets=selected_datasets,
            k=k or self.default_k,
            metadata_filter=merged_filter or None,
        )

    def analyze(
        self,
        task: "DecisionTask",
        *,
        datasets: tuple[DatasetName, ...] | None = None,
        metadata_filter: dict[str, Any] | None = None,
        k: int | None = None,
    ) -> dict[str, Any]:
        """Return a structured decision-memory payload for the advisory agent."""
        selected_datasets = datasets or self.default_datasets
        query = self.build_query(task)
        documents = self.retrieve_context(
            query,
            datasets=selected_datasets,
            metadata_filter=metadata_filter,
            k=k,
        )
        return self.build_context(task, query=query, datasets=selected_datasets, documents=documents)

    def build_context(
        self,
        task: "DecisionTask",
        *,
        query: str,
        datasets: tuple[DatasetName, ...],
        documents: list[Any],
    ) -> dict[str, Any]:
        """Build an agent-friendly context payload from retrieved decision records."""
        serialized_documents = [self.serialize_document(document) for document in documents]
        return {
            "agent": self.agent_name,
            "subject": task.subject,
            "symbol": task.symbol,
            "trade_date": task.trade_date,
            "query": query,
            "datasets": list(datasets),
            "document_count": len(serialized_documents),
            "documents": serialized_documents,
            "evidence": self.collect_evidence(serialized_documents),
        }

    def serialize_document(self, document: Any) -> dict[str, Any]:
        """Convert a retrieved document into a decision-service friendly payload."""
        metadata = dict(getattr(document, "metadata", {}))
        return {
            "title": metadata.get("title", ""),
            "text": getattr(document, "page_content", ""),
            "metadata": metadata,
        }

    def collect_evidence(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize serialized documents into compact evidence entries."""
        evidence: list[dict[str, Any]] = []
        for document in documents:
            metadata = dict(document.get("metadata", {}))
            evidence.append(
                {
                    "source_type": metadata.get("source_type", "internal"),
                    "title": document.get("title", ""),
                    "content": self.build_excerpt(document.get("text", "")),
                    "metadata": metadata,
                }
            )
        return evidence

    def build_excerpt(self, text: str, *, limit: int = 280) -> str:
        """Return a compact evidence excerpt suitable for prompts."""
        compact_text = " ".join(text.split())
        if len(compact_text) <= limit:
            return compact_text
        return compact_text[: limit - 3].rstrip() + "..."
