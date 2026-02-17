import sys
import types

import pytest

from analytics_insights_agent import AnalyticsInsightsAgent
from agents.common.integration_services import NotificationService
from change_configuration_agent import ChangeConfigurationAgent
from project_definition_agent import ProjectDefinitionAgent
from quality_management_agent import QualityManagementAgent
from release_deployment_agent import ReleaseDeploymentAgent
from resource_capacity_agent import ResourceCapacityAgent
from risk_management_agent import RiskManagementAgent
from schedule_planning_agent import SchedulePlanningAgent
from tests.helpers.service_bus import build_test_event_bus

if "requests" not in sys.modules:
    sys.modules["requests"] = types.SimpleNamespace(
        RequestException=Exception,
        get=lambda *args, **kwargs: None,
        post=lambda *args, **kwargs: None,
    )

from compliance_regulatory_agent import ComplianceRegulatoryAgent


class ApprovalMock:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.requests.append(input_data)
        return {"approval_id": "approval-1", "status": "approved"}


class QualityGateMock:
    async def process(self, input_data: dict) -> dict:
        return {"passed": True, "details": input_data}


class ChangeGateMock:
    async def process(self, input_data: dict) -> dict:
        return {"approved": True, "details": input_data}


class RiskGateMock:
    async def process(self, input_data: dict) -> dict:
        return {"acceptable": True, "details": input_data}


class ComplianceGateMock:
    async def process(self, input_data: dict) -> dict:
        return {"met": True, "details": input_data}


class FailingQualityGateMock:
    def __init__(self) -> None:
        self.calls = 0

    async def process(self, input_data: dict) -> dict:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("quality service unavailable")
        return {"passed": True, "details": input_data}


class EventPublisherAdapter:
    def __init__(self, event_bus):
        self.event_bus = event_bus

    async def publish_event(self, topic: str, payload: dict) -> None:
        await self.event_bus.publish(topic, payload)


@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_end_to_end_project_lifecycle(tmp_path):
    event_bus = build_test_event_bus()
    observed_events: list[tuple[str, dict]] = []

    event_bus.subscribe("risk.identified", lambda payload: observed_events.append(("risk.identified", payload)))
    event_bus.subscribe(
        "quality.test_case.created",
        lambda payload: observed_events.append(("quality.test_case.created", payload)),
    )
    event_bus.subscribe(
        "schedule.created",
        lambda payload: observed_events.append(("schedule.created", payload)),
    )
    event_bus.subscribe(
        "notification.sent",
        lambda payload: observed_events.append(("notification.sent", payload)),
    )

    approval_mock = ApprovalMock()
    project_agent = ProjectDefinitionAgent(
        config={
            "event_bus": event_bus,
            "approval_agent": approval_mock,
            "charter_store_path": tmp_path / "charters.json",
            "wbs_store_path": tmp_path / "wbs.json",
            "requirements_store_path": tmp_path / "requirements.json",
        }
    )
    await project_agent.initialize()

    charter = await project_agent.process(
        {
            "action": "generate_charter",
            "tenant_id": "tenant-alpha",
            "charter_data": {
                "title": "Project Nova",
                "description": "Deliver a new analytics platform",
                "project_type": "delivery",
                "methodology": "hybrid",
                "requester": "pm-1",
            },
        }
    )
    project_id = charter["project_id"]

    schedule_agent = SchedulePlanningAgent(
        config={
            "event_bus": event_bus,
            "schedule_store_path": tmp_path / "schedules.json",
            "schedule_baseline_store_path": tmp_path / "baselines.json",
        }
    )
    await schedule_agent.initialize()
    schedule = await schedule_agent.process(
        {
            "action": "create_schedule",
            "tenant_id": "tenant-alpha",
            "project_id": project_id,
            "schedule_data": {"name": "Initial Plan", "tasks": []},
        }
    )

    resource_agent = ResourceCapacityAgent(
        config={
            "event_bus": event_bus,
            "resource_store_path": tmp_path / "resources.json",
            "allocation_store_path": tmp_path / "allocations.json",
        }
    )
    await resource_agent.initialize()
    await resource_agent.process(
        {
            "action": "add_resource",
            "tenant_id": "tenant-alpha",
            "resource": {"resource_id": "res-1", "name": "Alex", "role": "Engineer"},
        }
    )
    await resource_agent.process(
        {
            "action": "allocate_resource",
            "tenant_id": "tenant-alpha",
            "allocation": {
                "resource_id": "res-1",
                "project_id": project_id,
                "allocation_pct": 0.5,
                "start_date": "2026-02-01",
                "end_date": "2026-03-01",
            },
        }
    )

    risk_agent = RiskManagementAgent(
        config={"event_bus": event_bus, "risk_store_path": tmp_path / "risks.json"}
    )
    await risk_agent.initialize()
    await risk_agent.process(
        {
            "action": "identify_risk",
            "tenant_id": "tenant-alpha",
            "risk": {
                "title": "Capacity constraints",
                "description": "Resource shortages could delay delivery",
                "category": "resource",
            },
        }
    )

    quality_agent = QualityManagementAgent(
        config={
            "event_bus": event_bus,
            "test_case_store_path": tmp_path / "test_cases.json",
            "quality_plan_store_path": tmp_path / "quality_plans.json",
            "defect_store_path": tmp_path / "defects.json",
        }
    )
    await quality_agent.initialize()
    await quality_agent.process(
        {
            "action": "create_test_case",
            "tenant_id": "tenant-alpha",
            "test_case": {"name": "API smoke test", "type": "integration", "priority": "high"},
        }
    )

    compliance_agent = ComplianceRegulatoryAgent(
        config={"event_bus": event_bus, "evidence_store_path": tmp_path / "evidence.json"}
    )
    await compliance_agent.initialize()
    await compliance_agent.process(
        {
            "action": "assess_compliance",
            "tenant_id": "tenant-alpha",
            "project_id": project_id,
            "scope": ["security"],
        }
    )

    change_agent = ChangeConfigurationAgent(
        config={
            "event_publisher": EventPublisherAdapter(event_bus),
            "approval_agent": approval_mock,
            "change_store_path": tmp_path / "changes.json",
            "cmdb_store_path": tmp_path / "cmdb.json",
        }
    )
    await change_agent.initialize()
    change = await change_agent.process(
        {
            "action": "submit_change_request",
            "tenant_id": "tenant-alpha",
            "change": {
                "title": "Release prep change",
                "description": "Prepare release pipeline",
                "change_type": "normal",
                "priority": "medium",
            },
        }
    )

    release_agent = ReleaseDeploymentAgent(
        config={
            "event_bus": event_bus,
            "approval_agent": approval_mock,
            "quality_agent": QualityGateMock(),
            "change_agent": ChangeGateMock(),
            "risk_agent": RiskGateMock(),
            "compliance_agent": ComplianceGateMock(),
            "release_store_path": tmp_path / "release_calendar.json",
            "deployment_plan_store_path": tmp_path / "deployment_plans.json",
        }
    )
    await release_agent.initialize()
    await release_agent.process(
        {
            "action": "plan_release",
            "tenant_id": "tenant-alpha",
            "release": {
                "name": "Release 1.0",
                "target_environment": "staging",
                "project_id": project_id,
                "change_id": change["change_id"],
                "planned_date": "2026-03-15",
            },
        }
    )

    analytics_agent = AnalyticsInsightsAgent(
        config={
            "event_bus": event_bus,
            "analytics_output_store_path": tmp_path / "analytics_outputs.json",
            "analytics_event_store_path": tmp_path / "analytics_events.json",
        }
    )
    await analytics_agent.initialize()
    await analytics_agent.process(
        {"action": "get_insights", "tenant_id": "tenant-alpha", "project_id": project_id}
    )

    notification_service = NotificationService(event_bus)
    await notification_service.send(
        {
            "recipient": "owner@example.com",
            "subject": "Release planned",
            "body": "Release 1.0 has been scheduled for staging.",
        }
    )

    assert project_agent.charter_store.get("tenant-alpha", project_id)
    assert schedule_agent.schedule_store.get("tenant-alpha", schedule["schedule_id"])
    assert risk_agent.risk_store.list("tenant-alpha")
    assert any(topic == "risk.identified" for topic, _ in observed_events)
    assert any(topic == "quality.test_case.created" for topic, _ in observed_events)
    assert any(topic == "notification.sent" for topic, _ in observed_events)


@pytest.mark.asyncio
async def test_release_readiness_failure_then_recovery_without_duplicate_side_effects(tmp_path):
    """Ensure mid-workflow gate failure can recover without duplicate release side effects."""
    event_bus = build_test_event_bus()
    published_release_events: list[dict] = []
    event_bus.subscribe("deployment.release_planned", lambda payload: published_release_events.append(payload))

    quality_gate = FailingQualityGateMock()
    release_agent = ReleaseDeploymentAgent(
        config={
            "event_bus": event_bus,
            "approval_agent": ApprovalMock(),
            "quality_agent": quality_gate,
            "change_agent": ChangeGateMock(),
            "risk_agent": RiskGateMock(),
            "compliance_agent": ComplianceGateMock(),
            "release_store_path": tmp_path / "release_calendar.json",
            "deployment_plan_store_path": tmp_path / "deployment_plans.json",
        }
    )
    await release_agent.initialize()

    payload = {
        "action": "plan_release",
        "tenant_id": "tenant-alpha",
        "release": {
            "name": "Release Recovery",
            "target_environment": "staging",
            "project_id": "proj-1",
            "change_id": "chg-1",
            "planned_date": "2026-03-15",
        },
    }

    with pytest.raises(RuntimeError, match="quality service unavailable"):
        await release_agent.process(payload)

    recovered = await release_agent.process(payload)
    release_entries = release_agent.release_store.list("tenant-alpha")

    assert recovered["status"] == "planned"
    assert len(release_entries) == 1
    assert len(published_release_events) == 1


@pytest.mark.asyncio
async def test_release_planning_degraded_mode_when_non_critical_event_bus_is_down(tmp_path):
    """Ensure release planning still succeeds when event publishing is unavailable."""
    release_agent = ReleaseDeploymentAgent(
        config={
            "event_bus": None,
            "approval_agent": ApprovalMock(),
            "quality_agent": QualityGateMock(),
            "change_agent": ChangeGateMock(),
            "risk_agent": RiskGateMock(),
            "compliance_agent": ComplianceGateMock(),
            "release_store_path": tmp_path / "release_calendar.json",
            "deployment_plan_store_path": tmp_path / "deployment_plans.json",
        }
    )
    await release_agent.initialize()

    result = await release_agent.process(
        {
            "action": "plan_release",
            "tenant_id": "tenant-alpha",
            "release": {
                "name": "Release Degraded",
                "target_environment": "staging",
                "project_id": "proj-2",
                "change_id": "chg-2",
                "planned_date": "2026-04-01",
            },
        }
    )

    assert result["status"] == "planned"
    assert release_agent.release_store.get("tenant-alpha", result["release_id"])
