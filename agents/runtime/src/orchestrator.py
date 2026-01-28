from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from agents.runtime.src.base_agent import BaseAgent
from agents.runtime.src.event_bus import InMemoryEventBus
from agents.runtime.src.memory_store import ConversationMemoryStore, InMemoryConversationStore

RetryPredicate = Callable[[Exception | None, dict[str, Any] | None], bool]


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0
    jitter_seconds: float = 0.2
    retry_predicate: RetryPredicate | None = None

    def should_retry(self, exc: Exception | None, response: dict[str, Any] | None) -> bool:
        if self.retry_predicate is not None:
            return self.retry_predicate(exc, response)
        if exc is not None:
            return True
        if response is None:
            return False
        return not response.get("success", False)


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    agent: BaseAgent
    input_data: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OrchestrationResult:
    results: dict[str, dict[str, Any]]
    context: dict[str, Any]
    metrics: dict[str, Any]


class Orchestrator:
    """Async orchestration engine for running agent DAGs."""

    def __init__(
        self,
        *,
        event_bus: InMemoryEventBus | None = None,
        memory_store: ConversationMemoryStore | None = None,
        retry_policy: RetryPolicy | None = None,
        max_parallel_tasks: int = 4,
    ) -> None:
        self._event_bus = event_bus or InMemoryEventBus()
        self._memory_store = memory_store or InMemoryConversationStore()
        self._retry_policy = retry_policy or RetryPolicy()
        self._max_parallel_tasks = max_parallel_tasks
        self._active_tasks = 0
        self._max_parallel_seen = 0
        self._context_lock = asyncio.Lock()

    @property
    def event_bus(self) -> InMemoryEventBus:
        return self._event_bus

    async def run(
        self,
        tasks: list[AgentTask],
        *,
        context: dict[str, Any] | None = None,
        memory_key: str | None = None,
    ) -> OrchestrationResult:
        if not tasks:
            return OrchestrationResult(results={}, context=context or {}, metrics={})

        task_lookup = {task.task_id: task for task in tasks}
        self._validate_tasks(task_lookup)
        resolved_memory_key = memory_key or (context or {}).get("correlation_id") or "default"
        shared_context = await self._load_context(resolved_memory_key, context or {})
        results: dict[str, dict[str, Any]] = {}

        pending_deps = {task_id: set(task.depends_on) for task_id, task in task_lookup.items()}
        dependents: dict[str, set[str]] = {task_id: set() for task_id in task_lookup}
        for task in tasks:
            for dependency in task.depends_on:
                dependents[dependency].add(task.task_id)

        semaphore = asyncio.Semaphore(self._max_parallel_tasks)
        ready_queue = [task_id for task_id, deps in pending_deps.items() if not deps]
        running: dict[asyncio.Task[tuple[str, dict[str, Any]]], str] = {}

        async def _launch(task_id: str) -> None:
            task = task_lookup[task_id]
            running_task = asyncio.create_task(
                self._run_task(
                    task,
                    shared_context,
                    results,
                    resolved_memory_key,
                    semaphore,
                )
            )
            running[running_task] = task_id

        for task_id in ready_queue:
            await _launch(task_id)

        while running:
            done, _ = await asyncio.wait(running.keys(), return_when=asyncio.FIRST_COMPLETED)
            for completed in done:
                task_id = running.pop(completed)
                result_task_id, result_payload = completed.result()
                results[result_task_id] = result_payload
                for dependent_id in dependents.get(task_id, set()):
                    pending = pending_deps[dependent_id]
                    pending.discard(task_id)
                    if not pending:
                        await _launch(dependent_id)

        await self._memory_store.save(resolved_memory_key, shared_context)
        metrics = {
            "max_parallel_tasks": self._max_parallel_seen,
            "total_tasks": len(tasks),
        }
        return OrchestrationResult(results=results, context=shared_context, metrics=metrics)

    async def _run_task(
        self,
        task: AgentTask,
        shared_context: dict[str, Any],
        results: dict[str, dict[str, Any]],
        memory_key: str,
        semaphore: asyncio.Semaphore,
    ) -> tuple[str, dict[str, Any]]:
        async with semaphore:
            async with self._context_lock:
                self._active_tasks += 1
                self._max_parallel_seen = max(self._max_parallel_seen, self._active_tasks)
                await self._publish_metrics()

            dependency_results = {dep: results[dep] for dep in task.depends_on}
            input_data = {
                **task.input_data,
                "context": shared_context,
                "dependency_results": dependency_results,
            }
            await self._event_bus.publish(
                "orchestrator.task.started",
                {"task_id": task.task_id, "depends_on": list(task.depends_on)},
            )
            try:
                result_payload = await self._execute_with_retries(task, input_data)
                await self._event_bus.publish(
                    "orchestrator.task.completed",
                    {"task_id": task.task_id, "success": result_payload.get("success", False)},
                )
            except Exception as exc:  # noqa: BLE001
                result_payload = {
                    "success": False,
                    "error": str(exc),
                    "metadata": {"task_id": task.task_id},
                }
                await self._event_bus.publish(
                    "orchestrator.task.failed",
                    {"task_id": task.task_id, "error": str(exc)},
                )
            finally:
                async with self._context_lock:
                    self._active_tasks -= 1
                    self._max_parallel_seen = max(self._max_parallel_seen, self._active_tasks)
                    await self._update_context(shared_context, task.task_id, result_payload)
                    await self._memory_store.save(memory_key, shared_context)
                    await self._publish_metrics()

            return task.task_id, result_payload

    async def _execute_with_retries(
        self,
        task: AgentTask,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        attempt = 0
        last_error: Exception | None = None
        while attempt < self._retry_policy.max_attempts:
            attempt += 1
            try:
                result = await task.agent.execute(input_data)
                if not self._retry_policy.should_retry(None, result):
                    return result
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if not self._retry_policy.should_retry(exc, None):
                    raise
            if attempt < self._retry_policy.max_attempts:
                await self._event_bus.publish(
                    "orchestrator.task.retry",
                    {"task_id": task.task_id, "attempt": attempt},
                )
                await self._backoff(attempt)
        if last_error:
            raise last_error
        return {
            "success": False,
            "error": f"Task {task.task_id} failed after retries",
            "metadata": {"task_id": task.task_id},
        }

    async def _backoff(self, attempt: int) -> None:
        base_delay = self._retry_policy.base_delay_seconds * (2 ** (attempt - 1))
        delay = min(base_delay, self._retry_policy.max_delay_seconds)
        delay += random.uniform(0, self._retry_policy.jitter_seconds)
        await asyncio.sleep(delay)

    async def _load_context(
        self, memory_key: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        persisted = await self._memory_store.load(memory_key)
        merged = {**persisted, **context}
        merged.setdefault("history", [])
        merged.setdefault("agent_outputs", {})
        return merged

    async def _update_context(
        self, context: dict[str, Any], task_id: str, result_payload: dict[str, Any]
    ) -> None:
        history = context.setdefault("history", [])
        history.append(
            {
                "task_id": task_id,
                "timestamp": time.time(),
                "success": result_payload.get("success", False),
            }
        )
        agent_outputs = context.setdefault("agent_outputs", {})
        agent_outputs[task_id] = result_payload

    async def _publish_metrics(self) -> None:
        await self._event_bus.publish(
            "orchestrator.metrics",
            {
                "active_tasks": self._active_tasks,
                "max_parallel_tasks": self._max_parallel_seen,
            },
        )

    def _validate_tasks(self, tasks: dict[str, AgentTask]) -> None:
        if len(tasks) != len(set(tasks.keys())):
            raise ValueError("Task IDs must be unique")
        for task_id, task in tasks.items():
            for dependency in task.depends_on:
                if dependency not in tasks:
                    raise ValueError(f"Task {task_id} depends on unknown task {dependency}")
        visited: set[str] = set()
        stack: set[str] = set()

        def _visit(node: str) -> None:
            if node in stack:
                raise ValueError("Task graph contains a cycle")
            if node in visited:
                return
            stack.add(node)
            for dependency in tasks[node].depends_on:
                _visit(dependency)
            stack.remove(node)
            visited.add(node)

        for task_id in tasks:
            _visit(task_id)
