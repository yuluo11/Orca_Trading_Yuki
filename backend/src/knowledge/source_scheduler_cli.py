"""Command-line entrypoint for the dynamic knowledge crawl scheduler.

Examples:
    python -m backend.src.knowledge.source_scheduler_cli list
    python -m backend.src.knowledge.source_scheduler_cli due
    python -m backend.src.knowledge.source_scheduler_cli run-due
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Sequence

from .repository import KnowledgeRepository
from .source_scheduler import CrawlRunResult, DynamicKnowledgeCrawlScheduler


def build_parser() -> argparse.ArgumentParser:
    """Build the scheduler CLI parser."""
    parser = argparse.ArgumentParser(description="Dynamic knowledge source scheduler")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Knowledge data root. Defaults to backend/data.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_config = subparsers.add_parser(
        "import-config",
        help="Register sources from a JSON source config file",
    )
    import_config.add_argument("--config", type=Path, required=True)
    import_config.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and show sources without writing the schedule file.",
    )

    register = subparsers.add_parser("register", help="Register or update a scheduled source")
    register.add_argument("--source-type", required=True, choices=("rss_feed", "web_page"))
    register.add_argument("--url", required=True)
    register.add_argument("--source-id", default=None)
    register.add_argument("--dataset", default="dynamic", choices=("foundation", "dynamic"))
    register.add_argument("--category", default="news")
    register.add_argument("--symbol", default=None)
    register.add_argument("--topic", default=None)
    register.add_argument("--title", default=None)
    register.add_argument("--max-items", type=int, default=10)
    register.add_argument("--refresh-interval-minutes", type=int, default=None)
    register.add_argument("--next-run-at", default=None)
    register.add_argument("--disabled", action="store_true")

    list_sources = subparsers.add_parser("list", help="List scheduled sources")
    list_sources.add_argument("--active-only", action="store_true")

    subparsers.add_parser("due", help="List sources that are currently due")

    run_due = subparsers.add_parser("run-due", help="Run all currently due sources")
    run_due.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report due sources without fetching them.",
    )

    run_source = subparsers.add_parser("run-source", help="Run one scheduled source")
    run_source.add_argument("--source-id", required=True)
    run_source.add_argument("--force", action="store_true")
    run_source.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report the selected source without fetching it.",
    )

    return parser


def run_cli(argv: Sequence[str] | None = None) -> dict[str, Any]:
    """Run a scheduler CLI command and return a JSON-serializable payload."""
    parser = build_parser()
    args = parser.parse_args(argv)
    repository = KnowledgeRepository(data_root=args.data_root) if args.data_root else KnowledgeRepository()
    scheduler = DynamicKnowledgeCrawlScheduler(repository=repository)

    if args.command == "import-config":
        return import_config_file(
            scheduler,
            args.config,
            dry_run=args.dry_run,
        )

    if args.command == "register":
        source = scheduler.register_source(
            source_id=args.source_id,
            source_type=args.source_type,
            url=args.url,
            dataset=args.dataset,
            category=args.category,
            enabled=not args.disabled,
            symbol=args.symbol,
            topic=args.topic,
            title=args.title,
            max_items=args.max_items,
            refresh_interval_minutes=args.refresh_interval_minutes,
            next_run_at=args.next_run_at,
        )
        return {"source": serialize_dataclass(source), "schedulePath": str(scheduler.store.path)}

    if args.command == "list":
        sources = scheduler.list_sources(include_disabled=not args.active_only)
        return {
            "count": len(sources),
            "sources": [serialize_dataclass(source) for source in sources],
            "schedulePath": str(scheduler.store.path),
        }

    if args.command == "due":
        sources = scheduler.due_sources()
        return {
            "count": len(sources),
            "sources": [serialize_dataclass(source) for source in sources],
            "schedulePath": str(scheduler.store.path),
        }

    if args.command == "run-due":
        if args.dry_run:
            sources = scheduler.due_sources()
            return {
                "dryRun": True,
                "count": len(sources),
                "sources": [serialize_dataclass(source) for source in sources],
                "schedulePath": str(scheduler.store.path),
            }
        results = scheduler.run_due_sources()
        return serialize_run_results(results, schedule_path=str(scheduler.store.path))

    if args.command == "run-source":
        if args.dry_run:
            sources = [
                source
                for source in scheduler.list_sources()
                if source.source_id == args.source_id
            ]
            return {
                "dryRun": True,
                "count": len(sources),
                "sources": [serialize_dataclass(source) for source in sources],
                "schedulePath": str(scheduler.store.path),
            }
        result = scheduler.run_source(args.source_id, force=args.force)
        return serialize_run_results([result], schedule_path=str(scheduler.store.path))

    raise ValueError(f"Unsupported command: {args.command}")


def import_config_file(
    scheduler: DynamicKnowledgeCrawlScheduler,
    config_path: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Import scheduled sources from a JSON config file."""
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("Source config must contain a sources list")

    imported_sources: list[dict[str, Any]] = []
    for source_payload in sources:
        if not isinstance(source_payload, dict):
            raise ValueError("Each source config entry must be an object")
        if dry_run:
            imported_sources.append(dict(source_payload))
            continue
        source = scheduler.register_source(
            source_id=source_payload.get("source_id"),
            source_type=source_payload["source_type"],
            url=source_payload["url"],
            dataset=source_payload.get("dataset", "dynamic"),
            category=source_payload.get("category", "news"),
            enabled=source_payload.get("enabled", True),
            symbol=source_payload.get("symbol"),
            topic=source_payload.get("topic"),
            title=source_payload.get("title"),
            max_items=int(source_payload.get("max_items", 10)),
            refresh_interval_minutes=source_payload.get("refresh_interval_minutes"),
            next_run_at=source_payload.get("next_run_at"),
        )
        imported_sources.append(serialize_dataclass(source))

    return {
        "dryRun": dry_run,
        "count": len(imported_sources),
        "sources": imported_sources,
        "configPath": str(config_path),
        "schedulePath": str(scheduler.store.path),
    }


def serialize_run_results(
    results: list[CrawlRunResult],
    *,
    schedule_path: str,
) -> dict[str, Any]:
    """Serialize scheduler run results."""
    return {
        "count": len(results),
        "results": [serialize_dataclass(result) for result in results],
        "schedulePath": schedule_path,
    }


def serialize_dataclass(value: Any) -> dict[str, Any]:
    """Serialize one scheduler dataclass."""
    return asdict(value)


def main(argv: Sequence[str] | None = None) -> int:
    """Print a scheduler command result as JSON."""
    result = run_cli(argv)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
