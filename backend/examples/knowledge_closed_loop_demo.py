"""Deterministic dynamic-knowledge closed-loop demo.

Run with:
    python -m backend.examples.knowledge_closed_loop_demo

The default run uses a temporary data directory, so it does not mutate the
project's real backend/data knowledge base.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from backend.src.agents.analysts.base_agent import AnalystTask
from backend.src.agents.analysts.news_agent import NewsAnalystAgent
from backend.src.agents.analysts.orchestrator import AnalystOrchestrator
from backend.src.agents.decision.advisory_agent import DecisionAdvisoryAgent
from backend.src.agents.decision.base_agent import DecisionTask
from backend.src.agents.reflection.base_agent import ReflectionTask
from backend.src.agents.reflection.reflection_agent import ReflectionAgent
from backend.src.knowledge.collector_service import KnowledgeCollectorService
from backend.src.knowledge.ingest import KnowledgeIngestor
from backend.src.knowledge.policy import KnowledgePolicy
from backend.src.knowledge.repository import KnowledgeRepository
from backend.src.knowledge.source_scheduler import DynamicKnowledgeCrawlScheduler, to_iso
from backend.src.routes.knowledge import search_knowledge_payload
from backend.src.services.analysts.news_service import NewsAnalystService
from backend.src.services.decision.memory import DecisionKnowledgeService
from backend.src.services.reflection import ReflectionContextService, ReflectionPersistenceService

SAMPLE_RSS_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Demo Market Feed</title>
    <item>
      <title>NVDA catalyst confirmation improves</title>
      <link>https://example.com/nvda-catalyst-confirmation</link>
      <description>
        NVIDIA momentum improved after fresh AI infrastructure commentary,
        while event fade and valuation risk remain the main watch items.
      </description>
      <pubDate>Mon, 18 May 2026 08:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def run_demo(data_root: Path | None = None) -> dict[str, Any]:
    """Run the closed-loop demo and return a compact verification summary."""
    if data_root is not None:
        repository = KnowledgeRepository(data_root=data_root)
        return _run_demo_with_repository(repository)

    with TemporaryDirectory() as tmpdir:
        repository = KnowledgeRepository(data_root=Path(tmpdir))
        return _run_demo_with_repository(repository)


def _run_demo_with_repository(repository: KnowledgeRepository) -> dict[str, Any]:
    policy = KnowledgePolicy()
    policy.indexing.rebuild_after_processed_updates = True
    policy.indexing.snapshot_enabled = True
    collector_service = KnowledgeCollectorService(
        repository=repository,
        ingestor=KnowledgeIngestor(repository, policy=policy),
    )
    scheduler = DynamicKnowledgeCrawlScheduler(
        repository=repository,
        collector_service=collector_service,
    )
    run_at = datetime(2026, 5, 18, 8, 0, tzinfo=UTC)
    scheduler.register_source(
        source_id="demo_rss_feed",
        source_type="rss_feed",
        url="https://example.com/demo-feed.xml",
        symbol="NVDA",
        topic="AI infrastructure catalyst",
        max_items=1,
        next_run_at=to_iso(run_at),
        now=run_at,
    )
    crawl_results = scheduler.run_due_sources(
        now=run_at,
        fetchers={"demo_rss_feed": lambda url: SAMPLE_RSS_XML},
    )
    search = search_knowledge_payload(
        {
            "query": "NVDA catalyst confirmation event fade valuation risk",
            "datasets": ["dynamic"],
            "metadata_filter": {"symbol": "NVDA", "category": "news"},
            "k": 3,
        },
        repository=repository,
    )

    news_agent = NewsAnalystAgent(
        service=NewsAnalystService(repository=repository),
        llm_client=None,
    )
    analyst_task = AnalystTask(
        subject="NVIDIA catalyst continuation check",
        symbol="NVDA",
        trade_date="2026-05-18",
        datasets=("dynamic",),
        metadata_filter={"category": "news"},
        max_documents=3,
    )
    orchestrator = AnalystOrchestrator(
        analysts={"news_analyst": news_agent},
        sequence=("news_analyst",),
        llm_client=None,
    )
    analyst_payload = orchestrator.run(analyst_task)

    portfolio_context = {
        "cash_pct": 20,
        "max_single_name_pct": 8,
        "positions": [],
    }
    decision_agent = DecisionAdvisoryAgent(
        service=DecisionKnowledgeService(repository=repository),
        llm_client=None,
    )
    decision_output = decision_agent.invoke(
        DecisionTask.from_analyst_payload(
            analyst_payload,
            portfolio_context=portfolio_context,
            datasets=("dynamic",),
            max_documents=3,
        )
    )

    reflection_agent = ReflectionAgent(
        service=ReflectionContextService(repository=repository),
        llm_client=None,
    )
    reflection_output = reflection_agent.invoke(
        ReflectionTask.from_decision_payload(
            decision_output,
            analyst_payload=analyst_payload,
            portfolio_context=portfolio_context,
            execution_summary={
                "entry_date": "2026-05-18",
                "exit_date": "2026-05-24",
                "holding_period_days": 6,
            },
            outcome_metrics={
                "realized_pnl_pct": -1.2,
                "max_drawdown_pct": -3.4,
            },
            exit_context={"exit_reason": "reduced after mixed follow-through"},
            post_trade_notes="The catalyst held attention, but confirmation stayed mixed.",
            datasets=("dynamic",),
            max_documents=3,
        )
    )
    persistence = ReflectionPersistenceService(repository).persist_reflection_result(
        reflection_output,
        force=True,
    )

    return {
        "data_root": str(repository.data_root),
        "crawl": {
            "source_id": crawl_results[0].source_id if crawl_results else "",
            "status": crawl_results[0].status if crawl_results else "skipped",
            "items": crawl_results[0].collected_count if crawl_results else 0,
            "ingested": crawl_results[0].imported_count if crawl_results else 0,
        },
        "search": {
            "count": search["count"],
            "top_title": search["documents"][0]["title"] if search["documents"] else "",
        },
        "analyst": {
            "overall_confidence": analyst_payload["overall_confidence"],
            "document_count": len(analyst_payload["analyst_results"][0]["documents"]),
            "key_signals": analyst_payload["key_signals"],
        },
        "decision": {
            "recommendation": decision_output["recommendation"],
            "confidence": decision_output["confidence"],
        },
        "reflection": {
            "confidence_change": reflection_output["confidence_change"],
            "lessons": reflection_output["lessons"],
            "persisted": persistence["persisted"],
        },
        "processed_record_count": len(repository.load_all_processed_records("dynamic")),
        "index_files": [str(path) for path in repository.list_index_files("*.json")],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Optional data root to persist demo records; omitted means temporary.",
    )
    args = parser.parse_args()
    print(json.dumps(run_demo(args.data_root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
