"""
Unit tests for BusinessCaseInvestmentAgent.

Covers:
- Input validation (valid and invalid)
- Business case generation
- ROI calculation
- Business case retrieval
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

from business_case_investment_agent import BusinessCaseInvestmentAgent

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class DummyEventBus:
    """Lightweight event bus stub that records published messages."""

    def __init__(self) -> None:
        self.published: list[tuple[str, object]] = []

    async def publish(self, topic: str, payload: object) -> None:
        self.published.append((topic, payload))


def _make_agent(tmp_path: Path) -> BusinessCaseInvestmentAgent:
    return BusinessCaseInvestmentAgent(
        config={
            "event_bus": DummyEventBus(),
            "business_case_store_path": str(tmp_path / "business_cases.json"),
            "business_case_settings_path": str(tmp_path / "settings.yaml"),
        }
    )


_VALID_REQUEST = {
    "title": "Cloud ERP Migration",
    "description": "Migrate legacy ERP to cloud-native platform",
    "project_type": "it",
    "estimated_cost": 500_000,
    "estimated_benefits": 900_000,
    "requester": "pmo@example.com",
}

_VALID_COSTS = {"total_cost": 200_000}
_VALID_BENEFITS = {"total_benefits": 400_000}


# ---------------------------------------------------------------------------
# Test 1: validate_input rejects missing action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_input_rejects_missing_action(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.validate_input({})
    assert result is False


# ---------------------------------------------------------------------------
# Test 2: validate_input rejects generate_business_case without required fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_input_rejects_incomplete_generate_request(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.validate_input(
        {
            "action": "generate_business_case",
            "request": {"title": "Only Title"},  # missing description, project_type, etc.
        }
    )
    assert result is False


# ---------------------------------------------------------------------------
# Test 3: validate_input accepts valid generate_business_case request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_input_accepts_valid_generate_request(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    result = await agent.validate_input(
        {
            "action": "generate_business_case",
            "request": _VALID_REQUEST,
        }
    )
    assert result is True


# ---------------------------------------------------------------------------
# Test 4: process generate_business_case returns business_case_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_generate_business_case_returns_id(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)

    result = await agent.process(
        {
            "action": "generate_business_case",
            "request": _VALID_REQUEST,
        }
    )

    assert "business_case_id" in result
    assert result["business_case_id"].startswith("BC-")
    assert result["status"] == "Draft"
    assert "document" in result
    assert "financial_metrics" in result


# ---------------------------------------------------------------------------
# Test 5: process get_business_case for nonexistent ID raises ValueError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_get_business_case_nonexistent_raises(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)

    with pytest.raises(ValueError, match="Business case not found"):
        await agent.process(
            {
                "action": "get_business_case",
                "business_case_id": "BC-NONEXISTENT",
                "context": {"tenant_id": "test-tenant"},
            }
        )


# ---------------------------------------------------------------------------
# Test 6: process get_business_case after generation returns the record
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_get_business_case_after_generation(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    tenant_id = "tenant-xyz"

    gen_result = await agent.process(
        {
            "action": "generate_business_case",
            "request": _VALID_REQUEST,
            "context": {"tenant_id": tenant_id},
        }
    )
    bc_id = gen_result["business_case_id"]

    get_result = await agent.process(
        {
            "action": "get_business_case",
            "business_case_id": bc_id,
            "context": {"tenant_id": tenant_id},
        }
    )

    assert get_result["business_case_id"] == bc_id
    assert get_result["title"] == _VALID_REQUEST["title"]


# ---------------------------------------------------------------------------
# Test 7: process calculate_roi returns ROI metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_calculate_roi_returns_metrics(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)

    result = await agent.process(
        {
            "action": "calculate_roi",
            "costs": _VALID_COSTS,
            "benefits": _VALID_BENEFITS,
        }
    )

    assert "npv" in result
    assert "irr" in result
    assert "payback_period_months" in result
    assert "roi_percentage" in result
    assert "tco" in result
    assert "sensitivity_analysis" in result
    assert "monte_carlo_summary" in result

    # With benefits > costs, ROI should be positive
    assert result["roi_percentage"] > 0


# ---------------------------------------------------------------------------
# Test 8: calculate_roi handles zero cost gracefully
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_calculate_roi_zero_cost(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)

    result = await agent.process(
        {
            "action": "calculate_roi",
            "costs": {"total_cost": 0},
            "benefits": {"total_benefits": 100_000},
        }
    )

    assert result["roi_percentage"] == 0.0


# ---------------------------------------------------------------------------
# Test 9: get_capabilities returns expected items
# ---------------------------------------------------------------------------


def test_get_capabilities_returns_expected_items(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)
    capabilities = agent.get_capabilities()

    assert isinstance(capabilities, list)
    assert len(capabilities) > 0

    expected_capabilities = {
        "business_case_generation",
        "roi_calculation",
        "scenario_modelling",
        "npv_calculation",
        "payback_period_calculation",
    }
    actual_set = set(capabilities)
    missing = expected_capabilities - actual_set
    assert not missing, f"Missing expected capabilities: {missing}"


# ---------------------------------------------------------------------------
# Test 10: process run_scenario_analysis returns comparison
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_run_scenario_analysis_returns_comparison(tmp_path: Path) -> None:
    agent = _make_agent(tmp_path)

    scenarios = [
        {
            "name": "Base Case",
            "base_cost": 200_000,
            "base_benefit": 400_000,
            "parameters": {"cost_multiplier": 1.0, "benefit_multiplier": 1.0},
        },
        {
            "name": "Optimistic",
            "base_cost": 200_000,
            "base_benefit": 400_000,
            "parameters": {"cost_multiplier": 0.9, "benefit_multiplier": 1.2},
        },
    ]

    result = await agent.process(
        {
            "action": "run_scenario_analysis",
            "business_case_id": "BC-TEST-001",
            "scenarios": scenarios,
        }
    )

    assert "scenarios" in result
    assert len(result["scenarios"]) == len(scenarios)
    assert "comparison" in result
    assert "recommendation" in result
