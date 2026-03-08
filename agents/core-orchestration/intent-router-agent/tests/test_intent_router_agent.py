from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[3]
SRC_DIR = TESTS_DIR.parent / "src"
sys.path.extend(
    [
        str(SRC_DIR),
        str(REPO_ROOT),
        str(REPO_ROOT / "packages"),
        str(REPO_ROOT / "agents" / "runtime"),
        str(REPO_ROOT / "agents" / "runtime" / "prompts"),
    ]
)

from intent_router_agent import IntentRouterAgent
from intent_router_models import IntentPrediction, IntentRouterRequest, RoutingDecision
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------


def test_intent_router_request_rejects_empty_query() -> None:
    """IntentRouterRequest should reject a query that is only whitespace."""
    with pytest.raises(ValidationError):
        IntentRouterRequest(query="   ")


def test_intent_router_request_rejects_zero_length_query() -> None:
    """IntentRouterRequest should reject an empty string query."""
    with pytest.raises(ValidationError):
        IntentRouterRequest(query="")


def test_intent_router_request_normalizes_whitespace() -> None:
    """IntentRouterRequest should strip leading/trailing whitespace from query."""
    req = IntentRouterRequest(query="  show portfolio status  ")
    assert req.query == "show portfolio status"


def test_intent_prediction_rejects_out_of_range_confidence() -> None:
    """IntentPrediction should reject confidence values outside [0.0, 1.0]."""
    with pytest.raises(ValidationError):
        IntentPrediction(intent="portfolio_query", confidence=1.5)


def test_intent_prediction_accepts_boundary_confidence() -> None:
    """IntentPrediction should accept boundary confidence values."""
    low = IntentPrediction(intent="risk_query", confidence=0.0)
    high = IntentPrediction(intent="risk_query", confidence=1.0)
    assert low.confidence == 0.0
    assert high.confidence == 1.0


def test_routing_decision_rejects_out_of_range_priority() -> None:
    """RoutingDecision should reject priority outside [0.0, 1.0]."""
    with pytest.raises(ValidationError):
        RoutingDecision(agent_id="some-agent", priority=2.0, intent="portfolio_query")


def test_routing_decision_defaults_depends_on_empty() -> None:
    """RoutingDecision should default depends_on to an empty list."""
    decision = RoutingDecision(agent_id="financial-agent", priority=0.8, intent="financial_query")
    assert decision.depends_on == []


# ---------------------------------------------------------------------------
# Agent input validation tests
# ---------------------------------------------------------------------------


def _make_agent() -> IntentRouterAgent:
    """Build an IntentRouterAgent with minimal config to avoid real I/O."""
    # Provide a minimal routing config so loading doesn't hit the filesystem.
    import tempfile

    import yaml

    routing_config = {
        "version": 1,
        "intents": [
            {
                "name": "portfolio_query",
                "description": "Portfolio status queries",
                "routes": [{"agent_id": "portfolio-management-agent"}],
            },
            {
                "name": "financial_query",
                "description": "Budget and financial queries",
                "routes": [{"agent_id": "financial-management-agent"}],
            },
            {
                "name": "general_query",
                "description": "Fallback for unclassified queries",
                "routes": [],
            },
        ],
        "fallback_intent": "general_query",
        "default_min_confidence": 0.5,
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as routing_file:
        yaml.safe_dump(routing_config, routing_file)
        routing_path = routing_file.name

    agent_config_yaml = {"top_k_intents": 2, "classifier_model_name": "distilbert-base-uncased"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as agent_cfg_file:
        yaml.safe_dump(agent_config_yaml, agent_cfg_file)
        agent_cfg_path = agent_cfg_file.name

    class _MockLLM:
        async def complete(self, system: str, user: str) -> object:
            class _Resp:
                content = '{"intents": [{"intent": "portfolio_query", "confidence": 0.9}]}'

            return _Resp()

    agent = IntentRouterAgent(
        config={
            "routing_config_path": routing_path,
            "agent_config_path": agent_cfg_path,
            "llm_client": _MockLLM(),
            "disable_transformers": True,
            "intent_confidence_threshold": 0.5,
        }
    )
    return agent


@pytest.mark.anyio
async def test_validate_input_rejects_missing_query() -> None:
    """validate_input should return False when 'query' key is absent."""
    agent = _make_agent()
    valid = await agent.validate_input({"context": {"tenant_id": "t1"}})
    assert valid is False


@pytest.mark.anyio
async def test_validate_input_accepts_valid_query() -> None:
    """validate_input should return True for a well-formed query."""
    agent = _make_agent()
    valid = await agent.validate_input({"query": "What is the portfolio health?"})
    assert valid is True


# ---------------------------------------------------------------------------
# Process / routing tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_process_returns_routing_with_mock_llm() -> None:
    """process() should return intents and routing when LLM returns a valid response."""
    agent = _make_agent()
    # Initialize prompt registry with a minimal prompt
    agent.prompt_text = "System:\nClassify intent.\nUser:\n{{request.text}}"
    agent.prompt_version = 1

    result = await agent.process(
        {
            "query": "Show me the portfolio status",
            "context": {"tenant_id": "tenant-test"},
        }
    )
    assert "intents" in result
    assert "routing" in result
    assert isinstance(result["intents"], list)
    assert isinstance(result["routing"], list)


@pytest.mark.anyio
async def test_process_falls_back_to_keyword_classifier_on_llm_error() -> None:
    """process() should use keyword fallback when LLM returns invalid JSON."""

    class _BrokenLLM:
        async def complete(self, system: str, user: str) -> object:
            class _Resp:
                content = "NOT_JSON"

            return _Resp()

    import tempfile

    import yaml

    routing_config = {
        "version": 1,
        "intents": [
            {"name": "portfolio_query", "routes": [{"agent_id": "portfolio-management-agent"}]},
            {"name": "general_query", "routes": []},
        ],
        "fallback_intent": "general_query",
        "default_min_confidence": 0.5,
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(routing_config, f)
        routing_path = f.name

    agent = IntentRouterAgent(
        config={
            "routing_config_path": routing_path,
            "llm_client": _BrokenLLM(),
            "disable_transformers": True,
            "intent_confidence_threshold": 0.5,
        }
    )
    agent.prompt_text = "System:\nClassify.\nUser:\n{{request.text}}"
    agent.prompt_version = 1

    result = await agent.process(
        {"query": "Show portfolio overview", "context": {"tenant_id": "tenant-x"}}
    )
    assert "intents" in result
    assert len(result["intents"]) >= 1


# ---------------------------------------------------------------------------
# Capabilities test
# ---------------------------------------------------------------------------


def test_get_capabilities_returns_expected() -> None:
    """get_capabilities should return the documented list of capabilities."""
    agent = _make_agent()
    caps = agent.get_capabilities()
    assert "intent_classification" in caps
    assert "query_disambiguation" in caps
    assert "multi_intent_detection" in caps
    assert "agent_routing" in caps
    assert "parameter_extraction" in caps


# ---------------------------------------------------------------------------
# Supported intents from config
# ---------------------------------------------------------------------------


def test_supported_intents_loaded_from_config() -> None:
    """supported_intents should reflect intents declared in the routing config."""
    agent = _make_agent()
    assert "portfolio_query" in agent.supported_intents
    assert "financial_query" in agent.supported_intents
    assert "general_query" in agent.supported_intents
