import pytest
from program_management_agent import ProgramManagementAgent


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


@pytest.mark.asyncio
async def test_program_creation_and_roadmap_events(tmp_path):
    event_bus = EventCollector()
    agent = ProgramManagementAgent(
        config={
            "event_bus": event_bus,
            "program_store_path": tmp_path / "programs.json",
            "program_roadmap_store_path": tmp_path / "roadmaps.json",
            "program_dependency_store_path": tmp_path / "dependencies.json",
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "create_program",
            "tenant_id": "tenant-a",
            "program": {
                "name": "Customer Experience Modernization",
                "description": "Upgrade customer-facing systems",
                "strategic_objectives": ["Increase retention"],
                "constituent_projects": ["PROJ-1", "PROJ-2"],
                "portfolio_id": "PORT-1",
                "created_by": "pm",
            },
        }
    )

    program_id = response["program_id"]
    assert program_id
    assert any(topic == "program.created" for topic, _ in event_bus.events)

    roadmap = await agent.process(
        {
            "action": "generate_roadmap",
            "tenant_id": "tenant-a",
            "program_id": program_id,
        }
    )

    assert roadmap["program_id"] == program_id
    assert any(topic == "program.roadmap.updated" for topic, _ in event_bus.events)

    stored = await agent.process(
        {
            "action": "get_program",
            "tenant_id": "tenant-a",
            "program_id": program_id,
        }
    )
    assert stored["program_id"] == program_id


@pytest.mark.asyncio
async def test_program_health_summary(tmp_path):
    agent = ProgramManagementAgent(
        config={
            "program_store_path": tmp_path / "programs.json",
            "program_roadmap_store_path": tmp_path / "roadmaps.json",
            "program_dependency_store_path": tmp_path / "dependencies.json",
        }
    )
    await agent.initialize()

    created = await agent.process(
        {
            "action": "create_program",
            "tenant_id": "tenant-a",
            "program": {
                "name": "Modernization",
                "description": "Upgrade systems",
                "strategic_objectives": ["Efficiency"],
                "constituent_projects": ["PROJ-1"],
            },
        }
    )

    response = await agent.process(
        {
            "action": "get_program_health",
            "tenant_id": "tenant-a",
            "program_id": created["program_id"],
        }
    )

    assert response["program_id"] == created["program_id"]


@pytest.mark.asyncio
async def test_program_validation_rejects_invalid_action(tmp_path):
    agent = ProgramManagementAgent(
        config={
            "program_store_path": tmp_path / "programs.json",
            "program_roadmap_store_path": tmp_path / "roadmaps.json",
            "program_dependency_store_path": tmp_path / "dependencies.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_program_validation_rejects_missing_fields(tmp_path):
    agent = ProgramManagementAgent(
        config={
            "program_store_path": tmp_path / "programs.json",
            "program_roadmap_store_path": tmp_path / "roadmaps.json",
            "program_dependency_store_path": tmp_path / "dependencies.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "create_program", "program": {"name": "X"}})

    assert valid is False
