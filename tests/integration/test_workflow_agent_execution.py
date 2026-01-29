from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

WORKFLOW_SRC = Path(__file__).resolve().parents[2] / "apps" / "workflow-engine" / "src"
if str(WORKFLOW_SRC) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_SRC))

from workflow_runtime import WorkflowRuntime  # noqa: E402
from workflow_storage import WorkflowStore  # noqa: E402


class DummyApprovalAgent:
    async def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"approval_id": "approval-1"}


class RecordingAgentClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def execute(
        self, agent_id: str, action: str, payload: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        self.calls.append(
            {"agent_id": agent_id, "action": action, "payload": payload, "context": context}
        )
        return {"result": "ok"}


class FailingAgentClient:
    async def execute(
        self, agent_id: str, action: str, payload: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        raise RuntimeError("agent failure")


@pytest.mark.asyncio
async def test_task_step_executes_agent(tmp_path: Path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    agent_client = RecordingAgentClient()
    runtime = WorkflowRuntime(store, DummyApprovalAgent(), agent_client)
    definition = {
        "steps": [
            {
                "id": "task-step",
                "type": "task",
                "next": None,
                "config": {"agent": "demand_intake_agent", "action": "capture_request"},
            }
        ]
    }
    instance = store.create("run-1", "workflow-1", "tenant-1", {"request": "hello"})

    result = await runtime.start(instance, definition, {"id": "actor-1"})

    assert result.status == "completed"
    step_state = store.get_step_state(result.run_id, "task-step")
    assert step_state
    assert step_state.output["agent"] == "demand_intake_agent"
    assert step_state.output["response"] == {"result": "ok"}
    assert agent_client.calls


@pytest.mark.asyncio
async def test_failed_agent_call_marks_step_failed(tmp_path: Path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    runtime = WorkflowRuntime(store, DummyApprovalAgent(), FailingAgentClient())
    definition = {
        "steps": [
            {
                "id": "task-step",
                "type": "task",
                "next": None,
                "config": {"agent": "risk_management_agent", "action": "score_risk"},
            }
        ]
    }
    instance = store.create("run-2", "workflow-2", "tenant-2", {"request": "hello"})

    result = await runtime.start(instance, definition, {"id": "actor-2"})

    assert result.status == "failed"
    step_state = store.get_step_state(result.run_id, "task-step")
    assert step_state
    assert step_state.status == "failed"
    assert "Agent call failed" in (step_state.error or "")
