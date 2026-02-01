import pytest

from portfolio_strategy_agent import PortfolioStrategyAgent
from program_management_agent import ProgramManagementAgent


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
        return {"total_cost": 400, "expected_value": 900, "roi": 0.25}


class FakeResourceAgent:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def process(self, payload: dict) -> dict:
        self.calls.append(payload)
        return {"allocations": {"engineer": ["R1", "R2"]}}


@pytest.mark.asyncio
async def test_portfolio_optimization_uses_financial_agent(tmp_path):
    financial_agent = FakeFinancialAgent()
    event_bus = EventCollector()
    agent = PortfolioStrategyAgent(
        config={
            "portfolio_store_path": tmp_path / "portfolio.json",
            "financial_agent": financial_agent,
            "event_bus": event_bus,
        }
    )
    await agent.initialize()

    result = await agent.process(
        {
            "action": "optimize_portfolio",
            "projects": [{"project_id": "P1", "name": "AI Ops"}],
            "constraints": {"budget_ceiling": 1000, "resource_capacity": {}},
            "tenant_id": "tenant-a",
        }
    )

    assert financial_agent.calls
    assert result["total_cost"] == 400
    assert any(topic == "portfolio.optimized" for topic, _ in event_bus.events)


@pytest.mark.asyncio
async def test_program_optimization_uses_resource_agent(tmp_path):
    event_bus = EventCollector()
    resource_agent = FakeResourceAgent()
    agent = ProgramManagementAgent(
        config={
            "event_bus": event_bus,
            "program_store_path": tmp_path / "programs.json",
            "program_roadmap_store_path": tmp_path / "roadmaps.json",
            "program_dependency_store_path": tmp_path / "dependencies.json",
            "resource_agent": resource_agent,
        }
    )
    await agent.initialize()

    created = await agent.process(
        {
            "action": "create_program",
            "tenant_id": "tenant-a",
            "program": {
                "name": "Resource Program",
                "description": "Integration test",
                "strategic_objectives": ["Efficiency"],
                "constituent_projects": ["A"],
            },
        }
    )

    result = await agent.process(
        {
            "action": "optimize_program",
            "tenant_id": "tenant-a",
            "program_id": created["program_id"],
            "constraints": {"iterations": 2},
        }
    )

    assert resource_agent.calls
    assert result["optimized_schedule"]
    assert any(topic == "program.optimized" for topic, _ in event_bus.events)
