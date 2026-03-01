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
from collections import Counter
from pathlib import Path
from typing import Any

_COMMON_SRC = Path(__file__).resolve().parents[5] / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths()

import yaml  # noqa: E402
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator  # noqa: E402

from agents.runtime import BaseAgent  # noqa: E402
from llm import LLMGateway  # noqa: E402
from observability.tracing import get_trace_id  # noqa: E402
from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402
from prompt_registry import PromptRegistry, enforce_redaction  # noqa: E402


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
        allowed = {"AUD", "EUR", "GBP", "JPY"}
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
    prompt_version: int | None = None


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

    def __init__(self, agent_id: str = "intent-router-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)
        self.agent_config = self._load_agent_config()
        self.routing_config = self._load_routing_config()
        self.intent_definitions = {intent.name: intent for intent in self.routing_config.intents}
        self.supported_intents = list(self.intent_definitions.keys())
        self.intent_descriptions = {
            intent.name: (intent.description or intent.name.replace("_", " "))
            for intent in self.routing_config.intents
        }
        self.intent_confidence_threshold = self.config.get(
            "intent_confidence_threshold",
            self.routing_config.default_min_confidence,
        )
        self.top_k_intents = int(
            self.config.get("top_k_intents") or self.agent_config.get("top_k_intents") or 2
        )
        self.intent_confidence_thresholds: dict[str, float] = {
            str(intent): float(threshold)
            for intent, threshold in (self.agent_config.get("confidence_thresholds") or {}).items()
        }
        self.classifier_model_name = str(
            self.config.get("classifier_model_name")
            or self.agent_config.get("classifier_model_name")
            or "distilbert-base-uncased"
        )
        self.classifier_model_path = Path(
            self.config.get("classifier_model_path")
            or self.agent_config.get("classifier_model_path")
            or (Path(__file__).resolve().parents[1] / "models" / "intent_classifier")
        )
        self.intent_classifier = self.config.get("intent_classifier")
        self.nlp_model = self.config.get("nlp_model")
        self._entity_patterns = self._build_entity_patterns()
        self._label_prefix_pattern = re.compile(r"^[A-Z_]+\s*:\s*")
        self._currency_aliases = {"$": "AUD", "€": "EUR", "£": "GBP", "¥": "JPY"}
        self._portfolio_pattern = re.compile(r"^PORT(?:FOLIO)?[-_\s]?\d{1,6}$", re.IGNORECASE)
        self._project_pattern = re.compile(
            r"^(?:PROJ|PRJ|PROJECT)?[-_\s]?[A-Z0-9]{2,20}$", re.IGNORECASE
        )
        llm_config = self.config.get("llm_config") or {}
        if (
            not llm_config
            and (self.config.get("llm_provider") or os.getenv("LLM_PROVIDER")) == "mock"
        ):
            mock_response = self._load_mock_response()
            if mock_response is not None:
                llm_config = {"mock_response": mock_response}

        self.llm_client = self.config.get("llm_client") or LLMGateway(
            provider=self.config.get("llm_provider"),
            config=llm_config,
        )
        self.prompt_registry = PromptRegistry()
        self.prompt_text: str | None = None
        self.prompt_version: int | None = None
        self._last_validation_error: dict[str, Any] | None = None
        if self.intent_classifier is None:
            self.intent_classifier = self._load_transformer_classifier()
        if self.nlp_model is None:
            self.nlp_model = self._load_nlp_model()

    async def initialize(self) -> None:
        """Initialize NLP models and routing configuration."""
        await super().initialize()
        self.logger.info("Loading intent classification prompt registry...")
        prompt_record = self.prompt_registry.get_prompt_record("intent-router")
        self.prompt_text = prompt_record.content
        self.prompt_version = prompt_record.version

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

        self.logger.info(
            "Classifying query",
            extra={"query": query, "tenant_id": tenant_id, "correlation_id": correlation_id},
        )

        llm_payload = {
            "request": {"text": query, "context": context},
        }
        if not self.prompt_text:
            raise ValueError("Prompt registry not initialized")
        redacted_payload = enforce_redaction(llm_payload)
        prompt_templates = self._extract_prompt_templates(self.prompt_text)
        system_prompt = self._render_prompt(prompt_templates["system"], redacted_payload)
        user_prompt = self._render_prompt(prompt_templates["user"], redacted_payload)

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
            prompt_version=self.prompt_version,
        )
        return response.model_dump()

    def _extract_prompt_templates(self, prompt_text: str) -> dict[str, str]:
        sections = {"system": "", "user": ""}
        current: str | None = None
        buffer: list[str] = []
        for line in prompt_text.splitlines():
            normalized = line.strip().lower()
            if normalized == "system:":
                current = "system"
                continue
            if normalized == "user:":
                if current:
                    sections[current] = "\n".join(buffer).strip()
                current = "user"
                buffer = []
                continue
            if current:
                buffer.append(line)
        if current:
            sections[current] = "\n".join(buffer).strip()

        if not sections["system"] or not sections["user"]:
            raise ValueError("Prompt file must include System and User sections")
        return sections

    def _load_routing_config(self) -> IntentRoutingConfig:
        config_path = Path(
            self.config.get("routing_config_path")
            or os.getenv("INTENT_ROUTING_CONFIG_PATH")
            or (Path(__file__).resolve().parents[4] / "ops" / "config" / "agents" / "intent-routing.yaml")
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

    def _load_agent_config(self) -> dict[str, Any]:
        config_path = Path(
            self.config.get("agent_config_path")
            or os.getenv("INTENT_ROUTER_AGENT_CONFIG_PATH")
            or (
                Path(__file__).resolve().parents[4]
                / "ops"
                / "config"
                / "agents"
                / "intent-router.yaml"
            )
        )
        try:
            payload = yaml.safe_load(config_path.read_text())
        except OSError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _load_transformer_classifier(self) -> Any:
        if self.config.get("disable_transformers"):
            return None
        try:
            from transformers import pipeline
        except ImportError:
            self.logger.warning("transformers not available; fallback classifier disabled")
            return None
        model_target = str(self.classifier_model_path)
        if not self.classifier_model_path.exists():
            model_target = self.classifier_model_name
        try:
            return pipeline(
                "zero-shot-classification",
                model=model_target,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            self.logger.warning(
                "Unable to initialize transformer classifier", extra={"error": str(exc)}
            )
            return None

    def _load_nlp_model(self) -> Any:
        try:
            import spacy
        except ImportError:
            self.logger.warning("spaCy not available; entity extraction will use regex patterns")
            return None
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            nlp = spacy.blank("en")
        if "entity_ruler" not in nlp.pipe_names:
            ruler = nlp.add_pipe("entity_ruler")
        else:
            ruler = nlp.get_pipe("entity_ruler")
        ruler.add_patterns(self._entity_patterns)
        return nlp

    def _build_entity_patterns(self) -> list[dict[str, Any]]:
        return [
            {"label": "SCHEDULE_FOCUS", "pattern": "critical path"},
            {"label": "SCHEDULE_FOCUS", "pattern": "milestone"},
            {"label": "SCHEDULE_FOCUS", "pattern": "milestones"},
            {"label": "CURRENCY", "pattern": [{"LOWER": {"IN": ["usd", "eur", "gbp", "jpy"]}}]},
            {
                "label": "PROJECT_ID",
                "pattern": [{"LOWER": "project"}, {"IS_ASCII": True, "OP": "+"}],
            },
            {
                "label": "PORTFOLIO_ID",
                "pattern": [{"LOWER": "portfolio"}, {"IS_ASCII": True, "OP": "+"}],
            },
        ]

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
            override_threshold = self.intent_confidence_thresholds.get(intent)
            effective_threshold = max(
                self.intent_confidence_threshold,
                min_confidence,
                override_threshold if override_threshold is not None else 0.0,
            )
            if confidence_value < effective_threshold:
                continue
            normalized.append(
                {
                    "intent": intent,
                    "confidence": round(min(max(confidence_value, 0.0), 1.0), 2),
                }
            )
        normalized.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)
        return normalized[: self.top_k_intents]

    # Keyword patterns for intent detection when no NLP model is available.
    _INTENT_KEYWORDS: dict[str, list[str]] = {
        "portfolio_query": ["portfolio", "programme", "program", "roadmap", "overview", "status", "health"],
        "financial_query": ["budget", "financial", "finance", "cost", "spend", "variance", "roi", "profit", "expenditure", "forecast revenue"],
        "schedule_query": ["schedule", "timeline", "milestone", "deadline", "gantt", "critical path", "delay", "due date"],
        "risk_query": ["risk", "issue", "threat", "vulnerability", "mitigation", "register", "hazard"],
        "resource_query": ["resource", "capacity", "utilization", "allocation", "headcount", "team", "staffing"],
        "compliance_query": ["compliance", "regulatory", "regulation", "hipaa", "audit", "gdpr", "policy", "governance"],
    }

    def _keyword_classify_intent(self, query: str) -> list[dict[str, Any]]:
        """Classify intent from keywords when no transformer model is available."""
        lowered = query.lower()
        scored: list[dict[str, Any]] = []
        for intent, keywords in self._INTENT_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in lowered)
            if hits:
                confidence = min(0.5 + hits * 0.1, 0.95)
                scored.append({"intent": intent, "confidence": round(confidence, 2)})
        if scored:
            scored.sort(key=lambda x: x["confidence"], reverse=True)
            return scored[: self.top_k_intents]
        fallback_intent = self.routing_config.fallback_intent
        return [{"intent": fallback_intent, "confidence": 0.5}]

    async def _classify_intent(self, query: str) -> list[dict[str, Any]]:
        """
        Classify user intent using NLP models.

        Returns list of intents with confidence scores.
        """
        if self.intent_classifier is None:
            # Use keyword-based matching when no transformer model is available.
            return self._keyword_classify_intent(query)

        try:
            classification = self.intent_classifier(
                query,
                candidate_labels=self.supported_intents,
                hypothesis_template="This request is about {}.",
                multi_label=True,
            )
        except (ValueError, RuntimeError, TypeError, KeyError) as exc:
            self.logger.warning("Transformer classification failed", extra={"error": str(exc)})
            fallback_intent = self.routing_config.fallback_intent
            return [{"intent": fallback_intent, "confidence": 0.5}]

        labels = classification.get("labels", [])
        scores = classification.get("scores", [])
        predictions = [
            IntentPrediction(intent=str(label), confidence=float(score))
            for label, score in zip(labels, scores)
        ]
        normalized = self._normalize_intents(predictions)
        if normalized:
            return normalized
        fallback_intent = self.routing_config.fallback_intent
        return [{"intent": fallback_intent, "confidence": 0.5}]

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

        if self.nlp_model is not None:
            doc = self.nlp_model(query)
            for ent in doc.ents:
                cleaned = self._clean_entity_value(ent.text)
                if ent.label_ == "PROJECT_ID" and cleaned:
                    parameters["project_id"] = self._normalize_project_id(cleaned)
                    parameters["entity_type"] = "project"
                elif ent.label_ == "PORTFOLIO_ID" and cleaned:
                    parameters["portfolio_id"] = self._normalize_portfolio_id(cleaned)
                    parameters["entity_type"] = "portfolio"
                elif ent.label_ == "CURRENCY" and cleaned:
                    parameters["currency"] = cleaned.upper()
                elif ent.label_ == "SCHEDULE_FOCUS":
                    parameters["schedule_focus"] = (
                        "critical_path" if "critical" in cleaned.lower() else "milestones"
                    )

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

        amount_pattern = re.compile(
            r"(?:(?P<symbol>[\$€£¥])\s*)?(?P<value>\d+(?:\.\d+)?)\s?(?P<suffix>k|m)?\b"
        )
        for amount_match in amount_pattern.finditer(query_lower):
            context_window = query_lower[
                max(0, amount_match.start() - 12) : amount_match.end() + 12
            ]
            if not (
                amount_match.group("symbol")
                or amount_match.group("suffix")
                or re.search(r"\b(usd|eur|gbp|jpy|budget|cost|amount|forecast)\b", context_window)
            ):
                continue
            amount = float(amount_match.group("value"))
            suffix = amount_match.group("suffix")
            if suffix == "k":
                amount *= 1_000
            elif suffix == "m":
                amount *= 1_000_000
            parameters["amount"] = amount
            break

        if "currency" not in parameters:
            symbol_counter = Counter(char for char in query if char in self._currency_aliases)
            if symbol_counter:
                symbol = symbol_counter.most_common(1)[0][0]
                parameters["currency"] = self._currency_aliases[symbol]

        if "critical path" in query_lower:
            parameters["schedule_focus"] = "critical_path"
        elif "milestone" in query_lower:
            parameters["schedule_focus"] = "milestones"

        try:
            return ExtractedParameters.model_validate(parameters).model_dump(exclude_none=True)
        except ValidationError:
            return parameters

    def _clean_entity_value(self, value: str) -> str:
        cleaned = value.strip().strip(".,:;()[]{}")
        return self._label_prefix_pattern.sub("", cleaned).strip()

    def _normalize_project_id(self, value: str) -> str:
        token = value.replace(" ", "-").upper()
        if token.startswith("PROJECT-"):
            token = token.removeprefix("PROJECT-")
        return token

    def _normalize_portfolio_id(self, value: str) -> str:
        token = value.replace(" ", "-").upper()
        if token.startswith("PORTFOLIO-"):
            token = token.removeprefix("PORTFOLIO-")
        return token

    def get_capabilities(self) -> list[str]:
        """Return list of capabilities."""
        return [
            "intent_classification",
            "query_disambiguation",
            "multi_intent_detection",
            "agent_routing",
            "parameter_extraction",
        ]
