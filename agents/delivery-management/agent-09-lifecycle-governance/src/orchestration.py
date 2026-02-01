"""Durable workflow orchestration primitives for lifecycle governance."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 0.5
    max_backoff_seconds: float = 5.0
    jitter: float = 0.1

    def get_delay(self, attempt: int) -> float:
        base = min(self.backoff_seconds * (2 ** max(attempt - 1, 0)), self.max_backoff_seconds)
        return max(0.0, base + random.uniform(-self.jitter, self.jitter))


@dataclass(slots=True)
class OrchestrationContext:
    workflow_id: str
    tenant_id: str
    project_id: str
    correlation_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


TaskAction = Callable[[OrchestrationContext], Awaitable[Any] | Any]
CompensationAction = Callable[[OrchestrationContext, Exception | None], Awaitable[None] | None]


@dataclass(slots=True)
class DurableTask:
    name: str
    action: TaskAction
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    compensation: CompensationAction | None = None

    async def run(self, context: OrchestrationContext, sleep: Callable[[float], Awaitable[None]]) -> Any:
        attempt = 0
        while True:
            try:
                result = self.action(context)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            except Exception as exc:  # pragma: no cover - retry paths
                attempt += 1
                if attempt >= self.retry_policy.max_attempts:
                    raise
                delay = self.retry_policy.get_delay(attempt)
                if delay > 0:
                    await sleep(delay)


@dataclass(slots=True)
class DurableWorkflow:
    name: str
    tasks: list[DurableTask]
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep

    async def run(self, context: OrchestrationContext) -> OrchestrationContext:
        executed: list[DurableTask] = []
        try:
            for task in self.tasks:
                result = await task.run(context, self.sleep)
                context.results[task.name] = result
                executed.append(task)
            return context
        except Exception as exc:
            await self._compensate(executed, context, exc)
            raise

    async def _compensate(
        self, executed: list[DurableTask], context: OrchestrationContext, exc: Exception
    ) -> None:
        for task in reversed(executed):
            if not task.compensation:
                continue
            result = task.compensation(context, exc)
            if asyncio.iscoroutine(result):
                await result


@dataclass(slots=True)
class WorkflowHandle:
    workflow_id: str
    task: asyncio.Task
    started_at: datetime


class DurableWorkflowEngine:
    def __init__(
        self,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        monitor: Any | None = None,
    ) -> None:
        self.sleep = sleep
        self.monitor = monitor
        self._active: dict[str, WorkflowHandle] = {}

    async def run(self, workflow: DurableWorkflow, context: OrchestrationContext) -> OrchestrationContext:
        started_at = datetime.now(timezone.utc)
        self._active[context.workflow_id] = WorkflowHandle(
            workflow_id=context.workflow_id,
            task=asyncio.current_task(),
            started_at=started_at,
        )
        if self.monitor:
            self.monitor.workflow_started(context, workflow.name)
        try:
            result = await workflow.run(context)
            return result
        except Exception as exc:
            if self.monitor:
                self.monitor.workflow_failed(context, workflow.name, exc)
            raise
        finally:
            finished_at = datetime.now(timezone.utc)
            if self.monitor:
                self.monitor.workflow_completed(context, workflow.name, started_at, finished_at)
            self._active.pop(context.workflow_id, None)

    def start(self, workflow: DurableWorkflow, context: OrchestrationContext) -> WorkflowHandle:
        async def runner() -> OrchestrationContext:
            return await self.run(workflow, context)

        task = asyncio.create_task(runner())
        handle = WorkflowHandle(
            workflow_id=context.workflow_id,
            task=task,
            started_at=datetime.now(timezone.utc),
        )
        self._active[context.workflow_id] = handle
        return handle

    def cancel(self, workflow_id: str) -> bool:
        handle = self._active.get(workflow_id)
        if not handle:
            return False
        handle.task.cancel()
        return True

    async def shutdown(self) -> None:
        for workflow_id in list(self._active.keys()):
            self.cancel(workflow_id)
        await asyncio.sleep(0)
