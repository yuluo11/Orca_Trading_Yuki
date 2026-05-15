"""Utilities for converting knowledge records into LangChain documents."""

from dataclasses import dataclass
from typing import Any

from .record import ProcessedKnowledgeRecord
from .repository import DatasetName, KnowledgeRepository


@dataclass(slots=True)
class LocalDocument:
    """Fallback document type used when LangChain is not installed."""

    page_content: str
    metadata: dict[str, Any]


def record_to_document(record: ProcessedKnowledgeRecord) -> Any:
    """Convert a processed knowledge record into a LangChain Document."""
    metadata = dict(record["metadata"])
    try:
        from langchain_core.documents import Document
    except ModuleNotFoundError:
        return LocalDocument(page_content=record["text"], metadata=metadata)

    return Document(page_content=record["text"], metadata=metadata)


def load_dataset_documents(
    repository: KnowledgeRepository,
    dataset: DatasetName,
) -> list[Any]:
    """Load all processed records from a dataset as LangChain documents."""
    records = repository.load_all_processed_records(dataset)
    return [record_to_document(record) for record in records]
