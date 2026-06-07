"""Command-line entrypoint for user-fixed knowledge retrieval evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .evaluation import KnowledgeRetrievalEvaluator
from .repository import KnowledgeRepository


def build_parser() -> argparse.ArgumentParser:
    """Build the evaluation CLI parser."""
    parser = argparse.ArgumentParser(description="Run knowledge retrieval eval sets")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Knowledge data root. Defaults to backend/data.",
    )
    parser.add_argument(
        "--eval-set",
        type=Path,
        required=True,
        help="Path to a user-fixed knowledge eval set JSON file.",
    )
    parser.add_argument(
        "--include-disabled",
        action="store_true",
        help="Run disabled eval cases too.",
    )
    return parser


def run_cli(argv: Sequence[str] | None = None) -> dict[str, Any]:
    """Run evaluation and return a JSON-serializable payload."""
    args = build_parser().parse_args(argv)
    repository = KnowledgeRepository(data_root=args.data_root) if args.data_root else KnowledgeRepository()
    summary = KnowledgeRetrievalEvaluator(repository).evaluate_file(
        args.eval_set,
        include_disabled=args.include_disabled,
    )
    return {
        **summary.to_dict(),
        "evalSetPath": str(args.eval_set),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Print evaluation results as JSON."""
    result = run_cli(argv)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
