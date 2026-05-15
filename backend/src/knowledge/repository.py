"""Knowledge repository entrypoint for shared data directory access."""

import json
from pathlib import Path
from typing import Any, Literal

from .record import ProcessedKnowledgeRecord

DatasetName = Literal["foundation", "dynamic"]
DatasetStage = Literal["raw", "processed"]


class KnowledgeRepository:
    """Expose the canonical paths for the project's knowledge base."""

    def __init__(self, data_root: Path | None = None) -> None:
        src_root = Path(__file__).resolve().parents[1]
        default_root = src_root.parent / "data"
        self.data_root = data_root or default_root

    @property
    def foundation_raw(self) -> Path:
        return self.data_root / "foundation" / "raw"

    @property
    def foundation_processed(self) -> Path:
        return self.data_root / "foundation" / "processed"

    @property
    def dynamic_raw(self) -> Path:
        return self.data_root / "dynamic" / "raw"

    @property
    def dynamic_processed(self) -> Path:
        return self.data_root / "dynamic" / "processed"

    @property
    def indexes(self) -> Path:
        return self.data_root / "indexes"

    @property
    def manifests(self) -> Path:
        return self.data_root / "manifests"

    @property
    def manifest_path(self) -> Path:
        return self.manifests / "knowledge_manifest.json"

    def ensure_structure(self) -> None:
        """Create the expected knowledge-base directories if they are missing."""
        for path in (
            self.foundation_raw,
            self.foundation_processed,
            self.dynamic_raw,
            self.dynamic_processed,
            self.indexes,
            self.manifests,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def manifest_exists(self) -> bool:
        """Return whether the manifest file exists on disk."""
        return self.manifest_path.exists()

    def load_manifest(self) -> dict[str, Any]:
        """Load the knowledge manifest from disk."""
        return self._load_json_file(self.manifest_path)

    def save_manifest(self, manifest: dict[str, Any]) -> None:
        """Write the knowledge manifest back to disk."""
        self.manifests.mkdir(parents=True, exist_ok=True)
        with self.manifest_path.open("w", encoding="utf-8") as file:
            json.dump(manifest, file, ensure_ascii=False, indent=2)

    def get_dataset_path(self, dataset: DatasetName, stage: DatasetStage) -> Path:
        """Return the canonical path for a dataset stage."""
        return self.data_root / dataset / stage

    def list_dataset_files(
        self,
        dataset: DatasetName,
        stage: DatasetStage,
        pattern: str = "*",
    ) -> list[Path]:
        """List files under a dataset stage."""
        dataset_path = self.get_dataset_path(dataset, stage)
        if not dataset_path.exists():
            return []
        return sorted(path for path in dataset_path.rglob(pattern) if path.is_file())

    def list_index_files(self, pattern: str = "*") -> list[Path]:
        """List files stored under the indexes directory."""
        if not self.indexes.exists():
            return []
        return sorted(path for path in self.indexes.rglob(pattern) if path.is_file())

    def get_processed_record_path(self, dataset: DatasetName, record_name: str) -> Path:
        """Return the path for a processed knowledge record."""
        record_path = self.get_dataset_path(dataset, "processed") / record_name
        return record_path if record_path.suffix else record_path.with_suffix(".json")

    def list_processed_record_paths(self, dataset: DatasetName) -> list[Path]:
        """List all processed knowledge record files for a dataset."""
        return self.list_dataset_files(dataset, "processed", pattern="*.json")

    def load_processed_record(
        self,
        dataset: DatasetName,
        record_name: str,
    ) -> ProcessedKnowledgeRecord:
        """Load a single processed knowledge record from disk."""
        record_path = self.get_processed_record_path(dataset, record_name)
        if not record_path.exists():
            raise FileNotFoundError(f"Processed knowledge record not found: {record_path}")
        record = self._load_json_file(record_path)
        return self._validate_processed_record(record, record_path, dataset)

    def _load_json_file(self, path: Path) -> dict[str, Any]:
        """Load a JSON file and return its parsed dictionary content."""
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError(f"Expected a JSON object in {path}, got {type(data).__name__}")
        return data

    def _validate_processed_record(
        self,
        record: dict[str, Any],
        path: Path,
        dataset: DatasetName,
    ) -> ProcessedKnowledgeRecord:
        """Validate the minimum shape of a processed knowledge record."""
        text = record.get("text")
        metadata = record.get("metadata")

        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Processed record {path} must contain a non-empty 'text' field")

        if not isinstance(metadata, dict):
            raise ValueError(f"Processed record {path} must contain a 'metadata' object")

        record_dataset = metadata.get("dataset")
        if record_dataset is not None and record_dataset != dataset:
            raise ValueError(
                f"Processed record {path} dataset mismatch: {record_dataset!r} != {dataset!r}"
            )

        return record  # type: ignore[return-value]

    def load_all_processed_records(
        self,
        dataset: DatasetName,
    ) -> list[ProcessedKnowledgeRecord]:
        """Load all processed knowledge records for a dataset."""
        records: list[ProcessedKnowledgeRecord] = []
        for record_path in self.list_processed_record_paths(dataset):
            record = self._load_json_file(record_path)
            records.append(self._validate_processed_record(record, record_path, dataset))
        return records
