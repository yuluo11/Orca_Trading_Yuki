"""Ingestion utilities for building processed knowledge records."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .record import KnowledgeMetadata, ProcessedKnowledgeRecord
from .repository import DatasetName, KnowledgeRepository


class KnowledgeIngestor:
    """Create processed knowledge records from raw text inputs."""

    def __init__(self, repository: KnowledgeRepository) -> None:
        self.repository = repository

    def ingest_text(
        self,
        dataset: DatasetName,
        name: str,
        text: str,
        metadata: KnowledgeMetadata | None = None,
    ) -> Path:
        """Persist a processed knowledge record and update the manifest."""
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Cannot ingest an empty knowledge record")

        record_name = self._normalize_record_name(name)
        record_path = self.repository.get_processed_record_path(dataset, record_name)
        record_path.parent.mkdir(parents=True, exist_ok=True)

        prepared_metadata = self._prepare_metadata(dataset, metadata)
        record: ProcessedKnowledgeRecord = {
            "text": cleaned_text,
            "metadata": prepared_metadata,
        }

        self.repository.save_manifest(
            self._update_manifest(
                dataset=dataset,
                stage="processed",
                entry={
                    "name": record_path.stem,
                    "path": str(record_path.relative_to(self.repository.data_root)),
                    "title": prepared_metadata.get("title", record_path.stem),
                    "category": prepared_metadata.get("category", ""),
                    "updated_at": prepared_metadata["updated_at"],
                },
            )
        )

        record_path.write_text(self._to_json(record), encoding="utf-8")
        return record_path

    def ingest_raw_text_file(
        self,
        dataset: DatasetName,
        raw_file: str | Path,
        *,
        metadata: KnowledgeMetadata | None = None,
        processed_name: str | None = None,
    ) -> Path:
        """Read a raw text file, create a processed record, and update the manifest."""
        raw_path = Path(raw_file)
        if not raw_path.exists():
            raise FileNotFoundError(f"Raw knowledge file not found: {raw_path}")

        text = raw_path.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"Raw knowledge file is empty: {raw_path}")

        manifest = self._update_manifest(
            dataset=dataset,
            stage="raw",
            entry={
                "name": raw_path.stem,
                "path": str(raw_path),
                "updated_at": self._now_iso(),
            },
        )
        self.repository.save_manifest(manifest)

        target_name = processed_name or raw_path.stem
        return self.ingest_text(dataset, target_name, text, metadata=metadata)

    def _prepare_metadata(
        self,
        dataset: DatasetName,
        metadata: KnowledgeMetadata | None,
    ) -> KnowledgeMetadata:
        """Fill default metadata fields for a processed knowledge record."""
        prepared: KnowledgeMetadata = dict(metadata or {})
        timestamp = self._now_iso()
        prepared["dataset"] = dataset
        prepared.setdefault("created_at", timestamp)
        prepared["updated_at"] = timestamp
        return prepared

    def _update_manifest(
        self,
        *,
        dataset: DatasetName,
        stage: str,
        entry: dict[str, Any],
    ) -> dict[str, Any]:
        """Insert or replace a manifest entry for a dataset stage."""
        manifest = self.repository.load_manifest()
        dataset_manifest = manifest.setdefault("datasets", {}).setdefault(dataset, {})
        entries = dataset_manifest.setdefault(stage, [])

        filtered_entries = [
            existing
            for existing in entries
            if not (
                isinstance(existing, dict)
                and existing.get("name") == entry.get("name")
            )
        ]
        filtered_entries.append(entry)
        dataset_manifest[stage] = filtered_entries
        return manifest

    def _normalize_record_name(self, name: str) -> str:
        """Create a filesystem-friendly record name."""
        normalized = re.sub(r"[^a-z0-9]+", "_", name.strip().lower())
        normalized = normalized.strip("_")
        if not normalized:
            raise ValueError("Record name must contain at least one alphanumeric character")
        return normalized

    def _now_iso(self) -> str:
        """Return the current UTC timestamp in ISO 8601 format."""
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _to_json(self, payload: dict[str, Any]) -> str:
        """Serialize a payload using a stable JSON representation."""
        import json

        return json.dumps(payload, ensure_ascii=False, indent=2)
