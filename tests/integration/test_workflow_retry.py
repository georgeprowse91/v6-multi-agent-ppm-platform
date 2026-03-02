from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKFLOW_SRC = Path(__file__).resolve().parents[2] / "apps" / "workflow-service" / "src"
sys.path.insert(0, str(WORKFLOW_SRC))

from workflow_runtime import WorkflowRuntime  # noqa: E402
from workflow_storage import WorkflowStore  # noqa: E402


class DummyApprovalAgent:
    async def process(self, payload: dict) -> dict:
        return {"approval_id": "approval-1"}


class FlakyAgentClient:
    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.calls = 0

    async def execute(self, agent_id: str, action: str, payload: dict, context: dict) -> dict:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("transient failure")
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_workflow_retries_task_failures(tmp_path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    agent_client = FlakyAgentClient(fail_times=2)
    runtime = WorkflowRuntime(store, DummyApprovalAgent(), agent_client)
    definition = {
        "metadata": {"name": "Retry workflow"},
        "steps": [
            {
                "id": "task-1",
                "type": "task",
                "next": None,
                "retry": {"max_attempts": 3, "delay_seconds": 0},
                "config": {"agent": "test-agent-alpha", "action": "run"},
            }
        ],
    }
    instance = store.create("run-1", "workflow-1", "tenant-1", payload={})

    result = await runtime.start(instance, definition, actor={"id": "user-1"})

    assert result.status == "completed"
    state = store.get_step_state(result.run_id, "task-1")
    assert state is not None
    assert state.status == "completed"
    assert state.attempts == 3
    assert agent_client.calls == 3
