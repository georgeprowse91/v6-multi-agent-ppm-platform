"""
Agent 1: Intent Router Agent

Purpose:
The Intent Router Agent classifies user queries and determines which domain agents
should handle the request.

Specification: agents/core-orchestration/agent-01-intent-router/README.md
"""

import json
import re
import sys
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from agents.runtime import BaseAgent

LLM_ROOT = Path(__file__).resolve().parents[5] / "packages" / "llm" / "src"
if str(LLM_ROOT) not in sys.path:
    sys.path.insert(0, str(LLM_ROOT))

PROMPT_ROOT = Path(__file__).resolve().parents[3] / "runtime" / "prompts"
if str(PROMPT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROMPT_ROOT))

from llm import LLMClient  # noqa: E402
from prompt_registry import enforce_redaction, load_prompt_by_agent  # noqa: E402

from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402
from observability.tracing import get_trace_id  # noqa: E402


class IntentRouterAgent(BaseAgent):
    """
    Intent Router Agent - Routes user queries to appropriate domain agents.

    Key Capabilities:
    - NLP-based intent classification
    - Query disambiguation
    - Multi-intent detection
    - Agent routing and prioritization
    """

    def __init__(self, agent_id: str = "intent-router", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)
        self.supported_intents = [
            "portfolio_query",
            "project_create",
            "schedule_query",
            "financial_query",
            "risk_query",
            "resource_query",
            "demand_intake",
            "compliance_query",
            "analytics_query",
            "general_query",
        ]
        self.intent_signals = {
            "portfolio_query": ["portfolio", "program", "initiative", "portfolio health"],
            "project_create": ["create project", "start project", "new project", "project charter"],
            "schedule_query": ["schedule", "timeline", "deadline", "critical path", "milestone"],
            "financial_query": ["budget", "cost", "financial", "npv", "irr", "roi", "forecast"],
            "risk_query": ["risk", "risks", "issue", "mitigation", "risk register"],
            "resource_query": ["resource", "capacity", "staffing", "utilization", "allocation"],
            "demand_intake": ["demand", "intake", "request", "idea", "proposal"],
            "compliance_query": ["compliance", "regulatory", "audit", "policy"],
            "analytics_query": ["analytics", "insights", "report", "dashboard", "kpi"],
        }
        self.stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "for",
            "of",
            "in",
            "on",
            "with",
            "me",
            "show",
            "get",
            "please",
        }
        self.intent_confidence_threshold = self.config.get("intent_confidence_threshold", 0.6)
        self.llm_client = self.config.get("llm_client") or LLMClient(
            provider=self.config.get("llm_provider"),
            config=self.config.get("llm_config"),
        )
        self.prompt: dict[str, Any] | None = None

    async def initialize(self) -> None:
        """Initialize NLP models and routing configuration."""
        await super().initialize()
        self.logger.info("Loading intent classification prompt registry...")
        self.prompt = load_prompt_by_agent("intent-router", "intent-routing")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate that query is present and valid."""
        if "query" not in input_data:
            return False
        if not isinstance(input_data["query"], str):
            return False
        if len(input_data["query"].strip()) == 0:
            return False
        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Classify intent and route to appropriate agents.

        Args:
            input_data: {
                "query": "User's natural language query",
                "context": Optional context (user_id, session_id, etc.)
            }

        Returns:
            {
                "intents": List of detected intents with confidence scores,
                "routing": List of agents to invoke,
                "parameters": Extracted parameters for downstream agents
            }
        """
        query = input_data["query"]
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        self.logger.info(f"Classifying query: {query}")

        llm_payload = {
            "request": {"text": query, "context": context},
        }
        if not self.prompt:
            raise ValueError("Prompt registry not initialized")
        redacted_payload = enforce_redaction(self.prompt, llm_payload)
        system_prompt = self._render_prompt(self.prompt["prompt"]["system"], redacted_payload)
        user_prompt = self._render_prompt(self.prompt["prompt"]["user"], redacted_payload)

        llm_response = await self.llm_client.complete(system_prompt, user_prompt)
        llm_data = self._parse_llm_response(llm_response.content)
        intents = self._normalize_intents(llm_data.get("intents", []))
        parameters = llm_data.get("parameters") or {}
        agents = await self._determine_agents(intents, llm_data.get("dependencies"))

        audit_event = build_audit_event(
            tenant_id=tenant_id,
            action="intent.classified",
            outcome="success",
            actor_id=self.agent_id,
            actor_type="service",
            actor_roles=[],
            resource_id=query[:64] or "query",
            resource_type="intent_classification",
            metadata={
                "intents": intents,
                "routing": agents,
                "parameters": parameters,
            },
            trace_id=get_trace_id(),
            correlation_id=correlation_id,
        )
        emit_audit_event(audit_event)

        return {
            "intents": intents,
            "routing": agents,
            "parameters": parameters,
            "query": query,
            "context": context,
        }

    def _render_prompt(self, template: str, payload: dict[str, Any]) -> str:
        def _resolve(path: str) -> Any:
            current: Any = payload
            for part in path.split("."):
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return ""
            return current

        def _replace(match: re.Match[str]) -> str:
            value = _resolve(match.group(1).strip())
            if value is None:
                return ""
            if isinstance(value, (dict, list)):
                return json.dumps(value)
            return str(value)

        return re.sub(r"{{\\s*([\\w\\.]+)\\s*}}", _replace, template)

    def _parse_llm_response(self, content: str) -> dict[str, Any]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            self.logger.error("Failed to parse LLM response", extra={"content": content})
            raise ValueError("Invalid LLM response payload") from exc
        if not isinstance(data, dict):
            raise ValueError("LLM response must be a JSON object")
        return data

    def _normalize_intents(self, intents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for entry in intents:
            intent = str(entry.get("intent", "general_query"))
            confidence = entry.get("confidence", 0.0)
            if intent not in self.supported_intents:
                intent = "general_query"
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                confidence_value = 0.0
            if confidence_value < self.intent_confidence_threshold:
                continue
            normalized.append(
                {
                    "intent": intent,
                    "confidence": round(min(max(confidence_value, 0.0), 1.0), 2),
                }
            )
        if not normalized:
            normalized = [{"intent": "general_query", "confidence": 0.5}]

        normalized.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)
        return normalized

    async def _classify_intent(self, query: str) -> list[dict[str, Any]]:
        """
        Classify user intent using NLP models.

        Returns list of intents with confidence scores.
        """
        query_lower = query.lower()
        tokens = [token for token in re.findall(r"[a-z0-9']+", query_lower) if token]
        filtered_tokens = [token for token in tokens if token not in self.stopwords]
        token_counts = Counter(filtered_tokens)

        intents: list[dict[str, Any]] = []
        max_score = 0.0

        for intent, signals in self.intent_signals.items():
            score = 0.0
            for signal in signals:
                if " " in signal:
                    if signal in query_lower:
                        score += 1.5
                else:
                    score += min(1.0, token_counts.get(signal, 0))

            if score > 0:
                max_score = max(max_score, score)
                intents.append({"intent": intent, "raw_score": score})

        if not intents:
            return [{"intent": "general_query", "confidence": 0.5}]

        normalized_intents = []
        for intent_entry in intents:
            raw_score = float(intent_entry.get("raw_score", 0))
            confidence = 0.55 + (raw_score / max_score) * 0.4
            normalized_intents.append(
                {
                    "intent": str(intent_entry.get("intent", "general_query")),
                    "confidence": round(min(confidence, 0.98), 2),
                }
            )

        def _confidence_key(item: dict[str, Any]) -> float:
            confidence = item.get("confidence")
            return float(confidence) if confidence is not None else 0.0

        normalized_intents.sort(key=_confidence_key, reverse=True)
        return normalized_intents

    async def _determine_agents(
        self, intents: list[dict[str, Any]], dependencies: dict[str, list[str]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Map intents to specific agents that should handle the request.

        Returns list of agents with execution order.
        """
        agent_mapping = {
            "portfolio_query": ["portfolio-strategy-agent"],
            "schedule_query": ["schedule-planning-agent"],
            "financial_query": ["financial-management-agent"],
            "risk_query": ["risk-management-agent"],
            "resource_query": ["resource-capacity-agent"],
            "analytics_query": ["analytics-insights-agent"],
        }

        agents = []
        for intent in intents:
            intent_type = intent["intent"]
            if intent_type in agent_mapping:
                for agent_id in agent_mapping[intent_type]:
                    depends_on = []
                    if dependencies and agent_id in dependencies:
                        depends_on = list(dependencies.get(agent_id, []))
                    agents.append(
                        {
                            "agent_id": agent_id,
                            "priority": intent["confidence"],
                            "intent": intent_type,
                            "depends_on": depends_on,
                        }
                    )

        # Sort by priority (confidence)
        agents.sort(key=lambda x: x["priority"], reverse=True)

        return agents

    async def _extract_parameters(
        self, query: str, intents: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Extract parameters from the query for downstream agents.

        Returns dictionary of extracted parameters.
        """
        parameters: dict[str, Any] = {}
        query_lower = query.lower()

        project_match = re.search(r"project\s+([a-z0-9_-]+)", query_lower)
        if project_match:
            parameters["project_id"] = project_match.group(1).upper()
            parameters["entity_type"] = "project"

        portfolio_match = re.search(r"portfolio\s+([a-z0-9_-]+)", query_lower)
        if portfolio_match:
            parameters["portfolio_id"] = portfolio_match.group(1).upper()
            parameters["entity_type"] = "portfolio"

        currency_match = re.search(r"\b(usd|eur|gbp|jpy)\b", query_lower)
        if currency_match:
            parameters["currency"] = currency_match.group(1).upper()

        amount_match = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s?(k|m)?", query_lower)
        if amount_match:
            amount = float(amount_match.group(1))
            suffix = amount_match.group(2)
            if suffix == "k":
                amount *= 1_000
            elif suffix == "m":
                amount *= 1_000_000
            parameters["amount"] = amount

        if any(intent["intent"] == "schedule_query" for intent in intents):
            if "critical path" in query_lower:
                parameters["schedule_focus"] = "critical_path"
            if "milestone" in query_lower:
                parameters["schedule_focus"] = "milestones"

        return parameters

    def get_capabilities(self) -> list[str]:
        """Return list of capabilities."""
        return [
            "intent_classification",
            "query_disambiguation",
            "multi_intent_detection",
            "agent_routing",
            "parameter_extraction",
        ]
