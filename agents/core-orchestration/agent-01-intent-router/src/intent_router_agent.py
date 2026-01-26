"""
Agent 1: Intent Router Agent

Purpose:
The Intent Router Agent classifies user queries and determines which domain agents
should handle the request.

Specification: agents/core-orchestration/agent-01-intent-router/README.md
"""

import re
from collections import Counter
from typing import Any

from agents.runtime import BaseAgent


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

    async def initialize(self) -> None:
        """Initialize NLP models and routing configuration."""
        await super().initialize()
        self.logger.info("Loading intent classification models...")
        # Future work: Load Azure OpenAI or other NLP models
        # Future work: Load routing configuration

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

        self.logger.info(f"Classifying query: {query}")

        # Future work: Implement actual NLP classification using Azure OpenAI
        # For now, return a mock response
        intent = await self._classify_intent(query)
        agents = await self._determine_agents(intent)
        parameters = await self._extract_parameters(query, intent)

        return {
            "intents": intent,
            "routing": agents,
            "parameters": parameters,
            "query": query,
            "context": context,
        }

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

    async def _determine_agents(self, intents: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                    agents.append(
                        {
                            "agent_id": agent_id,
                            "priority": intent["confidence"],
                            "intent": intent_type,
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
