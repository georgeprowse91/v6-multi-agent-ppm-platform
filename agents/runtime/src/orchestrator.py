from __future__ import annotations

import asyncio
import logging
import os
import random
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.runtime.src.base_agent import BaseAgent
from agents.runtime.src.data_service import DataServiceClient
from agents.runtime.src.audit import build_audit_event, emit_audit_event
from agents.runtime.src.event_bus import EventBus, get_event_bus, publish_insight
from agents.runtime.src.models import AgentRun, AgentRunStatus
from packages.memory_client import MemoryClient
from services.memory_service.memory_service import MemoryService
from agents.runtime.src.notification_service import NotificationServiceClient

FEATURE_FLAGS_ROOT = Path(__file__).resolve().parents[3] / "packages" / "feature-flags" / "src"
if str(FEATURE_FLAGS_ROOT) not in sys.path:
    sys.path.insert(0, str(FEATURE_FLAGS_ROOT))

from feature_flags import is_feature_enabled  # noqa: E402

logger = logging.getLogger("agents.runtime.orchestrator")

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
        event_bus: EventBus | None = None,
        memory_client: MemoryClient | None = None,
        retry_policy: RetryPolicy | None = None,
        max_parallel_tasks: int = 4,
        data_service_client: DataServiceClient | None = None,
    ) -> None:
        self._event_bus = event_bus or get_event_bus()
        self._memory_client = memory_client or MemoryClient(MemoryService(backend="memory"))
        self._retry_policy = retry_policy or RetryPolicy()
        self._max_parallel_tasks = max_parallel_tasks
        self._active_tasks = 0
        self._max_parallel_seen = 0
        self._context_lock = asyncio.Lock()
        self._data_service = data_service_client or self._build_data_service_client()
        self._notification_service = self._build_notification_service_client()

    @property
    def event_bus(self) -> EventBus:
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

        self._memory_client.save_context(resolved_memory_key, shared_context)
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
            agent_run = await self._initialize_agent_run(task, shared_context)
            agent_run = await self._transition_agent_run(
                agent_run, AgentRunStatus.running, {"event": "task_started"}
            )
            async with self._context_lock:
                self._active_tasks += 1
                self._max_parallel_seen = max(self._max_parallel_seen, self._active_tasks)
                await self._publish_metrics()

            dependency_results = {dep: results[dep] for dep in task.depends_on}
            task.agent.memory_client = self._memory_client
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
                final_status = (
                    AgentRunStatus.succeeded
                    if result_payload.get("success", False)
                    else AgentRunStatus.failed
                )
                completion_reason = self._resolve_completion_reason(result_payload, final_status)
                agent_run = await self._transition_agent_run(
                    agent_run,
                    final_status,
                    {"event": "task_completed", "success": result_payload.get("success", False)},
                    completion_reason=completion_reason,
                )
                if agent_run is not None:
                    await self._send_agent_run_notification(agent_run, result_payload)
                await self._event_bus.publish(
                    "orchestrator.task.completed",
                    {"task_id": task.task_id, "success": result_payload.get("success", False)},
                )
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # noqa: BLE001
                metadata = {"task_id": task.task_id}
                if isinstance(exc, TimeoutError):
                    metadata["timeout"] = True
                    if hasattr(exc, "timeout_seconds") and exc.timeout_seconds is not None:
                        metadata["timeout_seconds"] = exc.timeout_seconds
                result_payload = {
                    "success": False,
                    "error": str(exc),
                    "metadata": metadata,
                }
                agent_run = await self._transition_agent_run(
                    agent_run,
                    AgentRunStatus.failed,
                    {"event": "task_failed", "error": str(exc)},
                    completion_reason=str(exc),
                )
                if agent_run is not None:
                    await self._send_agent_run_notification(agent_run, result_payload)
                await self._event_bus.publish(
                    "orchestrator.task.failed",
                    {"task_id": task.task_id, "error": str(exc)},
                )
            finally:
                async with self._context_lock:
                    self._active_tasks -= 1
                    self._max_parallel_seen = max(self._max_parallel_seen, self._active_tasks)
                    new_insights = await self._update_context(
                        shared_context, task.task_id, result_payload
                    )
                    self._memory_client.save_context(memory_key, shared_context)
                    if new_insights:
                        await publish_insight(
                            self._event_bus,
                            {
                                "task_id": task.task_id,
                                "correlation_id": memory_key,
                                "insights": new_insights,
                            },
                        )
                    await self._publish_metrics()

            return task.task_id, result_payload

    async def _execute_with_retries(
        self,
        task: AgentTask,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        attempt = 0
        last_error: Exception | None = None
        timeout_seconds = self._resolve_timeout_seconds(task)
        while attempt < self._retry_policy.max_attempts:
            attempt += 1
            try:
                result = await self._execute_with_timeout(task, input_data, timeout_seconds)
                if not self._retry_policy.should_retry(None, result):
                    return result
            except asyncio.TimeoutError as exc:
                last_error = self._build_timeout_error(task, timeout_seconds, exc)
                if not self._retry_policy.should_retry(last_error, None):
                    raise last_error
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # noqa: BLE001
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

    async def _execute_with_timeout(
        self,
        task: AgentTask,
        input_data: dict[str, Any],
        timeout_seconds: float | None,
    ) -> dict[str, Any]:
        if not timeout_seconds:
            return await task.agent.execute(input_data)
        return await asyncio.wait_for(
            task.agent.execute(input_data),
            timeout=timeout_seconds,
        )

    def _resolve_timeout_seconds(self, task: AgentTask) -> float | None:
        raw_timeout = task.agent.get_config("AGENT_TIMEOUT_SECONDS")
        if raw_timeout in (None, ""):
            raw_timeout = os.getenv("AGENT_TIMEOUT_SECONDS")
        if raw_timeout in (None, ""):
            return None
        try:
            timeout_seconds = float(raw_timeout)
        except (TypeError, ValueError) as exc:
            raise ValueError("AGENT_TIMEOUT_SECONDS must be a number") from exc
        if timeout_seconds <= 0:
            return None
        return timeout_seconds

    def _build_timeout_error(
        self,
        task: AgentTask,
        timeout_seconds: float | None,
        exc: asyncio.TimeoutError,
    ) -> TimeoutError:
        timeout_value = timeout_seconds if timeout_seconds is not None else 0.0
        error = TimeoutError(
            f"Task {task.task_id} exceeded timeout of {timeout_value:.2f} seconds"
        )
        error.timeout_seconds = timeout_seconds
        error.__cause__ = exc
        return error

    async def _backoff(self, attempt: int) -> None:
        base_delay = self._retry_policy.base_delay_seconds * (2 ** (attempt - 1))
        delay = min(base_delay, self._retry_policy.max_delay_seconds)
        delay += random.uniform(0, self._retry_policy.jitter_seconds)
        await asyncio.sleep(delay)

    async def _load_context(self, memory_key: str, context: dict[str, Any]) -> dict[str, Any]:
        persisted = self._memory_client.load_context(memory_key) or {}
        merged = {**persisted, **context}
        merged.setdefault("history", [])
        merged.setdefault("agent_outputs", {})
        return merged

    async def _update_context(
        self, context: dict[str, Any], task_id: str, result_payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
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
        insights = context.setdefault("insights", [])
        new_insights = self._normalize_insights(task_id, result_payload)
        insights.extend(new_insights)
        return new_insights

    async def _publish_metrics(self) -> None:
        await self._event_bus.publish(
            "orchestrator.metrics",
            {
                "active_tasks": self._active_tasks,
                "max_parallel_tasks": self._max_parallel_seen,
            },
        )

    def _normalize_insights(
        self, task_id: str, result_payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        raw_insights = result_payload.get("insights")
        if not raw_insights:
            return []
        if isinstance(raw_insights, list):
            insight_items = raw_insights
        else:
            insight_items = [raw_insights]
        normalized: list[dict[str, Any]] = []
        for insight in insight_items:
            if isinstance(insight, dict):
                payload = {"task_id": task_id, "timestamp": time.time(), **insight}
            else:
                payload = {
                    "task_id": task_id,
                    "timestamp": time.time(),
                    "summary": str(insight),
                }
            normalized.append(payload)
        return normalized

    def _build_data_service_client(self) -> DataServiceClient | None:
        base_url = os.getenv("DATA_SERVICE_URL")
        if not base_url:
            return None
        return DataServiceClient.from_url(base_url)

    def _build_notification_service_client(self) -> NotificationServiceClient | None:
        base_url = os.getenv("NOTIFICATION_SERVICE_URL")
        if not base_url:
            return None
        auth_token = os.getenv("NOTIFICATION_SERVICE_TOKEN")
        return NotificationServiceClient.from_url(base_url, auth_token=auth_token)

    def _resolve_completion_reason(
        self, result_payload: dict[str, Any], final_status: AgentRunStatus
    ) -> str | None:
        if final_status == AgentRunStatus.succeeded:
            return result_payload.get("completion_reason") or "success"
        if final_status == AgentRunStatus.failed:
            return result_payload.get("error") or "failed"
        return None

    async def _send_agent_run_notification(
        self, agent_run: AgentRun, result_payload: dict[str, Any]
    ) -> None:
        if agent_run.status not in {AgentRunStatus.succeeded, AgentRunStatus.failed}:
            return
        if not self._agent_async_notifications_enabled():
            return
        if not self._notification_service:
            logger.info(
                "agent_run_notification_skipped",
                extra={"reason": "notification_service_unconfigured", "agent_run_id": agent_run.id},
            )
            return
        channel = os.getenv("AGENT_RUN_NOTIFICATION_CHANNEL", "stdout")
        recipient = os.getenv("AGENT_RUN_NOTIFICATION_RECIPIENT")
        variables = {
            "agent_id": agent_run.agent_id,
            "agent_run_id": agent_run.id,
            "tenant_id": agent_run.tenant_id,
            "status": agent_run.status.value,
            "completed_at": agent_run.completed_at or "",
            "completion_reason": agent_run.completion_reason or "",
            "delay_reason": agent_run.delay_reason or "",
            "task_id": agent_run.metadata.get("task_id"),
            "correlation_id": agent_run.metadata.get("correlation_id"),
            "success": result_payload.get("success"),
        }
        try:
            await self._notification_service.send_notification(
                tenant_id=agent_run.tenant_id,
                template="agent-run-status",
                variables=variables,
                channel=channel,
                recipient=recipient,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "agent_run_notification_failed",
                extra={"agent_run_id": agent_run.id, "error": str(exc)},
            )

    def _agent_run_tracking_enabled(self) -> bool:
        environment = os.getenv("ENVIRONMENT", "dev")
        return is_feature_enabled("agent_run_tracking", environment=environment, default=False)

    def _agent_async_notifications_enabled(self) -> bool:
        environment = os.getenv("ENVIRONMENT", "dev")
        return is_feature_enabled(
            "agent_async_notifications", environment=environment, default=False
        )

    async def _initialize_agent_run(
        self, task: AgentTask, context: dict[str, Any]
    ) -> AgentRun | None:
        if not self._agent_run_tracking_enabled():
            return None
        tenant_id = context.get("tenant_id") or "unknown"
        correlation_id = context.get("correlation_id")
        metadata = {
            "task_id": task.task_id,
            "depends_on": list(task.depends_on),
            "correlation_id": correlation_id,
        }
        agent_run = AgentRun(
            id=f"run-{uuid.uuid4().hex}",
            tenant_id=tenant_id,
            agent_id=task.agent.agent_id,
            status=AgentRunStatus.queued,
            metadata=metadata,
        )
        await self._persist_agent_run(agent_run)
        self._emit_agent_run_audit(agent_run, previous_status=None)
        return agent_run

    async def _transition_agent_run(
        self,
        agent_run: AgentRun | None,
        new_status: AgentRunStatus,
        metadata_update: dict[str, Any] | None = None,
        completion_reason: str | None = None,
        delay_reason: str | None = None,
    ) -> AgentRun | None:
        if agent_run is None:
            return None
        updated = agent_run.transition_to(
            new_status,
            metadata_update=metadata_update,
            completion_reason=completion_reason,
            delay_reason=delay_reason,
        )
        await self._persist_agent_run(updated)
        self._emit_agent_run_audit(updated, previous_status=agent_run.status)
        return updated

    async def _persist_agent_run(self, agent_run: AgentRun) -> None:
        if not self._data_service:
            logger.info("agent_run_persistence_skipped", extra={"reason": "data_service_unconfigured"})
            return
        try:
            await self._data_service.store_entity(
                "agent-run",
                data=agent_run.model_dump(),
                tenant_id=agent_run.tenant_id,
                entity_id=agent_run.id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "agent_run_persist_failed",
                extra={"agent_run_id": agent_run.id, "error": str(exc)},
            )

    def _emit_agent_run_audit(
        self,
        agent_run: AgentRun,
        *,
        previous_status: AgentRunStatus | None,
    ) -> None:
        metadata = {
            "agent_run_id": agent_run.id,
            "agent_id": agent_run.agent_id,
            "status": agent_run.status.value,
            "previous_status": previous_status.value if previous_status else None,
            "metadata": agent_run.metadata,
        }
        event = build_audit_event(
            tenant_id=agent_run.tenant_id,
            action="agent_run.status_changed",
            outcome="success",
            actor_id="orchestrator",
            actor_type="system",
            actor_roles=[],
            resource_id=agent_run.id,
            resource_type="agent_run",
            metadata=metadata,
            trace_id=agent_run.metadata.get("trace_id"),
            correlation_id=agent_run.metadata.get("correlation_id"),
        )
        emit_audit_event(event)

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
