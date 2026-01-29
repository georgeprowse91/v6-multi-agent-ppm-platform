from __future__ import annotations

import asyncio
from typing import Any

from agent_client import AgentClient
from approval_workflow_agent import ApprovalWorkflowAgent

from circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerRegistry
from workflow_storage import WorkflowApproval, WorkflowInstance, WorkflowStore


class WorkflowRuntime:
    def __init__(
        self,
        store: WorkflowStore,
        approval_agent: ApprovalWorkflowAgent,
        agent_client: AgentClient | None = None,
        circuit_breakers: CircuitBreakerRegistry | None = None,
    ) -> None:
        self.store = store
        self.approval_agent = approval_agent
        self.agent_client = agent_client
        self.circuit_breakers = circuit_breakers or CircuitBreakerRegistry()

    async def start(
        self, instance: WorkflowInstance, definition: dict[str, Any], actor: dict[str, Any]
    ) -> WorkflowInstance:
        if instance.status != "running":
            self.store.update_status(instance.run_id, "running", instance.current_step_id)
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
            return self.store.get(instance.run_id)

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
        self.store.update_status(instance.run_id, "running", approval.step_id)
        instance = self.store.get(instance.run_id)
        definition_record = self.store.get_definition(instance.workflow_id)
        if not definition_record:
            return instance
        return await self._run_until_pause(instance, definition_record.definition, {"id": approver_id})

    async def _run_until_pause(
        self, instance: WorkflowInstance, definition: dict[str, Any], actor: dict[str, Any]
    ) -> WorkflowInstance:
        steps = definition.get("steps", [])
        if not steps:
            self.store.update_status(instance.run_id, "failed", instance.current_step_id)
            self.store.add_event(instance.run_id, "failed", "Workflow has no steps")
            return self.store.get(instance.run_id)

        step_map = {step["id"]: step for step in steps}
        current_step_id = instance.current_step_id or steps[0]["id"]

        while current_step_id:
            step = step_map.get(current_step_id)
            if not step:
                self.store.update_status(instance.run_id, "failed", current_step_id)
                self.store.add_event(
                    instance.run_id, "failed", f"Unknown step {current_step_id}", current_step_id
                )
                return self.store.get(instance.run_id)

            step_type = step["type"]
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
                    instance = self.store.get(instance.run_id)
                    continue
                if existing_approval and existing_approval.status == "rejected":
                    self.store.update_status(instance.run_id, "rejected", current_step_id)
                    self.store.add_event(
                        instance.run_id,
                        "rejected",
                        f"Approval {existing_approval.approval_id} rejected",
                        current_step_id,
                    )
                    return self.store.get(instance.run_id)
                approval = await self._ensure_approval(instance, step, actor)
                self.store.update_status(instance.run_id, "waiting_approval", current_step_id)
                self.store.add_event(
                    instance.run_id,
                    "waiting_approval",
                    f"Waiting on approval {approval.approval_id}",
                    current_step_id,
                )
                return self.store.get(instance.run_id)

            step_output = {}
            existing = self.store.get_step_state(instance.run_id, current_step_id)
            previous_attempts = existing.attempts if existing else 0
            attempts = previous_attempts + 1
            retry_policy = step.get("retry", {})
            max_attempts = max(1, retry_policy.get("max_attempts", 1))
            delay_seconds = max(0, retry_policy.get("delay_seconds", 0))
            failures_before_success = step.get("config", {}).get("failures_before_success", 0)
            simulate_timeout = step.get("config", {}).get("simulate_timeout", False)
            breaker = self._get_circuit_breaker(step, instance)

            if breaker and not breaker.allow():
                self.store.upsert_step_state(
                    instance.run_id,
                    current_step_id,
                    "paused",
                    previous_attempts,
                    step_output,
                )
                self.store.update_status(instance.run_id, "paused", current_step_id)
                self.store.add_event(
                    instance.run_id,
                    "paused",
                    f"Circuit open for step {current_step_id}; retry after "
                    f"{breaker.time_until_retry():.0f}s",
                    current_step_id,
                )
                return self.store.get(instance.run_id)

            if simulate_timeout and step.get("timeout_seconds"):
                self.store.update_step_error(
                    instance.run_id,
                    current_step_id,
                    f"Step timed out after {step['timeout_seconds']} seconds",
                )
                self.store.update_status(instance.run_id, "failed", current_step_id)
                self.store.add_event(
                    instance.run_id,
                    "failed",
                    f"Step {current_step_id} timed out",
                    current_step_id,
                )
                return self.store.get(instance.run_id)

            if failures_before_success and attempts <= failures_before_success:
                retry_action = await self._handle_retry(
                    instance,
                    current_step_id,
                    attempts,
                    max_attempts,
                    delay_seconds,
                    step_output,
                    breaker,
                    failure_message="Simulated failure before success",
                )
                if retry_action == "retry":
                    continue
                if retry_action == "pause":
                    return self.store.get(instance.run_id)
                self.store.update_step_error(
                    instance.run_id,
                    current_step_id,
                    f"Step failed after {attempts} attempts",
                )
                self.store.update_status(instance.run_id, "failed", current_step_id)
                self.store.add_event(
                    instance.run_id,
                    "failed",
                    f"Step {current_step_id} failed after retries",
                    current_step_id,
                )
                return self.store.get(instance.run_id)

            if step_type == "task":
                agent_config = step.get("config", {})
                agent_id = agent_config.get("agent")
                action = agent_config.get("action")
                if not self.agent_client:
                    self.store.upsert_step_state(
                        instance.run_id, current_step_id, "failed", attempts, step_output
                    )
                    self.store.update_step_error(
                        instance.run_id, current_step_id, "Agent client not configured"
                    )
                    self.store.update_status(instance.run_id, "failed", current_step_id)
                    self.store.add_event(
                        instance.run_id,
                        "failed",
                        f"Agent client not configured for step {current_step_id}",
                        current_step_id,
                    )
                    return self.store.get(instance.run_id)
                if not agent_id or not action:
                    self.store.upsert_step_state(
                        instance.run_id, current_step_id, "failed", attempts, step_output
                    )
                    self.store.update_step_error(
                        instance.run_id,
                        current_step_id,
                        "Task step missing agent or action",
                    )
                    self.store.update_status(instance.run_id, "failed", current_step_id)
                    self.store.add_event(
                        instance.run_id,
                        "failed",
                        f"Task step {current_step_id} missing agent/action",
                        current_step_id,
                    )
                    return self.store.get(instance.run_id)
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
                            "step_id": current_step_id,
                            "payload": instance.payload,
                            "config": resolved_config,
                            "actor": actor,
                        },
                        context={
                            "tenant_id": instance.tenant_id,
                            "correlation_id": instance.run_id,
                        },
                    )
                except Exception as exc:
                    retry_action = await self._handle_retry(
                        instance,
                        current_step_id,
                        attempts,
                        max_attempts,
                        delay_seconds,
                        step_output,
                        breaker,
                        failure_message=f"Agent call failed: {exc}",
                    )
                    if retry_action == "retry":
                        continue
                    if retry_action == "pause":
                        return self.store.get(instance.run_id)
                    self.store.upsert_step_state(
                        instance.run_id, current_step_id, "failed", attempts, step_output
                    )
                    self.store.update_step_error(
                        instance.run_id, current_step_id, f"Agent call failed: {exc}"
                    )
                    self.store.update_status(instance.run_id, "failed", current_step_id)
                    self.store.add_event(
                        instance.run_id,
                        "failed",
                        f"Agent call failed for step {current_step_id}",
                        current_step_id,
                    )
                    return self.store.get(instance.run_id)
                step_output = {
                    "agent": agent_id,
                    "action": action,
                    "response": agent_response,
                }
                if breaker:
                    breaker.record_success()

            self.store.upsert_step_state(
                instance.run_id, current_step_id, "completed", attempts, step_output
            )
            self.store.add_event(
                instance.run_id,
                "completed",
                f"Step {current_step_id} completed",
                current_step_id,
            )
            current_step_id = self._next_step_id(step, instance.payload)
            self.store.update_status(instance.run_id, "running", current_step_id)
            instance = self.store.get(instance.run_id)

        self.store.update_status(instance.run_id, "completed", None)
        self.store.add_event(instance.run_id, "completed", "Workflow completed")
        return self.store.get(instance.run_id)

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

    def _next_step_id(self, step: dict[str, Any], payload: dict[str, Any]) -> str | None:
        if step["type"] != "decision":
            return step.get("next")

        for branch in step.get("branches", []):
            condition = branch.get("condition")
            if condition and self._evaluate_condition(condition, payload):
                return branch.get("next")
        return step.get("default_next") or step.get("next")

    def _evaluate_condition(self, condition: dict[str, Any], payload: dict[str, Any]) -> bool:
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        resolved = self._resolve_reference(field, payload)

        if operator == "exists":
            return resolved is not None
        if operator == "equals":
            return resolved == value
        if operator == "not_equals":
            return resolved != value
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
