import pytest
from llm.client import LLMResponse
from program_management_agent import ProgramManagementAgent


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class FakeCosmosContainer:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    async def upsert_item(self, item: dict) -> dict:
        self.items[item["id"]] = item
        return item

    async def read_item(self, item: str, partition_key: str) -> dict:
        return self.items[item]

    async def delete_item(self, item: str, partition_key: str) -> None:
        self.items.pop(item, None)

    async def query_items(self, query: str):
        for item in self.items.values():
            yield item


class FakeLLMClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        self.prompts.append(user_prompt)
        return LLMResponse(content="Program narrative summary.", raw={})


class FakeHealthModel:
    name = "mock-health-model"

    def predict(self, features):
        return [0.88]


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
    fake_llm = FakeLLMClient()
    agent = ProgramManagementAgent(
        config={
            "program_store_path": tmp_path / "programs.json",
            "program_roadmap_store_path": tmp_path / "roadmaps.json",
            "program_dependency_store_path": tmp_path / "dependencies.json",
            "llm_client": fake_llm,
            "ml_model": FakeHealthModel(),
            "dependency_container": FakeCosmosContainer(),
            "mapping_container": FakeCosmosContainer(),
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
    assert response["narrative"] == "Program narrative summary."
    assert "Schedule health" in fake_llm.prompts[0]


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


@pytest.mark.asyncio
async def test_synergy_analysis_detects_overlap(tmp_path):
    agent = ProgramManagementAgent(
        config={
            "program_store_path": tmp_path / "programs.json",
            "program_roadmap_store_path": tmp_path / "roadmaps.json",
            "program_dependency_store_path": tmp_path / "dependencies.json",
            "synergy_detection_threshold": 0.2,
        }
    )
    await agent.initialize()

    synergies = await agent.analyze_synergies(
        {
            "PROJ-1": {"name": "CRM Upgrade", "description": "Upgrade CRM data platform"},
            "PROJ-2": {"name": "CRM Analytics", "description": "Analytics for CRM platform"},
        }
    )

    assert synergies["shared_components"]


@pytest.mark.asyncio
async def test_dependency_optimization_recommendations(tmp_path):
    dependency_container = FakeCosmosContainer()
    agent = ProgramManagementAgent(
        config={
            "program_store_path": tmp_path / "programs.json",
            "program_roadmap_store_path": tmp_path / "roadmaps.json",
            "program_dependency_store_path": tmp_path / "dependencies.json",
            "dependency_container": dependency_container,
            "mapping_container": FakeCosmosContainer(),
        }
    )
    await agent.initialize()

    created = await agent.process(
        {
            "action": "create_program",
            "tenant_id": "tenant-a",
            "program": {
                "name": "Optimization Program",
                "description": "Dependency management",
                "strategic_objectives": ["Efficiency"],
                "constituent_projects": ["A", "B", "C", "D", "E"],
            },
        }
    )

    async def fake_dependencies(project_ids: list[str]):
        return [
            {"predecessor": "A", "successor": "B"},
            {"predecessor": "A", "successor": "C"},
            {"predecessor": "A", "successor": "D"},
            {"predecessor": "A", "successor": "E"},
            {"predecessor": "E", "successor": "A"},
        ]

    agent._identify_dependencies = fake_dependencies  # type: ignore

    response = await agent.process(
        {
            "action": "track_dependencies",
            "tenant_id": "tenant-a",
            "program_id": created["program_id"],
        }
    )

    optimization = response["optimization"]
    assert optimization["conflicts"]
    assert optimization["recommendations"]
