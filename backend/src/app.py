"""Application entrypoints for analyst realization and analyst-runtime assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from .config import build_app_config
from .knowledge.collector_service import (
    KnowledgeCollectorService,
    RSSFeedCollectionResult,
    WebPageCollectionResult,
)
from .knowledge.collectors.web_page import HtmlFetcher
from .knowledge.repository import DatasetName, KnowledgeRepository
from .knowledge.source_scheduler import DynamicKnowledgeCrawlScheduler
from .knowledge.source_governance import DynamicSourceGovernancePolicy
from .llm.client import LLMClient, LLMRunnable, ensure_llm_client
from .llm import build_configured_llm_client
from .models import (
    AnalystOrchestrationResult,
    AnalystResult,
    DecisionOutput,
    DecisionRealizationResult,
    GuidanceObservationPersistenceResult,
    GuidanceObservationSummary,
    GuidancePriorsSummary,
    ReflectionOutput,
    ReflectionPersistenceResult,
    ReflectionPersistenceRunResult,
)
from .agents.analysts.base_agent import (
    AnalystRuntimeState,
    AnalystTask,
    FilePromptProvider as AnalystFilePromptProvider,
    BaseLangGraphAnalystAgent,
)
from .agents.decision import DecisionAdvisoryAgent, DecisionTask
from .agents.decision.base_agent import FilePromptProvider as DecisionFilePromptProvider
from .agents.reflection import ReflectionAgent, ReflectionTask
from .agents.reflection.base_agent import FilePromptProvider as ReflectionFilePromptProvider
from .agents.analysts.graph_agent import GraphAnalystAgent
from .agents.analysts.market_agent import MarketAnalystAgent
from .agents.analysts.news_agent import NewsAnalystAgent
from .agents.analysts.orchestrator import AnalystOrchestrator
from .agents.analysts.sentiment_agent import SentimentAnalystAgent
from .agents.analysts.social_agent import SocialAnalystAgent
from .services.analysts.graph_service import GraphAnalystService
from .services.analysts.market_service import MarketAnalystService
from .services.analysts.news_service import NewsAnalystService
from .services.analysts.sentiment_service import SentimentAnalystService
from .services.analysts.social_service import SocialAnalystService
from .services.decision import (
    DecisionGuidanceObservationAnalyticsService,
    DecisionGuidanceObservationService,
    DecisionKnowledgeService,
)
from .services.reflection import ReflectionContextService, ReflectionPersistenceService
from .tools.analyst.tooling import AnalystToolRegistry, KnowledgeBaseSearchTool

APP_CONFIG = build_app_config()
PROMPTS_ROOT_DIR = APP_CONFIG.prompts.root_dir
ANALYST_PROMPTS_DIR = APP_CONFIG.prompts.analysts_dir
DECISION_PROMPTS_DIR = APP_CONFIG.prompts.decision_dir
REFLECTION_PROMPTS_DIR = APP_CONFIG.prompts.reflection_dir
DEFAULT_ANALYST_SEQUENCE = APP_CONFIG.workflow.default_analyst_sequence

# Registry mapping analyst names to their (AgentClass, ServiceClass) pairs.
# Adding a new analyst only requires one entry here.
ANALYST_REGISTRY: dict[
    str,
    tuple[type[BaseLangGraphAnalystAgent], type],
] = {
    "graph_analyst": (GraphAnalystAgent, GraphAnalystService),
    "market_analyst": (MarketAnalystAgent, MarketAnalystService),
    "news_analyst": (NewsAnalystAgent, NewsAnalystService),
    "sentiment_analyst": (SentimentAnalystAgent, SentimentAnalystService),
    "social_analyst": (SocialAnalystAgent, SocialAnalystService),
}


class AppRuntimeState(TypedDict, total=False):
    """Top-level workflow state used by the first LangGraph runtime."""

    subject: str
    symbol: str | None
    trade_date: str | None
    extra_context: str | None
    datasets: tuple[DatasetName, ...] | list[DatasetName] | None
    metadata_filter: dict[str, Any] | None
    max_documents: int | None
    messages: list[Any]
    analyst_outputs: dict[str, AnalystResult]
    decision_output: DecisionOutput
    reflection_output: ReflectionOutput
    portfolio_context: dict[str, Any] | None


def build_prompt_provider(
    prompts_dir: str | Path | None = None,
) -> AnalystFilePromptProvider:
    """Build the prompt provider backed by prompt files on disk."""
    return AnalystFilePromptProvider(prompts_dir or ANALYST_PROMPTS_DIR)


def build_tool_registry(
    service: Any,
) -> AnalystToolRegistry:
    """Register the first analyst tools available to the runtime."""
    registry = AnalystToolRegistry()
    registry.register(KnowledgeBaseSearchTool(service))
    return registry


def build_decision_prompt_provider(
    prompts_dir: str | Path | None = None,
) -> DecisionFilePromptProvider:
    """Build the prompt provider for the decision advisory layer."""
    return DecisionFilePromptProvider(prompts_dir or DECISION_PROMPTS_DIR)


def build_reflection_prompt_provider(
    prompts_dir: str | Path | None = None,
) -> ReflectionFilePromptProvider:
    """Build the prompt provider for the post-decision reflection layer."""
    return ReflectionFilePromptProvider(prompts_dir or REFLECTION_PROMPTS_DIR)


def build_default_llm_client() -> LLMClient | None:
    """Build the configured default live client when LLM settings are present."""
    return build_configured_llm_client(APP_CONFIG.llm)


def resolve_runtime_llm_client(
    *,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> LLMClient | None:
    """Resolve the runtime llm_client from explicit inputs or app configuration."""
    resolved = ensure_llm_client(llm_client=llm_client, llm=llm)
    if resolved is not None:
        return resolved
    return build_default_llm_client()


def _build_analyst_agent(
    analyst_name: str,
    *,
    repository: KnowledgeRepository | None = None,
    prompt_provider: AnalystFilePromptProvider | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> BaseLangGraphAnalystAgent:
    """Generic factory that builds any registered analyst agent by name."""
    agent_cls, service_cls = ANALYST_REGISTRY[analyst_name]
    service = service_cls(repository=repository)
    tool_reg = build_tool_registry(service)
    return agent_cls(
        service=service,
        tool_registry=tool_reg,
        prompt_provider=prompt_provider or build_prompt_provider(),
        llm_client=resolve_runtime_llm_client(llm_client=llm_client, llm=llm),
    )


# Backward-compatible thin wrappers ------------------------------------------


def build_graph_analyst_agent(**kwargs: Any) -> BaseLangGraphAnalystAgent:
    """Assemble the graph analyst agent."""
    return _build_analyst_agent("graph_analyst", **kwargs)


def build_market_analyst_agent(**kwargs: Any) -> BaseLangGraphAnalystAgent:
    """Assemble the market analyst agent."""
    return _build_analyst_agent("market_analyst", **kwargs)


def build_news_analyst_agent(**kwargs: Any) -> BaseLangGraphAnalystAgent:
    """Assemble the news analyst agent."""
    return _build_analyst_agent("news_analyst", **kwargs)


def build_sentiment_analyst_agent(**kwargs: Any) -> BaseLangGraphAnalystAgent:
    """Assemble the sentiment analyst agent."""
    return _build_analyst_agent("sentiment_analyst", **kwargs)


def build_social_analyst_agent(**kwargs: Any) -> BaseLangGraphAnalystAgent:
    """Assemble the social analyst agent."""
    return _build_analyst_agent("social_analyst", **kwargs)


def build_default_analyst_agents(
    *,
    repository: KnowledgeRepository | None = None,
    prompt_provider: AnalystFilePromptProvider | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> dict[str, BaseLangGraphAnalystAgent]:
    """Build the default set of analyst agents used by the workflow."""
    resolved_prompt_provider = prompt_provider or build_prompt_provider()
    return {
        name: _build_analyst_agent(
            name,
            repository=repository,
            prompt_provider=resolved_prompt_provider,
            llm_client=llm_client,
            llm=llm,
        )
        for name in ANALYST_REGISTRY
    }


def build_analyst_orchestrator(
    *,
    repository: KnowledgeRepository | None = None,
    prompt_provider: AnalystFilePromptProvider | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> AnalystOrchestrator:
    """Build the internal orchestrator coordinating the default analyst sequence."""
    return AnalystOrchestrator(
        analysts=build_default_analyst_agents(
            repository=repository,
            prompt_provider=prompt_provider,
            llm_client=llm_client,
            llm=llm,
        ),
        sequence=DEFAULT_ANALYST_SEQUENCE,
        llm_client=resolve_runtime_llm_client(llm_client=llm_client, llm=llm),
        prompts_dir=ANALYST_PROMPTS_DIR,
    )


def build_decision_advisory_agent(
    *,
    repository: KnowledgeRepository | None = None,
    prompt_provider: DecisionFilePromptProvider | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> DecisionAdvisoryAgent:
    """Assemble the decision advisory agent and its dedicated prompt assets."""
    service = DecisionKnowledgeService(repository=repository)
    return DecisionAdvisoryAgent(
        service=service,
        prompt_provider=prompt_provider or build_decision_prompt_provider(),
        llm_client=resolve_runtime_llm_client(llm_client=llm_client, llm=llm),
    )


def build_reflection_agent(
    *,
    repository: KnowledgeRepository | None = None,
    prompt_provider: ReflectionFilePromptProvider | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> ReflectionAgent:
    """Assemble the post-decision reflection agent and prompt assets."""
    service = ReflectionContextService(repository=repository)
    return ReflectionAgent(
        service=service,
        prompt_provider=prompt_provider or build_reflection_prompt_provider(),
        llm_client=resolve_runtime_llm_client(llm_client=llm_client, llm=llm),
    )


def build_reflection_persistence_service(
    *,
    repository: KnowledgeRepository | None = None,
) -> ReflectionPersistenceService:
    """Build the reflection persistence service for postmortem memory writeback."""
    return ReflectionPersistenceService(repository=repository)


def build_decision_guidance_observation_service(
    *,
    repository: KnowledgeRepository | None = None,
) -> DecisionGuidanceObservationService:
    """Build the decision guidance observation persistence service."""
    return DecisionGuidanceObservationService(repository=repository)


def build_decision_guidance_observation_analytics_service(
    *,
    repository: KnowledgeRepository | None = None,
) -> DecisionGuidanceObservationAnalyticsService:
    """Build the decision guidance observation analytics service."""
    return DecisionGuidanceObservationAnalyticsService(repository=repository)


def build_knowledge_collector_service(
    *,
    repository: KnowledgeRepository | None = None,
    source_policy: DynamicSourceGovernancePolicy | None = None,
) -> KnowledgeCollectorService:
    """Build the knowledge collector service used by URL and manual collection flows."""
    return KnowledgeCollectorService(repository=repository, source_policy=source_policy)


def build_dynamic_knowledge_scheduler(
    *,
    repository: KnowledgeRepository | None = None,
    source_policy: DynamicSourceGovernancePolicy | None = None,
) -> DynamicKnowledgeCrawlScheduler:
    """Build the persistent dynamic knowledge crawl scheduler."""
    return DynamicKnowledgeCrawlScheduler(
        repository=repository,
        source_policy=source_policy,
    )


def collect_web_page_knowledge(
    *,
    url: str,
    persist: bool = False,
    dataset: DatasetName = "dynamic",
    category: str = "web_page",
    symbol: str | None = None,
    topic: str | None = None,
    title: str | None = None,
    repository: KnowledgeRepository | None = None,
    fetcher: HtmlFetcher | None = None,
    source_policy: DynamicSourceGovernancePolicy | None = None,
) -> WebPageCollectionResult:
    """Collect a user-provided URL as temporary context or dynamic knowledge."""
    return build_knowledge_collector_service(
        repository=repository,
        source_policy=source_policy,
    ).collect_web_page(
        url,
        persist=persist,
        dataset=dataset,
        category=category,
        symbol=symbol,
        topic=topic,
        title=title,
        fetcher=fetcher,
    )


def collect_rss_feed_knowledge(
    *,
    feed_url: str,
    persist: bool = False,
    dataset: DatasetName = "dynamic",
    category: str = "news",
    symbol: str | None = None,
    topic: str | None = None,
    max_items: int = 10,
    repository: KnowledgeRepository | None = None,
    fetcher: HtmlFetcher | None = None,
    source_policy: DynamicSourceGovernancePolicy | None = None,
) -> RSSFeedCollectionResult:
    """Collect RSS/Atom feed entries for immediate context or persistent knowledge."""
    return build_knowledge_collector_service(
        repository=repository,
        source_policy=source_policy,
    ).collect_rss_feed(
        feed_url,
        persist=persist,
        dataset=dataset,
        category=category,
        symbol=symbol,
        topic=topic,
        max_items=max_items,
        fetcher=fetcher,
    )


def run_analyst(
    analyst_name: str,
    *,
    subject: str,
    symbol: str | None = None,
    trade_date: str | None = None,
    extra_context: str | None = None,
    datasets: tuple[DatasetName, ...] | None = None,
    metadata_filter: dict[str, Any] | None = None,
    max_documents: int | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> AnalystResult:
    """Run any registered analyst by name without compiling a LangGraph workflow."""
    task = AnalystTask(
        subject=subject,
        symbol=symbol,
        trade_date=trade_date,
        extra_context=extra_context,
        datasets=datasets,
        metadata_filter=metadata_filter,
        max_documents=max_documents,
    )
    return _build_analyst_agent(analyst_name, llm_client=llm_client, llm=llm).invoke(task)


# Backward-compatible thin wrappers ------------------------------------------


def run_graph_analyst(**kwargs: Any) -> AnalystResult:
    """Run the graph analyst directly."""
    return run_analyst("graph_analyst", **kwargs)


def run_market_analyst(**kwargs: Any) -> AnalystResult:
    """Run the market analyst directly."""
    return run_analyst("market_analyst", **kwargs)


def run_news_analyst(**kwargs: Any) -> AnalystResult:
    """Run the news analyst directly."""
    return run_analyst("news_analyst", **kwargs)


def run_sentiment_analyst(**kwargs: Any) -> AnalystResult:
    """Run the sentiment analyst directly."""
    return run_analyst("sentiment_analyst", **kwargs)


def run_social_analyst(**kwargs: Any) -> AnalystResult:
    """Run the social analyst directly."""
    return run_analyst("social_analyst", **kwargs)


def run_analyst_orchestrator(
    *,
    subject: str,
    symbol: str | None = None,
    trade_date: str | None = None,
    extra_context: str | None = None,
    datasets: tuple[DatasetName, ...] | None = None,
    metadata_filter: dict[str, Any] | None = None,
    max_documents: int | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> AnalystOrchestrationResult:
    """Run the internal multi-analyst orchestrator and return the aggregate result."""
    task = AnalystTask(
        subject=subject,
        symbol=symbol,
        trade_date=trade_date,
        extra_context=extra_context,
        datasets=datasets,
        metadata_filter=metadata_filter,
        max_documents=max_documents,
    )
    orchestrator = build_analyst_orchestrator(llm_client=llm_client, llm=llm)
    return orchestrator.run(task)


def run_analyst_realization(
    *,
    subject: str,
    symbol: str | None = None,
    trade_date: str | None = None,
    extra_context: str | None = None,
    datasets: tuple[DatasetName, ...] | None = None,
    metadata_filter: dict[str, Any] | None = None,
    max_documents: int | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> dict[str, Any]:
    """Run a full analyst realization and return the top-level aggregated result."""
    return run_analyst_orchestrator(
        subject=subject,
        symbol=symbol,
        trade_date=trade_date,
        extra_context=extra_context,
        datasets=datasets,
        metadata_filter=metadata_filter,
        max_documents=max_documents,
        llm_client=llm_client,
        llm=llm,
    )


def run_decision_advisory(
    *,
    analyst_payload: AnalystOrchestrationResult,
    portfolio_context: dict[str, Any] | None = None,
    datasets: tuple[DatasetName, ...] | None = None,
    metadata_filter: dict[str, Any] | None = None,
    max_documents: int | None = None,
    repository: KnowledgeRepository | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> DecisionOutput:
    """Run the decision advisory agent over an analyst orchestration payload."""
    task = DecisionTask.from_analyst_payload(
        analyst_payload,
        portfolio_context=portfolio_context,
        datasets=datasets,
        metadata_filter=metadata_filter,
        max_documents=max_documents,
    )
    agent = build_decision_advisory_agent(
        repository=repository,
        llm_client=llm_client,
        llm=llm,
    )
    return agent.invoke(task)


def run_reflection(
    *,
    decision_output: DecisionOutput,
    analyst_payload: AnalystOrchestrationResult | None = None,
    portfolio_context: dict[str, Any] | None = None,
    execution_summary: dict[str, Any] | None = None,
    outcome_metrics: dict[str, Any] | None = None,
    exit_context: dict[str, Any] | None = None,
    post_trade_notes: str | None = None,
    realized_outcome: dict[str, Any] | None = None,
    feedback_notes: str | None = None,
    datasets: tuple[DatasetName, ...] | None = None,
    metadata_filter: dict[str, Any] | None = None,
    max_documents: int | None = None,
    repository: KnowledgeRepository | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> ReflectionOutput:
    """Run the post-decision reflection agent over a finalized decision payload."""
    task = ReflectionTask.from_decision_payload(
        decision_output,
        analyst_payload=analyst_payload,
        portfolio_context=portfolio_context,
        execution_summary=execution_summary,
        outcome_metrics=outcome_metrics,
        exit_context=exit_context,
        post_trade_notes=post_trade_notes,
        realized_outcome=realized_outcome,
        feedback_notes=feedback_notes,
        datasets=datasets,
        metadata_filter=metadata_filter,
        max_documents=max_documents,
    )
    agent = build_reflection_agent(
        repository=repository,
        llm_client=llm_client,
        llm=llm,
    )
    return agent.invoke(task)


def persist_reflection_memory(
    *,
    reflection_result: ReflectionOutput,
    dataset: DatasetName = "dynamic",
    force: bool = False,
    repository: KnowledgeRepository | None = None,
) -> ReflectionPersistenceResult:
    """Persist a reflection candidate memory into the processed knowledge base."""
    service = build_reflection_persistence_service(repository=repository)
    return service.persist_reflection_result(
        reflection_result,
        dataset=dataset,
        force=force,
    )


def persist_decision_guidance_observation(
    *,
    decision_result: DecisionOutput,
    dataset: DatasetName = "dynamic",
    force: bool = False,
    repository: KnowledgeRepository | None = None,
) -> GuidanceObservationPersistenceResult:
    """Persist a structured observation describing applied postmortem guidance."""
    service = build_decision_guidance_observation_service(repository=repository)
    return service.persist_guidance_observation(
        decision_result,
        dataset=dataset,
        force=force,
    )


def summarize_decision_guidance_observations(
    *,
    dataset: DatasetName = "dynamic",
    symbol: str | None = None,
    recommendation: str | None = None,
    top_n: int = 5,
    repository: KnowledgeRepository | None = None,
) -> GuidanceObservationSummary:
    """Summarize persisted decision-guidance observation records."""
    service = build_decision_guidance_observation_analytics_service(repository=repository)
    return service.summarize_observations(
        dataset=dataset,
        symbol=symbol,
        recommendation=recommendation,
        top_n=top_n,
    )


def summarize_decision_guidance_priors(
    *,
    datasets: tuple[DatasetName, ...] | list[DatasetName] | None = None,
    symbol: str | None = None,
    recommendation: str | None = None,
    scenario_profile: dict[str, Any] | None = None,
    top_n: int = 3,
    repository: KnowledgeRepository | None = None,
) -> GuidancePriorsSummary:
    """Summarize recurring applied-guidance priors for future decision runs."""
    service = build_decision_guidance_observation_analytics_service(repository=repository)
    return service.summarize_guidance_priors(
        datasets=datasets,
        symbol=symbol,
        recommendation=recommendation,
        scenario_profile=scenario_profile,
        top_n=top_n,
    )


def summarize_decision_setup_outcomes(
    *,
    datasets: tuple[DatasetName, ...] | list[DatasetName] | None = None,
    symbol: str | None = None,
    scenario_profile: dict[str, Any] | None = None,
    top_n: int = 3,
    repository: KnowledgeRepository | None = None,
) -> dict[str, Any]:
    """Summarize setup-level historical outcomes from persisted decision memories."""
    service = build_decision_guidance_observation_analytics_service(repository=repository)
    return service.summarize_setup_outcome_priors(
        datasets=datasets,
        symbol=symbol,
        scenario_profile=scenario_profile,
        top_n=top_n,
    )


def summarize_decision_setup_recommendation_outcomes(
    *,
    datasets: tuple[DatasetName, ...] | list[DatasetName] | None = None,
    symbol: str | None = None,
    scenario_profile: dict[str, Any] | None = None,
    top_n: int = 5,
    repository: KnowledgeRepository | None = None,
) -> dict[str, Any]:
    """Summarize historical recommendation-to-outcome patterns for one setup."""
    service = build_decision_guidance_observation_analytics_service(repository=repository)
    return service.summarize_setup_recommendation_outcomes(
        datasets=datasets,
        symbol=symbol,
        scenario_profile=scenario_profile,
        top_n=top_n,
    )


def run_reflection_and_persist(
    *,
    decision_output: DecisionOutput,
    analyst_payload: AnalystOrchestrationResult | None = None,
    portfolio_context: dict[str, Any] | None = None,
    execution_summary: dict[str, Any] | None = None,
    outcome_metrics: dict[str, Any] | None = None,
    exit_context: dict[str, Any] | None = None,
    post_trade_notes: str | None = None,
    realized_outcome: dict[str, Any] | None = None,
    feedback_notes: str | None = None,
    datasets: tuple[DatasetName, ...] | None = None,
    metadata_filter: dict[str, Any] | None = None,
    max_documents: int | None = None,
    persistence_dataset: DatasetName = "dynamic",
    persistence_force: bool = False,
    repository: KnowledgeRepository | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> ReflectionPersistenceRunResult:
    """Run reflection and then persist the candidate memory when eligible."""
    reflection_result = run_reflection(
        decision_output=decision_output,
        analyst_payload=analyst_payload,
        portfolio_context=portfolio_context,
        execution_summary=execution_summary,
        outcome_metrics=outcome_metrics,
        exit_context=exit_context,
        post_trade_notes=post_trade_notes,
        realized_outcome=realized_outcome,
        feedback_notes=feedback_notes,
        datasets=datasets,
        metadata_filter=metadata_filter,
        max_documents=max_documents,
        repository=repository,
        llm_client=llm_client,
        llm=llm,
    )
    persistence_result = persist_reflection_memory(
        reflection_result=reflection_result,
        dataset=persistence_dataset,
        force=persistence_force,
        repository=repository,
    )
    return {
        "reflection": reflection_result,
        "persistence": persistence_result,
    }


def run_decision_realization(
    *,
    subject: str,
    symbol: str | None = None,
    trade_date: str | None = None,
    extra_context: str | None = None,
    portfolio_context: dict[str, Any] | None = None,
    analyst_datasets: tuple[DatasetName, ...] | None = None,
    analyst_metadata_filter: dict[str, Any] | None = None,
    analyst_max_documents: int | None = None,
    decision_datasets: tuple[DatasetName, ...] | None = None,
    decision_metadata_filter: dict[str, Any] | None = None,
    decision_max_documents: int | None = None,
    repository: KnowledgeRepository | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> DecisionRealizationResult:
    """Run the analyst layer first, then synthesize an advisory decision payload."""
    analyst_payload = run_analyst_orchestrator(
        subject=subject,
        symbol=symbol,
        trade_date=trade_date,
        extra_context=extra_context,
        datasets=analyst_datasets,
        metadata_filter=analyst_metadata_filter,
        max_documents=analyst_max_documents,
        llm_client=llm_client,
        llm=llm,
    )
    decision_payload = run_decision_advisory(
        analyst_payload=analyst_payload,
        portfolio_context=portfolio_context,
        datasets=decision_datasets,
        metadata_filter=decision_metadata_filter,
        max_documents=decision_max_documents,
        repository=repository,
        llm_client=llm_client,
        llm=llm,
    )
    return {
        "subject": subject,
        "symbol": symbol,
        "trade_date": trade_date,
        "portfolio_context": portfolio_context,
        "analyst": analyst_payload,
        "decision": decision_payload,
    }


def build_langgraph_workflow(
    *,
    repository: KnowledgeRepository | None = None,
    prompt_provider: AnalystFilePromptProvider | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> Any:
    """Compile the default multi-analyst workflow when optional deps are installed."""
    try:
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "langgraph is not installed. Install langgraph to compile the analyst runtime."
        ) from error

    agents = build_default_analyst_agents(
        repository=repository,
        prompt_provider=prompt_provider,
        llm_client=llm_client,
        llm=llm,
    )
    workflow = StateGraph(AppRuntimeState)
    for analyst_name in DEFAULT_ANALYST_SEQUENCE:
        workflow.add_node(analyst_name, agents[analyst_name].as_node())
    workflow.set_entry_point(DEFAULT_ANALYST_SEQUENCE[0])
    for current_name, next_name in zip(
        DEFAULT_ANALYST_SEQUENCE,
        DEFAULT_ANALYST_SEQUENCE[1:],
    ):
        workflow.add_edge(current_name, next_name)
    workflow.add_edge(DEFAULT_ANALYST_SEQUENCE[-1], END)
    return workflow.compile()


def run_langgraph_workflow(
    *,
    subject: str,
    symbol: str | None = None,
    trade_date: str | None = None,
    extra_context: str | None = None,
    datasets: tuple[DatasetName, ...] | None = None,
    metadata_filter: dict[str, Any] | None = None,
    max_documents: int | None = None,
    llm_client: LLMClient | None = None,
    llm: LLMRunnable | None = None,
) -> AnalystRuntimeState:
    """Run the compiled workflow when langgraph is available."""
    workflow = build_langgraph_workflow(llm_client=llm_client, llm=llm)
    initial_state: AnalystRuntimeState = {
        "subject": subject,
        "symbol": symbol,
        "trade_date": trade_date,
        "extra_context": extra_context,
        "datasets": datasets,
        "metadata_filter": metadata_filter,
        "max_documents": max_documents,
        "messages": [],
        "analyst_outputs": {},
    }
    return workflow.invoke(initial_state)
