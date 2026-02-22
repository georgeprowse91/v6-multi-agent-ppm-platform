from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKFLOW_SRC = Path(__file__).resolve().parents[2] / "apps" / "workflow-engine" / "src"
sys.path.insert(0, str(WORKFLOW_SRC))

from workflow_runtime import WorkflowRuntime  # noqa: E402
from workflow_storage import WorkflowStore  # noqa: E402


class DummyApprovalAgent:
    async def process(self, payload: dict) -> dict:
        return {"approval_id": "approval-1"}


class DummyAgentClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def execute(self, agent_id: str, action: str, payload: dict, context: dict) -> dict:
        self.calls.append({"agent_id": agent_id, "action": action})
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_parallel_workflow_completes(tmp_path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    agent_client = DummyAgentClient()
    runtime = WorkflowRuntime(store, DummyApprovalAgent(), agent_client)
    definition = {
        "metadata": {"name": "Parallel workflow"},
        "steps": [
            {
                "id": "start",
                "type": "task",
                "next": "parallel-work",
                "config": {"agent": "agent-a", "action": "start"},
            },
            {
                "id": "parallel-work",
                "type": "parallel",
                "join": "join-step",
                "branches": [
                    {"name": "a", "next": "branch-a"},
                    {"name": "b", "next": "branch-b"},
                ],
            },
            {
                "id": "branch-a",
                "type": "task",
                "next": None,
                "config": {"agent": "agent-a", "action": "branch"},
            },
            {
                "id": "branch-b",
                "type": "task",
                "next": None,
                "config": {"agent": "agent-b", "action": "branch"},
            },
            {
                "id": "join-step",
                "type": "notification",
                "next": None,
                "config": {"channel": "teams", "template": "joined"},
            },
        ],
    }
    instance = store.create("run-parallel", "workflow-parallel", "tenant-1", payload={})

    result = await runtime.start(instance, definition, actor={"id": "user-1"})

    assert result.status == "completed"
    assert store.get_step_state(result.run_id, "branch-a")
    assert store.get_step_state(result.run_id, "branch-b")
    assert store.get_step_state(result.run_id, "join-step")
    assert any(call["agent_id"] == "agent-b" for call in agent_client.calls)


@pytest.mark.asyncio
async def test_loop_workflow_iterations(tmp_path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    agent_client = DummyAgentClient()
    runtime = WorkflowRuntime(store, DummyApprovalAgent(), agent_client)
    definition = {
        "metadata": {"name": "Loop workflow"},
        "steps": [
            {
                "id": "initialize",
                "type": "task",
                "next": "monitor-loop",
                "config": {"agent": "agent-a", "action": "init"},
            },
            {
                "id": "monitor-loop",
                "type": "loop",
                "next": "loop-task",
                "exit": "finish",
                "max_iterations": 2,
                "condition": {"field": "$.payload.status", "operator": "equals", "value": "open"},
            },
            {
                "id": "loop-task",
                "type": "task",
                "next": "monitor-loop",
                "config": {"agent": "agent-a", "action": "refresh"},
            },
            {
                "id": "finish",
                "type": "notification",
                "next": None,
                "config": {"channel": "teams", "template": "done"},
            },
        ],
    }
    instance = store.create("run-loop", "workflow-loop", "tenant-1", payload={"status": "open"})

    result = await runtime.start(instance, definition, actor={"id": "user-1"})

    assert result.status == "completed"
    loop_state = store.get_step_state(result.run_id, "monitor-loop")
    assert loop_state is not None
    assert loop_state.attempts == 2
    assert store.get_step_state(result.run_id, "finish")
