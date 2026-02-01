import pytest
from release_deployment_agent import ReleaseDeploymentAgent


class ApprovalStub:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.requests.append(input_data)
        return {"approval_id": "appr-release", "status": "pending"}


class QualityStub:
    def __init__(self, passed: bool = True) -> None:
        self.passed = passed

    async def process(self, input_data: dict) -> dict:
        return {"passed": self.passed, "test_pass_rate": 88.0}


class ChangeStub:
    def __init__(self, approved: bool = True) -> None:
        self.approved = approved

    async def process(self, input_data: dict) -> dict:
        return {"approved": self.approved}


class RiskStub:
    def __init__(self, acceptable: bool = True) -> None:
        self.acceptable = acceptable

    async def process(self, input_data: dict) -> dict:
        return {"acceptable": self.acceptable, "risk_score": 0.8}


class ComplianceStub:
    def __init__(self, met: bool = True) -> None:
        self.met = met

    async def process(self, input_data: dict) -> dict:
        return {"met": self.met, "requirements": []}


class PolicyStub:
    async def assess_compliance(self, environment: dict) -> dict:
        return {
            "compliance_state": "noncompliant",
            "drift_items": [{"policy": "allowed-locations", "status": "noncompliant"}],
        }


class OpenAIStub:
    async def generate(self, prompt: str) -> str:
        return "AI Release Notes"


class ScheduleStub:
    async def process(self, input_data: dict) -> dict:
        return {"scheduled_window": {"start_time": "2024-06-02T01:00:00", "duration_hours": 2}}


class EventBusStub:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []
        self.subscriptions: dict[str, list] = {}

    def subscribe(self, topic: str, handler) -> None:
        self.subscriptions.setdefault(topic, []).append(handler)

    async def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))
        for handler in self.subscriptions.get(topic, []):
            await handler(payload)

    def get_metrics(self) -> dict:
        return {}

    def get_recent_events(self, topic: str | None = None) -> list:
        return []


class ReservationStub:
    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.reserved: list[dict] = []
        self.released: list[dict] = []

    async def check_availability(self, payload: dict) -> dict:
        return {"available": self.available}

    async def reserve(self, payload: dict) -> dict:
        reservation = {"reservation_id": "res-1", "status": "reserved", **payload}
        self.reserved.append(reservation)
        return reservation

    async def release(self, allocation: dict) -> dict:
        self.released.append(allocation)
        return {"status": "released"}


class MonitoringStub:
    async def get_metrics(self, deployment_plan: dict) -> dict:
        return {"response_time_ms": 300.0, "error_rate": 0.05}

    async def get_baseline(self, deployment_plan: dict) -> dict:
        return {"response_time_ms": {"mean": 120.0, "std": 20.0}, "error_rate": {"mean": 0.001}}


class BlockerQualityStub:
    async def process(self, input_data: dict) -> dict:
        return {"passed": False, "issues": [{"severity": "critical", "summary": "Tests failing"}]}


@pytest.mark.asyncio
async def test_release_deployment_requires_approval_before_execute(tmp_path):
    approval_stub = ApprovalStub()
    agent = ReleaseDeploymentAgent(
        config={
            "approval_agent": approval_stub,
            "release_store_path": tmp_path / "releases.json",
            "deployment_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    release_response = await agent.process(
        {
            "action": "plan_release",
            "tenant_id": "tenant-rel",
            "release": {
                "name": "Release 1",
                "target_environment": "production",
                "planned_date": "2024-06-01",
                "requester": "release-manager",
            },
        }
    )
    assert release_response["approval_required"] is True
    assert agent.release_store.get("tenant-rel", release_response["release_id"])

    plan_response = await agent.process(
        {
            "action": "create_deployment_plan",
            "tenant_id": "tenant-rel",
            "release_id": release_response["release_id"],
            "deployment_plan": {"owner": "release-manager"},
        }
    )
    assert agent.deployment_plan_store.get("tenant-rel", plan_response["deployment_plan_id"])

    execute_response = await agent.process(
        {
            "action": "execute_deployment",
            "tenant_id": "tenant-rel",
            "deployment_plan_id": plan_response["deployment_plan_id"],
        }
    )
    assert execute_response["status"] == "Pending Approval"
    assert approval_stub.requests


@pytest.mark.asyncio
async def test_release_deployment_readiness_gate_blocks(tmp_path):
    agent = ReleaseDeploymentAgent(
        config={
            "quality_agent": QualityStub(passed=False),
            "change_agent": ChangeStub(approved=False),
            "risk_agent": RiskStub(acceptable=False),
            "compliance_agent": ComplianceStub(met=True),
            "release_store_path": tmp_path / "releases.json",
            "deployment_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    release_response = await agent.process(
        {
            "action": "plan_release",
            "tenant_id": "tenant-rel",
            "release": {
                "name": "Release 2",
                "target_environment": "staging",
                "planned_date": "2024-06-03",
            },
        }
    )
    plan_response = await agent.process(
        {
            "action": "create_deployment_plan",
            "tenant_id": "tenant-rel",
            "release_id": release_response["release_id"],
        }
    )
    execute_response = await agent.process(
        {
            "action": "execute_deployment",
            "tenant_id": "tenant-rel",
            "deployment_plan_id": plan_response["deployment_plan_id"],
        }
    )

    assert execute_response["status"] == "Blocked"
    assert execute_response["readiness"]["recommendation"] == "NO-GO"


@pytest.mark.asyncio
async def test_release_deployment_calendar_success(tmp_path):
    agent = ReleaseDeploymentAgent(
        config={
            "release_store_path": tmp_path / "releases.json",
            "deployment_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    response = await agent.process({"action": "get_release_calendar", "tenant_id": "tenant-rel"})

    assert "releases" in response


@pytest.mark.asyncio
async def test_release_deployment_validation_rejects_invalid_action(tmp_path):
    agent = ReleaseDeploymentAgent(config={"release_store_path": tmp_path / "releases.json"})
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_release_deployment_validation_rejects_missing_fields(tmp_path):
    agent = ReleaseDeploymentAgent(config={"release_store_path": tmp_path / "releases.json"})
    await agent.initialize()

    valid = await agent.validate_input({"action": "plan_release", "release": {"name": "X"}})

    assert valid is False


@pytest.mark.asyncio
async def test_release_deployment_configuration_drift_uses_policy(tmp_path):
    agent = ReleaseDeploymentAgent(
        config={
            "azure_policy_client": PolicyStub(),
            "release_store_path": tmp_path / "releases.json",
        }
    )
    await agent.initialize()

    env_response = await agent.process(
        {
            "action": "manage_environment",
            "environment": {
                "name": "Prod",
                "type": "production",
                "configuration": {"region": "eastus"},
            },
        }
    )

    drift_response = await agent.process(
        {"action": "check_configuration_drift", "environment_id": env_response["environment_id"]}
    )

    assert drift_response["drift_detected"] is True
    assert drift_response["policy_compliance"] == "noncompliant"


@pytest.mark.asyncio
async def test_release_deployment_release_notes_uses_openai(tmp_path):
    agent = ReleaseDeploymentAgent(
        config={
            "openai_client": OpenAIStub(),
            "release_store_path": tmp_path / "releases.json",
        }
    )
    await agent.initialize()

    release_response = await agent.process(
        {
            "action": "plan_release",
            "tenant_id": "tenant-rel",
            "release": {
                "name": "Release 3",
                "target_environment": "staging",
                "planned_date": "2024-06-05",
            },
        }
    )

    notes_response = await agent.process(
        {
            "action": "generate_release_notes",
            "release_id": release_response["release_id"],
        }
    )

    assert notes_response["content"] == "AI Release Notes"


@pytest.mark.asyncio
async def test_release_deployment_schedule_window_uses_schedule_agent(tmp_path):
    agent = ReleaseDeploymentAgent(
        config={
            "schedule_agent": ScheduleStub(),
            "schedule_agent_action": "suggest_deployment_window",
            "release_store_path": tmp_path / "releases.json",
        }
    )
    await agent.initialize()

    release_response = await agent.process(
        {
            "action": "plan_release",
            "tenant_id": "tenant-rel",
            "release": {
                "name": "Release 4",
                "target_environment": "production",
                "planned_date": "2024-06-07",
            },
        }
    )

    window_response = await agent.process(
        {
            "action": "schedule_deployment_window",
            "release_id": release_response["release_id"],
            "preferred_window": {"start_time": "2024-06-02T01:00:00"},
        }
    )

    assert window_response["scheduled_window"]["start_time"] == "2024-06-02T01:00:00"


@pytest.mark.asyncio
async def test_release_deployment_reserves_and_releases_environment(tmp_path):
    event_bus = EventBusStub()
    reservation = ReservationStub()
    agent = ReleaseDeploymentAgent(
        config={
            "event_bus": event_bus,
            "environment_reservation_client": reservation,
            "release_store_path": tmp_path / "releases.json",
            "deployment_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    release_response = await agent.process(
        {
            "action": "plan_release",
            "tenant_id": "tenant-rel",
            "release": {
                "name": "Release 5",
                "target_environment": "staging",
                "planned_date": "2024-06-09T01:00:00",
            },
        }
    )
    assert reservation.reserved
    plan_response = await agent.process(
        {
            "action": "create_deployment_plan",
            "tenant_id": "tenant-rel",
            "release_id": release_response["release_id"],
        }
    )
    await agent.process(
        {
            "action": "execute_deployment",
            "tenant_id": "tenant-rel",
            "deployment_plan_id": plan_response["deployment_plan_id"],
        }
    )
    assert reservation.released
    assert any(topic == "environment.released" for topic, _ in event_bus.published)


@pytest.mark.asyncio
async def test_release_deployment_readiness_blockers_fail(tmp_path):
    agent = ReleaseDeploymentAgent(
        config={
            "quality_agent": BlockerQualityStub(),
            "release_store_path": tmp_path / "releases.json",
        }
    )
    await agent.initialize()

    release_response = await agent.process(
        {
            "action": "plan_release",
            "tenant_id": "tenant-rel",
            "release": {
                "name": "Release 6",
                "target_environment": "staging",
                "planned_date": "2024-06-10",
            },
        }
    )
    readiness = await agent.process(
        {"action": "assess_readiness", "release_id": release_response["release_id"]}
    )
    assert readiness["recommendation"] == "NO-GO"
    assert readiness["critical_blockers"]


@pytest.mark.asyncio
async def test_release_deployment_anomaly_detection(tmp_path):
    agent = ReleaseDeploymentAgent(
        config={
            "monitoring_client": MonitoringStub(),
            "release_store_path": tmp_path / "releases.json",
        }
    )
    await agent.initialize()

    deployment_plan = {"deployment_plan_id": "plan-1"}
    anomalies = await agent._detect_post_deployment_anomalies(deployment_plan)
    assert any(anomaly["metric"] == "response_time_ms" for anomaly in anomalies)
    assert any(anomaly["metric"] == "error_rate" for anomaly in anomalies)


@pytest.mark.asyncio
async def test_release_deployment_pipeline_success_and_failure(tmp_path):
    event_bus = EventBusStub()
    agent = ReleaseDeploymentAgent(
        config={
            "event_bus": event_bus,
            "release_store_path": tmp_path / "releases.json",
            "deployment_plan_store_path": tmp_path / "plans.json",
        }
    )
    await agent.initialize()

    release_response = await agent.process(
        {
            "action": "plan_release",
            "tenant_id": "tenant-rel",
            "release": {
                "name": "Release 7",
                "target_environment": "staging",
                "planned_date": "2024-06-11",
                "deployment_strategy": "canary",
            },
        }
    )
    plan_response = await agent.process(
        {
            "action": "create_deployment_plan",
            "tenant_id": "tenant-rel",
            "release_id": release_response["release_id"],
            "deployment_plan": {"strategy": "canary"},
        }
    )
    success_response = await agent.process(
        {
            "action": "execute_deployment",
            "tenant_id": "tenant-rel",
            "deployment_plan_id": plan_response["deployment_plan_id"],
        }
    )
    assert success_response["status"] in {"Completed", "Failed"}
    assert any(topic == "deployment.started" for topic, _ in event_bus.published)

    failing_plan_response = await agent.process(
        {
            "action": "create_deployment_plan",
            "tenant_id": "tenant-rel",
            "release_id": release_response["release_id"],
            "deployment_plan": {
                "strategy": "rolling",
                "custom_steps": [{"step": 1, "action": "Deploy", "should_fail": True}],
            },
        }
    )
    failure_response = await agent.process(
        {
            "action": "execute_deployment",
            "tenant_id": "tenant-rel",
            "deployment_plan_id": failing_plan_response["deployment_plan_id"],
        }
    )
    assert failure_response["status"] == "Failed"
