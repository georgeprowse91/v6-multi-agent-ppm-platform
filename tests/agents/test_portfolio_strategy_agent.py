import pytest
from portfolio_strategy_agent import PortfolioStrategyAgent


@pytest.mark.asyncio
async def test_portfolio_optimization_knapsack_with_constraints():
    agent = PortfolioStrategyAgent(config={"budget_granularity": 100})
    await agent.initialize()

    projects = [
        {
            "project_id": "P1",
            "name": "Compliance Upgrade",
            "category": "compliance",
            "estimated_cost": 300,
            "expected_value": 500,
            "roi": 0.2,
            "resource_requirements": {"dev": 2},
        },
        {
            "project_id": "P2",
            "name": "Innovation Lab",
            "category": "innovation",
            "estimated_cost": 600,
            "expected_value": 1200,
            "roi": 0.4,
            "resource_requirements": {"dev": 4},
        },
        {
            "project_id": "P3",
            "name": "Ops Automation",
            "category": "operations",
            "estimated_cost": 400,
            "expected_value": 700,
            "roi": 0.3,
            "resource_requirements": {"dev": 3},
        },
    ]

    result = await agent.process(
        {
            "action": "optimize_portfolio",
            "projects": projects,
            "constraints": {
                "budget_ceiling": 900,
                "min_compliance_spend": 200,
                "resource_capacity": {"dev": 6},
            },
        }
    )

    selected_ids = {item["project_id"] for item in result["selected_projects"]}
    assert "P1" in selected_ids
    assert result["total_cost"] <= 900


@pytest.mark.asyncio
async def test_portfolio_get_status_success(tmp_path):
    agent = PortfolioStrategyAgent(config={"portfolio_store_path": tmp_path / "portfolio.json"})
    await agent.initialize()

    response = await agent.process({"action": "get_portfolio_status", "tenant_id": "tenant-a"})

    assert "total_projects" in response


@pytest.mark.asyncio
async def test_portfolio_validation_rejects_invalid_action():
    agent = PortfolioStrategyAgent()
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_portfolio_validation_rejects_missing_constraints():
    agent = PortfolioStrategyAgent()
    await agent.initialize()

    valid = await agent.validate_input({"action": "optimize_portfolio", "constraints": {}})

    assert valid is False
