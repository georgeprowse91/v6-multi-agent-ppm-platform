import pytest
from portfolio_strategy_agent import PortfolioStrategyAgent


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class FakeFinancialAgent:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def process(self, payload: dict) -> dict:
        self.calls.append(payload)
        project_id = payload.get("project_id")
        return {
            "project_id": project_id,
            "total_cost": 500,
            "expected_value": 1200,
            "roi": 0.3,
        }


@pytest.mark.asyncio
async def test_portfolio_optimization_knapsack_with_constraints():
    agent = PortfolioStrategyAgent(
        config={"budget_granularity": 100, "event_bus": EventCollector()}
    )
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
async def test_portfolio_optimization_mean_variance():
    agent = PortfolioStrategyAgent(
        config={"budget_granularity": 100, "event_bus": EventCollector()}
    )
    await agent.initialize()

    projects = [
        {
            "project_id": "P1",
            "name": "Risky Growth",
            "category": "innovation",
            "estimated_cost": 500,
            "expected_value": 1500,
            "roi": 0.6,
            "risk_level": "high",
        },
        {
            "project_id": "P2",
            "name": "Steady Ops",
            "category": "operations",
            "estimated_cost": 400,
            "expected_value": 900,
            "roi": 0.3,
            "risk_level": "low",
        },
    ]

    result = await agent.process(
        {
            "action": "optimize_portfolio",
            "projects": projects,
            "constraints": {
                "budget_ceiling": 700,
                "resource_capacity": {},
                "optimization_method": "mean_variance",
                "risk_aversion": 0.8,
            },
        }
    )

    assert result["selected_projects"]
    assert result["total_cost"] <= 700


@pytest.mark.asyncio
async def test_portfolio_financial_integration_enrichment():
    financial_agent = FakeFinancialAgent()
    agent = PortfolioStrategyAgent(
        config={
            "budget_granularity": 100,
            "financial_agent": financial_agent,
            "event_bus": EventCollector(),
        }
    )
    await agent.initialize()

    result = await agent.process(
        {
            "action": "optimize_portfolio",
            "projects": [
                {"project_id": "P1", "name": "Financial Sync", "category": "operations"}
            ],
            "constraints": {"budget_ceiling": 800, "resource_capacity": {}},
        }
    )

    assert financial_agent.calls
    assert result["total_cost"] == 500


@pytest.mark.asyncio
async def test_portfolio_get_status_success(tmp_path):
    agent = PortfolioStrategyAgent(
        config={"portfolio_store_path": tmp_path / "portfolio.json", "event_bus": EventCollector()}
    )
    await agent.initialize()

    response = await agent.process({"action": "get_portfolio_status", "tenant_id": "tenant-a"})

    assert "total_projects" in response


@pytest.mark.asyncio
async def test_portfolio_validation_rejects_invalid_action():
    agent = PortfolioStrategyAgent(config={"event_bus": EventCollector()})
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_portfolio_validation_rejects_missing_constraints():
    agent = PortfolioStrategyAgent(config={"event_bus": EventCollector()})
    await agent.initialize()

    valid = await agent.validate_input({"action": "optimize_portfolio", "constraints": {}})

    assert valid is False
