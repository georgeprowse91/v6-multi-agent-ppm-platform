import pytest

from intent_router_agent import IntentRouterAgent


@pytest.mark.asyncio
async def test_intent_router_classifies_multi_intent():
    agent = IntentRouterAgent()
    await agent.initialize()

    result = await agent.process({"query": "Show portfolio budget and risk for Project Apollo"})
    intents = result["intents"]

    intent_names = [intent["intent"] for intent in intents]
    assert "portfolio_query" in intent_names
    assert "financial_query" in intent_names
    assert "risk_query" in intent_names
    assert intents[0]["confidence"] >= intents[-1]["confidence"]
    assert result["parameters"]["project_id"] == "APOLLO"
