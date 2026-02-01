import project_definition_agent as project_definition_module
import pytest
from project_definition_agent import ProjectDefinitionAgent


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class ApprovalMock:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.requests.append(input_data)
        return {"approval_id": "appr-1", "status": "pending"}


class OpenAIMock:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if "executive summary" in prompt.lower():
            return "AI-generated executive summary."
        if "work breakdown structure" in prompt.lower():
            return "1.0 - Project Management\n2.0 - Delivery Phase"
        if "raci" in prompt.lower():
            return "Deliverable A | Alice | Responsible"
        return "AI response"


class FormRecognizerMock:
    async def extract_requirements(
        self, *, document_content: str | None = None, document_url: str | None = None
    ) -> list[dict[str, str]]:
        return [{"text": "The system shall support SSO."}]


class RequirementsSyncMock:
    def __init__(self) -> None:
        self.synced: list[dict] = []

    async def sync_requirements(self, *, project_id: str, requirements: list[dict]) -> None:
        self.synced.append({"project_id": project_id, "requirements": requirements})


@pytest.mark.asyncio
async def test_project_definition_persists_charter_and_wbs(tmp_path):
    event_bus = EventCollector()
    approval_mock = ApprovalMock()
    agent = ProjectDefinitionAgent(
        config={
            "event_bus": event_bus,
            "approval_agent": approval_mock,
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
    assert len(approval_mock.requests) >= 2


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


@pytest.mark.asyncio
async def test_project_definition_openai_charter_and_wbs(tmp_path):
    openai_mock = OpenAIMock()
    agent = ProjectDefinitionAgent(
        config={
            "openai_client": openai_mock,
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
                "title": "Project Orion",
                "description": "AI scope",
                "project_type": "delivery",
                "methodology": "agile",
            },
        }
    )

    assert "AI-generated executive summary." in charter_response["document"]["executive_summary"]
    wbs_response = await agent.process(
        {
            "action": "generate_wbs",
            "tenant_id": "tenant-a",
            "project_id": charter_response["project_id"],
            "scope_statement": {},
            "requester": "pm-1",
        }
    )
    assert any("Delivery Phase" in node.get("name", "") for node in wbs_response["structure"].values())


@pytest.mark.asyncio
async def test_project_definition_requirements_sync_and_form_recognizer(tmp_path):
    form_recognizer = FormRecognizerMock()
    doors_mock = RequirementsSyncMock()
    agent = ProjectDefinitionAgent(
        config={
            "form_recognizer_client": form_recognizer,
            "doors_client": doors_mock,
            "charter_store_path": tmp_path / "charters.json",
            "wbs_store_path": tmp_path / "wbs.json",
        }
    )
    await agent.initialize()

    requirements = await agent.process(
        {
            "action": "manage_requirements",
            "project_id": "proj-1",
            "requirements": [{"document_content": "Spec document"}],
        }
    )

    assert any("SSO" in req.get("text", "") for req in requirements["requirements"])
    assert doors_mock.synced


@pytest.mark.asyncio
async def test_project_definition_scope_baseline_and_scope_creep_event(tmp_path):
    event_bus = EventCollector()
    agent = ProjectDefinitionAgent(
        config={
            "event_bus": event_bus,
            "charter_store_path": tmp_path / "charters.json",
            "wbs_store_path": tmp_path / "wbs.json",
            "scope_baseline_store_path": tmp_path / "baseline.json",
        }
    )
    await agent.initialize()

    charter_response = await agent.process(
        {
            "action": "generate_charter",
            "tenant_id": "tenant-a",
            "charter_data": {
                "title": "Project Nova",
                "description": "Define scope",
                "project_type": "delivery",
                "methodology": "hybrid",
                "in_scope": ["Feature A"],
                "deliverables": ["Portal"],
            },
        }
    )
    await agent.process(
        {
            "action": "generate_wbs",
            "tenant_id": "tenant-a",
            "project_id": charter_response["project_id"],
            "scope_statement": {"phase_1": {"name": "Discovery"}},
            "requester": "pm-1",
        }
    )
    await agent.process(
        {
            "action": "manage_requirements",
            "project_id": charter_response["project_id"],
            "requirements": [{"text": "The system shall log in."}],
        }
    )

    baseline = await agent.process(
        {"action": "manage_scope_baseline", "project_id": charter_response["project_id"]}
    )
    assert baseline["baseline_id"]
    assert any(topic == "scope.baseline.locked" for topic, _ in event_bus.events)

    scope_creep = await agent.process(
        {
            "action": "detect_scope_creep",
            "project_id": charter_response["project_id"],
            "current_scope": {"in_scope": ["Feature A", "Feature B"], "deliverables": ["Portal"]},
        }
    )
    assert scope_creep["changes_detected"]
