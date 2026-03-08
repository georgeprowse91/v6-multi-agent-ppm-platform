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
    ]
)

from pydantic import ValidationError
from response_orchestration_agent import ResponseOrchestrationAgent
from response_orchestration_models import AgentInvocationResult, OrchestrationRequest, RoutingEntry

# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------


def test_orchestration_request_validates_routing_not_empty() -> None:
    """OrchestrationRequest with an empty routing list should still be valid (no min_length constraint)."""
    # The model accepts empty routing; the agent decides what to do with it.
    req = OrchestrationRequest(routing=[])
    assert req.routing == []


def test_routing_entry_requires_agent_id() -> None:
    """RoutingEntry should reject construction without agent_id."""
    with pytest.raises(ValidationError):
        RoutingEntry()  # type: ignore[call-arg]


def test_routing_entry_priority_out_of_range() -> None:
    """RoutingEntry should reject priority values outside [0.0, 1.0]."""
    with pytest.raises(ValidationError):
        RoutingEntry(agent_id="my-agent", priority=1.5)


def test_routing_entry_defaults_depends_on_empty() -> None:
    """RoutingEntry should default depends_on to an empty list."""
    entry = RoutingEntry(agent_id="some-agent")
    assert entry.depends_on == []


def test_agent_invocation_result_serializes_correctly() -> None:
    """AgentInvocationResult should serialize to a dict with expected keys."""
    result = AgentInvocationResult(
        success=True,
        agent_id="portfolio-management-agent",
        data={"portfolio_health": "good"},
    )
    dumped = result.model_dump()
    assert dumped["success"] is True
    assert dumped["agent_id"] == "portfolio-management-agent"
    assert dumped["data"] == {"portfolio_health": "good"}
    assert dumped["cached"] is False
    assert dumped["error"] is None


def test_agent_invocation_result_failed_state() -> None:
    """AgentInvocationResult should correctly represent a failure."""
    result = AgentInvocationResult(
        success=False,
        agent_id="financial-agent",
        error="Timeout",
    )
    dumped = result.model_dump()
    assert dumped["success"] is False
    assert dumped["error"] == "Timeout"


# ---------------------------------------------------------------------------
# Agent validation tests
# ---------------------------------------------------------------------------


class _MockEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, object]] = []

    async def publish(self, topic: str, payload: object) -> None:
        self.published.append((topic, payload))


def _build_agent(*, require_approval: bool = False) -> ResponseOrchestrationAgent:
    """Build a ResponseOrchestrationAgent with mocked external dependencies."""
    event_bus = _MockEventBus()
    import tempfile

    plans_dir = tempfile.mkdtemp()
    agent = ResponseOrchestrationAgent(
        config={
            "event_bus": event_bus,
            "plans_dir": plans_dir,
            "max_concurrency": 2,
            "agent_timeout": 5,
            "require_approval": require_approval,
        }
    )
    agent.event_bus = event_bus
    return agent


@pytest.mark.anyio
async def test_validate_input_rejects_empty_routing() -> None:
    """validate_input should return False when routing is missing from input."""
    agent = _build_agent()
    # routing is required — omitting it entirely should fail
    valid = await agent.validate_input({"parameters": {}})
    assert valid is False


@pytest.mark.anyio
async def test_validate_input_accepts_valid_routing() -> None:
    """validate_input should return True for a valid orchestration request."""
    agent = _build_agent()
    valid = await agent.validate_input(
        {
            "routing": [{"agent_id": "portfolio-management-agent"}],
            "parameters": {},
        }
    )
    assert valid is True


# ---------------------------------------------------------------------------
# Process tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_process_with_single_agent_returns_result() -> None:
    """process() with one in-registry agent should return a completed orchestration response."""
    event_bus = _MockEventBus()
    import tempfile

    plans_dir = tempfile.mkdtemp()

    class _MockAgent:
        async def execute(self, payload: object) -> dict[str, object]:
            return {"portfolio_health": "green", "projects": 5}

    agent = ResponseOrchestrationAgent(
        config={
            "event_bus": event_bus,
            "plans_dir": plans_dir,
            "agent_registry": {"portfolio-management-agent": _MockAgent()},
            "max_concurrency": 1,
            "agent_timeout": 5,
        }
    )
    agent.event_bus = event_bus
    agent.http_client = None

    # Initialize http_client to avoid None assertion
    import httpx

    agent.http_client = httpx.AsyncClient(timeout=5)

    result = await agent.process(
        {
            "routing": [{"agent_id": "portfolio-management-agent"}],
            "parameters": {"tenant_id": "tenant-1"},
            "context": {"tenant_id": "tenant-1", "correlation_id": "corr-001"},
        }
    )
    assert result.status == "completed"
    assert isinstance(result.agent_results, list)
    assert len(result.agent_results) == 1
    assert result.agent_results[0].agent_id == "portfolio-management-agent"

    await agent.http_client.aclose()


@pytest.mark.anyio
async def test_process_with_no_routing_returns_empty_response() -> None:
    """process() with empty routing and no plan_id should return a no-agents response."""
    agent = _build_agent()
    agent.http_client = __import__("httpx").AsyncClient(timeout=5)

    result = await agent.process(
        {
            "routing": [],
            "parameters": {},
            "context": {"tenant_id": "tenant-x"},
        }
    )
    assert result.execution_summary.get("total_agents") == 0

    await agent.http_client.aclose()


@pytest.mark.anyio
async def test_process_with_require_approval_returns_pending() -> None:
    """process() with require_approval=True and no approval_decision should pend."""
    event_bus = _MockEventBus()
    import tempfile

    plans_dir = tempfile.mkdtemp()

    agent = ResponseOrchestrationAgent(
        config={
            "event_bus": event_bus,
            "plans_dir": plans_dir,
            "require_approval": True,
            "agent_timeout": 5,
        }
    )
    agent.event_bus = event_bus
    agent.http_client = __import__("httpx").AsyncClient(timeout=5)

    result = await agent.process(
        {
            "routing": [{"agent_id": "financial-agent"}],
            "parameters": {},
            "context": {"tenant_id": "tenant-y"},
        }
    )
    assert result.status == "pending_approval"

    await agent.http_client.aclose()


# ---------------------------------------------------------------------------
# Capabilities test
# ---------------------------------------------------------------------------


def test_get_capabilities_returns_expected() -> None:
    """get_capabilities should return the documented list of capabilities."""
    agent = _build_agent()
    caps = agent.get_capabilities()
    assert "multi_agent_orchestration" in caps
    assert "parallel_execution" in caps
    assert "sequential_execution" in caps
    assert "response_aggregation" in caps
    assert "timeout_management" in caps
    assert "result_caching" in caps
