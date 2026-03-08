"""
Unit tests for PortfolioStrategyAgent.

Covers:
- Input validation (valid and invalid)
- Portfolio prioritization
- Portfolio status retrieval
- Agent capability declaration
"""

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

from portfolio_strategy_agent import PortfolioStrategyAgent

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class DummyEventBus:
    """Lightweight event bus stub that records published messages."""

    def __init__(self) -> None:
        self.published: list[tuple[str, object]] = []

    async def publish(self, topic: str, payload: object) -> None:
        self.published.append((topic, payload))


def _make_agent(tmp_path: Path) -> PortfolioStrategyAgent:
    return PortfolioStrategyAgent(
        config={
            "event_bus": DummyEventBus(),
            "portfolio_store_path": str(tmp_path / "portfolio.json"),
            "approval_agent_enabled": False,
        }
    )


_SAMPLE_PROJECTS = [
    {
        "project_id": "p1",
        "name": "Cloud Migration",
        "roi": 0.45,
        "risk_level": "low",
        "category": "innovation",
        "strategic_score": 0.8,
    },
    {
        "project_id": "p2",
        "name": "ERP Upgrade",
        "roi": 0.25,
        "risk_level": "medium",
        "category": "operations",
        "strategic_score": 0.6,
    },
    {
        "project_id": "p3",
        "name": "GDPR Compliance",
        "roi": 0.05,
        "risk_level": "low",
        "category": "compliance",
        "strategic_score": 0.5,
    },
]


# ---------------------------------------------------------------------------
# Test 1: validate_input rejects missing action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_input_rejects_missing_action(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.validate_input({})
    assert result is False


# ---------------------------------------------------------------------------
# Test 2: validate_input accepts prioritize_portfolio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_input_accepts_prioritize_portfolio(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.validate_input({"action": "prioritize_portfolio"})
    assert result is True


# ---------------------------------------------------------------------------
# Test 3: validate_input rejects optimize_portfolio without constraints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_input_rejects_optimize_without_constraints(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.validate_input({"action": "optimize_portfolio", "constraints": {}})
    assert result is False


# ---------------------------------------------------------------------------
# Test 4: validate_input rejects optimize_portfolio with partial constraints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_input_accepts_optimize_with_budget_constraint(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.validate_input(
        {
            "action": "optimize_portfolio",
            "constraints": {"budget_ceiling": 1_000_000},
        }
    )
    assert result is True


# ---------------------------------------------------------------------------
# Test 5: process prioritize_portfolio returns ranked projects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_prioritize_portfolio_returns_ranked_projects(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)

    result = await agent.process(
        {
            "action": "prioritize_portfolio",
            "projects": _SAMPLE_PROJECTS,
        }
    )

    assert "ranked_projects" in result
    ranked = result["ranked_projects"]
    assert len(ranked) == len(_SAMPLE_PROJECTS)

    # Verify projects are ranked in descending overall_score order
    scores = [p["overall_score"] for p in ranked]
    assert scores == sorted(scores, reverse=True), "Projects must be sorted by score desc"

    # Verify rank field is populated starting from 1
    ranks = [p["rank"] for p in ranked]
    assert ranks == list(range(1, len(_SAMPLE_PROJECTS) + 1))

    # Verify each project has a recommendation
    for project in ranked:
        assert project["recommendation"] in {"approve", "defer", "reject"}


# ---------------------------------------------------------------------------
# Test 6: process get_portfolio_status returns status for empty store
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_get_portfolio_status_empty(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)

    result = await agent.process(
        {
            "action": "get_portfolio_status",
            "portfolio_id": "nonexistent-id",
            "context": {"tenant_id": "test-tenant"},
        }
    )

    assert "total_projects" in result
    assert result["total_projects"] == 0
    assert "retrieved_at" in result


# ---------------------------------------------------------------------------
# Test 7: process get_portfolio_status returns data after prioritization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_get_portfolio_status_after_prioritization(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    tenant_id = "tenant-abc"

    # First prioritize to populate the store
    priority_result = await agent.process(
        {
            "action": "prioritize_portfolio",
            "projects": _SAMPLE_PROJECTS,
            "context": {"tenant_id": tenant_id},
        }
    )
    portfolio_id = priority_result["portfolio_id"]

    # Now fetch status
    status = await agent.process(
        {
            "action": "get_portfolio_status",
            "portfolio_id": portfolio_id,
            "context": {"tenant_id": tenant_id},
        }
    )

    assert status["portfolio_id"] == portfolio_id
    assert status["total_projects"] == len(_SAMPLE_PROJECTS)


# ---------------------------------------------------------------------------
# Test 8: get_capabilities returns expected items
# ---------------------------------------------------------------------------


def test_get_capabilities_returns_expected_items(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    capabilities = agent.get_capabilities()

    assert isinstance(capabilities, list)
    assert len(capabilities) > 0

    expected_capabilities = {
        "portfolio_prioritization",
        "strategic_alignment_scoring",
        "capacity_constrained_optimization",
        "scenario_planning",
        "portfolio_rebalancing",
    }
    actual_set = set(capabilities)
    missing = expected_capabilities - actual_set
    assert not missing, f"Missing expected capabilities: {missing}"


# ---------------------------------------------------------------------------
# Test 9: process list_scenarios returns empty list initially
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_list_scenarios_empty_initially(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.process({"action": "list_scenarios"})
    assert "scenarios" in result
    assert isinstance(result["scenarios"], list)
    assert len(result["scenarios"]) == 0


# ---------------------------------------------------------------------------
# Test 10: process upsert_scenario then get_scenario round-trip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_and_get_scenario_round_trip(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    scenario_def = {
        "id": "scen-test-001",
        "name": "Optimistic Budget",
        "budget_ceiling": 2_000_000,
        "projects": [],
    }

    upsert_result = await agent.process(
        {
            "action": "upsert_scenario",
            "scenario": scenario_def,
        }
    )
    assert upsert_result["scenario_id"] == "scen-test-001"

    get_result = await agent.process(
        {
            "action": "get_scenario",
            "scenario_id": "scen-test-001",
        }
    )
    assert get_result["scenario_id"] == "scen-test-001"
    assert get_result["scenario"]["name"] == "Optimistic Budget"
