from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, cast

import httpx
from agent_client import AgentClient
from approval_workflow_agent import ApprovalWorkflowAgent
from circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerRegistry
from workflow_storage import WorkflowApproval, WorkflowInstance, WorkflowStore

try:
    from event_bus import get_event_bus
except ImportError:  # pragma: no cover - optional dependency
    get_event_bus = None


class WorkflowRuntime:
    def __init__(
        self,
        store: WorkflowStore,
        approval_agent: ApprovalWorkflowAgent,
        agent_client: AgentClient | None = None,
        circuit_breakers: CircuitBreakerRegistry | None = None,
        event_bus: Any | None = None,
    ) -> None:
        self.store = store
        self.approval_agent = approval_agent
        self.agent_client = agent_client
        self.circuit_breakers = circuit_breakers or CircuitBreakerRegistry()
        self.event_bus = event_bus or self._load_event_bus()

    def _require_instance(self, run_id: str) -> WorkflowInstance:
        instance = self.store.get(run_id)
        if not instance:
            raise ValueError("Workflow instance not found")
        return instance

    def _as_optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return str(value)

    async def start(
        self, instance: WorkflowInstance, definition: dict[str, Any], actor: dict[str, Any]
    ) -> WorkflowInstance:
        if instance.status != "running":
            self.store.update_status(instance.run_id, "running", instance.current_step_id)
        await self._publish_event(
            "workflow.started",
            {
                "run_id": instance.run_id,
                "workflow_id": instance.workflow_id,
                "tenant_id": instance.tenant_id,
                "actor": actor,
            },
        )
        return await self._run_until_pause(instance, definition, actor)

    async def resume(
        self, instance: WorkflowInstance, definition: dict[str, Any], actor: dict[str, Any]
    ) -> WorkflowInstance:
        return await self._run_until_pause(instance, definition, actor)

    async def handle_approval_decision(
        self,
        approval: WorkflowApproval,
        decision: str,
        approver_id: str,
        comments: str | None,
        resume_after_decision: bool = True,
    ) -> WorkflowInstance:
        await self.approval_agent.process(
            {
                "approval_id": approval.approval_id,
                "decision": decision,
                "approver_id": approver_id,
                "comments": comments,
                "tenant_id": approval.tenant_id,
                "context": {"tenant_id": approval.tenant_id, "correlation_id": approval.run_id},
            }
        )
        metadata = dict(approval.metadata)
        metadata["decision"] = decision
        metadata["decided_by"] = approver_id
        metadata["comments"] = comments
        self.store.upsert_approval(
            approval_id=approval.approval_id,
            run_id=approval.run_id,
            step_id=approval.step_id,
            tenant_id=approval.tenant_id,
            status=decision,
            metadata=metadata,
            decision=decision,
            approver_id=approver_id,
            comments=comments,
        )
        instance = self.store.get(approval.run_id)
        if not instance:
            raise ValueError("Workflow instance not found")
        if decision != "approved":
            self.store.update_status(instance.run_id, "rejected", approval.step_id)
            self.store.add_event(
                instance.run_id,
                "rejected",
                f"Approval {approval.approval_id} rejected by {approver_id}",
                approval.step_id,
            )
            await self._publish_event(
                "workflow.failed",
                {
                    "run_id": instance.run_id,
                    "workflow_id": instance.workflow_id,
                    "tenant_id": instance.tenant_id,
                    "reason": "Approval rejected",
                    "step_id": approval.step_id,
                },
            )
            return self._require_instance(instance.run_id)

        self.store.upsert_step_state(
            approval.run_id,
            approval.step_id,
            "completed",
            attempts=1,
            output={"approval_id": approval.approval_id, "decision": decision},
        )
        self.store.add_event(
            instance.run_id,
            "approved",
            f"Approval {approval.approval_id} approved by {approver_id}",
            approval.step_id,
        )
        await self._publish_event(
            "workflow.step.completed",
            {
                "run_id": instance.run_id,
                "workflow_id": instance.workflow_id,
                "tenant_id": instance.tenant_id,
                "step_id": approval.step_id,
                "step_type": "approval",
            },
        )
        self.store.update_status(instance.run_id, "running", approval.step_id)
        instance = self._require_instance(instance.run_id)
        definition_record = self.store.get_definition(instance.workflow_id)
        if not definition_record:
            return instance
        if resume_after_decision:
            return await self._run_until_pause(
                instance, definition_record.definition, {"id": approver_id}
            )
        steps = definition_record.definition.get("steps", [])
        step_map = {step["id"]: step for step in steps}
        step = step_map.get(approval.step_id)
        if not step:
            return instance
        next_step_id = self._next_step_id(step, instance.payload)
        if next_step_id:
            self.store.update_status(instance.run_id, "running", next_step_id)
            return self._require_instance(instance.run_id)
        self.store.update_status(instance.run_id, "completed", None)
        self.store.add_event(instance.run_id, "completed", "Workflow completed")
        await self._publish_event(
            "workflow.completed",
            {
                "run_id": instance.run_id,
                "workflow_id": instance.workflow_id,
                "tenant_id": instance.tenant_id,
            },
        )
        return self._require_instance(instance.run_id)

    @dataclass
    class StepExecutionResult:
        instance: WorkflowInstance
        status: str
        next_step_id: str | None
        should_retry: bool = False
        retry_delay_seconds: int = 0
        parallel_branches: list[str] | None = None
        join_step_id: str | None = None

    async def execute_step(
        self,
        instance: WorkflowInstance,
        definition: dict[str, Any],
        actor: dict[str, Any],
        step_id: str,
        skip_parallel_join: bool = False,
    ) -> StepExecutionResult:
        steps = definition.get("steps", [])
        if not steps:
            self.store.update_status(instance.run_id, "failed", instance.current_step_id)
            self.store.add_event(instance.run_id, "failed", "Workflow has no steps")
            await self._publish_event(
                "workflow.failed",
                {
                    "run_id": instance.run_id,
                    "workflow_id": instance.workflow_id,
                    "tenant_id": instance.tenant_id,
                    "reason": "Workflow has no steps",
                },
            )
            return self.StepExecutionResult(self._require_instance(instance.run_id), "failed", None)

        step_map = {step["id"]: step for step in steps}
        step = step_map.get(step_id)
        if not step:
            self.store.update_status(instance.run_id, "failed", step_id)
            self.store.add_event(
                instance.run_id, "failed", f"Unknown step {step_id}", step_id
            )
            await self._publish_event(
                "workflow.failed",
                {
                    "run_id": instance.run_id,
                    "workflow_id": instance.workflow_id,
                    "tenant_id": instance.tenant_id,
                    "reason": f"Unknown step {step_id}",
                },
            )
            return self.StepExecutionResult(self._require_instance(instance.run_id), "failed", None)

        step_type = step["type"]
        existing_state = self.store.get_step_state(instance.run_id, step_id)
        if (
            existing_state
            and existing_state.status == "completed"
            and step_type not in {"loop", "decision"}
        ):
            instance = self._require_instance(instance.run_id)
            return self.StepExecutionResult(instance, "completed", instance.current_step_id)
        await self._publish_event(
            "workflow.step.started",
            {
                "run_id": instance.run_id,
                "workflow_id": instance.workflow_id,
                "tenant_id": instance.tenant_id,
                "step_id": step_id,
                "step_type": step_type,
            },
        )

        if step_type == "parallel":
            branches = [branch.get("next") for branch in step.get("branches", [])]
            branch_ids = [branch for branch in branches if branch]
            join_step_id = step.get("join")
            if not branch_ids or not join_step_id:
                self.store.update_status(instance.run_id, "failed", step_id)
                self.store.add_event(
                    instance.run_id,
                    "failed",
                    f"Parallel step {step_id} missing branches or join",
                    step_id,
                )
                await self._publish_event(
                    "workflow.failed",
                    {
                        "run_id": instance.run_id,
                        "workflow_id": instance.workflow_id,
                        "tenant_id": instance.tenant_id,
                        "reason": f"Parallel step {step_id} missing branches or join",
                    },
                )
                return self.StepExecutionResult(self._require_instance(instance.run_id), "failed", None)

            self.store.upsert_step_state(
                instance.run_id,
                step_id,
                "completed",
                attempts=1,
                output={"branches": branch_ids, "join": join_step_id},
            )
            self.store.update_status(instance.run_id, "waiting_parallel", step_id)
            self.store.add_event(
                instance.run_id,
                "parallel_started",
                f"Parallel step {step_id} dispatched",
                step_id,
            )
            await self._publish_event(
                "workflow.step.completed",
                {
                    "run_id": instance.run_id,
                    "workflow_id": instance.workflow_id,
                    "tenant_id": instance.tenant_id,
                    "step_id": step_id,
                    "step_type": step_type,
                },
            )
            return self.StepExecutionResult(
                self._require_instance(instance.run_id),
                "parallel",
                None,
                parallel_branches=branch_ids,
                join_step_id=join_step_id,
            )
        if step_type == "approval":
            existing_approval = self.store.find_approval_for_step(instance.run_id, step_id)
            if existing_approval and existing_approval.status == "approved":
                self.store.upsert_step_state(
                    instance.run_id,
                    step_id,
                    "completed",
                    attempts=1,
                    output={"approval_id": existing_approval.approval_id},
                )
                self.store.add_event(
                    instance.run_id,
                    "completed",
                    f"Approval {existing_approval.approval_id} approved",
                    step_id,
                )
                next_step_id = self._next_step_id(step, instance.payload)
                if next_step_id:
                    self.store.update_status(instance.run_id, "running", next_step_id)
                    return self.StepExecutionResult(
                        self._require_instance(instance.run_id), "completed", next_step_id
                    )
                self.store.update_status(instance.run_id, "completed", None)
                self.store.add_event(instance.run_id, "completed", "Workflow completed")
                await self._publish_event(
                    "workflow.completed",
                    {
                        "run_id": instance.run_id,
                        "workflow_id": instance.workflow_id,
                        "tenant_id": instance.tenant_id,
                    },
                )
                return self.StepExecutionResult(
                    self._require_instance(instance.run_id), "completed", None
                )
            if existing_approval and existing_approval.status == "rejected":
                self.store.update_status(instance.run_id, "rejected", step_id)
                self.store.add_event(
                    instance.run_id,
                    "rejected",
                    f"Approval {existing_approval.approval_id} rejected",
                    step_id,
                )
                return self.StepExecutionResult(
                    self._require_instance(instance.run_id), "rejected", None
                )
            approval = await self._ensure_approval(instance, step, actor)
            self.store.update_status(instance.run_id, "waiting_approval", step_id)
            self.store.add_event(
                instance.run_id,
                "waiting_approval",
                f"Waiting on approval {approval.approval_id}",
                step_id,
            )
            return self.StepExecutionResult(
                self._require_instance(instance.run_id), "waiting_approval", None
            )

        step_output: dict[str, Any] = {}
        previous_attempts = existing_state.attempts if existing_state else 0
        attempts = previous_attempts + 1
        retry_policy = step.get("retry", {})
        max_attempts = max(1, retry_policy.get("max_attempts", 1))
        delay_seconds = max(0, retry_policy.get("delay_seconds", 0))
        failures_before_success = step.get("config", {}).get("failures_before_success", 0)
        simulate_timeout = step.get("config", {}).get("simulate_timeout", False)
        breaker = self._get_circuit_breaker(step, instance)

        if breaker and not breaker.allow():
            self.store.upsert_step_state(
                instance.run_id, step_id, "paused", previous_attempts, step_output
            )
            self.store.update_status(instance.run_id, "paused", step_id)
            self.store.add_event(
                instance.run_id,
                "paused",
                f"Circuit open for step {step_id}; retry after "
                f"{breaker.time_until_retry():.0f}s",
                step_id,
            )
            await self._publish_event(
                "workflow.failed",
                {
                    "run_id": instance.run_id,
                    "workflow_id": instance.workflow_id,
                    "tenant_id": instance.tenant_id,
                    "reason": f"Circuit open for step {step_id}",
                },
            )
            return self.StepExecutionResult(self._require_instance(instance.run_id), "paused", None)

        if simulate_timeout and step.get("timeout_seconds"):
            self.store.update_step_error(
                instance.run_id,
                step_id,
                f"Step timed out after {step['timeout_seconds']} seconds",
            )
            self.store.update_status(instance.run_id, "failed", step_id)
            self.store.add_event(
                instance.run_id,
                "failed",
                f"Step {step_id} timed out",
                step_id,
            )
            await self._run_compensation(instance, step, actor, reason="timeout")
            await self._publish_event(
                "workflow.failed",
                {
                    "run_id": instance.run_id,
                    "workflow_id": instance.workflow_id,
                    "tenant_id": instance.tenant_id,
                    "reason": f"Step {step_id} timed out",
                },
            )
            return self.StepExecutionResult(self._require_instance(instance.run_id), "failed", None)

        if failures_before_success and attempts <= failures_before_success:
            return await self._prepare_retry(
                instance,
                step,
                actor,
                step_id,
                attempts,
                max_attempts,
                delay_seconds,
                step_output,
                breaker,
                failure_message="Simulated failure before success",
            )

        if step_type == "task":
            agent_config = step.get("config", {})
            agent_id = agent_config.get("agent")
            action = agent_config.get("action")
            if not self.agent_client:
                self.store.upsert_step_state(
                    instance.run_id, step_id, "failed", attempts, step_output
                )
                self.store.update_step_error(
                    instance.run_id, step_id, "Agent client not configured"
                )
                self.store.update_status(instance.run_id, "failed", step_id)
                self.store.add_event(
                    instance.run_id,
                    "failed",
                    f"Agent client not configured for step {step_id}",
                    step_id,
                )
                await self._run_compensation(instance, step, actor, reason="agent_client_missing")
                await self._publish_event(
                    "workflow.failed",
                    {
                        "run_id": instance.run_id,
                        "workflow_id": instance.workflow_id,
                        "tenant_id": instance.tenant_id,
                        "reason": f"Agent client not configured for step {step_id}",
                    },
                )
                return self.StepExecutionResult(self._require_instance(instance.run_id), "failed", None)
            if not agent_id or not action:
                self.store.upsert_step_state(
                    instance.run_id, step_id, "failed", attempts, step_output
                )
                self.store.update_step_error(
                    instance.run_id, step_id, "Task step missing agent or action"
                )
                self.store.update_status(instance.run_id, "failed", step_id)
                self.store.add_event(
                    instance.run_id,
                    "failed",
                    f"Task step {step_id} missing agent/action",
                    step_id,
                )
                await self._run_compensation(instance, step, actor, reason="agent_config_missing")
                await self._publish_event(
                    "workflow.failed",
                    {
                        "run_id": instance.run_id,
                        "workflow_id": instance.workflow_id,
                        "tenant_id": instance.tenant_id,
                        "reason": f"Task step {step_id} missing agent/action",
                    },
                )
                return self.StepExecutionResult(self._require_instance(instance.run_id), "failed", None)
            resolved_config = {
                key: self._resolve_reference(value, instance.payload)
                for key, value in agent_config.items()
                if key not in {"agent", "action"}
            }
            try:
                agent_response = await self.agent_client.execute(
                    agent_id=agent_id,
                    action=action,
                    payload={
                        "workflow_id": instance.workflow_id,
                        "run_id": instance.run_id,
                        "step_id": step_id,
                        "payload": instance.payload,
                        "config": resolved_config,
                        "actor": actor,
                    },
                    context={
                        "tenant_id": instance.tenant_id,
                        "correlation_id": instance.run_id,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - bubble up with retry metadata
                return await self._prepare_retry(
                    instance,
                    step,
                    actor,
                    step_id,
                    attempts,
                    max_attempts,
                    delay_seconds,
                    step_output,
                    breaker,
                    failure_message=f"Agent call failed: {exc}",
                )
            step_output = {
                "agent": agent_id,
                "action": action,
                "response": agent_response,
            }
            if breaker:
                breaker.record_success()
        elif step_type == "api":
            config = step.get("config", {})
            endpoint = config.get("endpoint")
            if not endpoint:
                self.store.update_status(instance.run_id, "failed", step_id)
                self.store.add_event(
                    instance.run_id, "failed", f"API step {step_id} missing endpoint", step_id
                )
                await self._run_compensation(instance, step, actor, reason="api_missing_endpoint")
                await self._publish_event(
                    "workflow.failed",
                    {
                        "run_id": instance.run_id,
                        "workflow_id": instance.workflow_id,
                        "tenant_id": instance.tenant_id,
                        "reason": f"API step {step_id} missing endpoint",
                    },
                )
                return self.StepExecutionResult(self._require_instance(instance.run_id), "failed", None)
            method = str(config.get("method", "POST")).upper()
            headers = config.get("headers", {})
            body = config.get("payload", {})
            timeout = config.get("timeout_seconds", step.get("timeout_seconds", 10))
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(method, endpoint, json=body, headers=headers)
                    response.raise_for_status()
                    step_output = {"endpoint": endpoint, "status_code": response.status_code}
            except Exception as exc:  # noqa: BLE001
                return await self._prepare_retry(
                    instance,
                    step,
                    actor,
                    step_id,
                    attempts,
                    max_attempts,
                    delay_seconds,
                    step_output,
                    breaker,
                    failure_message=f"API call failed: {exc}",
                )
        elif step_type == "notification":
            step_output = {
                "channel": step.get("config", {}).get("channel"),
                "template": step.get("config", {}).get("template"),
            }
        elif step_type == "script":
            step_output = {"script": step.get("script")}
        elif step_type in {"decision", "loop"}:
            next_step_id = self._next_step_id(step, instance.payload, attempts)
            self.store.upsert_step_state(
                instance.run_id,
                step_id,
                "completed",
                attempts,
                {"iteration": attempts, "next": next_step_id},
            )
            self.store.add_event(
                instance.run_id,
                "completed",
                f"Step {step_id} evaluated",
                step_id,
            )
            if next_step_id:
                self.store.update_status(instance.run_id, "running", next_step_id)
                return self.StepExecutionResult(
                    self._require_instance(instance.run_id), "completed", next_step_id
                )
            self.store.update_status(instance.run_id, "completed", None)
            self.store.add_event(instance.run_id, "completed", "Workflow completed")
            await self._publish_event(
                "workflow.completed",
                {
                    "run_id": instance.run_id,
                    "workflow_id": instance.workflow_id,
                    "tenant_id": instance.tenant_id,
                },
            )
            return self.StepExecutionResult(self._require_instance(instance.run_id), "completed", None)

        self.store.upsert_step_state(
            instance.run_id, step_id, "completed", attempts, step_output
        )
        self.store.add_event(
            instance.run_id,
            "completed",
            f"Step {step_id} completed",
            step_id,
        )
        await self._publish_event(
            "workflow.step.completed",
            {
                "run_id": instance.run_id,
                "workflow_id": instance.workflow_id,
                "tenant_id": instance.tenant_id,
                "step_id": step_id,
                "step_type": step_type,
            },
        )
        next_step_id = self._next_step_id(step, instance.payload, attempts)
        if not skip_parallel_join:
            next_step_id = self._maybe_trigger_parallel_join(
                instance.run_id, definition, step_id, next_step_id
            )
        if next_step_id:
            self.store.update_status(instance.run_id, "running", next_step_id)
            return self.StepExecutionResult(
                self._require_instance(instance.run_id), "completed", next_step_id
            )
        self.store.update_status(instance.run_id, "completed", None)
        self.store.add_event(instance.run_id, "completed", "Workflow completed")
        await self._publish_event(
            "workflow.completed",
            {
                "run_id": instance.run_id,
                "workflow_id": instance.workflow_id,
                "tenant_id": instance.tenant_id,
            },
        )
        return self.StepExecutionResult(self._require_instance(instance.run_id), "completed", None)

    async def _prepare_retry(
        self,
        instance: WorkflowInstance,
        step: dict[str, Any],
        actor: dict[str, Any],
        step_id: str,
        attempts: int,
        max_attempts: int,
        delay_seconds: int,
        step_output: dict[str, Any],
        breaker: CircuitBreaker | None,
        failure_message: str,
    ) -> StepExecutionResult:
        if breaker:
            breaker.record_failure()
            if breaker.is_open():
                self.store.upsert_step_state(
                    instance.run_id, step_id, "paused", attempts, step_output
                )
                self.store.update_status(instance.run_id, "paused", step_id)
                self.store.add_event(
                    instance.run_id,
                    "paused",
                    f"Circuit opened for step {step_id} after failure",
                    step_id,
                )
                return self.StepExecutionResult(self._require_instance(instance.run_id), "paused", None)
        if attempts < max_attempts:
            self.store.upsert_step_state(
                instance.run_id, step_id, "retrying", attempts, step_output
            )
            self.store.add_event(
                instance.run_id,
                "retrying",
                f"{failure_message}. Retrying step {step_id} ({attempts}/{max_attempts})",
                step_id,
            )
            return self.StepExecutionResult(
                self._require_instance(instance.run_id),
                "retrying",
                step_id,
                should_retry=True,
                retry_delay_seconds=delay_seconds * (2 ** (attempts - 1)),
            )
        self.store.update_step_error(
            instance.run_id, step_id, f"Step failed after {attempts} attempts"
        )
        self.store.update_status(instance.run_id, "failed", step_id)
        self.store.add_event(
            instance.run_id,
            "failed",
            f"Step {step_id} failed after retries",
            step_id,
        )
        await self._run_compensation(instance, step, actor, reason="retries_exhausted")
        return self.StepExecutionResult(self._require_instance(instance.run_id), "failed", None)

    def _maybe_trigger_parallel_join(
        self,
        run_id: str,
        definition: dict[str, Any],
        step_id: str,
        next_step_id: str | None,
    ) -> str | None:
        parallel_step = self._find_parallel_step(definition, step_id)
        if not parallel_step:
            return next_step_id
        branch_ids = [branch.get("next") for branch in parallel_step.get("branches", [])]
        branch_ids = [branch for branch in branch_ids if branch]
        join_step_id = parallel_step.get("join")
        if not join_step_id:
            return next_step_id
        completed = [
            self.store.get_step_state(run_id, branch)
            for branch in branch_ids
            if branch
        ]
        if all(state and state.status == "completed" for state in completed):
            return self._as_optional_str(join_step_id)
        self.store.update_status(run_id, "waiting_parallel", parallel_step.get("id"))
        return None

    async def _run_until_pause(
        self, instance: WorkflowInstance, definition: dict[str, Any], actor: dict[str, Any]
    ) -> WorkflowInstance:
        steps = definition.get("steps", [])
        if not steps:
            self.store.update_status(instance.run_id, "failed", instance.current_step_id)
            self.store.add_event(instance.run_id, "failed", "Workflow has no steps")
            await self._publish_event(
                "workflow.failed",
                {
                    "run_id": instance.run_id,
                    "workflow_id": instance.workflow_id,
                    "tenant_id": instance.tenant_id,
                    "reason": "Workflow has no steps",
                },
            )
            return self._require_instance(instance.run_id)

        step_map = {step["id"]: step for step in steps}
        current_step_id = instance.current_step_id or steps[0]["id"]

        while current_step_id:
            step = step_map.get(current_step_id)
            if not step:
                self.store.update_status(instance.run_id, "failed", current_step_id)
                self.store.add_event(
                    instance.run_id, "failed", f"Unknown step {current_step_id}", current_step_id
                )
                await self._publish_event(
                    "workflow.failed",
                    {
                        "run_id": instance.run_id,
                        "workflow_id": instance.workflow_id,
                        "tenant_id": instance.tenant_id,
                        "reason": f"Unknown step {current_step_id}",
                    },
                )
                return self._require_instance(instance.run_id)

            step_type = step["type"]
            if step_type == "parallel":
                result = await self.execute_step(
                    instance, definition, actor, current_step_id, skip_parallel_join=True
                )
                branch_ids = result.parallel_branches or []
                join_step_id = result.join_step_id
                for branch_id in branch_ids:
                    instance = await self._run_branch_until(
                        instance, definition, actor, branch_id, join_step_id
                    )
                    if instance.status in {"failed", "rejected", "paused", "waiting_approval"}:
                        return instance
                current_step_id = join_step_id
                self.store.update_status(instance.run_id, "running", current_step_id)
                instance = self._require_instance(instance.run_id)
                continue
            if step_type == "approval":
                existing_approval = self.store.find_approval_for_step(
                    instance.run_id, current_step_id
                )
                if existing_approval and existing_approval.status == "approved":
                    self.store.upsert_step_state(
                        instance.run_id,
                        current_step_id,
                        "completed",
                        attempts=1,
                        output={"approval_id": existing_approval.approval_id},
                    )
                    self.store.add_event(
                        instance.run_id,
                        "completed",
                        f"Approval {existing_approval.approval_id} approved",
                        current_step_id,
                    )
                    current_step_id = self._next_step_id(step, instance.payload)
                    self.store.update_status(instance.run_id, "running", current_step_id)
                    instance = self._require_instance(instance.run_id)
                    continue
                if existing_approval and existing_approval.status == "rejected":
                    self.store.update_status(instance.run_id, "rejected", current_step_id)
                    self.store.add_event(
                        instance.run_id,
                        "rejected",
                        f"Approval {existing_approval.approval_id} rejected",
                        current_step_id,
                    )
                    return self._require_instance(instance.run_id)
                approval = await self._ensure_approval(instance, step, actor)
                self.store.update_status(instance.run_id, "waiting_approval", current_step_id)
                self.store.add_event(
                    instance.run_id,
                    "waiting_approval",
                    f"Waiting on approval {approval.approval_id}",
                    current_step_id,
                )
                return self._require_instance(instance.run_id)
            result = await self.execute_step(
                instance, definition, actor, current_step_id, skip_parallel_join=True
            )
            instance = result.instance
            if result.status in {"failed", "rejected", "waiting_approval", "paused"}:
                return instance
            if result.should_retry and result.next_step_id:
                if result.retry_delay_seconds:
                    await asyncio.sleep(result.retry_delay_seconds)
                current_step_id = result.next_step_id
                continue
            current_step_id = result.next_step_id
            instance = self._require_instance(instance.run_id)

        self.store.update_status(instance.run_id, "completed", None)
        self.store.add_event(instance.run_id, "completed", "Workflow completed")
        await self._publish_event(
            "workflow.completed",
            {
                "run_id": instance.run_id,
                "workflow_id": instance.workflow_id,
                "tenant_id": instance.tenant_id,
            },
        )
        return self._require_instance(instance.run_id)

    def _get_circuit_breaker(
        self, step: dict[str, Any], instance: WorkflowInstance
    ) -> CircuitBreaker | None:
        config = step.get("config", {}).get("circuit_breaker", {})
        failure_threshold = int(config.get("failure_threshold", 0))
        if failure_threshold <= 0:
            return None
        recovery_timeout = int(config.get("recovery_timeout_seconds", 30))
        breaker_config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_timeout,
        )
        key = f"{instance.tenant_id}:{instance.workflow_id}:{step['id']}"
        return self.circuit_breakers.get(key, breaker_config)

    async def _handle_retry(
        self,
        instance: WorkflowInstance,
        step_id: str,
        attempts: int,
        max_attempts: int,
        delay_seconds: int,
        step_output: dict[str, Any],
        breaker: CircuitBreaker | None,
        failure_message: str,
    ) -> str:
        if breaker:
            breaker.record_failure()
            if breaker.is_open():
                self.store.upsert_step_state(
                    instance.run_id, step_id, "paused", attempts, step_output
                )
                self.store.update_status(instance.run_id, "paused", step_id)
                self.store.add_event(
                    instance.run_id,
                    "paused",
                    f"Circuit opened for step {step_id} after failure",
                    step_id,
                )
                return "pause"
        if attempts < max_attempts:
            self.store.upsert_step_state(
                instance.run_id, step_id, "retrying", attempts, step_output
            )
            self.store.add_event(
                instance.run_id,
                "retrying",
                f"{failure_message}. Retrying step {step_id} ({attempts}/{max_attempts})",
                step_id,
            )
            if delay_seconds:
                await asyncio.sleep(delay_seconds * (2 ** (attempts - 1)))
            return "retry"
        return "fail"

    def _next_step_id(
        self, step: dict[str, Any], payload: dict[str, Any], attempts: int = 1
    ) -> str | None:
        if step["type"] == "loop":
            max_iterations = step.get("max_iterations") or step.get("config", {}).get(
                "max_iterations", 0
            )
            condition = step.get("condition")
            should_continue = condition and self._evaluate_condition(condition, payload)
            if max_iterations and attempts >= max_iterations:
                return self._as_optional_str(step.get("exit") or step.get("default_next"))
            if should_continue:
                return self._as_optional_str(step.get("next"))
            return self._as_optional_str(
                step.get("exit") or step.get("default_next") or step.get("next")
            )

        if step["type"] != "decision":
            return self._as_optional_str(step.get("next"))

        for branch in step.get("branches", []):
            condition = branch.get("condition")
            if condition and self._evaluate_condition(condition, payload):
                return self._as_optional_str(branch.get("next"))
        return self._as_optional_str(step.get("default_next") or step.get("next"))

    def _evaluate_condition(self, condition: dict[str, Any], payload: dict[str, Any]) -> bool:
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        resolved = self._resolve_reference(field, payload)

        if operator == "exists":
            return resolved is not None
        if operator == "equals":
            return bool(resolved == value)
        if operator == "not_equals":
            return bool(resolved != value)
        if operator == "greater_than":
            return resolved is not None and resolved > value
        if operator == "less_than":
            return resolved is not None and resolved < value
        if operator == "contains":
            if isinstance(resolved, (list, tuple, set)):
                return value in resolved
            if isinstance(resolved, str):
                return str(value) in resolved
        return False

    async def _ensure_approval(
        self, instance: WorkflowInstance, step: dict[str, Any], actor: dict[str, Any]
    ) -> WorkflowApproval:
        existing = self.store.find_approval_for_step(instance.run_id, step["id"])
        if existing:
            return existing
        config = step.get("config", {})
        request_type = config.get("request_type", "phase_gate")
        request_id = self._resolve_reference(config.get("request_id"), instance.payload) or (
            f"{instance.run_id}:{step['id']}"
        )
        requester = self._resolve_reference(config.get("requester"), instance.payload) or actor.get(
            "id", "system"
        )
        details = {
            key: self._resolve_reference(value, instance.payload)
            for key, value in config.get("details", {}).items()
        }
        details["workflow_id"] = instance.workflow_id
        details["run_id"] = instance.run_id
        details["step_id"] = step["id"]

        response = await self.approval_agent.process(
            {
                "request_type": request_type,
                "request_id": request_id,
                "requester": requester,
                "details": details,
                "tenant_id": instance.tenant_id,
                "context": {"tenant_id": instance.tenant_id, "correlation_id": instance.run_id},
            }
        )
        approval_id = response.get("approval_id")
        if not approval_id:
            raise ValueError("Approval agent did not return an approval ID")
        approvers = response.get("approvers") or config.get("approvers") or [requester]
        metadata = {
            "request_type": request_type,
            "request_id": request_id,
            "approvers": approvers,
            "approval_chain": response.get("approval_chain"),
            "deadline": response.get("deadline"),
            "details": details,
        }
        if step.get("timeout_seconds"):
            metadata["timeout_seconds"] = step.get("timeout_seconds")
        return self.store.upsert_approval(
            approval_id=approval_id,
            run_id=instance.run_id,
            step_id=step["id"],
            tenant_id=instance.tenant_id,
            status="pending",
            metadata=metadata,
        )

    async def _run_compensation(
        self, instance: WorkflowInstance, step: dict[str, Any], actor: dict[str, Any], reason: str
    ) -> None:
        compensation = step.get("on_error", {}).get("compensation") or step.get("compensation")
        if not compensation:
            return
        if not self.agent_client:
            return
        agent_id = compensation.get("agent")
        action = compensation.get("action")
        if not agent_id or not action:
            return
        config = compensation.get("config", {})
        await self.agent_client.execute(
            agent_id=agent_id,
            action=action,
            payload={
                "workflow_id": instance.workflow_id,
                "run_id": instance.run_id,
                "step_id": step.get("id"),
                "payload": instance.payload,
                "config": config,
                "actor": actor,
                "reason": reason,
            },
            context={
                "tenant_id": instance.tenant_id,
                "correlation_id": instance.run_id,
            },
        )
        self.store.add_event(
            instance.run_id,
            "compensated",
            f"Compensation executed for step {step.get('id')}",
            step.get("id"),
        )

    def _load_event_bus(self) -> Any | None:
        if get_event_bus is None:
            return None
        try:
            return get_event_bus()
        except Exception:
            return None

    async def _publish_event(self, topic: str, payload: dict[str, Any]) -> None:
        if not self.event_bus:
            return
        try:
            result = self.event_bus.publish(topic, payload)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            return

    async def _run_branch_until(
        self,
        instance: WorkflowInstance,
        definition: dict[str, Any],
        actor: dict[str, Any],
        start_step_id: str,
        stop_step_id: str | None,
    ) -> WorkflowInstance:
        current_step_id: str | None = start_step_id
        while current_step_id and current_step_id != stop_step_id:
            result = await self.execute_step(
                instance, definition, actor, current_step_id, skip_parallel_join=True
            )
            instance = result.instance
            if result.status in {"failed", "rejected", "waiting_approval", "paused"}:
                return instance
            current_step_id = result.next_step_id
        return instance

    def _find_parallel_step(
        self, definition: dict[str, Any], step_id: str
    ) -> dict[str, Any] | None:
        for step in definition.get("steps", []):
            if step.get("type") != "parallel":
                continue
            for branch in step.get("branches", []):
                if branch.get("next") == step_id:
                    return cast(dict[str, Any], step)
        return None

    def _resolve_reference(self, value: Any, payload: dict[str, Any]) -> Any:
        if not isinstance(value, str):
            return value
        if not value.startswith("$."):
            return value
        path = value[2:].split(".")
        current: Any = {"payload": payload}
        for part in path:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
