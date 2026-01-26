import pytest

from quality_management_agent import QualityManagementAgent


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


@pytest.mark.asyncio
async def test_quality_management_persists_and_emits_events(tmp_path):
    event_bus = EventCollector()
    agent = QualityManagementAgent(
        config={
            "event_bus": event_bus,
            "quality_plan_store_path": tmp_path / "plans.json",
            "test_case_store_path": tmp_path / "cases.json",
            "defect_store_path": tmp_path / "defects.json",
            "audit_store_path": tmp_path / "audits.json",
        }
    )
    await agent.initialize()

    plan_response = await agent.process(
        {
            "action": "create_quality_plan",
            "tenant_id": "tenant-q",
            "plan": {"project_id": "project-1", "objectives": ["zero defects"]},
        }
    )
    assert agent.quality_plan_store.get("tenant-q", plan_response["plan_id"])

    defect_response = await agent.process(
        {
            "action": "log_defect",
            "tenant_id": "tenant-q",
            "defect": {"summary": "Login fails", "severity": "high", "component": "auth"},
        }
    )
    assert agent.defect_store.get("tenant-q", defect_response["defect_id"])

    audit_response = await agent.process(
        {
            "action": "conduct_audit",
            "tenant_id": "tenant-q",
            "audit": {"project_id": "project-1", "title": "Sprint audit"},
        }
    )
    assert agent.audit_store.get("tenant-q", audit_response["audit_id"])
    assert any(topic == "quality.plan.created" for topic, _ in event_bus.events)
    assert any(topic == "quality.defect.logged" for topic, _ in event_bus.events)
    assert any(topic == "quality.audit.completed" for topic, _ in event_bus.events)
