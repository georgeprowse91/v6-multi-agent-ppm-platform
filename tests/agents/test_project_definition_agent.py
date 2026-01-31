import project_definition_agent as project_definition_module
import pytest
from project_definition_agent import ProjectDefinitionAgent


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class ApprovalStub:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.requests.append(input_data)
        return {"approval_id": "appr-1", "status": "pending"}


@pytest.mark.asyncio
async def test_project_definition_persists_charter_and_wbs(tmp_path):
    event_bus = EventCollector()
    approval_stub = ApprovalStub()
    agent = ProjectDefinitionAgent(
        config={
            "event_bus": event_bus,
            "approval_agent": approval_stub,
            "charter_store_path": tmp_path / "charters.json",
            "wbs_store_path": tmp_path / "wbs.json",
        }
    )
    await agent.initialize()

    charter_response = await agent.process(
        {
            "action": "generate_charter",
            "tenant_id": "tenant-a",
            "charter_data": {
                "title": "Project Atlas",
                "description": "Define scope",
                "project_type": "delivery",
                "methodology": "hybrid",
                "requester": "pm-1",
            },
        }
    )

    project_id = charter_response["project_id"]
    assert charter_response["charter_id"]
    assert agent.charter_store.get("tenant-a", project_id)
    assert any(topic == "charter.created" for topic, _ in event_bus.events)

    wbs_response = await agent.process(
        {
            "action": "generate_wbs",
            "tenant_id": "tenant-a",
            "project_id": project_id,
            "scope_statement": {"phase_1": {"name": "Discovery"}},
            "requester": "pm-1",
        }
    )

    assert wbs_response["wbs_id"]
    assert agent.wbs_store.get("tenant-a", project_id)
    assert any(topic == "wbs.created" for topic, _ in event_bus.events)
    assert len(approval_stub.requests) >= 2


@pytest.mark.asyncio
async def test_project_definition_get_charter(tmp_path):
    agent = ProjectDefinitionAgent(
        config={
            "charter_store_path": tmp_path / "charters.json",
            "wbs_store_path": tmp_path / "wbs.json",
        }
    )
    await agent.initialize()

    created = await agent.process(
        {
            "action": "generate_charter",
            "tenant_id": "tenant-a",
            "charter_data": {
                "title": "Project Borealis",
                "description": "Define scope",
                "project_type": "delivery",
                "methodology": "agile",
            },
        }
    )

    charter = await agent.process(
        {
            "action": "get_charter",
            "tenant_id": "tenant-a",
            "project_id": created["project_id"],
        }
    )

    assert charter["project_id"] == created["project_id"]


@pytest.mark.asyncio
async def test_project_definition_validation_rejects_invalid_action(tmp_path):
    agent = ProjectDefinitionAgent(
        config={
            "charter_store_path": tmp_path / "charters.json",
            "wbs_store_path": tmp_path / "wbs.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_project_definition_validation_rejects_missing_fields(tmp_path):
    agent = ProjectDefinitionAgent(
        config={
            "charter_store_path": tmp_path / "charters.json",
            "wbs_store_path": tmp_path / "wbs.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input(
        {"action": "generate_charter", "charter_data": {"title": "X"}}
    )

    assert valid is False


@pytest.mark.asyncio
async def test_project_definition_scope_research_uses_external_search(monkeypatch, tmp_path):
    calls = {"search": 0}

    async def fake_search(query: str, *, result_limit: int | None = None) -> list[str]:
        calls["search"] += 1
        return ["Vendor guidance snippet"]

    async def fake_generate(*_args, **_kwargs):
        return {
            "scope": {"in_scope": ["A"], "out_of_scope": [], "deliverables": []},
            "requirements": ["Req 1"],
            "wbs": ["1.0 Discovery"],
            "summary": "Summary",
        }

    monkeypatch.setattr(project_definition_module, "search_web", fake_search)
    monkeypatch.setattr(project_definition_module, "generate_scope_from_search", fake_generate)

    agent = ProjectDefinitionAgent(
        config={
            "enable_external_research": True,
            "search_result_limit": 2,
            "charter_store_path": tmp_path / "charters.json",
            "wbs_store_path": tmp_path / "wbs.json",
        }
    )
    await agent.initialize()

    result = await agent.process(
        {
            "action": "generate_scope_research",
            "tenant_id": "tenant-a",
            "project_id": "proj-1",
            "objective": "Launch a new compliance reporting portal.",
            "requester": "pm-1",
        }
    )

    assert calls["search"] == 1
    assert result["used_external_research"] is True
    assert result["requirements"] == ["Req 1"]


@pytest.mark.asyncio
async def test_project_definition_scope_research_falls_back_without_results(monkeypatch, tmp_path):
    async def fake_search(*_args, **_kwargs):
        return []

    async def fail_generate(*_args, **_kwargs):
        raise AssertionError("Should not call generate_scope_from_search")

    monkeypatch.setattr(project_definition_module, "search_web", fake_search)
    monkeypatch.setattr(project_definition_module, "generate_scope_from_search", fail_generate)

    agent = ProjectDefinitionAgent(
        config={
            "enable_external_research": True,
            "charter_store_path": tmp_path / "charters.json",
            "wbs_store_path": tmp_path / "wbs.json",
        }
    )
    await agent.initialize()

    result = await agent.process(
        {
            "action": "generate_scope_research",
            "tenant_id": "tenant-a",
            "project_id": "proj-2",
            "objective": "Modernize the HR onboarding process.",
            "requester": "pm-1",
        }
    )

    assert result["used_external_research"] is False
