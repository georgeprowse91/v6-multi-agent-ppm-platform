from __future__ import annotations

import asyncio
import time
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from agents.runtime.src.base_agent import BaseAgent
from agents.runtime.src.event_bus import InMemoryEventBus
from agents.runtime.src.memory_store import InMemoryConversationStore
from agents.runtime.src.orchestrator import AgentTask, Orchestrator, RetryPolicy

ORCHESTRATOR_SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "orchestration-service"
    / "src"
    / "orchestrator.py"
)


def _load_service_orchestrator():
    spec = spec_from_file_location("orchestration_service_orchestrator", ORCHESTRATOR_SERVICE_PATH)
    if not spec or not spec.loader:
        raise ImportError("Unable to load orchestration service orchestrator module")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.AgentOrchestrator


class SleepAgent(BaseAgent):
    def __init__(self, agent_id: str, delay: float, payload: str) -> None:
        super().__init__(agent_id)
        self.delay = delay
        self.payload = payload

    async def process(self, input_data: dict) -> dict:
        await asyncio.sleep(self.delay)
        return {"payload": self.payload, "deps": input_data.get("dependency_results", {})}


class FlakyAgent(BaseAgent):
    def __init__(self, agent_id: str) -> None:
        super().__init__(agent_id)
        self.attempts = 0

    async def process(self, input_data: dict) -> dict:
        self.attempts += 1
        if self.attempts < 2:
            raise RuntimeError("transient")
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_orchestrator_runs_dag_in_parallel() -> None:
    event_bus = InMemoryEventBus()
    orchestrator = Orchestrator(event_bus=event_bus, max_parallel_tasks=2)

    start_times: dict[str, float] = {}
    completion_times: dict[str, float] = {}
    metrics: list[dict] = []

    async def on_start(payload: dict) -> None:
        start_times[payload["task_id"]] = time.monotonic()

    async def on_complete(payload: dict) -> None:
        completion_times[payload["task_id"]] = time.monotonic()

    async def on_metrics(payload: dict) -> None:
        metrics.append(payload)

    event_bus.subscribe("orchestrator.task.started", on_start)
    event_bus.subscribe("orchestrator.task.completed", on_complete)
    event_bus.subscribe("orchestrator.metrics", on_metrics)

    tasks = [
        AgentTask(task_id="a", agent=SleepAgent("agent-a", 0.05, "a")),
        AgentTask(task_id="b", agent=SleepAgent("agent-b", 0.1, "b"), depends_on=["a"]),
        AgentTask(task_id="c", agent=SleepAgent("agent-c", 0.1, "c"), depends_on=["a"]),
    ]

    result = await orchestrator.run(tasks, context={"correlation_id": "dag-test"})

    assert result.metrics["max_parallel_tasks"] >= 2
    assert any(metric["active_tasks"] == 2 for metric in metrics)
    assert start_times["a"] < start_times["b"]
    assert start_times["a"] < start_times["c"]
    assert completion_times["a"] <= start_times["b"]
    assert completion_times["a"] <= start_times["c"]


@pytest.mark.asyncio
async def test_orchestrator_retries_transient_failures() -> None:
    retry_policy = RetryPolicy(
        max_attempts=3,
        base_delay_seconds=0,
        max_delay_seconds=0,
        jitter_seconds=0,
        retry_predicate=lambda exc, response: bool(exc) or not response.get("success", False),
    )
    orchestrator = Orchestrator(retry_policy=retry_policy, max_parallel_tasks=1)
    agent = FlakyAgent("flaky")
    tasks = [AgentTask(task_id="flaky-task", agent=agent)]

    result = await orchestrator.run(tasks)

    assert agent.attempts == 2
    assert result.results["flaky-task"]["success"] is True


@pytest.mark.asyncio
async def test_orchestrator_persists_memory_across_calls() -> None:
    memory_store = InMemoryConversationStore()
    orchestrator = Orchestrator(memory_store=memory_store)
    tasks = [AgentTask(task_id="first", agent=SleepAgent("agent-1", 0, "one"))]

    await orchestrator.run(tasks, memory_key="conversation-1")
    await orchestrator.run(tasks, memory_key="conversation-1")

    persisted = await memory_store.load("conversation-1")
    history = persisted.get("history", [])
    assert len(history) == 2


@pytest.mark.asyncio
async def test_service_orchestrator_calls_workflow_client() -> None:
    AgentOrchestrator = _load_service_orchestrator()

    class StubWorkflowClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        async def start_workflow(
            self, payload: dict, headers: dict[str, str]
        ) -> dict[str, str]:
            self.calls.append({"payload": payload, "headers": headers})
            return {"run_id": "run-123"}

    workflow_client = StubWorkflowClient()
    orchestrator = AgentOrchestrator(workflow_client=workflow_client)

    response = await orchestrator.start_workflow(
        tenant_id="tenant-1",
        workflow_id="intake-triage",
        payload={"request": "run"},
        actor={"id": "user-1", "type": "user", "roles": ["PMO_ADMIN"]},
        headers={"Authorization": "Bearer token"},
    )

    assert response["run_id"] == "run-123"
    assert workflow_client.calls
    assert workflow_client.calls[0]["payload"]["workflow_id"] == "intake-triage"
    assert workflow_client.calls[0]["headers"]["X-Tenant-ID"] == "tenant-1"
