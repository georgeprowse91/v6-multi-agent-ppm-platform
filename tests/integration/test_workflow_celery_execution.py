from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("celery")

WORKFLOW_SRC = Path(__file__).resolve().parents[2] / "services" / "workflow-service" / "src"
WORKFLOW_PACKAGE = Path(__file__).resolve().parents[2] / "packages" / "workflow" / "src"
for path in (WORKFLOW_SRC, WORKFLOW_PACKAGE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from workflow_storage import WorkflowStore  # noqa: E402


class DummyAgentClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def execute(self, agent_id: str, action: str, payload: dict, context: dict) -> dict:
        self.calls.append({"agent_id": agent_id, "action": action})
        return {"status": "ok"}


def _reload_workflow_modules():
    celery_app_module = importlib.import_module("workflow.celery_app")
    importlib.reload(celery_app_module)
    workflow_tasks = importlib.import_module("workflow.tasks")
    importlib.reload(workflow_tasks)
    return workflow_tasks


def test_celery_workflow_completes(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_DB_PATH", str(tmp_path / "workflow.db"))
    monkeypatch.setenv("WORKFLOW_CELERY_EAGER", "true")
    monkeypatch.setenv("WORKFLOW_BROKER_URL", "memory://")
    monkeypatch.setenv("WORKFLOW_RESULT_BACKEND", "cache+memory://")

    workflow_tasks = _reload_workflow_modules()
    workflow_tasks._CONTEXT = None
    workflow_tasks.AGENT_CLIENT_OVERRIDE = DummyAgentClient()

    store = WorkflowStore(tmp_path / "workflow.db")
    definition = {
        "metadata": {"name": "Celery Workflow", "version": "v1", "owner": "test"},
        "steps": [
            {
                "id": "step-1",
                "type": "task",
                "next": "step-2",
                "config": {"agent": "test-agent-alpha", "action": "do"},
            },
            {
                "id": "step-2",
                "type": "task",
                "config": {"agent": "test-agent-alpha", "action": "finish"},
            },
        ],
    }
    store.upsert_definition("workflow-1", definition)
    store.create("run-1", "workflow-1", "tenant-1", payload={}, current_step_id="step-1")

    dispatcher_module = importlib.import_module("workflow.dispatcher")
    importlib.reload(dispatcher_module)
    dispatcher = dispatcher_module.WorkflowDispatcher()
    dispatcher.dispatch_step("run-1", "step-1", {"id": "tester"})

    instance = store.get("run-1")
    assert instance is not None
    assert instance.status == "completed"
    assert workflow_tasks.AGENT_CLIENT_OVERRIDE.calls


def test_celery_workflow_retries(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_DB_PATH", str(tmp_path / "workflow.db"))
    monkeypatch.setenv("WORKFLOW_CELERY_EAGER", "true")
    monkeypatch.setenv("WORKFLOW_BROKER_URL", "memory://")
    monkeypatch.setenv("WORKFLOW_RESULT_BACKEND", "cache+memory://")

    workflow_tasks = _reload_workflow_modules()
    workflow_tasks._CONTEXT = None
    workflow_tasks.AGENT_CLIENT_OVERRIDE = DummyAgentClient()

    store = WorkflowStore(tmp_path / "workflow.db")
    definition = {
        "metadata": {"name": "Retry Workflow", "version": "v1", "owner": "test"},
        "steps": [
            {
                "id": "step-1",
                "type": "task",
                "config": {
                    "agent": "test-agent-alpha",
                    "action": "do",
                    "failures_before_success": 2,
                },
                "retry": {"max_attempts": 3, "delay_seconds": 0},
            }
        ],
    }
    store.upsert_definition("workflow-1", definition)
    store.create("run-1", "workflow-1", "tenant-1", payload={}, current_step_id="step-1")

    dispatcher_module = importlib.import_module("workflow.dispatcher")
    importlib.reload(dispatcher_module)
    dispatcher = dispatcher_module.WorkflowDispatcher()
    dispatcher.dispatch_step("run-1", "step-1", {"id": "tester"})

    instance = store.get("run-1")
    assert instance is not None
    assert instance.status == "completed"
    step_state = store.get_step_state("run-1", "step-1")
    assert step_state is not None
    assert step_state.attempts == 3
