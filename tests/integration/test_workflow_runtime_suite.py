from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

WORKFLOW_SRC = Path(__file__).resolve().parents[2] / "apps" / "workflow-service" / "src"
sys.path.insert(0, str(WORKFLOW_SRC))

from workflow_runtime import WorkflowRuntime  # noqa: E402
from workflow_storage import WorkflowStore  # noqa: E402


class FakeApprovalAgent:
    async def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"approval_id": "approval-1"}


class FakeAgentClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def execute(
        self, agent_id: str, action: str, payload: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "agent_id": agent_id,
                "action": action,
                "step_id": payload.get("step_id"),
                "compensation": payload.get("compensation", False),
            }
        )
        return {"ok": True}


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.events.append((topic, payload))


@pytest.mark.asyncio
async def test_runtime_sequences_and_branches_with_events(tmp_path: Path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    event_bus = FakeEventBus()
    agent_client = FakeAgentClient()
    store.ping()
    runtime = WorkflowRuntime(
        store, FakeApprovalAgent(), agent_client=agent_client, event_bus=event_bus
    )

    definition = {
        "steps": [
            {
                "id": "start",
                "type": "task",
                "next": "route",
                "config": {"agent": "a1", "action": "begin"},
            },
            {
                "id": "route",
                "type": "decision",
                "branches": [
                    {
                        "condition": {
                            "field": "$.payload.priority",
                            "operator": "equals",
                            "value": "high",
                        },
                        "next": "vip",
                    }
                ],
                "default_next": "normal",
            },
            {
                "id": "vip",
                "type": "task",
                "next": "finish",
                "config": {"agent": "a2", "action": "expedite"},
            },
            {
                "id": "normal",
                "type": "task",
                "next": "finish",
                "config": {"agent": "a3", "action": "standard"},
            },
            {
                "id": "finish",
                "type": "notification",
                "config": {"channel": "email", "template": "done"},
            },
        ]
    }
    instance = store.create("run-1", "wf-1", "tenant-1", payload={"priority": "high"})

    completed = await runtime.start(instance, definition, actor={"id": "u-1"})

    assert completed.status == "completed"
    assert [call["step_id"] for call in agent_client.calls] == ["start", "vip"]
    assert store.get_step_state("run-1", "route").status == "completed"
    topics = [topic for topic, _ in event_bus.events]
    assert "workflow.started" in topics
    assert topics[-1] == "workflow.completed"


@pytest.mark.asyncio
async def test_runtime_parallel_join_and_failure_compensation(tmp_path: Path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    event_bus = FakeEventBus()
    agent_client = FakeAgentClient()
    store.ping()
    runtime = WorkflowRuntime(
        store, FakeApprovalAgent(), agent_client=agent_client, event_bus=event_bus
    )

    definition = {
        "steps": [
            {
                "id": "setup",
                "type": "task",
                "next": "fanout",
                "config": {"agent": "setup-agent", "action": "setup"},
                "compensation": {"agent": "undo-agent", "action": "rollback"},
            },
            {
                "id": "fanout",
                "type": "parallel",
                "branches": [{"next": "branch-a"}, {"next": "branch-b"}],
                "join": "join",
            },
            {
                "id": "branch-a",
                "type": "task",
                "next": None,
                "config": {"agent": "a", "action": "run"},
            },
            {
                "id": "branch-b",
                "type": "task",
                "next": None,
                "config": {"agent": "b", "action": "run"},
            },
            {
                "id": "join",
                "type": "task",
                "next": "broken",
                "config": {"agent": "joiner", "action": "combine"},
            },
            {"id": "broken", "type": "task", "config": {}},
        ]
    }
    instance = store.create("run-2", "wf-2", "tenant-1", payload={})

    failed = await runtime.start(instance, definition, actor={"id": "u-2"})

    assert failed.status == "failed"
    assert store.get_step_state("run-2", "branch-a").status == "completed"
    assert store.get_step_state("run-2", "branch-b").status == "completed"
    assert any(call["compensation"] for call in agent_client.calls)
    workflow_journal = store.list_journal_entries("run-2", phase="workflow")
    assert workflow_journal[-1].status == "failing"
    compensation_events = [event.status for event in store.list_events("run-2")]
    assert "compensated" in compensation_events
