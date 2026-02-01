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


class FakeConnector:
    def __init__(self, projects: list[dict]) -> None:
        self.projects = projects
        self.requests: list[str] = []

    def authenticate(self) -> bool:
        return True

    def read(self, resource: str):
        self.requests.append(resource)
        if resource == "projects":
            return self.projects
        if resource == "program_health":
            return [
                {"id": project["id"], "health_score": project.get("health_score", 0.9)}
                for project in self.projects
            ]
        return []


class FakeResourceAgent:
    def __init__(self, allocations: dict[str, dict]) -> None:
        self.allocations = allocations
        self.calls: list[dict] = []

    async def process(self, payload: dict) -> dict:
        self.calls.append(payload)
        project_id = payload.get("project_id")
        return {"allocations": self.allocations.get(project_id, {})}


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
    fake_connector = FakeConnector(
        [
            {"id": "PROJ-1", "health_score": 0.92, "dependency_count": 2},
        ]
    )
    agent = ProgramManagementAgent(
        config={
            "event_bus": EventCollector(),
            "program_store_path": tmp_path / "programs.json",
            "program_roadmap_store_path": tmp_path / "roadmaps.json",
            "program_dependency_store_path": tmp_path / "dependencies.json",
            "llm_client": fake_llm,
            "ml_model": FakeHealthModel(),
            "dependency_container": FakeCosmosContainer(),
            "mapping_container": FakeCosmosContainer(),
            "planview_connector": fake_connector,
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
    assert response["external_signals"]["health_index"] == 0.92


@pytest.mark.asyncio
async def test_program_validation_rejects_invalid_action(tmp_path):
    agent = ProgramManagementAgent(
        config={
            "event_bus": EventCollector(),
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
            "event_bus": EventCollector(),
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
            "event_bus": EventCollector(),
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
            "event_bus": EventCollector(),
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

    async def fake_dependencies(project_ids: list[str], **kwargs):
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


@pytest.mark.asyncio
async def test_dependency_graph_crud_actions(tmp_path):
    dependency_container = FakeCosmosContainer()
    agent = ProgramManagementAgent(
        config={
            "event_bus": EventCollector(),
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
                "name": "CRUD Program",
                "description": "Dependency graph CRUD",
                "strategic_objectives": ["Visibility"],
                "constituent_projects": ["A", "B"],
            },
        }
    )

    await agent.process(
        {
            "action": "generate_roadmap",
            "tenant_id": "tenant-a",
            "program_id": created["program_id"],
        }
    )

    read = await agent.process(
        {
            "action": "get_dependency_graph",
            "program_id": created["program_id"],
        }
    )
    assert read["program_id"] == created["program_id"]

    listing = await agent.process({"action": "list_dependency_graphs"})
    assert listing["dependency_graphs"]

    deleted = await agent.process(
        {
            "action": "delete_dependency_graph",
            "program_id": created["program_id"],
        }
    )
    assert deleted["status"] == "deleted"


@pytest.mark.asyncio
async def test_program_optimization_with_resource_overlaps(tmp_path):
    event_bus = EventCollector()
    resource_agent = FakeResourceAgent(
        {
            "A": {"engineer": ["R1", "R2"]},
            "B": {"engineer": ["R2", "R3"]},
        }
    )
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
                "name": "Optimization Program",
                "description": "Resource overlaps",
                "strategic_objectives": ["Efficiency"],
                "constituent_projects": ["A", "B"],
            },
        }
    )

    result = await agent.process(
        {
            "action": "optimize_program",
            "tenant_id": "tenant-a",
            "program_id": created["program_id"],
            "constraints": {"iterations": 5, "max_shift_days": 2},
        }
    )

    assert result["optimized_schedule"]
    assert any(topic == "program.optimized" for topic, _ in event_bus.events)


@pytest.mark.asyncio
async def test_program_optimization_includes_synergy_and_alignment(tmp_path):
    event_bus = EventCollector()
    agent = ProgramManagementAgent(
        config={
            "event_bus": event_bus,
            "program_store_path": tmp_path / "programs.json",
            "program_roadmap_store_path": tmp_path / "roadmaps.json",
            "program_dependency_store_path": tmp_path / "dependencies.json",
            "synergy_detection_threshold": 0.1,
        }
    )
    await agent.initialize()

    created = await agent.process(
        {
            "action": "create_program",
            "tenant_id": "tenant-a",
            "program": {
                "name": "Synergy Program",
                "description": "Synergy optimization",
                "strategic_objectives": ["CRM", "Data Platform"],
                "constituent_projects": ["P1", "P2"],
            },
        }
    )

    async def fake_project_details(project_ids: list[str]) -> dict[str, dict]:
        return {
            "P1": {"name": "CRM Upgrade", "description": "CRM data platform"},
            "P2": {"name": "CRM Analytics", "description": "Analytics for CRM data"},
        }

    agent._get_project_details = fake_project_details  # type: ignore

    result = await agent.process(
        {
            "action": "optimize_program",
            "tenant_id": "tenant-a",
            "program_id": created["program_id"],
            "constraints": {"iterations": 4, "optimization_method": "mixed_integer"},
        }
    )

    assert result["synergy_savings"]["total"] >= 0
    assert "alignment_score" in result
    assert "synergy" in result["objective_breakdown"]
    assert any(topic == "program.status.updated" for topic, _ in event_bus.events)
