"""
Agent 1: Intent Router Agent

Purpose:
The Intent Router Agent classifies user queries and determines which domain agents
should handle the request.

Specification: agents/core-orchestration/agent-01-intent-router/README.md
"""

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

    async def initialize(self) -> None:
        """Initialize NLP models and routing configuration."""
        await super().initialize()
        self.logger.info("Loading intent classification models...")
        # TODO: Load Azure OpenAI or other NLP models
        # TODO: Load routing configuration

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

        # TODO: Implement actual NLP classification using Azure OpenAI
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
        # TODO: Implement Azure OpenAI classification
        # Placeholder implementation
        query_lower = query.lower()

        intents = []

        if any(word in query_lower for word in ["portfolio", "program", "initiative"]):
            intents.append({"intent": "portfolio_query", "confidence": 0.9})

        if any(word in query_lower for word in ["schedule", "timeline", "deadline"]):
            intents.append({"intent": "schedule_query", "confidence": 0.85})

        if any(word in query_lower for word in ["budget", "cost", "financial"]):
            intents.append({"intent": "financial_query", "confidence": 0.88})

        if any(word in query_lower for word in ["risk", "issue", "problem"]):
            intents.append({"intent": "risk_query", "confidence": 0.87})

        if not intents:
            intents.append({"intent": "general_query", "confidence": 0.5})

        return intents

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
        # TODO: Implement NER (Named Entity Recognition) using Azure OpenAI
        # Placeholder implementation
        parameters = {}

        # Simple keyword extraction
        query_lower = query.lower()

        if "project" in query_lower:
            # Extract project name/ID if present
            # TODO: Implement actual entity extraction
            parameters["entity_type"] = "project"

        if "portfolio" in query_lower:
            parameters["entity_type"] = "portfolio"

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
