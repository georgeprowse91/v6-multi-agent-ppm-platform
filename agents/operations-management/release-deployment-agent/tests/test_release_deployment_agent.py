import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.extend([str(REPO_ROOT), str(AGENT_SRC)])

from release_deployment_agent import ReleaseDeploymentAgent  # noqa: E402


class FakeDbService:
    def __init__(self) -> None:
        self.records = {}

    async def store(self, collection: str, key: str, payload: dict) -> None:
        self.records.setdefault(collection, {})[key] = payload


class FakeEventBus:
    def __init__(self) -> None:
        self.events = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class FakeDocService:
    async def publish_release_notes(self, **kwargs):  # type: ignore[no-untyped-def]
        return {"url": "https://docs.example/release", "platform": "mock"}


class FakeVcsClient:
    def __init__(self) -> None:
        self.restored = None

    async def restore_release(self, release_id):  # type: ignore[no-untyped-def]
        self.restored = release_id
        return {"success": True, "restored_release": release_id}


class FakeTrackingClient:
    async def get_records(self, release_id, record_type):  # type: ignore[no-untyped-def]
        return [
            {"id": f"{record_type}-1", "description": f"{record_type} item"},
        ]


@pytest.mark.anyio
async def test_readiness_assessment_persists_and_emits_event():
    agent = ReleaseDeploymentAgent(config={})
    agent.db_service = FakeDbService()
    agent.event_bus = FakeEventBus()
    release_id = "REL-TEST"
    agent.releases[release_id] = {
        "release_id": release_id,
        "name": "Test Release",
        "target_environment": "staging",
    }

    result = await agent._assess_readiness(release_id)

    assert result["assessment_id"] in agent.readiness_assessments
    assert "readiness_assessments" in agent.db_service.records
    assert any(event[0] == "deployment.readiness_assessed" for event in agent.event_bus.events)


class OptimizedAgent(ReleaseDeploymentAgent):
    async def _fetch_resource_availability(self, environment: str):
        return {"capacity_score": 0.9}

    async def _fetch_risk_exposure(self, environment: str):
        return {"risk_score": 0.1}

    async def _fetch_system_health(self, environment: str):
        return {"health_score": 0.95}

    async def _fetch_business_calendar(self, environment: str):
        return {"blackout": False}

    async def _analyze_usage_patterns(self, environment: str):
        return {"low_usage_hours": [2], "peak_hours": [10, 11]}


@pytest.mark.anyio
async def test_optimization_suggests_scored_windows():
    agent = OptimizedAgent(config={})
    windows = await agent._suggest_alternative_windows("2024-01-01T02:00:00", "production")
    assert windows
    assert all("score" in window for window in windows)
    assert windows[0]["score"] >= windows[-1]["score"]


@pytest.mark.anyio
async def test_rollback_executes_and_emits_events():
    agent = ReleaseDeploymentAgent(config={"version_control_client": FakeVcsClient()})
    agent.db_service = FakeDbService()
    agent.event_bus = FakeEventBus()
    deployment_plan_id = "DEPLOY-TEST"
    agent.deployment_plans[deployment_plan_id] = {
        "deployment_plan_id": deployment_plan_id,
        "release_id": "REL-123",
        "environment": "production",
        "strategy": "rolling",
        "rollback_procedures": [{"step": 1, "action": "Restore"}],
        "previous_release": "REL-122",
    }
    agent.deployment_artifacts[deployment_plan_id] = [
        {"artifact_id": "artifact-1", "version": "1.2.3"}
    ]

    result = await agent._rollback_deployment(deployment_plan_id)

    assert result["rollback_status"] == "Success"
    assert any(event[0] == "deployment.rollback.started" for event in agent.event_bus.events)
    assert any(event[0] == "deployment.rollback.completed" for event in agent.event_bus.events)


@pytest.mark.anyio
async def test_release_notes_include_tracking_records():
    agent = ReleaseDeploymentAgent(config={"tracking_clients": [FakeTrackingClient()]})
    agent.db_service = FakeDbService()
    agent.doc_publishing_service = FakeDocService()
    release_id = "REL-TRACK"
    agent.releases[release_id] = {
        "release_id": release_id,
        "name": "Tracked Release",
        "target_environment": "production",
        "planned_date": "2024-01-01T00:00:00",
    }

    notes = await agent._generate_release_notes(release_id)

    assert notes["features_count"] == 1
    assert notes["bug_fixes_count"] == 1
    assert notes["known_issues_count"] == 1


@pytest.mark.anyio
async def test_environment_reservation_and_release():
    agent = ReleaseDeploymentAgent(config={})
    agent.db_service = FakeDbService()
    agent.event_bus = FakeEventBus()
    allocation = await agent._reserve_environment(
        environment="staging",
        planned_date="2024-01-01T00:00:00",
        release_id="REL-RESERVE",
    )
    assert allocation is not None
    await agent._release_environment_allocation("REL-RESERVE", "DEPLOY-RESERVE")
    assert allocation["status"] == "released"
