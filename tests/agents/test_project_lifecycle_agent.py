import pytest
from project_lifecycle_agent import ProjectLifecycleAgent


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


class MetricAgentMock:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.requests: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.requests.append(input_data)
        return self.response


@pytest.mark.asyncio
async def test_project_lifecycle_gate_and_health(tmp_path):
    event_bus = EventCollector()
    approval_mock = ApprovalMock()
    metric_agents = {
        "schedule": MetricAgentMock({"schedule_variance_pct": -0.05}),
        "financial": MetricAgentMock({"budget_variance_pct": 0.02}),
        "risk": MetricAgentMock({"risk_summary": {"total_risks": 4, "high_risks": 1}}),
        "quality": MetricAgentMock({"quality_score": 0.9}),
        "resource": MetricAgentMock({"average_utilization": 0.85}),
    }
    agent = ProjectLifecycleAgent(
        config={
            "event_bus": event_bus,
            "approval_agent": approval_mock,
            "lifecycle_store_path": tmp_path / "lifecycle.json",
            "health_store_path": tmp_path / "health.json",
            "metric_agents": metric_agents,
        }
    )
    await agent.initialize()

    project_id = "proj-123"
    agent.projects[project_id] = {
        "project_id": project_id,
        "name": "Project Orion",
        "sponsor": "sponsor-1",
        "phase_history": [],
        "artifacts": {"charter": {"complete": True}, "deliverables": {"complete": True}},
        "approvals": {
            "charter": True,
            "scope_baseline": True,
            "schedule_baseline": True,
            "budget": True,
        },
        "metrics": {"quality_score": 0.9},
        "risk": {"open_risks": 2},
        "quality": {"defects": 2},
    }
    methodology_map = await agent._load_methodology_map("waterfall")
    agent.lifecycle_states[project_id] = {
        "current_phase": "Initiate",
        "methodology_map": methodology_map,
        "phase_start_date": "2024-01-01T00:00:00",
        "transitions": [],
        "gates_passed": [],
        "gates_pending": [],
        "project_id": project_id,
    }
    agent.lifecycle_store.upsert("tenant-a", project_id, agent.lifecycle_states[project_id])

    evaluation = await agent._evaluate_gate(project_id, "charter_gate", tenant_id="tenant-a")
    assert evaluation["criteria_met"] is True
    assert evaluation["readiness_score"] >= 0.9

    health = await agent._monitor_health(project_id, tenant_id="tenant-a")
    assert health["health_status"] in {"Healthy", "At Risk"}
    assert any(topic == "project.health.updated" for topic, _ in event_bus.events)

    transition = await agent._transition_phase(
        project_id,
        "Plan",
        tenant_id="tenant-a",
        correlation_id="corr-1",
        actor_id="user-1",
    )
    assert transition["success"] is True
    assert any(topic == "project.transitioned" for topic, _ in event_bus.events)

    override = await agent._override_gate(
        project_id,
        "baseline_gate",
        "Override required",
        tenant_id="tenant-a",
        correlation_id="corr-2",
        requester="user-2",
    )
    assert override["approval"]["status"] == "pending"
    assert approval_mock.requests


@pytest.mark.asyncio
async def test_project_lifecycle_dashboard_success(tmp_path):
    metric_agents = {
        "schedule": MetricAgentMock({"schedule_variance_pct": -0.02}),
        "financial": MetricAgentMock({"budget_variance_pct": 0.01}),
        "risk": MetricAgentMock({"risk_summary": {"total_risks": 2, "high_risks": 0}}),
        "quality": MetricAgentMock({"quality_score": 0.92}),
        "resource": MetricAgentMock({"average_utilization": 0.8}),
    }
    agent = ProjectLifecycleAgent(
        config={
            "lifecycle_store_path": tmp_path / "lifecycle.json",
            "health_store_path": tmp_path / "health.json",
            "metric_agents": metric_agents,
        }
    )
    await agent.initialize()

    project_id = "proj-200"
    agent.projects[project_id] = {
        "project_id": project_id,
        "name": "Project Vega",
        "methodology": "waterfall",
        "current_phase": "Initiate",
        "status": "On Track",
    }
    state = {
        "current_phase": "Initiate",
        "methodology_map": await agent._load_methodology_map("waterfall"),
        "phase_start_date": "2024-01-01T00:00:00",
        "transitions": [],
        "gates_passed": [],
        "gates_pending": [],
        "project_id": project_id,
    }
    agent.lifecycle_states[project_id] = state
    agent.lifecycle_store.upsert("tenant-a", project_id, state)

    response = await agent.process(
        {"action": "get_health_dashboard", "tenant_id": "tenant-a", "project_id": project_id}
    )

    assert response["project_id"] == project_id
    assert response["health_data"]["metrics"]["schedule"]["raw"] == -0.02


@pytest.mark.asyncio
async def test_project_lifecycle_generates_health_report(tmp_path):
    event_bus = EventCollector()
    metric_agents = {
        "schedule": MetricAgentMock({"schedule_variance_pct": -0.08}),
        "financial": MetricAgentMock({"budget_variance_pct": 0.05}),
        "risk": MetricAgentMock({"risk_summary": {"total_risks": 5, "high_risks": 2}}),
        "quality": MetricAgentMock({"quality_score": 0.8}),
        "resource": MetricAgentMock({"average_utilization": 0.9}),
    }
    agent = ProjectLifecycleAgent(
        config={
            "event_bus": event_bus,
            "lifecycle_store_path": tmp_path / "lifecycle.json",
            "health_store_path": tmp_path / "health.json",
            "metric_agents": metric_agents,
        }
    )
    await agent.initialize()

    project_id = "proj-300"
    agent.projects[project_id] = {
        "project_id": project_id,
        "name": "Project Nova",
        "methodology": "hybrid",
        "current_phase": "Plan",
        "status": "On Track",
    }
    agent.lifecycle_states[project_id] = {
        "current_phase": "Plan",
        "methodology_map": await agent._load_methodology_map("hybrid"),
        "phase_start_date": "2024-02-01T00:00:00",
        "transitions": [],
        "gates_passed": [],
        "gates_pending": [],
        "project_id": project_id,
    }

    report = await agent.process(
        {"action": "generate_health_report", "tenant_id": "tenant-a", "project_id": project_id}
    )

    assert report["project_id"] == project_id
    assert any(topic == "project.health.report.generated" for topic, _ in event_bus.events)


@pytest.mark.asyncio
async def test_project_lifecycle_validation_rejects_invalid_action(tmp_path):
    agent = ProjectLifecycleAgent(config={"lifecycle_store_path": tmp_path / "lifecycle.json"})
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_project_lifecycle_validation_rejects_missing_fields(tmp_path):
    agent = ProjectLifecycleAgent(config={"lifecycle_store_path": tmp_path / "lifecycle.json"})
    await agent.initialize()

    valid = await agent.validate_input(
        {"action": "initiate_project", "project_data": {"name": "X"}}
    )

    assert valid is False
