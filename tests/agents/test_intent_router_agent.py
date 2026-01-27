import pytest
from intent_router_agent import IntentRouterAgent


@pytest.mark.asyncio
async def test_intent_router_classifies_multi_intent():
    agent = IntentRouterAgent(
        config={
            "llm_provider": "mock",
            "llm_config": {
                "mock_response": {
                    "intents": [
                        {"intent": "portfolio_query", "confidence": 0.9},
                        {"intent": "financial_query", "confidence": 0.8},
                        {"intent": "risk_query", "confidence": 0.7},
                    ],
                    "parameters": {"project_id": "APOLLO"},
                }
            },
        }
    )
    await agent.initialize()

    result = await agent.process({"query": "Show portfolio budget and risk for Project Apollo"})
    intents = result["intents"]

    intent_names = [intent["intent"] for intent in intents]
    assert "portfolio_query" in intent_names
    assert "financial_query" in intent_names
    assert "risk_query" in intent_names
    assert intents[0]["confidence"] >= intents[-1]["confidence"]
    assert result["parameters"]["project_id"] == "APOLLO"


@pytest.mark.asyncio
async def test_intent_router_extracts_structured_parameters():
    agent = IntentRouterAgent(
        config={
            "llm_provider": "mock",
            "llm_config": {
                "mock_response": {"intents": [{"intent": "financial_query", "confidence": 0.8}]}
            },
        }
    )
    await agent.initialize()

    result = await agent.process({"query": "Budget for project Apollo is $5m in USD"})

    assert result["parameters"]["project_id"] == "APOLLO"
    assert result["parameters"]["currency"] == "USD"
    assert result["parameters"]["amount"] == 5_000_000


@pytest.mark.asyncio
async def test_intent_router_rejects_missing_query():
    agent = IntentRouterAgent()
    await agent.initialize()

    valid = await agent.validate_input({"context": {"tenant_id": "tenant-a"}})

    assert valid is False


@pytest.mark.asyncio
async def test_intent_router_invalid_llm_response_raises():
    agent = IntentRouterAgent(
        config={
            "llm_provider": "mock",
            "llm_config": {"mock_response": "not-json"},
        }
    )
    await agent.initialize()

    with pytest.raises(ValueError):
        await agent.process({"query": "show portfolio"})
