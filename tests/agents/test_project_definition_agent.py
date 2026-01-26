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
