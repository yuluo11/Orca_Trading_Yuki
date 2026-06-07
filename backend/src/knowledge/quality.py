"""Data quality audit for processed knowledge records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from .foundation import (
    directions_conflict,
    foundation_rule_key,
    normalize_foundation_metadata,
    validate_foundation_metadata,
)
from .repository import DatasetName, KnowledgeRepository

QualitySeverity = Literal["warning", "error"]


@dataclass(frozen=True, slots=True)
class KnowledgeQualityIssue:
    """One quality issue found in a processed knowledge record."""

    dataset: DatasetName
    record_name: str
    severity: QualitySeverity
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class KnowledgeQualitySummary:
    """Aggregate quality audit result."""

    passed: bool
    record_count: int
    issue_count: int
    error_count: int
    warning_count: int
    issues: tuple[KnowledgeQualityIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "recordCount": self.record_count,
            "issueCount": self.issue_count,
            "errorCount": self.error_count,
            "warningCount": self.warning_count,
            "issues": [
                {
                    "dataset": issue.dataset,
                    "recordName": issue.record_name,
                    "severity": issue.severity,
                    "code": issue.code,
                    "message": issue.message,
                }
                for issue in self.issues
            ],
        }


class KnowledgeQualityAuditor:
    """Audit processed knowledge for missing metadata, staleness, and duplicates."""

    def __init__(self, repository: KnowledgeRepository | None = None) -> None:
        self.repository = repository or KnowledgeRepository()

    def audit(
        self,
        *,
        datasets: tuple[DatasetName, ...] = ("foundation", "dynamic"),
        dynamic_max_age_days: int | None = 45,
        required_metadata: tuple[str, ...] = ("dataset", "title", "created_at", "updated_at"),
    ) -> KnowledgeQualitySummary:
        """Run a quality audit over processed records."""
        issues: list[KnowledgeQualityIssue] = []
        content_hash_index: dict[str, list[tuple[DatasetName, str]]] = {}
        foundation_records: list[tuple[str, dict[str, Any]]] = []
        record_count = 0

        for dataset in datasets:
            for record_path in self.repository.list_processed_record_paths(dataset):
                record_count += 1
                record = self.repository.load_processed_record(dataset, record_path.stem)
                metadata = dict(record.get("metadata", {}))
                text = str(record.get("text", ""))
                record_name = record_path.stem

                if len(text.strip()) < 20:
                    issues.append(_issue(dataset, record_name, "error", "short_text", "Record text is too short."))

                for field in required_metadata:
                    if not metadata.get(field):
                        issues.append(
                            _issue(
                                dataset,
                                record_name,
                                "error",
                                "missing_metadata",
                                f"Missing required metadata field: {field}.",
                            )
                        )

                if dataset == "dynamic":
                    _audit_dynamic_metadata(
                        issues,
                        dataset=dataset,
                        record_name=record_name,
                        metadata=metadata,
                        max_age_days=dynamic_max_age_days,
                    )
                elif dataset == "foundation":
                    normalized_metadata = dict(metadata)
                    normalize_foundation_metadata(normalized_metadata)
                    _audit_foundation_metadata(
                        issues,
                        record_name=record_name,
                        metadata=normalized_metadata,
                    )
                    foundation_records.append((record_name, normalized_metadata))

                content_hash = metadata.get("content_hash")
                if isinstance(content_hash, str) and content_hash:
                    content_hash_index.setdefault(content_hash, []).append((dataset, record_name))

        _audit_foundation_conflicts(issues, foundation_records)

        for content_hash, records in content_hash_index.items():
            if len(records) <= 1:
                continue
            duplicate_names = ", ".join(f"{dataset}/{name}" for dataset, name in records)
            for dataset, record_name in records:
                issues.append(
                    _issue(
                        dataset,
                        record_name,
                        "warning",
                        "duplicate_content_hash",
                        f"Content hash is shared by records: {duplicate_names}.",
                    )
                )

        error_count = sum(issue.severity == "error" for issue in issues)
        warning_count = sum(issue.severity == "warning" for issue in issues)
        return KnowledgeQualitySummary(
            passed=error_count == 0,
            record_count=record_count,
            issue_count=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            issues=tuple(issues),
        )


def _audit_dynamic_metadata(
    issues: list[KnowledgeQualityIssue],
    *,
    dataset: DatasetName,
    record_name: str,
    metadata: dict[str, Any],
    max_age_days: int | None,
) -> None:
    if not metadata.get("source_url"):
        issues.append(
            _issue(dataset, record_name, "warning", "missing_source_url", "Dynamic record has no source_url.")
        )
    if not metadata.get("source_domain"):
        issues.append(
            _issue(dataset, record_name, "warning", "missing_source_domain", "Dynamic record has no source_domain.")
        )
    if not metadata.get("published_at"):
        issues.append(
            _issue(dataset, record_name, "warning", "missing_published_at", "Dynamic record has no published_at.")
        )
    if max_age_days is not None:
        updated_at = _parse_iso(str(metadata.get("updated_at", "")))
        if updated_at is not None:
            age_days = (datetime.now(UTC) - updated_at).days
            if age_days > max_age_days:
                issues.append(
                    _issue(
                        dataset,
                        record_name,
                        "warning",
                        "stale_dynamic_record",
                        f"Dynamic record is {age_days} days old.",
                    )
                )


def _audit_foundation_metadata(
    issues: list[KnowledgeQualityIssue],
    *,
    record_name: str,
    metadata: dict[str, Any],
) -> None:
    for code in validate_foundation_metadata(metadata):
        issues.append(
            _issue(
                "foundation",
                record_name,
                "error",
                code,
                f"Foundation metadata failed validation: {code}.",
            )
        )

    if not metadata.get("applies_to"):
        issues.append(
            _issue(
                "foundation",
                record_name,
                "warning",
                "missing_applies_to",
                "Foundation record should define applies_to for better retrieval boundaries.",
            )
        )
    if not metadata.get("valid_when"):
        issues.append(
            _issue(
                "foundation",
                record_name,
                "warning",
                "missing_valid_when",
                "Foundation record should define valid_when to avoid overbroad agent behavior.",
            )
        )


def _audit_foundation_conflicts(
    issues: list[KnowledgeQualityIssue],
    records: list[tuple[str, dict[str, Any]]],
) -> None:
    by_rule_id = {
        str(metadata.get("rule_id")): record_name
        for record_name, metadata in records
        if metadata.get("rule_id")
    }
    for record_name, metadata in records:
        for conflict_id in metadata.get("conflicts_with", []) or ():
            if conflict_id not in by_rule_id:
                issues.append(
                    _issue(
                        "foundation",
                        record_name,
                        "warning",
                        "unknown_conflict_reference",
                        f"conflicts_with references an unknown rule_id: {conflict_id}.",
                    )
                )

    for index, (left_name, left_metadata) in enumerate(records):
        left_direction = str(left_metadata.get("rule_direction", "neutral"))
        if left_direction in {"neutral", "observe"}:
            continue
        for right_name, right_metadata in records[index + 1 :]:
            if foundation_rule_key(left_metadata) != foundation_rule_key(right_metadata):
                continue
            right_direction = str(right_metadata.get("rule_direction", "neutral"))
            if directions_conflict(left_direction, right_direction):
                message = (
                    f"Potential static rule conflict with {right_name}: "
                    f"{left_direction} vs {right_direction}."
                )
                issues.append(
                    _issue("foundation", left_name, "warning", "potential_static_conflict", message)
                )
                issues.append(
                    _issue(
                        "foundation",
                        right_name,
                        "warning",
                        "potential_static_conflict",
                        message.replace(right_name, left_name),
                    )
                )


def _issue(
    dataset: DatasetName,
    record_name: str,
    severity: QualitySeverity,
    code: str,
    message: str,
) -> KnowledgeQualityIssue:
    return KnowledgeQualityIssue(
        dataset=dataset,
        record_name=record_name,
        severity=severity,
        code=code,
        message=message,
    )


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
