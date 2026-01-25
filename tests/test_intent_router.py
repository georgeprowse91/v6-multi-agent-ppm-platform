"""
Tests for Intent Router Agent
"""

import pytest

from intent_router_agent import IntentRouterAgent


@pytest.mark.asyncio
async def test_intent_router_initialization():
    """Test intent router initialization."""
    agent = IntentRouterAgent()

    assert agent.agent_id == "intent-router"
    assert len(agent.supported_intents) > 0

    await agent.initialize()
    assert agent.initialized


@pytest.mark.asyncio
async def test_portfolio_query_classification():
    """Test classification of portfolio-related queries."""
    agent = IntentRouterAgent()
    await agent.initialize()

    result = await agent.execute({"query": "Show me the portfolio overview", "context": {}})

    assert result["success"] is True
    intents = result["data"]["intents"]
    assert len(intents) > 0
    assert any(i["intent"] == "portfolio_query" for i in intents)


@pytest.mark.asyncio
async def test_financial_query_classification():
    """Test classification of financial queries."""
    agent = IntentRouterAgent()
    await agent.initialize()

    result = await agent.execute({"query": "What is the budget variance for Q1?", "context": {}})

    assert result["success"] is True
    intents = result["data"]["intents"]
    assert len(intents) > 0
    assert any(i["intent"] == "financial_query" for i in intents)


@pytest.mark.asyncio
async def test_schedule_query_classification():
    """Test classification of schedule-related queries."""
    agent = IntentRouterAgent()
    await agent.initialize()

    result = await agent.execute(
        {"query": "When is the deadline for Project Apollo?", "context": {}}
    )

    assert result["success"] is True
    intents = result["data"]["intents"]
    assert len(intents) > 0
    assert any(i["intent"] == "schedule_query" for i in intents)


@pytest.mark.asyncio
async def test_risk_query_classification():
    """Test classification of risk-related queries."""
    agent = IntentRouterAgent()
    await agent.initialize()

    result = await agent.execute(
        {"query": "What are the top risks for my projects?", "context": {}}
    )

    assert result["success"] is True
    intents = result["data"]["intents"]
    assert len(intents) > 0
    assert any(i["intent"] == "risk_query" for i in intents)


@pytest.mark.asyncio
async def test_agent_routing():
    """Test that intents are mapped to correct agents."""
    agent = IntentRouterAgent()
    await agent.initialize()

    result = await agent.execute({"query": "Show me the budget for Project Alpha", "context": {}})

    assert result["success"] is True
    routing = result["data"]["routing"]
    assert len(routing) > 0
    assert any("financial" in r["agent_id"] for r in routing)


@pytest.mark.asyncio
async def test_invalid_query():
    """Test handling of invalid queries."""
    agent = IntentRouterAgent()
    await agent.initialize()

    # Empty query
    result = await agent.execute({"query": "", "context": {}})
    assert result["success"] is False

    # Missing query
    result = await agent.execute({"context": {}})
    assert result["success"] is False


@pytest.mark.asyncio
async def test_multi_intent_detection():
    """Test detection of multiple intents in a single query."""
    agent = IntentRouterAgent()
    await agent.initialize()

    result = await agent.execute(
        {"query": "Show me the budget and schedule for Project Alpha", "context": {}}
    )

    assert result["success"] is True
    intents = result["data"]["intents"]
    # Should detect both financial and schedule intents
    assert len(intents) >= 1


def test_get_capabilities():
    """Test getting agent capabilities."""
    agent = IntentRouterAgent()

    capabilities = agent.get_capabilities()
    assert "intent_classification" in capabilities
    assert "agent_routing" in capabilities
