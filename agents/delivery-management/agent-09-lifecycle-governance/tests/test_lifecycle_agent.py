from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[3]
SRC_DIR = TESTS_DIR.parent / "src"
APPROVAL_SRC = (
    REPO_ROOT / "agents" / "core-orchestration" / "agent-03-approval-workflow" / "src"
)
CONTRACTS_SRC = REPO_ROOT / "packages" / "contracts" / "src"
OBSERVABILITY_SRC = REPO_ROOT / "packages" / "observability" / "src"
sys.path.extend(
    [
        str(SRC_DIR),
        str(REPO_ROOT),
        str(REPO_ROOT / "packages"),
        str(APPROVAL_SRC),
        str(CONTRACTS_SRC),
        str(OBSERVABILITY_SRC),
    ]
)

from notifications import NotificationService
from readiness_model import ReadinessScoringModel
from sync_clients import ExternalSyncService
from project_lifecycle_agent import ProjectLifecycleAgent


class DummyEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []
        self.subscriptions: dict[str, list] = {}

    def subscribe(self, topic: str, handler: object) -> None:
        self.subscriptions.setdefault(topic, []).append(handler)

    async def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))


class FakeConnector:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def write(self, _resource: str, payload: dict) -> dict:
        self.calls.append(payload)
        return {"status": "ok"}


class DummyApprovalAgent:
    async def process(self, _payload: dict) -> dict:
        return {"status": "approved", "approval_id": "ap-1"}


@pytest.mark.anyio
async def test_gate_transition_persists_and_publishes() -> None:
    event_bus = DummyEventBus()
    planview = FakeConnector()
    clarity = FakeConnector()
    jira = FakeConnector()
    azure_devops = FakeConnector()
    external_sync = ExternalSyncService(
        planview=planview, clarity=clarity, jira=jira, azure_devops=azure_devops
    )
    agent = ProjectLifecycleAgent(
        config={
            "event_bus": event_bus,
            "external_sync": external_sync,
            "notification_service": NotificationService(),
            "approval_agent": DummyApprovalAgent(),
        }
    )
    project_id = "P-100"
    await agent._initiate_project(
        {"project_id": project_id, "name": "Apollo", "methodology": "waterfall"},
        tenant_id="tenant-a",
    )
    agent.projects[project_id]["artifacts"] = {"deliverables": {"complete": True}}
    agent.projects[project_id]["metrics"] = {"quality_score": 0.9}

    result = await agent._transition_phase(
        project_id,
        "Plan",
        tenant_id="tenant-a",
        correlation_id="corr-1",
        actor_id="user-1",
    )

    assert result["success"] is True
    assert any(topic == "gate.passed" for topic, _payload in event_bus.published)
    assert any(topic == "project.transitioned" for topic, _payload in event_bus.published)
    assert agent.persistence.gate_history
    assert planview.calls and clarity.calls and jira.calls and azure_devops.calls


def test_readiness_model_training() -> None:
    model = ReadinessScoringModel()
    samples = [
        {"features": {"criteria_ratio": 1.0, "schedule_score": 0.9}, "label": 1.0},
        {"features": {"criteria_ratio": 0.2, "schedule_score": 0.4}, "label": 0.0},
    ]
    model.fit(samples, iterations=100, lr=0.2)
    high_score = model.predict({"criteria_ratio": 1.0, "schedule_score": 0.9})
    low_score = model.predict({"criteria_ratio": 0.2, "schedule_score": 0.4})
    assert high_score > low_score
