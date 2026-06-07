"""Ingestion utilities for building processed knowledge records."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from .policy import DEFAULT_KNOWLEDGE_POLICY, KnowledgePolicy
from .foundation import normalize_foundation_metadata
from .indexing import KnowledgeIndexer
from .record import KnowledgeMetadata, ProcessedKnowledgeRecord
from .repository import DatasetName, KnowledgeRepository


IngestStatus = Literal["created", "updated", "unchanged", "skipped_duplicate"]
COMMON_NON_SYMBOL_TOKENS = {
    "alpha",
    "beta",
    "brief",
    "event",
    "guide",
    "guides",
    "learn",
    "macro",
    "market",
    "news",
    "note",
    "notes",
    "recap",
    "review",
    "risk",
    "setup",
    "signal",
    "summary",
    "trade",
    "update",
    "watch",
}


@dataclass(slots=True)
class IngestOutcome:
    """Structured result describing one ingest operation."""

    status: IngestStatus
    record_path: Path
    record_name: str
    source_path: Path | None = None
    reason: str | None = None
    index_snapshot_path: Path | None = None


@dataclass(slots=True)
class BatchIngestSummary:
    """Aggregate result for a batch import operation."""

    outcomes: list[IngestOutcome]

    @property
    def imported_count(self) -> int:
        return sum(outcome.status in {"created", "updated"} for outcome in self.outcomes)

    @property
    def skipped_count(self) -> int:
        return sum(outcome.status in {"unchanged", "skipped_duplicate"} for outcome in self.outcomes)

    @property
    def created_count(self) -> int:
        return sum(outcome.status == "created" for outcome in self.outcomes)

    @property
    def updated_count(self) -> int:
        return sum(outcome.status == "updated" for outcome in self.outcomes)


class KnowledgeIngestor:
    """Create processed knowledge records from raw text inputs."""

    def __init__(
        self,
        repository: KnowledgeRepository,
        *,
        policy: KnowledgePolicy = DEFAULT_KNOWLEDGE_POLICY,
    ) -> None:
        self.repository = repository
        self.policy = policy
        self.indexer = KnowledgeIndexer(repository)

    def ingest_text(
        self,
        dataset: DatasetName,
        name: str,
        text: str,
        metadata: KnowledgeMetadata | None = None,
    ) -> Path:
        """Persist a processed knowledge record and update the manifest."""
        outcome = self.ingest_text_with_outcome(
            dataset,
            name,
            text,
            metadata=metadata,
        )
        return outcome.record_path

    def ingest_text_with_outcome(
        self,
        dataset: DatasetName,
        name: str,
        text: str,
        metadata: KnowledgeMetadata | None = None,
        source_path: Path | None = None,
    ) -> IngestOutcome:
        """Persist a processed knowledge record and return a detailed ingest outcome."""
        cleaned_text = self._clean_text(text)
        if not cleaned_text:
            raise ValueError("Cannot ingest an empty knowledge record")

        record_name = self._normalize_record_name(name)
        record_path = self.repository.get_processed_record_path(dataset, record_name)
        record_path.parent.mkdir(parents=True, exist_ok=True)

        existing_duplicate = self._find_exact_text_duplicate(
            dataset,
            cleaned_text,
            exclude_path=record_path,
        )
        if existing_duplicate is not None:
            return IngestOutcome(
                status="skipped_duplicate",
                record_path=existing_duplicate,
                record_name=existing_duplicate.stem,
                reason="An equivalent processed record already exists in this dataset.",
            )

        similar_duplicate = self._find_similar_text_duplicate(
            dataset,
            cleaned_text,
            exclude_path=record_path,
        )
        if similar_duplicate is not None:
            return IngestOutcome(
                status="skipped_duplicate",
                record_path=similar_duplicate,
                record_name=similar_duplicate.stem,
                reason="A highly similar processed record already exists in this dataset.",
            )

        existing_status = "created"
        created_at: str | None = None
        if record_path.exists():
            existing_record = self.repository.load_processed_record(dataset, record_name)
            existing_text = self._clean_text(existing_record["text"])
            if existing_text == cleaned_text:
                return IngestOutcome(
                    status="unchanged",
                    record_path=record_path,
                    record_name=record_name,
                    reason="The target processed record already contains the same normalized text.",
                )
            created_at = existing_record.get("metadata", {}).get("created_at")
            existing_status = "updated"

        prepared_metadata = self._prepare_metadata(
            dataset,
            metadata,
            name=name,
            text=cleaned_text,
            created_at=created_at,
            source_path=source_path,
        )
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
                    "text_hash": self._text_hash(cleaned_text),
                },
            )
        )

        record_path.write_text(self._to_json(record), encoding="utf-8")
        index_snapshot_path = self._refresh_indexes_after_ingest(dataset)
        return IngestOutcome(
            status=existing_status,
            record_path=record_path,
            record_name=record_name,
            index_snapshot_path=index_snapshot_path,
        )

    def ingest_raw_text_file(
        self,
        dataset: DatasetName,
        raw_file: str | Path,
        *,
        metadata: KnowledgeMetadata | None = None,
        processed_name: str | None = None,
    ) -> Path:
        """Read a raw text file, create a processed record, and update the manifest."""
        outcome = self.ingest_raw_text_file_with_outcome(
            dataset,
            raw_file,
            metadata=metadata,
            processed_name=processed_name,
        )
        return outcome.record_path

    def ingest_raw_text_file_with_outcome(
        self,
        dataset: DatasetName,
        raw_file: str | Path,
        *,
        metadata: KnowledgeMetadata | None = None,
        processed_name: str | None = None,
    ) -> IngestOutcome:
        """Read a raw text file, create a processed record, and return the ingest outcome."""
        raw_path = Path(raw_file)
        if not raw_path.exists():
            raise FileNotFoundError(f"Raw knowledge file not found: {raw_path}")

        text = raw_path.read_text(encoding="utf-8")
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
        outcome = self.ingest_text_with_outcome(
            dataset,
            target_name,
            text,
            metadata=metadata,
            source_path=raw_path,
        )
        outcome.source_path = raw_path
        return outcome

    def ingest_raw_text_directory(
        self,
        dataset: DatasetName,
        raw_dir: str | Path,
        *,
        patterns: tuple[str, ...] = ("*.txt", "*.md", "*.markdown"),
        metadata: KnowledgeMetadata | None = None,
        metadata_by_name: dict[str, KnowledgeMetadata] | None = None,
    ) -> BatchIngestSummary:
        """Batch-ingest supported raw text files from one directory tree."""
        source_dir = Path(raw_dir)
        if not source_dir.exists():
            raise FileNotFoundError(f"Raw knowledge directory not found: {source_dir}")
        if not source_dir.is_dir():
            raise ValueError(f"Raw knowledge path is not a directory: {source_dir}")

        raw_paths: list[Path] = []
        seen_paths: set[Path] = set()
        for pattern in patterns:
            for path in sorted(source_dir.rglob(pattern)):
                if not path.is_file() or path in seen_paths:
                    continue
                seen_paths.add(path)
                raw_paths.append(path)

        outcomes: list[IngestOutcome] = []
        for raw_path in raw_paths:
            merged_metadata: KnowledgeMetadata = dict(metadata or {})
            if metadata_by_name and raw_path.stem in metadata_by_name:
                merged_metadata.update(metadata_by_name[raw_path.stem])
            outcomes.append(
                self.ingest_raw_text_file_with_outcome(
                    dataset,
                    raw_path,
                    metadata=merged_metadata or None,
                )
            )
        return BatchIngestSummary(outcomes)

    def _prepare_metadata(
        self,
        dataset: DatasetName,
        metadata: KnowledgeMetadata | None,
        *,
        name: str,
        text: str,
        created_at: str | None = None,
        source_path: Path | None = None,
    ) -> KnowledgeMetadata:
        """Fill default metadata fields for a processed knowledge record."""
        prepared: KnowledgeMetadata = dict(metadata or {})
        timestamp = self._now_iso()
        inferred_metadata = self._infer_metadata(dataset, name, source_path=source_path)
        for key, value in inferred_metadata.items():
            prepared.setdefault(key, value)
        prepared["dataset"] = dataset
        prepared.setdefault("title", self._default_title(name))
        prepared.setdefault("created_at", created_at or timestamp)
        prepared["updated_at"] = timestamp
        prepared.setdefault(
            "reliability",
            self.policy.metadata.default_reliability,
        )
        prepared.setdefault(
            "time_sensitivity",
            self.policy.metadata.default_time_sensitivity(dataset),
        )
        prepared.setdefault("content_hash", self._text_hash(text))
        prepared.setdefault("content_length", len(text))
        self._normalize_metadata_values(prepared)
        if dataset == "foundation":
            normalize_foundation_metadata(prepared)
        return prepared

    def _update_manifest(
        self,
        *,
        dataset: DatasetName,
        stage: str,
        entry: dict[str, Any],
    ) -> dict[str, Any]:
        """Insert or replace a manifest entry for a dataset stage."""
        manifest = (
            self.repository.load_manifest()
            if self.repository.manifest_exists()
            else {"datasets": {}}
        )
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

    def _default_title(self, name: str) -> str:
        """Build a human-readable default title from a raw record name."""
        collapsed = re.sub(r"[_\-]+", " ", name.strip())
        collapsed = re.sub(r"\s+", " ", collapsed)
        return collapsed.title() if collapsed else "Untitled Record"

    def _infer_metadata(
        self,
        dataset: DatasetName,
        name: str,
        *,
        source_path: Path | None,
    ) -> KnowledgeMetadata:
        """Infer lightweight metadata from the filename and directory structure."""
        inferred: KnowledgeMetadata = {}
        if source_path is not None and self.policy.cleaning.keep_source_in_metadata:
            inferred["source"] = str(source_path)

        if self.policy.metadata.infer_from_directory and source_path is not None:
            category = self._infer_category_from_directory(dataset, source_path)
            if category:
                inferred["category"] = category

        if self.policy.metadata.infer_from_filename:
            symbol = self._infer_symbol_from_name(name)
            if symbol:
                inferred["symbol"] = symbol
            topic = self._infer_topic_from_name(name)
            if topic:
                inferred["topic"] = topic

        return inferred

    def _infer_category_from_directory(
        self,
        dataset: DatasetName,
        source_path: Path,
    ) -> str | None:
        """Infer a category from the first nested directory below dataset/raw."""
        try:
            dataset_raw_root = self.repository.get_dataset_path(dataset, "raw").resolve()
            relative = source_path.resolve().relative_to(dataset_raw_root)
        except Exception:
            return None
        parts = relative.parts[:-1]
        if not parts:
            return None
        return parts[0].strip().lower() or None

    def _infer_symbol_from_name(self, name: str) -> str | None:
        """Infer a simple ticker-like symbol from the record name."""
        tokens = [
            token
            for token in re.split(r"[^A-Za-z0-9]+", name)
            if token
        ]
        if tokens:
            token = tokens[0]
            if (
                token.isalpha()
                and 1 <= len(token) <= 5
                and token.lower() not in COMMON_NON_SYMBOL_TOKENS
            ):
                return token.upper()
        return None

    def _infer_topic_from_name(self, name: str) -> str | None:
        """Infer a coarse topic string from non-symbol filename tokens."""
        raw_tokens = [
            token
            for token in re.split(r"[^A-Za-z0-9]+", name)
            if token
        ]
        symbol = self._infer_symbol_from_name(name)
        topic_tokens = [
            token.lower()
            for index, token in enumerate(raw_tokens)
            if index > 0 and token.upper() != (symbol or "")
        ]
        if not topic_tokens:
            return None
        return " ".join(topic_tokens[:4])

    def _normalize_metadata_values(self, metadata: KnowledgeMetadata) -> None:
        """Standardize common metadata fields before a record is persisted."""
        if "symbol" in metadata:
            symbol = str(metadata["symbol"]).strip().upper()
            if symbol:
                metadata["symbol"] = symbol
            else:
                metadata.pop("symbol", None)

        if "category" in metadata:
            category = str(metadata["category"]).strip().lower()
            category = re.sub(r"[^a-z0-9]+", "_", category).strip("_")
            if category:
                metadata["category"] = category
            else:
                metadata.pop("category", None)

        if "topic" in metadata:
            topic = re.sub(r"\s+", " ", str(metadata["topic"]).strip().lower())
            if topic:
                metadata["topic"] = topic
            else:
                metadata.pop("topic", None)

        if "title" in metadata:
            title = re.sub(r"\s+", " ", str(metadata["title"]).strip())
            metadata["title"] = title or "Untitled Record"

        if "source_url" in metadata and "source_domain" not in metadata:
            parsed = urlparse(str(metadata["source_url"]))
            if parsed.hostname:
                metadata["source_domain"] = parsed.hostname.lower()

        if "source_domain" in metadata:
            domain = str(metadata["source_domain"]).strip().lower()
            if domain:
                metadata["source_domain"] = domain
            else:
                metadata.pop("source_domain", None)

        if "tags" in metadata:
            raw_tags = metadata["tags"]
            if isinstance(raw_tags, str):
                raw_tag_values = raw_tags.split(",")
            else:
                raw_tag_values = list(raw_tags)
            tags: list[str] = []
            for tag in raw_tag_values:
                normalized = re.sub(r"\s+", " ", str(tag).strip().lower())
                if normalized and normalized not in tags:
                    tags.append(normalized)
            if tags:
                metadata["tags"] = tags
            else:
                metadata.pop("tags", None)

        if metadata.get("reliability") not in {"high", "medium", "low"}:
            metadata["reliability"] = self.policy.metadata.default_reliability
        if metadata.get("time_sensitivity") not in {"high", "medium", "low"}:
            metadata["time_sensitivity"] = self.policy.metadata.default_time_sensitivity(
                metadata["dataset"]
            )

    def _clean_text(self, text: str) -> str:
        """Apply lightweight normalization and boilerplate cleanup to raw text."""
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
        if self.policy.cleaning.strip_obvious_boilerplate:
            cleaned = self._strip_obvious_boilerplate(cleaned)

        lines = cleaned.split("\n")
        normalized_lines: list[str] = []
        for line in lines:
            candidate = line.strip() if self.policy.cleaning.trim_whitespace else line
            if self.policy.cleaning.collapse_repeated_spaces:
                candidate = re.sub(r"[ \t]{2,}", " ", candidate)
            if self.policy.cleaning.drop_empty_paragraphs and not candidate:
                normalized_lines.append("")
                continue
            normalized_lines.append(candidate)

        cleaned = "\n".join(normalized_lines)
        if self.policy.cleaning.collapse_extra_blank_lines:
            cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _strip_obvious_boilerplate(self, text: str) -> str:
        """Remove a few common non-knowledge boilerplate lines."""
        filtered_lines: list[str] = []
        boilerplate_patterns = (
            r"^copyright\b",
            r"^all rights reserved\.?$",
            r"^disclaimer\b",
            r"^page\s+\d+(\s+of\s+\d+)?$",
        )
        for raw_line in text.split("\n"):
            stripped = raw_line.strip()
            if any(re.match(pattern, stripped, flags=re.IGNORECASE) for pattern in boilerplate_patterns):
                continue
            filtered_lines.append(raw_line)
        return "\n".join(filtered_lines)

    def _find_exact_text_duplicate(
        self,
        dataset: DatasetName,
        cleaned_text: str,
        *,
        exclude_path: Path | None = None,
    ) -> Path | None:
        """Return an existing processed record path when exact-text deduplication matches."""
        if not self.policy.deduplication.exact_text_match_enabled:
            return None

        text_hash = self._text_hash(cleaned_text)
        for record_path in self.repository.list_processed_record_paths(dataset):
            if exclude_path is not None and record_path == exclude_path:
                continue
            existing_record = self.repository.load_processed_record(dataset, record_path.stem)
            if self._text_hash(self._clean_text(existing_record["text"])) == text_hash:
                return record_path
        return None

    def _find_similar_text_duplicate(
        self,
        dataset: DatasetName,
        cleaned_text: str,
        *,
        exclude_path: Path | None = None,
    ) -> Path | None:
        """Return a matching record path when high-similarity detection is enabled."""
        if not self.policy.deduplication.similar_text_detection_enabled:
            return None

        threshold = self.policy.deduplication.similar_text_threshold
        for record_path in self.repository.list_processed_record_paths(dataset):
            if exclude_path is not None and record_path == exclude_path:
                continue
            existing_record = self.repository.load_processed_record(dataset, record_path.stem)
            existing_text = self._clean_text(existing_record["text"])
            similarity = SequenceMatcher(a=cleaned_text, b=existing_text).ratio()
            if similarity >= threshold:
                return record_path
        return None

    def _text_hash(self, text: str) -> str:
        """Create a stable content hash for deduplication and manifest tracking."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _refresh_indexes_after_ingest(self, dataset: DatasetName) -> Path | None:
        """Rebuild the dataset-local index view and persist a snapshot when configured."""
        indexing_policy = self.policy.indexing
        if not (
            indexing_policy.rebuild_mode == "automatic"
            or indexing_policy.rebuild_after_processed_updates
        ):
            return None

        if not indexing_policy.snapshot_enabled:
            return None

        return self.indexer.save_persisted_token_vector_index(
            f"{dataset}_auto_index",
            datasets=(dataset,),
        )

    def _now_iso(self) -> str:
        """Return the current UTC timestamp in ISO 8601 format."""
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _to_json(self, payload: dict[str, Any]) -> str:
        """Serialize a payload using a stable JSON representation."""
        import json

        return json.dumps(payload, ensure_ascii=False, indent=2)
