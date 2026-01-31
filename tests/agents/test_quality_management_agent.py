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

    approval_response = await agent.process(
        {
            "action": "approve_quality_plan",
            "tenant_id": "tenant-q",
            "plan_id": plan_response["plan_id"],
            "approver": "qa-lead",
        }
    )
    assert approval_response["status"] == "Approved"

    test_case_response = await agent.process(
        {
            "action": "create_test_case",
            "tenant_id": "tenant-q",
            "test_case": {
                "project_id": "project-1",
                "name": "Login test",
                "steps": ["Open login", "Enter credentials"],
                "expected_results": "User logged in",
            },
        }
    )
    suite_response = await agent.process(
        {
            "action": "create_test_suite",
            "test_suite": {
                "project_id": "project-1",
                "name": "Regression",
                "test_case_ids": [test_case_response["test_case_id"]],
            },
        }
    )
    execution_response = await agent.process(
        {
            "action": "execute_tests",
            "tenant_id": "tenant-q",
            "test_execution": {
                "project_id": "project-1",
                "suite_id": suite_response["suite_id"],
                "execution_mode": "playwright",
                "auto_log_defects": False,
            },
        }
    )
    assert execution_response["artifact_blob"]["uri"].startswith("https://blob.local/")

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
    assert any(topic == "quality.plan.approved" for topic, _ in event_bus.events)
    assert any(topic == "quality.test_execution.completed" for topic, _ in event_bus.events)
    assert any(topic == "quality.defect.logged" for topic, _ in event_bus.events)
    assert any(topic == "quality.audit.completed" for topic, _ in event_bus.events)


@pytest.mark.asyncio
async def test_quality_management_dashboard_success(tmp_path):
    event_bus = EventCollector()
    agent = QualityManagementAgent(
        config={
            "event_bus": event_bus,
            "quality_plan_store_path": tmp_path / "plans.json",
            "defect_store_path": tmp_path / "defects.json",
        }
    )
    await agent.initialize()

    response = await agent.process({"action": "get_quality_dashboard", "tenant_id": "tenant-q"})

    assert "defect_statistics" in response


@pytest.mark.asyncio
async def test_quality_management_release_notes_report(tmp_path):
    agent = QualityManagementAgent(
        config={
            "event_bus": EventCollector(),
            "quality_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    response = await agent.process(
        {
            "action": "generate_quality_report",
            "report_type": "release_notes",
            "filters": {"project_id": "project-1"},
        }
    )

    assert response["report_type"] == "release_notes"
    assert "narrative" in response["data"]


@pytest.mark.asyncio
async def test_quality_management_validation_rejects_invalid_action(tmp_path):
    agent = QualityManagementAgent(
        config={
            "event_bus": EventCollector(),
            "quality_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_quality_management_validation_rejects_missing_fields(tmp_path):
    agent = QualityManagementAgent(
        config={
            "event_bus": EventCollector(),
            "quality_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input(
        {"action": "create_quality_plan", "plan": {"project_id": "X"}}
    )

    assert valid is False
