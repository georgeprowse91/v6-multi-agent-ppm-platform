import sys
import types
from pathlib import Path

import pytest

if "prometheus_client" not in sys.modules:

    class _DummyMetric:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

    sys.modules["prometheus_client"] = types.SimpleNamespace(
        Counter=lambda *args, **kwargs: _DummyMetric(),
        Histogram=lambda *args, **kwargs: _DummyMetric(),
    )

from intent_router_agent import IntentRouterAgent
from prompt_registry import PromptRegistry


@pytest.fixture
def registry() -> PromptRegistry:
    return PromptRegistry(
        prompts_root=Path(__file__).resolve().parents[2] / "agents" / "runtime" / "prompts"
    )


def test_prompt_registry_loads_latest_prompt(registry: PromptRegistry) -> None:
    prompt = registry.get_prompt("intent-router")

    assert prompt  # prompt content should be non-empty


def test_prompt_registry_returns_specific_version(registry: PromptRegistry) -> None:
    prompt = registry.get_prompt("intent-router", version=1)
    record = registry.get_prompt_record("intent-router", version=1)

    assert prompt  # prompt content should be non-empty
    assert record.version == 1


def test_prompt_registry_next_version(registry: PromptRegistry) -> None:
    assert registry.next_version("intent-router") == 2
    assert registry.next_version("non-existent-agent") == 1


@pytest.mark.asyncio
async def test_intent_router_includes_prompt_version() -> None:
    routing_path = Path("/tmp/intent-routing-test.yaml")
    routing_path.write_text(
        "\n".join(
            [
                "version: 1",
                "fallback_intent: general_query",
                "default_min_confidence: 0.6",
                "intents:",
                "  - name: portfolio_query",
                "    min_confidence: 0.6",
                "    routes:",
                "      - agent_id: portfolio-optimisation-agent",
            ]
        ),
        encoding="utf-8",
    )

    agent = IntentRouterAgent(
        config={
            "routing_config_path": str(routing_path),
            "llm_provider": "mock",
            "llm_config": {
                "mock_response": {
                    "intents": [{"intent": "portfolio_query", "confidence": 0.9}],
                    "parameters": {"project_id": "APOLLO"},
                }
            },
        }
    )
    await agent.initialize()

    result = await agent.process({"query": "Show portfolio status for Apollo"})

    assert result["prompt_version"] == 1
