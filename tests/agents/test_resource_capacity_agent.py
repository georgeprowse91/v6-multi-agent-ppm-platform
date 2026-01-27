import pytest
from resource_capacity_agent import ResourceCapacityAgent


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


@pytest.mark.asyncio
async def test_resource_allocation_persistence_and_events(tmp_path):
    event_bus = EventCollector()
    agent = ResourceCapacityAgent(
        config={
            "event_bus": event_bus,
            "resource_store_path": tmp_path / "resources.json",
            "allocation_store_path": tmp_path / "allocations.json",
        }
    )
    await agent.initialize()

    add_response = await agent.process(
        {
            "action": "add_resource",
            "tenant_id": "tenant-a",
            "resource": {
                "resource_id": "res-1",
                "name": "Avery",
                "role": "Engineer",
                "skills": ["python"],
                "location": "Remote",
            },
        }
    )
    assert add_response["data_quality"]["is_valid"] is True

    allocation_response = await agent.process(
        {
            "action": "allocate_resource",
            "tenant_id": "tenant-a",
            "correlation_id": "corr-1",
            "allocation": {
                "resource_id": "res-1",
                "project_id": "proj-1",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "allocation_percentage": 50,
            },
        }
    )

    assert allocation_response["allocation_id"]
    assert any(topic == "resource.allocation.created" for topic, _ in event_bus.events)


@pytest.mark.asyncio
async def test_resource_capacity_resource_pool(tmp_path):
    agent = ResourceCapacityAgent(
        config={
            "resource_store_path": tmp_path / "resources.json",
            "allocation_store_path": tmp_path / "allocations.json",
        }
    )
    await agent.initialize()

    response = await agent.process({"action": "get_resource_pool", "tenant_id": "tenant-a"})

    assert "resources" in response


@pytest.mark.asyncio
async def test_resource_capacity_validation_rejects_invalid_action(tmp_path):
    agent = ResourceCapacityAgent(
        config={
            "resource_store_path": tmp_path / "resources.json",
            "allocation_store_path": tmp_path / "allocations.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_resource_capacity_validation_rejects_missing_fields(tmp_path):
    agent = ResourceCapacityAgent(
        config={
            "resource_store_path": tmp_path / "resources.json",
            "allocation_store_path": tmp_path / "allocations.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input(
        {"action": "add_resource", "resource": {"resource_id": "res-1"}}
    )

    assert valid is False
