from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

WORKFLOW_SRC = Path(__file__).resolve().parents[2] / "apps" / "workflow-service" / "src"
if str(WORKFLOW_SRC) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_SRC))

import types

fake_approval_module = types.ModuleType("approval_workflow_agent")


class _ApprovalWorkflowAgent:
    async def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"approval_id": "approval-1"}


fake_approval_module.ApprovalWorkflowAgent = _ApprovalWorkflowAgent
sys.modules.setdefault("approval_workflow_agent", fake_approval_module)

from workflow_runtime import WorkflowRuntime  # noqa: E402
from workflow_storage import WorkflowStore  # noqa: E402


class DummyApprovalAgent:
    async def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"approval_id": "approval-1"}


class CompensationAwareAgentClient:
    def __init__(self) -> None:
        self.task_calls = 0
        self.compensation_calls = 0

    async def execute(
        self, agent_id: str, action: str, payload: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        if payload.get("compensation"):
            self.compensation_calls += 1
            return {"status": "compensated"}
        self.task_calls += 1
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_partial_failure_runs_reverse_compensation(tmp_path: Path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    store.ping()
    client = CompensationAwareAgentClient()
    runtime = WorkflowRuntime(store, DummyApprovalAgent(), client)
    definition = {
        "steps": [
            {
                "id": "step-a",
                "type": "task",
                "next": "step-b",
                "config": {"agent": "agent-a", "action": "do-a"},
                "compensation": {"agent": "agent-a", "action": "undo-a"},
            },
            {
                "id": "step-b",
                "type": "task",
                "next": None,
                "config": {"agent": "agent-b"},
            },
        ]
    }
    instance = store.create("run-comp-1", "workflow-comp", "tenant-1", {"payload": True})

    result = await runtime.start(instance, definition, {"id": "actor-1"})

    assert result.status == "failed"
    compensation = store.list_journal_entries(result.run_id, phase="compensation", step_id="step-a")
    assert any(entry.status == "completed" for entry in compensation)
    assert client.compensation_calls == 1


@pytest.mark.asyncio
async def test_compensation_idempotent_on_manual_retry(tmp_path: Path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    store.ping()
    client = CompensationAwareAgentClient()
    runtime = WorkflowRuntime(store, DummyApprovalAgent(), client)
    definition = {
        "steps": [
            {
                "id": "step-a",
                "type": "task",
                "next": "step-b",
                "config": {"agent": "agent-a", "action": "do-a"},
                "compensation": {"agent": "agent-a", "action": "undo-a"},
            },
            {
                "id": "step-b",
                "type": "task",
                "next": None,
                "config": {"agent": "agent-b"},
            },
        ]
    }
    instance = store.create("run-comp-2", "workflow-comp", "tenant-1", {"payload": True})

    await runtime.start(instance, definition, {"id": "actor-1"})
    calls_after_failure = client.compensation_calls

    await runtime.retry_compensation(store.get("run-comp-2"), definition, {"id": "actor-1"})

    assert client.compensation_calls == calls_after_failure


class FlakyCompensationClient(CompensationAwareAgentClient):
    def __init__(self) -> None:
        super().__init__()
        self.first_compensation = True

    async def execute(
        self, agent_id: str, action: str, payload: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        if payload.get("compensation") and self.first_compensation:
            self.first_compensation = False
            self.compensation_calls += 1
            raise RuntimeError("transient")
        return await super().execute(agent_id, action, payload, context)


@pytest.mark.asyncio
async def test_resume_after_crash_retries_failed_compensation(tmp_path: Path) -> None:
    store = WorkflowStore(tmp_path / "workflow.db")
    store.ping()
    runtime = WorkflowRuntime(store, DummyApprovalAgent(), FlakyCompensationClient())
    definition = {
        "steps": [
            {
                "id": "step-a",
                "type": "task",
                "next": None,
                "config": {"agent": "agent-a", "action": "do-a"},
                "compensation": {
                    "agent": "agent-a",
                    "action": "undo-a",
                    "retry": {"max_attempts": 2, "delay_seconds": 0},
                },
            }
        ]
    }
    instance = store.create("run-comp-3", "workflow-comp", "tenant-1", {"payload": True})
    store.add_journal_entry(
        instance.run_id,
        phase="execution",
        status="completed",
        attempt=1,
        step_id="step-a",
        details={"compensable": True},
    )
    store.update_status(instance.run_id, "compensation_failed", "step-a")

    recovered = await runtime.retry_compensation(instance, definition, {"id": "recovery-actor"})

    assert recovered.status == "failed"
    compensation = store.list_journal_entries(
        instance.run_id, phase="compensation", step_id="step-a"
    )
    assert any(entry.status == "failed" for entry in compensation)
    assert any(entry.status == "completed" for entry in compensation)
