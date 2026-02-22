import pytest
from intent_router_agent import IntentRouterAgent


class DummyTransformer:
    def __call__(self, *_args, **_kwargs):
        return {
            "labels": ["financial_query", "risk_query", "portfolio_query"],
            "scores": [0.91, 0.79, 0.22],
        }


@pytest.mark.asyncio
async def test_intent_router_multi_intent_top_two_predictions() -> None:
    agent = IntentRouterAgent(
        config={
            "intent_classifier": DummyTransformer(),
            "nlp_model": None,
            "disable_transformers": True,
            "llm_provider": "mock",
            "llm_config": {
                "mock_response": {"intents": [{"intent": "general_query", "confidence": 0.1}]}
            },
            "routing_config_path": "ops/config/agents/intent-routing.yaml",
            "agent_config_path": "ops/config/agents/intent-router.yaml",
        }
    )
    await agent.initialize()

    response = await agent.process({"query": "Show budget and risk trend for project Apollo"})

    intents = response["intents"]
    assert len(intents) == 2
    assert intents[0]["intent"] == "financial_query"
    assert intents[1]["intent"] == "risk_query"


@pytest.mark.asyncio
async def test_intent_router_extracts_entities_and_validates_schema() -> None:
    agent = IntentRouterAgent(
        config={
            "intent_classifier": DummyTransformer(),
            "nlp_model": None,
            "disable_transformers": True,
            "llm_provider": "mock",
            "llm_config": {
                "mock_response": {"intents": [{"intent": "general_query", "confidence": 0.1}]}
            },
            "routing_config_path": "ops/config/agents/intent-routing.yaml",
            "agent_config_path": "ops/config/agents/intent-router.yaml",
        }
    )
    await agent.initialize()

    response = await agent.process(
        {"query": "Show critical path for project AP-120 in portfolio PF-09 with €2.5m budget"}
    )

    assert response["parameters"]["project_id"] == "AP-120"
    assert response["parameters"]["portfolio_id"] == "PF-09"
    assert response["parameters"]["currency"] == "EUR"
    assert response["parameters"]["amount"] == 2_500_000
    assert response["parameters"]["schedule_focus"] == "critical_path"


@pytest.mark.asyncio
async def test_intent_router_applies_per_intent_thresholds() -> None:
    class ThresholdClassifier:
        def __call__(self, *_args, **_kwargs):
            return {
                "labels": ["financial_query", "risk_query", "portfolio_query"],
                "scores": [0.86, 0.69, 0.8],
            }

    agent = IntentRouterAgent(
        config={
            "intent_classifier": ThresholdClassifier(),
            "nlp_model": None,
            "disable_transformers": True,
            "llm_provider": "mock",
            "llm_config": {
                "mock_response": {"intents": [{"intent": "general_query", "confidence": 0.1}]}
            },
            "routing_config_path": "ops/config/agents/intent-routing.yaml",
            "agent_config_path": "ops/config/agents/intent-router.yaml",
        }
    )
    await agent.initialize()

    response = await agent.process({"query": "Need financial and risk posture for project Atlas"})
    intent_names = [intent["intent"] for intent in response["intents"]]

    assert "financial_query" in intent_names
    assert "risk_query" not in intent_names
