import pytest
from business_case_investment_agent import BusinessCaseInvestmentAgent


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


@pytest.mark.asyncio
async def test_business_case_creation_and_recommendation_events(tmp_path):
    event_bus = EventCollector()
    agent = BusinessCaseInvestmentAgent(
        config={
            "event_bus": event_bus,
            "business_case_store_path": tmp_path / "business_cases.json",
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "generate_business_case",
            "tenant_id": "tenant-a",
            "request": {
                "title": "Data platform upgrade",
                "description": "Modernize data platform for analytics",
                "project_type": "technology",
                "estimated_cost": 500000,
                "estimated_benefits": 850000,
                "requester": "alex",
                "demand_id": "DEM-1001",
            },
        }
    )

    business_case_id = response["business_case_id"]
    assert business_case_id
    assert any(topic == "business_case.created" for topic, _ in event_bus.events)

    recommendation = await agent.process(
        {
            "action": "generate_recommendation",
            "tenant_id": "tenant-a",
            "business_case_id": business_case_id,
        }
    )

    assert recommendation["business_case_id"] == business_case_id
    assert any(topic == "investment.recommendation" for topic, _ in event_bus.events)


@pytest.mark.asyncio
async def test_roi_validation_blocks_negative_values(tmp_path):
    agent = BusinessCaseInvestmentAgent(
        config={"business_case_store_path": tmp_path / "business_cases.json"}
    )
    await agent.initialize()

    valid = await agent.validate_input(
        {
            "action": "calculate_roi",
            "costs": {"total_cost": -50},
            "benefits": {"total_benefits": 100},
        }
    )

    assert valid is False


@pytest.mark.asyncio
async def test_business_case_get_business_case(tmp_path):
    agent = BusinessCaseInvestmentAgent(
        config={"business_case_store_path": tmp_path / "business_cases.json"}
    )
    await agent.initialize()

    created = await agent.process(
        {
            "action": "generate_business_case",
            "tenant_id": "tenant-a",
            "request": {
                "title": "Cloud refresh",
                "description": "Refresh cloud tooling",
                "project_type": "technology",
                "estimated_cost": 100000,
                "estimated_benefits": 250000,
            },
        }
    )

    response = await agent.process(
        {
            "action": "get_business_case",
            "tenant_id": "tenant-a",
            "business_case_id": created["business_case_id"],
        }
    )

    assert response["business_case_id"] == created["business_case_id"]


@pytest.mark.asyncio
async def test_business_case_invalid_action_rejected(tmp_path):
    agent = BusinessCaseInvestmentAgent(
        config={"business_case_store_path": tmp_path / "business_cases.json"}
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False
