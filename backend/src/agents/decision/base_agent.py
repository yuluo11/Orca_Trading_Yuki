"""Agent primitives for advisory-style decision synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, TypedDict

from ...knowledge.repository import DatasetName
from ...llm.client import LLMClient, LLMRunnable, ensure_llm_client
from ...services.decision.memory import DecisionKnowledgeService

ALLOWED_RECOMMENDATIONS = {
    "consider_buy",
    "consider_reduce",
    "hold",
    "keep_watch",
    "no_trade",
}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ADVISORY_SCOPE = "advisory_only"


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    """Return de-duplicated strings while keeping the first-seen ordering."""
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


@dataclass(slots=True)
class DecisionTask:
    """Structured input consumed by the decision advisory agent."""

    subject: str
    symbol: str | None = None
    trade_date: str | None = None
    extra_context: str | None = None
    overall_summary: str = ""
    overall_confidence: str = "low"
    key_signals: list[str] = field(default_factory=list)
    portfolio_risks: list[str] = field(default_factory=list)
    cross_analyst_observations: list[str] = field(default_factory=list)
    analyst_results: list[dict[str, Any]] = field(default_factory=list)
    analyst_sequence: list[str] = field(default_factory=list)
    portfolio_context: dict[str, Any] | None = None
    datasets: tuple[DatasetName, ...] | None = None
    metadata_filter: dict[str, Any] | None = None
    max_documents: int | None = None
    messages: list[Any] = field(default_factory=list)

    @classmethod
    def from_analyst_payload(
        cls,
        analyst_payload: dict[str, Any],
        *,
        portfolio_context: dict[str, Any] | None = None,
        datasets: tuple[DatasetName, ...] | None = None,
        metadata_filter: dict[str, Any] | None = None,
        max_documents: int | None = None,
        messages: list[Any] | None = None,
    ) -> "DecisionTask":
        """Build a decision task directly from analyst orchestrator output."""
        return cls(
            subject=str(analyst_payload.get("subject", "")).strip(),
            symbol=analyst_payload.get("symbol"),
            trade_date=analyst_payload.get("trade_date"),
            extra_context=analyst_payload.get("extra_context"),
            overall_summary=str(analyst_payload.get("overall_summary", "")).strip(),
            overall_confidence=str(analyst_payload.get("overall_confidence", "low")).strip(),
            key_signals=[
                str(item).strip()
                for item in analyst_payload.get("key_signals", [])
                if str(item).strip()
            ],
            portfolio_risks=[
                str(item).strip()
                for item in analyst_payload.get("portfolio_risks", [])
                if str(item).strip()
            ],
            cross_analyst_observations=[
                str(item).strip()
                for item in analyst_payload.get("cross_analyst_observations", [])
                if str(item).strip()
            ],
            analyst_results=list(analyst_payload.get("analyst_results", [])),
            analyst_sequence=[
                str(item).strip()
                for item in analyst_payload.get("analyst_sequence", [])
                if str(item).strip()
            ],
            portfolio_context=portfolio_context,
            datasets=datasets,
            metadata_filter=metadata_filter,
            max_documents=max_documents,
            messages=list(messages or analyst_payload.get("messages", [])),
        )


class DecisionRuntimeState(TypedDict, total=False):
    """State shape for future decision-oriented graph composition."""

    subject: str
    symbol: str | None
    trade_date: str | None
    extra_context: str | None
    overall_summary: str
    overall_confidence: str
    key_signals: list[str]
    portfolio_risks: list[str]
    cross_analyst_observations: list[str]
    analyst_results: list[dict[str, Any]]
    analyst_sequence: list[str]
    portfolio_context: dict[str, Any] | None
    datasets: tuple[DatasetName, ...] | list[DatasetName] | None
    metadata_filter: dict[str, Any] | None
    max_documents: int | None
    messages: list[Any]
    decision_output: dict[str, Any]


class PromptProvider(Protocol):
    """Prompt source used by decision agents."""

    def get_shared_prompt(self) -> str:
        """Return the shared prompt frame used by decision agents."""

    def get_analyst_prompt(self, analyst_name: str) -> str:
        """Return the role-specific prompt body."""


class FilePromptProvider:
    """Load the shared frame and role-specific prompts from disk."""

    def __init__(
        self,
        prompts_dir: str | Path,
        *,
        shared_prompt_name: str = "base_prompt.txt",
        shared_dir_name: str = "shared",
        roles_dir_name: str = "roles",
        suffix: str = ".txt",
    ) -> None:
        self.prompts_dir = Path(prompts_dir)
        self.shared_prompt_name = shared_prompt_name
        self.shared_dir_name = shared_dir_name
        self.roles_dir_name = roles_dir_name
        self.suffix = suffix

    def get_shared_prompt(self) -> str:
        """Return the shared prompt frame from disk."""
        return self._read_prompt(self.prompts_dir / self.shared_dir_name / self.shared_prompt_name)

    def get_analyst_prompt(self, analyst_name: str) -> str:
        """Return the agent-specific prompt body from disk."""
        return self._read_prompt(
            self.prompts_dir / self.roles_dir_name / f"{analyst_name}{self.suffix}"
        )

    def _read_prompt(self, prompt_path: Path) -> str:
        """Read a prompt file if it exists, otherwise return an empty prompt."""
        if not prompt_path.exists():
            return ""
        return prompt_path.read_text(encoding="utf-8").strip()


class BaseDecisionAgent:
    """Shared implementation for advisory decision agents."""

    agent_name = "decision_advisory"

    def __init__(
        self,
        *,
        agent_name: str | None = None,
        knowledge_service: DecisionKnowledgeService,
        prompt_provider: PromptProvider | None = None,
        llm_client: LLMClient | None = None,
        llm: LLMRunnable | None = None,
    ) -> None:
        if agent_name:
            self.agent_name = agent_name
        self.knowledge_service = knowledge_service
        self.prompt_provider = prompt_provider
        self.llm_client = ensure_llm_client(llm_client=llm_client, llm=llm)

    def retrieve_decision_context(self, task: DecisionTask) -> dict[str, Any]:
        """Retrieve decision-memory context relevant to the current advisory task."""
        return self.knowledge_service.analyze(
            task,
            datasets=task.datasets,
            metadata_filter=task.metadata_filter,
            k=task.max_documents,
        )

    def build_prompt_context(
        self,
        task: DecisionTask,
        decision_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the runtime context used while rendering the advisory prompt."""
        return {
            "subject": task.subject,
            "symbol": task.symbol,
            "trade_date": task.trade_date,
            "extra_context": task.extra_context,
            "overall_confidence": task.overall_confidence,
            "analyst_count": len(task.analyst_results),
            "has_portfolio_context": bool(task.portfolio_context),
            "decision_context": decision_context,
        }

    def render_prompt(self, prompt_context: dict[str, Any]) -> str:
        """Render the decision prompt from shared and role-specific prompt assets."""
        if self.prompt_provider is None:
            return ""

        shared_prompt = self.prompt_provider.get_shared_prompt()
        role_prompt = self.prompt_provider.get_analyst_prompt(self.agent_name)
        context_lines = [
            f"subject: {prompt_context.get('subject', '')}",
            f"symbol: {prompt_context.get('symbol') or 'N/A'}",
            f"trade_date: {prompt_context.get('trade_date') or 'N/A'}",
            f"extra_context: {prompt_context.get('extra_context') or 'N/A'}",
            f"overall_confidence: {prompt_context.get('overall_confidence') or 'low'}",
            f"analyst_count: {prompt_context.get('analyst_count', 0)}",
            f"portfolio_context_available: {prompt_context.get('has_portfolio_context', False)}",
            (
                "decision_memory_documents: "
                f"{prompt_context['decision_context'].get('document_count', 0)}"
            ),
        ]
        return "\n\n".join(
            block
            for block in (
                shared_prompt,
                role_prompt,
                "\n".join(context_lines),
            )
            if block
        )

    def build_llm_payload(
        self,
        task: DecisionTask,
        *,
        decision_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the structured payload sent into the configured llm_client."""
        return {
            "task": {
                "subject": task.subject,
                "symbol": task.symbol,
                "trade_date": task.trade_date,
                "extra_context": task.extra_context,
            },
            "analysis": {
                "overall_summary": task.overall_summary,
                "overall_confidence": task.overall_confidence,
                "key_signals": task.key_signals,
                "portfolio_risks": task.portfolio_risks,
                "cross_analyst_observations": task.cross_analyst_observations,
                "analyst_sequence": task.analyst_sequence,
                "analyst_results": task.analyst_results,
            },
            "portfolio_context": task.portfolio_context or {},
            "decision_memory": {
                "query": decision_context.get("query", ""),
                "document_count": decision_context.get("document_count", 0),
                "documents": decision_context.get("documents", []),
                "evidence": decision_context.get("evidence", []),
            },
            "instructions": (
                "Return a JSON object with keys: decision_summary, recommendation, "
                "advisory_scope, portfolio_context_used, portfolio_context_summary, "
                "position_impact, timing_decision, action_conditions, no_action_reasons, "
                "aggregated_risks, rationale, confidence, reference_cases, and "
                "case_fit_assessment. This is advisory only and must not imply trade execution "
                "or guaranteed outcomes."
            ),
        }

    def invoke(self, task: DecisionTask) -> dict[str, Any]:
        """Run the decision advisory flow end to end."""
        decision_context = self.retrieve_decision_context(task)
        prompt_context = self.build_prompt_context(task, decision_context)
        prompt = self.render_prompt(prompt_context)
        return self.synthesize(task, decision_context, prompt)

    def synthesize(
        self,
        task: DecisionTask,
        decision_context: dict[str, Any],
        prompt: str,
    ) -> dict[str, Any]:
        """Create the final decision payload using the model or fallback logic."""
        if self.llm_client is not None:
            return self._synthesize_with_llm(task, decision_context, prompt)
        return self._synthesize_fallback(task, decision_context, prompt)

    def _synthesize_with_llm(
        self,
        task: DecisionTask,
        decision_context: dict[str, Any],
        prompt: str,
    ) -> dict[str, Any]:
        """Invoke the llm_client and normalize the advisory output."""
        llm_payload = self.build_llm_payload(task, decision_context=decision_context)
        parsed_response = self.llm_client.invoke_json(
            prompt,
            payload=llm_payload,
            schema=self.decision_output_schema(),
        )
        return self.normalize_llm_result(
            parsed_response,
            task=task,
            decision_context=decision_context,
            prompt=prompt,
        )

    def _synthesize_fallback(
        self,
        task: DecisionTask,
        decision_context: dict[str, Any],
        prompt: str,
    ) -> dict[str, Any]:
        """Produce a cautious deterministic advisory result."""
        recommendation = self._fallback_recommendation(task)
        confidence = self._normalize_confidence(task.overall_confidence)
        reference_cases = self._fallback_reference_cases(decision_context)
        aggregated_risks = _dedupe_preserve_order(task.portfolio_risks)
        if not aggregated_risks:
            aggregated_risks = ["Current analyst evidence does not yet support a stronger action."]
        portfolio_context_summary = self._fallback_portfolio_context_summary(task)
        portfolio_context_used = bool(task.portfolio_context)
        position_impact = self._fallback_position_impact(task, recommendation=recommendation)
        timing_decision = self._fallback_timing_decision(
            task,
            recommendation=recommendation,
            confidence=confidence,
        )
        action_conditions = self._fallback_action_conditions(
            task,
            recommendation=recommendation,
        )
        no_action_reasons = self._fallback_no_action_reasons(
            task,
            recommendation=recommendation,
            aggregated_risks=aggregated_risks,
        )

        decision_summary = (
            f"Current analyst evidence for {task.subject} supports a {recommendation} stance."
        )
        rationale_parts = [
            f"The decision layer reviewed {len(task.analyst_results)} analyst perspective(s).",
            f"Overall analyst confidence is {confidence}.",
        ]
        if task.key_signals:
            rationale_parts.append(f"Leading signals: {', '.join(task.key_signals[:3])}.")
        if reference_cases:
            rationale_parts.append(
                f"Referenced {len(reference_cases)} decision-memory case(s) as supporting context."
            )
        rationale = " ".join(rationale_parts)

        if reference_cases:
            case_fit_assessment = (
                "Reference cases were used as advisory context only and should not be copied directly."
            )
        else:
            case_fit_assessment = (
                "No matching decision-memory cases were retrieved, so the recommendation relies on "
                "current analyst synthesis only."
            )

        return {
            "subject": task.subject,
            "symbol": task.symbol,
            "trade_date": task.trade_date,
            "decision_summary": decision_summary,
            "recommendation": recommendation,
            "advisory_scope": ADVISORY_SCOPE,
            "portfolio_context_used": portfolio_context_used,
            "portfolio_context_summary": portfolio_context_summary,
            "position_impact": position_impact,
            "timing_decision": timing_decision,
            "action_conditions": action_conditions,
            "no_action_reasons": no_action_reasons,
            "aggregated_risks": aggregated_risks,
            "rationale": rationale,
            "confidence": confidence,
            "reference_cases": reference_cases,
            "case_fit_assessment": case_fit_assessment,
            "prompt": prompt,
            "decision_context": decision_context,
        }

    def normalize_llm_result(
        self,
        llm_result: dict[str, Any],
        *,
        task: DecisionTask,
        decision_context: dict[str, Any],
        prompt: str,
    ) -> dict[str, Any]:
        """Normalize LLM output into the shared decision payload shape."""
        fallback_result = self._synthesize_fallback(task, decision_context, prompt)
        recommendation = str(llm_result.get("recommendation", fallback_result["recommendation"]))
        recommendation = recommendation.strip().lower()
        if recommendation not in ALLOWED_RECOMMENDATIONS:
            recommendation = fallback_result["recommendation"]

        return {
            "subject": task.subject,
            "symbol": task.symbol,
            "trade_date": task.trade_date,
            "decision_summary": str(
                llm_result.get("decision_summary", fallback_result["decision_summary"])
            ).strip()
            or fallback_result["decision_summary"],
            "recommendation": recommendation,
            "advisory_scope": self._normalize_advisory_scope(
                llm_result.get("advisory_scope", fallback_result["advisory_scope"])
            ),
            "portfolio_context_used": self._normalize_bool(
                llm_result.get("portfolio_context_used", fallback_result["portfolio_context_used"])
            ),
            "portfolio_context_summary": str(
                llm_result.get(
                    "portfolio_context_summary",
                    fallback_result["portfolio_context_summary"],
                )
            ).strip()
            or fallback_result["portfolio_context_summary"],
            "position_impact": str(
                llm_result.get("position_impact", fallback_result["position_impact"])
            ).strip()
            or fallback_result["position_impact"],
            "timing_decision": str(
                llm_result.get("timing_decision", fallback_result["timing_decision"])
            ).strip()
            or fallback_result["timing_decision"],
            "action_conditions": self._normalize_string_list(
                llm_result.get("action_conditions"),
                fallback=fallback_result["action_conditions"],
            ),
            "no_action_reasons": self._normalize_string_list(
                llm_result.get("no_action_reasons"),
                fallback=fallback_result["no_action_reasons"],
            ),
            "aggregated_risks": self._normalize_string_list(
                llm_result.get("aggregated_risks"),
                fallback=fallback_result["aggregated_risks"],
            ),
            "rationale": str(llm_result.get("rationale", fallback_result["rationale"])).strip()
            or fallback_result["rationale"],
            "confidence": self._normalize_confidence(
                llm_result.get("confidence", fallback_result["confidence"])
            ),
            "reference_cases": self._normalize_reference_cases(
                llm_result.get("reference_cases"),
                fallback=fallback_result["reference_cases"],
            ),
            "case_fit_assessment": str(
                llm_result.get("case_fit_assessment", fallback_result["case_fit_assessment"])
            ).strip()
            or fallback_result["case_fit_assessment"],
            "prompt": prompt,
            "decision_context": decision_context,
            "raw_model_output": llm_result,
        }

    def decision_output_schema(self) -> dict[str, Any]:
        """Return the target structured schema for decision advisory outputs."""
        return {
            "decision_summary": "string",
            "recommendation": "consider_buy|consider_reduce|hold|keep_watch|no_trade",
            "advisory_scope": "advisory_only",
            "portfolio_context_used": "boolean",
            "portfolio_context_summary": "string",
            "position_impact": "string",
            "timing_decision": "string",
            "action_conditions": ["string"],
            "no_action_reasons": ["string"],
            "aggregated_risks": ["string"],
            "rationale": "string",
            "confidence": "low|medium|high",
            "reference_cases": [
                {
                    "title": "string",
                    "memory_type": "decision_case|decision_postmortem|external_reference_decision",
                    "fit": "high|medium|low",
                    "why_relevant": "string",
                }
            ],
            "case_fit_assessment": "string",
        }

    def build_agent_message(self, result: dict[str, Any]) -> Any:
        """Create a graph-friendly message from the advisory decision payload."""
        content = result.get("decision_summary", "")
        try:
            from langchain_core.messages import AIMessage
        except ModuleNotFoundError:
            return {
                "role": "assistant",
                "name": self.agent_name,
                "content": content,
            }
        return AIMessage(content=content, name=self.agent_name)

    def _fallback_recommendation(self, task: DecisionTask) -> str:
        """Generate a conservative recommendation when no model output is available."""
        if not task.key_signals:
            return "no_trade"
        if self._has_material_conflict(task.cross_analyst_observations):
            return "keep_watch"
        if self._normalize_confidence(task.overall_confidence) == "high":
            return "hold"
        return "keep_watch"

    def _fallback_position_impact(
        self,
        task: DecisionTask,
        *,
        recommendation: str,
    ) -> str:
        """Describe the advisory effect on positioning without implying execution."""
        symbol_or_subject = task.symbol or task.subject
        position = self._find_relevant_position(task)
        current_weight = self._extract_position_weight(position)
        cash_pct = self._extract_numeric_value(
            task.portfolio_context,
            ("cash_pct", "cash_weight_pct", "cash_weight", "cash"),
        )
        max_single_name_pct = self._extract_max_single_name_pct(task.portfolio_context)
        headroom_pct = self._calculate_headroom_pct(
            current_weight=current_weight,
            max_single_name_pct=max_single_name_pct,
        )

        if recommendation == "consider_buy":
            if current_weight is not None:
                detail = (
                    f"If adopted, this would add to the existing {self._format_pct(current_weight)} "
                    f"portfolio weight in {symbol_or_subject}."
                )
                if headroom_pct is not None:
                    detail += (
                        f" Based on the current single-name limit, roughly "
                        f"{self._format_pct(headroom_pct)} of headroom remains."
                    )
                return detail
            detail = f"If adopted, this would initiate new exposure to {symbol_or_subject}."
            if max_single_name_pct is not None:
                detail += (
                    f" A prudent upper bound from the current portfolio context is around "
                    f"{self._format_pct(max_single_name_pct)}."
                )
            if cash_pct is not None:
                detail += f" Available cash currently screens at {self._format_pct(cash_pct)}."
            return detail
        if recommendation == "consider_reduce":
            if current_weight is not None:
                detail = (
                    f"If adopted, this would reduce the current {self._format_pct(current_weight)} "
                    f"portfolio weight in {symbol_or_subject}"
                )
                if max_single_name_pct is not None and current_weight > max_single_name_pct:
                    detail += (
                        f", which is currently above the configured single-name limit of "
                        f"{self._format_pct(max_single_name_pct)}"
                    )
                return detail + "."
            return (
                f"No live position in {symbol_or_subject} was found in the provided portfolio context, "
                "so a reduce recommendation would mainly lower planned rather than current exposure."
            )
        if recommendation == "hold":
            if current_weight is not None:
                return (
                    f"This stance keeps the current {self._format_pct(current_weight)} portfolio weight "
                    f"in {symbol_or_subject} unchanged while monitoring whether the evidence improves or weakens."
                )
            return (
                f"This stance does not imply a new trade in {symbol_or_subject}; it mainly preserves "
                "current exposure while monitoring risk."
            )
        if current_weight is not None:
            return (
                f"This stance does not justify changing the current {self._format_pct(current_weight)} "
                f"portfolio weight in {symbol_or_subject} yet."
            )
        return (
            f"This stance does not justify changing exposure to {symbol_or_subject} yet; "
            "current positioning impact is effectively neutral."
        )

    def _fallback_portfolio_context_summary(self, task: DecisionTask) -> str:
        """Summarize the portfolio context available to the decision layer."""
        portfolio_context = task.portfolio_context
        if not isinstance(portfolio_context, dict):
            return "No portfolio context was provided, so positioning impact remains advisory and generic."

        position = self._find_relevant_position(task)
        current_weight = self._extract_position_weight(position)
        cash_pct = self._extract_numeric_value(
            portfolio_context,
            ("cash_pct", "cash_weight_pct", "cash_weight", "cash"),
        )
        max_single_name_pct = self._extract_max_single_name_pct(portfolio_context)
        positions = portfolio_context.get("positions")
        position_count = len(positions) if isinstance(positions, list) else None

        parts: list[str] = []
        if position_count is not None:
            parts.append(f"Portfolio context includes {position_count} tracked position(s).")
        if current_weight is not None and task.symbol:
            parts.append(
                f"The current portfolio weight in {task.symbol} is {self._format_pct(current_weight)}."
            )
        elif task.symbol:
            parts.append(f"No live position in {task.symbol} was found in the supplied portfolio context.")
        if max_single_name_pct is not None:
            parts.append(
                f"The configured single-name limit is {self._format_pct(max_single_name_pct)}."
            )
        if cash_pct is not None:
            parts.append(f"Available cash is approximately {self._format_pct(cash_pct)}.")
        return " ".join(parts) or (
            "Portfolio context was provided, but it did not include readable sizing or limit fields."
        )

    def _fallback_timing_decision(
        self,
        task: DecisionTask,
        *,
        recommendation: str,
        confidence: str,
    ) -> str:
        """Return a bounded timing suggestion for the advisory output."""
        if recommendation in {"no_trade", "keep_watch"}:
            if self._has_material_conflict(task.cross_analyst_observations):
                return "Wait for stronger cross-analyst alignment before considering action."
            return "Wait for clearer confirmation in signals or reduced risk before considering action."
        if recommendation == "hold":
            if confidence == "high":
                return "Maintain the current stance now, but reassess around the next material signal change."
            return "Maintain the current stance for now and reassess as evidence improves."
        if recommendation == "consider_reduce":
            return "Any reduction should be considered around strength rather than after risk has already accelerated."
        return "Any action should be considered gradually and only after confirmation improves."

    def _fallback_action_conditions(
        self,
        task: DecisionTask,
        *,
        recommendation: str,
    ) -> list[str]:
        """List conditions that would strengthen the current advisory stance."""
        if recommendation == "consider_buy":
            return [
                "Cross-analyst conviction strengthens rather than diverges.",
                "The leading constructive signals remain intact without a parallel rise in top risks.",
                "Short-term confirmation improves before any stronger action is considered.",
            ]
        if recommendation == "consider_reduce":
            return [
                "The most important risks continue to intensify or spread across analysts.",
                "Protective action is considered before downside pressure becomes disorderly.",
                "Risk signals deteriorate faster than constructive signals improve.",
            ]
        return [
            "Cross-analyst alignment improves materially.",
            "The highest-priority risks begin to ease or are invalidated.",
            "A clearer confirmation window appears before the stance is upgraded.",
        ]

    def _fallback_no_action_reasons(
        self,
        task: DecisionTask,
        *,
        recommendation: str,
        aggregated_risks: list[str],
    ) -> list[str]:
        """Explain why the advisory layer is not escalating into a stronger action."""
        reasons: list[str] = []
        if recommendation in {"keep_watch", "no_trade"}:
            reasons.append("The current evidence is not strong enough to justify a higher-conviction action.")
        if self._has_material_conflict(task.cross_analyst_observations):
            reasons.append("Analyst perspectives still show material disagreement or uneven conviction.")
        if self._normalize_confidence(task.overall_confidence) == "low":
            reasons.append("Overall analyst confidence is still low.")
        reasons.extend(self._normalize_advisory_risk_reason(risk) for risk in aggregated_risks[:2])
        if not reasons and recommendation == "hold":
            reasons.append("The current evidence supports maintaining stance rather than changing it.")
        return _dedupe_preserve_order(reasons)

    def _normalize_advisory_risk_reason(self, risk: str) -> str:
        """Rewrite low-level risk text into user-facing advisory language when needed."""
        normalized = risk.strip()
        lowered = normalized.lower()
        if "first-pass synthesis pending a model-backed analyst prompt" in lowered:
            return "Some of the current evidence is still preliminary rather than fully model-refined."
        if "tool" in lowered and "failed" in lowered:
            return "Some supporting evidence may be incomplete because at least one tool path was unavailable."
        return normalized

    def _normalize_advisory_scope(self, value: Any) -> str:
        """Keep advisory scope pinned to the supported contract."""
        normalized = str(value or ADVISORY_SCOPE).strip().lower()
        if normalized != ADVISORY_SCOPE:
            return ADVISORY_SCOPE
        return normalized

    def _normalize_bool(self, value: Any) -> bool:
        """Normalize model output into a boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y"}
        return False

    def _find_relevant_position(self, task: DecisionTask) -> dict[str, Any] | None:
        """Return the portfolio position matching the current symbol when available."""
        portfolio_context = task.portfolio_context
        if not isinstance(portfolio_context, dict):
            return None
        positions = portfolio_context.get("positions")
        if not isinstance(positions, list) or not task.symbol:
            return None

        target_symbol = task.symbol.strip().upper()
        for position in positions:
            if not isinstance(position, dict):
                continue
            position_symbol = str(position.get("symbol", "")).strip().upper()
            if position_symbol == target_symbol:
                return position
        return None

    def _extract_position_weight(self, position: dict[str, Any] | None) -> float | None:
        """Extract a normalized position weight percentage from a position record."""
        if not isinstance(position, dict):
            return None
        return self._extract_numeric_value(
            position,
            ("weight_pct", "portfolio_weight_pct", "weight", "portfolio_weight", "exposure_pct"),
        )

    def _extract_max_single_name_pct(
        self,
        portfolio_context: dict[str, Any] | None,
    ) -> float | None:
        """Extract a configured single-name limit percentage from portfolio context."""
        if not isinstance(portfolio_context, dict):
            return None

        direct_limit = self._extract_numeric_value(
            portfolio_context,
            ("max_single_name_pct", "single_name_limit_pct", "max_position_pct"),
        )
        if direct_limit is not None:
            return direct_limit

        limits = portfolio_context.get("position_limits")
        if isinstance(limits, dict):
            return self._extract_numeric_value(
                limits,
                ("max_single_name_pct", "single_name_limit_pct", "max_position_pct"),
            )
        return None

    def _calculate_headroom_pct(
        self,
        *,
        current_weight: float | None,
        max_single_name_pct: float | None,
    ) -> float | None:
        """Calculate remaining single-name headroom in percentage points."""
        if current_weight is None or max_single_name_pct is None:
            return None
        return max(max_single_name_pct - current_weight, 0.0)

    def _extract_numeric_value(
        self,
        payload: dict[str, Any] | None,
        keys: tuple[str, ...],
    ) -> float | None:
        """Extract a numeric percentage-like value from a dictionary."""
        if not isinstance(payload, dict):
            return None

        for key in keys:
            if key not in payload:
                continue
            value = payload.get(key)
            if isinstance(value, bool) or value is None:
                continue
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                normalized = value.strip().rstrip("%")
                try:
                    return float(normalized)
                except ValueError:
                    continue
        return None

    def _format_pct(self, value: float) -> str:
        """Render a percentage-like number for advisory output."""
        formatted = f"{value:.2f}".rstrip("0").rstrip(".")
        return f"{formatted}%"

    def _fallback_reference_cases(
        self,
        decision_context: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Convert retrieved decision-memory documents into compact reference case records."""
        reference_cases: list[dict[str, str]] = []
        for document in decision_context.get("documents", [])[:3]:
            metadata = dict(document.get("metadata", {}))
            reference_cases.append(
                {
                    "title": str(document.get("title", "")).strip() or "Untitled decision case",
                    "memory_type": str(metadata.get("memory_type", "decision_case")).strip()
                    or "decision_case",
                    "fit": "medium",
                    "why_relevant": str(metadata.get("subject", "")).strip()
                    or "Retrieved as a potentially similar decision-memory case.",
                }
            )
        return reference_cases

    def _normalize_string_list(self, value: Any, *, fallback: list[str]) -> list[str]:
        """Normalize a model value into a non-empty list of strings."""
        if isinstance(value, list):
            normalized = [str(item).strip() for item in value if str(item).strip()]
            return normalized or fallback
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return fallback

    def _normalize_reference_cases(
        self,
        value: Any,
        *,
        fallback: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Normalize model output into the reference-case schema."""
        if not isinstance(value, list):
            return fallback

        normalized_cases: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            memory_type = str(item.get("memory_type", "decision_case")).strip() or "decision_case"
            fit = str(item.get("fit", "medium")).strip().lower() or "medium"
            if fit not in {"high", "medium", "low"}:
                fit = "medium"
            why_relevant = (
                str(item.get("why_relevant", "")).strip()
                or "Returned by the decision-memory retrieval layer."
            )
            normalized_cases.append(
                {
                    "title": title,
                    "memory_type": memory_type,
                    "fit": fit,
                    "why_relevant": why_relevant,
                }
            )
        return normalized_cases or fallback

    def _normalize_confidence(self, value: Any) -> str:
        """Normalize confidence labels into the supported set."""
        confidence = str(value or "low").strip().lower()
        if confidence not in ALLOWED_CONFIDENCE:
            return "low"
        return confidence

    def _has_material_conflict(self, observations: list[str]) -> bool:
        """Detect obvious cross-analyst disagreement from observation strings."""
        conflict_markers = ("disagree", "conflict", "mixed", "diverge", "uncertain")
        for observation in observations:
            normalized = observation.lower()
            if any(marker in normalized for marker in conflict_markers):
                return True
        return False
