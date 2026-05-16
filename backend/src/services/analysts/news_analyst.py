"""News analyst service backed by the shared knowledge layer."""

from typing import Any

from ...knowledge.repository import KnowledgeRepository
from .base_agent import BaseLangGraphAnalystAgent, LLMRunnable, PromptProvider
from .graph_analyst import KnowledgeBackedAnalystService
from .tooling import AnalystToolRegistry


class NewsAnalystService(KnowledgeBackedAnalystService):
    """Retrieve time-sensitive news context from the dynamic knowledge base."""

    analyst_name = "news_analyst"
    default_datasets = ("dynamic",)

    def default_metadata_filter(self) -> dict[str, Any]:
        return {"category": "news"}


class NewsAnalystAgent(BaseLangGraphAnalystAgent):
    """Agent wrapper around the news analyst knowledge service."""

    def __init__(
        self,
        *,
        repository: KnowledgeRepository | None = None,
        service: NewsAnalystService | None = None,
        tool_registry: AnalystToolRegistry | None = None,
        prompt_provider: PromptProvider | None = None,
        llm: LLMRunnable | None = None,
    ) -> None:
        news_service = service or NewsAnalystService(repository=repository)
        super().__init__(
            analyst_name=news_service.analyst_name,
            knowledge_service=news_service,
            tool_registry=tool_registry,
            prompt_provider=prompt_provider,
            llm=llm,
        )
