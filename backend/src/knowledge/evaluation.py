"""Configurable retrieval evaluation for fixed knowledge-base checks."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .indexing import KnowledgeIndexer
from .repository import DatasetName, KnowledgeRepository
from .retriever import KnowledgeRetriever


@dataclass(frozen=True, slots=True)
class KnowledgeEvalCase:
    """One user-defined retrieval check."""

    case_id: str
    query: str
    datasets: tuple[DatasetName, ...] = ("foundation", "dynamic")
    k: int = 4
    enabled: bool = True
    expected_symbols: tuple[str, ...] = ()
    expected_categories: tuple[str, ...] = ()
    must_include_terms: tuple[str, ...] = ()
    metadata_filter: dict[str, Any] | None = None
    min_results: int = 1


@dataclass(frozen=True, slots=True)
class KnowledgeEvalCaseResult:
    """Pass/fail result for one retrieval check."""

    case_id: str
    query: str
    passed: bool
    failures: tuple[str, ...]
    result_count: int
    top_results: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class KnowledgeEvalSummary:
    """Aggregate evaluation summary."""

    passed: bool
    total_count: int
    passed_count: int
    failed_count: int
    skipped_count: int
    results: tuple[KnowledgeEvalCaseResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "totalCount": self.total_count,
            "passedCount": self.passed_count,
            "failedCount": self.failed_count,
            "skippedCount": self.skipped_count,
            "results": [
                {
                    "caseId": result.case_id,
                    "query": result.query,
                    "passed": result.passed,
                    "failures": list(result.failures),
                    "resultCount": result.result_count,
                    "topResults": list(result.top_results),
                }
                for result in self.results
            ],
        }


class KnowledgeRetrievalEvaluator:
    """Run user-fixed retrieval checks against the current knowledge backend."""

    def __init__(self, repository: KnowledgeRepository | None = None) -> None:
        self.repository = repository or KnowledgeRepository()

    def load_cases(self, eval_set_path: str | Path) -> list[KnowledgeEvalCase]:
        """Load enabled and disabled cases from a JSON eval-set file."""
        path = Path(eval_set_path)
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        if not isinstance(payload, dict):
            raise ValueError(f"Knowledge eval set must be a JSON object: {path}")
        raw_cases = payload.get("cases", [])
        if not isinstance(raw_cases, list):
            raise ValueError("Knowledge eval set field 'cases' must be a list")
        return [parse_eval_case(raw_case) for raw_case in raw_cases]

    def evaluate_cases(
        self,
        cases: list[KnowledgeEvalCase],
        *,
        include_disabled: bool = False,
    ) -> KnowledgeEvalSummary:
        """Evaluate fixed cases and return a serializable summary."""
        active_cases = [
            case
            for case in cases
            if case.enabled or include_disabled
        ]
        results = tuple(self.evaluate_case(case) for case in active_cases)
        passed_count = sum(result.passed for result in results)
        failed_count = len(results) - passed_count
        skipped_count = len(cases) - len(active_cases)
        return KnowledgeEvalSummary(
            passed=failed_count == 0,
            total_count=len(results),
            passed_count=passed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            results=results,
        )

    def evaluate_file(
        self,
        eval_set_path: str | Path,
        *,
        include_disabled: bool = False,
    ) -> KnowledgeEvalSummary:
        """Load and evaluate a user-fixed JSON eval set."""
        return self.evaluate_cases(
            self.load_cases(eval_set_path),
            include_disabled=include_disabled,
        )

    def evaluate_case(self, case: KnowledgeEvalCase) -> KnowledgeEvalCaseResult:
        """Evaluate one retrieval check."""
        backend = KnowledgeIndexer(self.repository).load_or_build_default_backend(case.datasets)
        scored_documents = KnowledgeRetriever(
            self.repository,
            backend=backend,
        ).search_with_scores(
            case.query,
            datasets=case.datasets,
            k=case.k,
            metadata_filter=case.metadata_filter,
        )
        top_results = tuple(
            _serialize_scored_document(document, score)
            for document, score in scored_documents
        )
        failures = _evaluate_expectations(case, top_results)
        return KnowledgeEvalCaseResult(
            case_id=case.case_id,
            query=case.query,
            passed=not failures,
            failures=tuple(failures),
            result_count=len(top_results),
            top_results=top_results,
        )


def parse_eval_case(payload: Any) -> KnowledgeEvalCase:
    """Parse one JSON eval-set case."""
    if not isinstance(payload, dict):
        raise ValueError("Each knowledge eval case must be an object")
    case_id = _required_string(payload, "case_id")
    query = _required_string(payload, "query")
    datasets = _parse_datasets(payload.get("datasets", ("foundation", "dynamic")))
    metadata_filter = payload.get("metadata_filter")
    if metadata_filter is not None and not isinstance(metadata_filter, dict):
        raise ValueError(f"metadata_filter for eval case {case_id} must be an object")
    return KnowledgeEvalCase(
        case_id=case_id,
        query=query,
        datasets=datasets,
        k=_optional_positive_int(payload.get("k"), default=4),
        enabled=bool(payload.get("enabled", True)),
        expected_symbols=_string_tuple(payload.get("expected_symbols")),
        expected_categories=_string_tuple(payload.get("expected_categories")),
        must_include_terms=_string_tuple(payload.get("must_include_terms")),
        metadata_filter=metadata_filter,
        min_results=_optional_positive_int(payload.get("min_results"), default=1),
    )


def _evaluate_expectations(
    case: KnowledgeEvalCase,
    top_results: tuple[dict[str, Any], ...],
) -> list[str]:
    failures: list[str] = []
    if len(top_results) < case.min_results:
        failures.append(
            f"Expected at least {case.min_results} results, got {len(top_results)}."
        )

    metadata_values = [
        result.get("metadata", {})
        for result in top_results
        if isinstance(result.get("metadata", {}), dict)
    ]
    if case.expected_symbols:
        symbols = {str(metadata.get("symbol", "")).upper() for metadata in metadata_values}
        missing_symbols = [
            symbol
            for symbol in case.expected_symbols
            if symbol.upper() not in symbols
        ]
        if missing_symbols:
            failures.append(f"Missing expected symbols: {', '.join(missing_symbols)}.")

    if case.expected_categories:
        categories = {
            str(metadata.get("category", "")).lower()
            for metadata in metadata_values
        }
        missing_categories = [
            category
            for category in case.expected_categories
            if category.lower() not in categories
        ]
        if missing_categories:
            failures.append(f"Missing expected categories: {', '.join(missing_categories)}.")

    if case.must_include_terms:
        haystack = " ".join(
            str(result.get("text", ""))
            for result in top_results
        ).lower()
        missing_terms = [
            term
            for term in case.must_include_terms
            if term.lower() not in haystack
        ]
        if missing_terms:
            failures.append(f"Missing required terms: {', '.join(missing_terms)}.")

    return failures


def _serialize_scored_document(document: Any, score: float) -> dict[str, Any]:
    text = str(getattr(document, "page_content", ""))
    metadata = dict(getattr(document, "metadata", {}))
    return {
        "title": metadata.get("title", ""),
        "text": text,
        "excerpt": _excerpt(text),
        "score": round(score, 6),
        "metadata": metadata,
    }


def _parse_datasets(value: Any) -> tuple[DatasetName, ...]:
    if isinstance(value, str):
        return (_dataset(value),)
    if isinstance(value, list | tuple):
        datasets = tuple(_dataset(item) for item in value)
        if datasets:
            return datasets
    raise ValueError("datasets must be a dataset string or a non-empty list")


def _dataset(value: Any) -> DatasetName:
    if value not in {"foundation", "dynamic"}:
        raise ValueError("dataset must be either 'foundation' or 'dynamic'")
    return value


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required string field: {key}")
    return value.strip()


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, list | tuple):
        return tuple(str(item).strip() for item in value if str(item).strip())
    raise ValueError("Expected a string or list of strings")


def _optional_positive_int(value: Any, *, default: int) -> int:
    if value is None or value == "":
        return default
    parsed = int(value)
    if parsed < 1:
        raise ValueError("integer values must be positive")
    return parsed


def _excerpt(text: str, *, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."
