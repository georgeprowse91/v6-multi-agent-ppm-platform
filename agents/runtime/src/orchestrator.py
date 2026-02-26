from __future__ import annotations

import asyncio
import copy
import logging
import os
import random
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_COMMON_SRC = Path(__file__).resolve().parents[3] / "packages" / "common" / "src"
if str(_COMMON_SRC) not in sys.path:
    sys.path.insert(0, str(_COMMON_SRC))

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths()

import yaml  # noqa: E402
from observability.metrics import build_agent_execution_metrics  # noqa: E402

from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402
from agents.runtime.src.base_agent import BaseAgent  # noqa: E402
from agents.runtime.src.data_service import DataServiceClient  # noqa: E402
from agents.runtime.src.event_bus import EventBus, get_event_bus, publish_insight  # noqa: E402
from agents.runtime.src.models import AgentRun, AgentRunStatus  # noqa: E402
from agents.runtime.src.notification_service import NotificationServiceClient  # noqa: E402
from packages.memory_client import MemoryClient  # noqa: E402
from services.memory_service.memory_service import MemoryService  # noqa: E402
from template_mappings import get_template_mapping  # noqa: E402
from feature_flags import is_feature_enabled  # noqa: E402

logger = logging.getLogger("agents.runtime.orchestrator")
HUMAN_REVIEW_CONFIG_PATH = (
    Path(__file__).resolve().parents[3] / "ops" / "config" / "human_review.yaml"
)

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


@dataclass(frozen=True)
class HumanReviewRule:
    name: str
    action_type: str
    agent_ids: set[str]
    conditions: list[dict[str, Any]]


@dataclass
class HumanReviewRequest:
    review_id: str
    correlation_id: str
    task_id: str
    agent_id: str
    proposed_action: dict[str, Any]
    relevant_data: dict[str, Any]
    rule_name: str


class _TemplateWorkflowAgent(BaseAgent):
    def __init__(self, agent_id: str) -> None:
        super().__init__(agent_id=agent_id)

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": True,
            "metadata": {
                "workflow_event": input_data.get("lifecycle_event"),
                "template_id": input_data.get("template_id"),
            },
            "actions": [],
        }

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return await self.process(input_data)


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
        self._human_review_rules = self._load_human_review_rules()
        self._human_review_timeout_seconds = self._load_human_review_timeout_seconds()
        self._pending_human_reviews: dict[str, HumanReviewRequest] = {}
        self._execution_metrics = build_agent_execution_metrics("agent-orchestrator")
        self._human_review_decisions: dict[str, dict[str, Any]] = {}
        self._human_review_waiters: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._event_bus.subscribe("human_review_decision", self._handle_human_review_decision_event)

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
        request_context = dict(context or {})
        correlation_id = request_context.get("correlation_id") or memory_key or str(uuid.uuid4())
        request_context["correlation_id"] = correlation_id
        resolved_memory_key = memory_key or correlation_id
        shared_context = await self._load_context(resolved_memory_key, request_context)
        shared_context["correlation_id"] = correlation_id
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
        cost_summary = self._aggregate_costs(results)
        shared_context["cost_summary"] = cost_summary
        metrics = {
            "max_parallel_tasks": self._max_parallel_seen,
            "total_tasks": len(tasks),
            "cost_summary": cost_summary,
        }
        return OrchestrationResult(results=results, context=shared_context, metrics=metrics)

    async def run_template_workflow(
        self,
        *,
        template_id: str,
        lifecycle_event: str,
        context_refs: dict[str, Any],
    ) -> OrchestrationResult:
        mapping = get_template_mapping(template_id)
        if mapping is None:
            raise ValueError(f"Unknown template mapping for `{template_id}`")

        if lifecycle_event not in {"generate", "update", "review", "approve", "publish"}:
            raise ValueError(f"Unsupported lifecycle_event `{lifecycle_event}`")

        selected_agents = getattr(mapping.agent_bindings, lifecycle_event)
        if not selected_agents:
            return OrchestrationResult(results={}, context=context_refs, metrics={"skipped": True})

        dependency_status: dict[str, bool] = context_refs.get("completed_templates", {})
        missing_dependencies = [
            template
            for template in mapping.agent_bindings.orchestration.depends_on_templates
            if not dependency_status.get(template, False)
        ]
        if missing_dependencies:
            raise ValueError(
                f"Template workflow prerequisites not satisfied: {', '.join(missing_dependencies)}"
            )

        if (
            lifecycle_event in {"review", "approve"}
            or "publish_external" in mapping.agent_bindings.orchestration.side_effects
        ):
            context_refs = {**context_refs, "human_review_required": True}

        tasks = [
            AgentTask(
                task_id=f"template-{template_id}-{lifecycle_event}-{index}",
                agent=_TemplateWorkflowAgent(agent_id),
                input_data={
                    "template_id": template_id,
                    "lifecycle_event": lifecycle_event,
                    "connector_binding": mapping.connector_binding.model_dump(),
                    "side_effects": mapping.agent_bindings.orchestration.side_effects,
                    "context_refs": context_refs,
                },
                depends_on=(
                    [] if index == 0 else [f"template-{template_id}-{lifecycle_event}-{index - 1}"]
                ),
            )
            for index, agent_id in enumerate(selected_agents)
        ]
        return await self.run(tasks, context=context_refs)

    async def run_methodology_node_action(
        self,
        *,
        methodology_id: str,
        stage_id: str,
        activity_id: str | None,
        task_id: str | None,
        lifecycle_event: str,
        template_ids: list[str],
        context_refs: dict[str, Any],
    ) -> OrchestrationResult:
        if not template_ids:
            return OrchestrationResult(results={}, context=context_refs, metrics={"skipped": True})

        completed_templates = dict(context_refs.get("completed_templates", {}))
        combined_results: dict[str, dict[str, Any]] = {}
        template_runs: list[dict[str, Any]] = []
        combined_context = dict(context_refs)
        combined_metrics: dict[str, Any] = {"templates_executed": 0}

        for template_id in template_ids:
            mapping = get_template_mapping(template_id)
            if mapping is None:
                raise ValueError(f"Unknown template mapping for `{template_id}`")

            missing_dependencies = [
                dependency
                for dependency in mapping.agent_bindings.orchestration.depends_on_templates
                if not completed_templates.get(dependency, False)
            ]
            if missing_dependencies:
                raise ValueError(
                    "Template workflow prerequisites not satisfied for "
                    f"`{template_id}`: {', '.join(missing_dependencies)}"
                )

            requires_review = (
                lifecycle_event in {"review", "approve", "publish"}
                or "publish_external" in mapping.agent_bindings.orchestration.side_effects
            )
            template_context = {
                **combined_context,
                "methodology_id": methodology_id,
                "stage_id": stage_id,
                "activity_id": activity_id,
                "task_id": task_id,
                "completed_templates": completed_templates,
                "human_review_required": combined_context.get("human_review_required", False)
                or requires_review,
            }

            run_result = await self.run_template_workflow(
                template_id=template_id,
                lifecycle_event=lifecycle_event,
                context_refs=template_context,
            )

            combined_results.update(run_result.results)
            template_runs.append(
                {
                    "template_id": template_id,
                    "result_task_ids": list(run_result.results.keys()),
                    "metrics": run_result.metrics,
                }
            )
            completed_templates[template_id] = True
            combined_context.update(run_result.context)
            combined_context["completed_templates"] = completed_templates
            combined_metrics["templates_executed"] += 1

        combined_context["template_runs"] = template_runs
        return OrchestrationResult(
            results=combined_results,
            context=combined_context,
            metrics=combined_metrics,
        )

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
            started_at = time.perf_counter()
            task.agent.memory_client = self._memory_client
            input_data = {
                **task.input_data,
                "context": shared_context,
                "dependency_results": dependency_results,
            }
            await self._event_bus.publish(
                "orchestrator.task.started",
                {
                    "task_id": task.task_id,
                    "depends_on": list(task.depends_on),
                    "correlation_id": memory_key,
                },
            )
            try:
                result_payload = await self._execute_with_retries(task, input_data)
                result_payload = await self._gate_actions_with_human_review(
                    task=task,
                    input_data=input_data,
                    result_payload=result_payload,
                    correlation_id=memory_key,
                )
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
                    {
                        "task_id": task.task_id,
                        "success": result_payload.get("success", False),
                        "correlation_id": memory_key,
                    },
                )
                self._execution_metrics.duration_seconds.record(
                    time.perf_counter() - started_at,
                    {
                        "agent_id": task.agent.agent_id,
                        "task_id": task.task_id,
                        "correlation_id": memory_key,
                    },
                )
                if not result_payload.get("success", False):
                    self._execution_metrics.errors_total.add(
                        1,
                        {
                            "agent_id": task.agent.agent_id,
                            "task_id": task.task_id,
                            "correlation_id": memory_key,
                        },
                    )
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:  # noqa: BLE001
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
                    {"task_id": task.task_id, "error": str(exc), "correlation_id": memory_key},
                )
                self._execution_metrics.duration_seconds.record(
                    time.perf_counter() - started_at,
                    {
                        "agent_id": task.agent.agent_id,
                        "task_id": task.task_id,
                        "correlation_id": memory_key,
                    },
                )
                self._execution_metrics.errors_total.add(
                    1,
                    {
                        "agent_id": task.agent.agent_id,
                        "task_id": task.task_id,
                        "correlation_id": memory_key,
                    },
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

    def get_pending_human_reviews(self) -> list[dict[str, Any]]:
        return [
            {
                "review_id": request.review_id,
                "correlation_id": request.correlation_id,
                "task_id": request.task_id,
                "agent_id": request.agent_id,
                "proposed_action": copy.deepcopy(request.proposed_action),
                "relevant_data": copy.deepcopy(request.relevant_data),
                "rule_name": request.rule_name,
            }
            for request in self._pending_human_reviews.values()
        ]

    async def _gate_actions_with_human_review(
        self,
        *,
        task: AgentTask,
        input_data: dict[str, Any],
        result_payload: dict[str, Any],
        correlation_id: str,
    ) -> dict[str, Any]:
        actions = self._extract_proposed_actions(result_payload)
        if not actions:
            return result_payload

        review_metadata = result_payload.setdefault("metadata", {})
        review_results = review_metadata.setdefault("human_review", [])
        for action in actions:
            matching_rule = self._find_matching_human_review_rule(task, action, result_payload)
            if matching_rule is None:
                continue
            decision = await self._request_human_review(
                task=task,
                action=action,
                result_payload=result_payload,
                rule=matching_rule,
                correlation_id=correlation_id,
                input_data=input_data,
            )
            outcome = (decision.get("decision") or "").lower()
            review_results.append(
                {
                    "review_id": decision.get("review_id"),
                    "rule": matching_rule.name,
                    "decision": outcome,
                    "reviewer": decision.get("reviewer"),
                }
            )
            if outcome == "reject":
                action["status"] = "rejected_by_human_review"
            elif outcome == "modify":
                modified_action = decision.get("modified_action")
                if isinstance(modified_action, dict):
                    action.clear()
                    action.update(modified_action)
                    action["status"] = "modified_by_human_review"
            else:
                action["status"] = "approved_by_human_review"
        return result_payload

    async def _request_human_review(
        self,
        *,
        task: AgentTask,
        action: dict[str, Any],
        result_payload: dict[str, Any],
        rule: HumanReviewRule,
        correlation_id: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        review_id = f"review-{uuid.uuid4().hex}"
        review_request = HumanReviewRequest(
            review_id=review_id,
            correlation_id=correlation_id,
            task_id=task.task_id,
            agent_id=task.agent.agent_id,
            proposed_action=copy.deepcopy(action),
            relevant_data={
                "result_payload": copy.deepcopy(result_payload),
                "context": copy.deepcopy(input_data.get("context", {})),
                "dependency_results": copy.deepcopy(input_data.get("dependency_results", {})),
            },
            rule_name=rule.name,
        )
        waiter: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending_human_reviews[review_id] = review_request
        self._human_review_waiters[review_id] = waiter
        await self._event_bus.publish(
            "human_review_required",
            {
                "review_id": review_id,
                "correlation_id": correlation_id,
                "task_id": task.task_id,
                "agent_id": task.agent.agent_id,
                "rule": rule.name,
                "proposed_action": copy.deepcopy(action),
                "relevant_data": review_request.relevant_data,
            },
        )
        try:
            decision = await asyncio.wait_for(waiter, timeout=self._human_review_timeout_seconds)
            return decision
        except TimeoutError:
            return {
                "review_id": review_id,
                "decision": "reject",
                "reason": "human review timeout",
            }
        finally:
            self._pending_human_reviews.pop(review_id, None)
            self._human_review_waiters.pop(review_id, None)
            self._human_review_decisions.pop(review_id, None)

    async def _handle_human_review_decision_event(self, payload: dict[str, Any]) -> None:
        review_id = payload.get("review_id")
        if not isinstance(review_id, str) or not review_id:
            return
        decision = dict(payload)
        self._human_review_decisions[review_id] = decision
        waiter = self._human_review_waiters.get(review_id)
        if waiter and not waiter.done():
            waiter.set_result(decision)

    def _extract_proposed_actions(self, result_payload: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(result_payload, dict):
            return []
        raw_actions = result_payload.get("proposed_actions")
        if not isinstance(raw_actions, list):
            data = result_payload.get("data", {})
            if isinstance(data, dict):
                raw_actions = data.get("proposed_actions") or data.get("actions")
        if not isinstance(raw_actions, list):
            return []
        return [action for action in raw_actions if isinstance(action, dict)]

    def _find_matching_human_review_rule(
        self,
        task: AgentTask,
        action: dict[str, Any],
        result_payload: dict[str, Any],
    ) -> HumanReviewRule | None:
        action_type = str(action.get("action_type") or "").strip().lower()
        payload = {
            "action": action,
            "result": result_payload,
            "task_id": task.task_id,
            "agent_id": task.agent.agent_id,
        }
        for rule in self._human_review_rules:
            if action_type != rule.action_type:
                continue
            if task.agent.agent_id not in rule.agent_ids:
                continue
            if self._conditions_match(payload, rule.conditions):
                return rule
        return None

    def _conditions_match(self, payload: dict[str, Any], conditions: list[dict[str, Any]]) -> bool:
        if not conditions:
            return True
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            expected = condition.get("value")
            if not isinstance(field, str) or not isinstance(operator, str):
                return False
            value = self._get_by_path(payload, field)
            if not self._evaluate_condition(value, operator.lower(), expected):
                return False
        return True

    def _evaluate_condition(self, value: Any, operator: str, expected: Any) -> bool:
        if operator == "gte":
            return self._as_float(value) >= self._as_float(expected)
        if operator == "lte":
            return self._as_float(value) <= self._as_float(expected)
        if operator == "gt":
            return self._as_float(value) > self._as_float(expected)
        if operator == "lt":
            return self._as_float(value) < self._as_float(expected)
        if operator == "equals":
            return value == expected
        if operator == "in":
            return isinstance(expected, list) and value in expected
        return False

    def _as_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float("nan")

    def _get_by_path(self, payload: dict[str, Any], path: str) -> Any:
        current: Any = payload
        for part in path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _load_human_review_rules(self) -> list[HumanReviewRule]:
        if not HUMAN_REVIEW_CONFIG_PATH.exists():
            return []
        raw = HUMAN_REVIEW_CONFIG_PATH.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}
        rules: list[HumanReviewRule] = []
        for item in data.get("review_rules", []):
            if not isinstance(item, dict):
                continue
            action_type = str(item.get("action_type") or "").strip().lower()
            agent_ids = item.get("agent_ids")
            if not action_type or not isinstance(agent_ids, list):
                continue
            rules.append(
                HumanReviewRule(
                    name=str(item.get("name") or action_type),
                    action_type=action_type,
                    agent_ids={str(agent_id) for agent_id in agent_ids if str(agent_id).strip()},
                    conditions=[c for c in item.get("conditions", []) if isinstance(c, dict)],
                )
            )
        return rules

    def _load_human_review_timeout_seconds(self) -> float:
        if not HUMAN_REVIEW_CONFIG_PATH.exists():
            return 120.0
        raw = HUMAN_REVIEW_CONFIG_PATH.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}
        timeout = data.get("decision_timeout_seconds", 120)
        try:
            resolved = float(timeout)
        except (TypeError, ValueError):
            return 120.0
        return resolved if resolved > 0 else 120.0

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
            except TimeoutError as exc:
                last_error = self._build_timeout_error(task, timeout_seconds, exc)
                if not self._retry_policy.should_retry(last_error, None):
                    raise last_error
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:  # noqa: BLE001
                last_error = exc
                if not self._retry_policy.should_retry(exc, None):
                    raise
            if attempt < self._retry_policy.max_attempts:
                correlation_id = (input_data.get("context") or {}).get(
                    "correlation_id"
                ) or "unknown"
                await self._event_bus.publish(
                    "orchestrator.task.retry",
                    {"task_id": task.task_id, "attempt": attempt, "correlation_id": correlation_id},
                )
                self._execution_metrics.retries_total.add(
                    1,
                    {
                        "agent_id": task.agent.agent_id,
                        "task_id": task.task_id,
                        "correlation_id": correlation_id,
                    },
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
        error = TimeoutError(f"Task {task.task_id} exceeded timeout of {timeout_value:.2f} seconds")
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
        if isinstance(result_payload.get("data"), dict):
            risk_data = result_payload["data"].get("risk_data")
            if isinstance(risk_data, dict):
                context["risk_data"] = risk_data
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
            logger.info(
                "agent_run_persistence_skipped", extra={"reason": "data_service_unconfigured"}
            )
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

    def _aggregate_costs(self, results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        per_agent: dict[str, dict[str, Any]] = {}
        total_cost_usd = 0.0
        total_llm_tokens = 0
        for task_id, result in results.items():
            metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
            cost_summary = metadata.get("cost_summary", {}) if isinstance(metadata, dict) else {}
            if not isinstance(cost_summary, dict):
                continue
            api_cost = float(cost_summary.get("api_cost_total_usd", 0.0) or 0.0)
            llm_tokens = int(
                (cost_summary.get("llm_tokens", {}) or {}).get("total", 0)
                if isinstance(cost_summary.get("llm_tokens"), dict)
                else 0
            )
            per_agent[task_id] = {
                "api_cost_total_usd": api_cost,
                "llm_tokens_total": llm_tokens,
            }
            total_cost_usd += api_cost
            total_llm_tokens += llm_tokens
        return {
            "total_api_cost_usd": total_cost_usd,
            "total_llm_tokens": total_llm_tokens,
            "per_agent": per_agent,
        }
