"""
Agent 1: Intent Router Agent

Purpose:
The Intent Router Agent classifies user queries and determines which domain agents
should handle the request.

Specification: agents/core-orchestration/agent-01-intent-router/README.md
"""

import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from agents.runtime import BaseAgent

LLM_ROOT = Path(__file__).resolve().parents[5] / "packages" / "llm" / "src"
if str(LLM_ROOT) not in sys.path:
    sys.path.insert(0, str(LLM_ROOT))

PROMPT_ROOT = Path(__file__).resolve().parents[3] / "runtime" / "prompts"
if str(PROMPT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROMPT_ROOT))

from llm import LLMClient  # noqa: E402
from observability.tracing import get_trace_id  # noqa: E402
from prompt_registry import enforce_redaction, load_prompt_by_agent  # noqa: E402

from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402


class IntentRouterContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    tenant_id: str | None = None
    correlation_id: str | None = None


class IntentRouterRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    query: str = Field(..., min_length=1)
    context: dict[str, Any] | None = None

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must not be empty")
        return cleaned


class IntentPrediction(BaseModel):
    intent: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class IntentRouterLLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intents: list[IntentPrediction] = Field(..., min_length=1)
    parameters: dict[str, Any] | None = None
    dependencies: dict[str, list[str]] | None = None


class IntentRouteConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    action: str | None = None
    dependencies: list[str] = Field(default_factory=list)


class IntentDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    routes: list[IntentRouteConfig] = Field(default_factory=list)
    description: str | None = None


class IntentRoutingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    intents: list[IntentDefinition]
    fallback_intent: str = "general_query"
    default_min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class ExtractedParameters(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_id: str | None = None
    portfolio_id: str | None = None
    currency: str | None = None
    amount: float | None = Field(default=None, ge=0.0)
    entity_type: str | None = None
    schedule_focus: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        currency = value.upper()
        allowed = {"USD", "EUR", "GBP", "JPY"}
        if currency not in allowed:
            raise ValueError("Unsupported currency")
        return currency


class RoutingDecision(BaseModel):
    agent_id: str
    priority: float = Field(..., ge=0.0, le=1.0)
    intent: str
    depends_on: list[str] = Field(default_factory=list)
    action: str | None = None


class IntentRouterResponse(BaseModel):
    intents: list[IntentPrediction]
    routing: list[RoutingDecision]
    parameters: dict[str, Any]
    query: str
    context: dict[str, Any]


class ValidationErrorPayload(BaseModel):
    error: str
    details: list[dict[str, Any]]


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
        self.routing_config = self._load_routing_config()
        self.intent_definitions = {intent.name: intent for intent in self.routing_config.intents}
        self.supported_intents = list(self.intent_definitions.keys())
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
        self.intent_confidence_threshold = self.config.get(
            "intent_confidence_threshold",
            self.routing_config.default_min_confidence,
        )
        llm_config = self.config.get("llm_config") or {}
        if (
            not llm_config
            and (self.config.get("llm_provider") or os.getenv("LLM_PROVIDER")) == "mock"
        ):
            mock_response = self._load_mock_response()
            if mock_response is not None:
                llm_config = {"mock_response": mock_response}

        self.llm_client = self.config.get("llm_client") or LLMClient(
            provider=self.config.get("llm_provider"),
            config=llm_config,
        )
        self.prompt: dict[str, Any] | None = None
        self._last_validation_error: dict[str, Any] | None = None

    async def initialize(self) -> None:
        """Initialize NLP models and routing configuration."""
        await super().initialize()
        self.logger.info("Loading intent classification prompt registry...")
        self.prompt = load_prompt_by_agent("intent-router", "intent-routing")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate that query is present and valid."""
        try:
            IntentRouterRequest.model_validate(input_data)
        except ValidationError as exc:
            self._last_validation_error = ValidationErrorPayload(
                error="validation_error", details=exc.errors()
            ).model_dump()
            return False
        self._last_validation_error = None
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
        request = IntentRouterRequest.model_validate(input_data)
        query = request.query
        context = request.context or {}
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

        fallback_reason: str | None = None
        fallback_used = False

        llm_response = await self.llm_client.complete(system_prompt, user_prompt)
        llm_data: IntentRouterLLMResponse | None = None
        try:
            llm_data = self._parse_llm_response(llm_response.content)
            intents = self._normalize_intents(llm_data.intents)
            if not intents:
                fallback_reason = "llm_low_confidence"
        except ValueError as exc:
            fallback_reason = "llm_parse_error"
            self.logger.warning(
                "LLM response invalid, using fallback classifier",
                extra={"error": str(exc)},
            )

        if fallback_reason:
            fallback_used = True
            intents = await self._classify_intent(query)
            parameters: dict[str, Any] = {}
            dependencies = None
        else:
            parameters = llm_data.parameters or {}
            dependencies = llm_data.dependencies

        if not parameters:
            parameters = await self._extract_parameters(query, intents)
        agents = await self._determine_agents(intents, dependencies)

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
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason,
            },
            trace_id=get_trace_id(),
            correlation_id=correlation_id,
        )
        emit_audit_event(audit_event)
        if fallback_used:
            fallback_audit = build_audit_event(
                tenant_id=tenant_id,
                action="intent.fallback",
                outcome="success",
                actor_id=self.agent_id,
                actor_type="service",
                actor_roles=[],
                resource_id=query[:64] or "query",
                resource_type="intent_classification",
                metadata={
                    "fallback_reason": fallback_reason,
                    "intents": intents,
                },
                trace_id=get_trace_id(),
                correlation_id=correlation_id,
            )
            emit_audit_event(fallback_audit)

        response = IntentRouterResponse(
            intents=[IntentPrediction(**intent) for intent in intents],
            routing=[RoutingDecision(**agent) for agent in agents],
            parameters=parameters,
            query=query,
            context=context,
        )
        return response.model_dump()

    def _load_routing_config(self) -> IntentRoutingConfig:
        config_path = Path(
            self.config.get("routing_config_path")
            or os.getenv("INTENT_ROUTING_CONFIG_PATH")
            or (Path(__file__).resolve().parents[4] / "config" / "agents" / "intent-routing.yaml")
        )
        try:
            payload = yaml.safe_load(config_path.read_text())
        except OSError as exc:
            raise ValueError(f"Unable to read routing config at {config_path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Routing config must be a YAML mapping: {config_path}")
        try:
            return IntentRoutingConfig.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"Routing config invalid: {config_path}") from exc

    def _load_mock_response(self) -> dict[str, Any] | None:
        mock_path = os.getenv("LLM_MOCK_RESPONSE_PATH")
        if mock_path:
            try:
                return json.loads(Path(mock_path).read_text())
            except (OSError, json.JSONDecodeError) as exc:
                self.logger.warning("Failed to load LLM mock response", extra={"error": str(exc)})
        mock_raw = os.getenv("LLM_MOCK_RESPONSE")
        if mock_raw:
            try:
                return json.loads(mock_raw)
            except json.JSONDecodeError as exc:
                self.logger.warning("Failed to parse LLM mock response", extra={"error": str(exc)})
        return None

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

    def _parse_llm_response(self, content: str) -> IntentRouterLLMResponse:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            self.logger.error("Failed to parse LLM response", extra={"content": content})
            raise ValueError("Invalid LLM response payload") from exc
        if not isinstance(data, dict):
            raise ValueError("LLM response must be a JSON object")
        try:
            return IntentRouterLLMResponse.model_validate(data)
        except ValidationError as exc:
            raise ValueError("LLM response schema invalid") from exc

    def _normalize_intents(self, intents: list[IntentPrediction]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for entry in intents:
            intent = str(entry.intent or "general_query")
            confidence = entry.confidence
            if intent not in self.supported_intents:
                continue
            intent_config = self.intent_definitions.get(intent)
            min_confidence = (
                intent_config.min_confidence if intent_config else self.intent_confidence_threshold
            )
            confidence_value = float(confidence)
            if confidence_value < max(self.intent_confidence_threshold, min_confidence):
                continue
            normalized.append(
                {
                    "intent": intent,
                    "confidence": round(min(max(confidence_value, 0.0), 1.0), 2),
                }
            )
        normalized.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)
        return normalized

    async def _classify_intent(self, query: str) -> list[dict[str, Any]]:
        """
        Classify user intent using NLP models.

        Returns list of intents with confidence scores.
        """
        query_lower = query.lower()
        tokens = [token for token in re.findall(r"[a-z0-9']+", query_lower) if token]
        filtered_tokens = {token for token in tokens if token not in self.stopwords}

        intents: list[dict[str, Any]] = []
        max_score = 0.0

        for intent, signals in self.intent_signals.items():
            if intent not in self.supported_intents:
                continue
            score = 0.0
            for signal in signals:
                if " " in signal:
                    if signal in query_lower:
                        score += 2.0
                else:
                    if signal in filtered_tokens:
                        score += 1.0

            if score > 0:
                max_score = max(max_score, score)
                intents.append({"intent": intent, "raw_score": score})

        if not intents:
            fallback_intent = self.routing_config.fallback_intent
            return [{"intent": fallback_intent, "confidence": 0.5}]

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
        agents = []
        for intent in intents:
            intent_type = intent["intent"]
            intent_config = self.intent_definitions.get(intent_type)
            if not intent_config:
                continue
            for route in intent_config.routes:
                depends_on = list(route.dependencies)
                if dependencies and route.agent_id in dependencies:
                    depends_on.extend(dependencies.get(route.agent_id, []))
                agents.append(
                    {
                        "agent_id": route.agent_id,
                        "priority": intent["confidence"],
                        "intent": intent_type,
                        "depends_on": sorted(set(depends_on)),
                        "action": route.action,
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

        try:
            return ExtractedParameters.model_validate(parameters).model_dump(exclude_none=True)
        except ValidationError:
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
