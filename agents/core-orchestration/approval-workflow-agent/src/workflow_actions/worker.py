"""Worker loop and task-execution helpers."""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from workflow_task_queue import build_task_message

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


async def run_worker_once(agent: WorkflowEngineAgent) -> dict[str, Any] | None:
    message = await agent.task_queue.reserve_task()
    if not message:
        return None
    result: dict[str, Any]
    try:
        result = await _handle_task_message(agent, message)
        await agent.task_queue.ack_task(message.message_id)
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        await mark_task_failed(
            agent,
            message.tenant_id,
            message.task_id,
            message.instance_id,
            reason=str(exc),
        )
        await agent.task_queue.fail_task(message.message_id, str(exc))
        result = {
            "task_id": message.task_id,
            "instance_id": message.instance_id,
            "status": "failed",
            "error": str(exc),
        }
    return result


async def _handle_task_message(agent: WorkflowEngineAgent, message: Any) -> dict[str, Any]:
    tenant_id = message.tenant_id
    task_id = message.task_id
    assignment = await agent._load_task_assignment(tenant_id, task_id)
    if not assignment:
        raise ValueError(f"Task assignment not found: {task_id}")
    if assignment.get("status") == "retrying" and assignment.get("next_retry_at"):
        next_retry = datetime.fromisoformat(assignment["next_retry_at"])
        if datetime.now(timezone.utc) < next_retry:
            await agent.task_queue.publish_task(
                build_task_message(
                    tenant_id=tenant_id,
                    instance_id=message.instance_id,
                    task_id=task_id,
                    task_type=assignment.get("task_type"),
                    payload=assignment.get("task_payload", {}),
                )
            )
            return {
                "task_id": task_id,
                "status": "retry_scheduled",
                "next_retry_at": assignment["next_retry_at"],
            }
    assignment["status"] = "in_progress"
    assignment["worker_id"] = agent.worker_id
    assignment["started_at"] = datetime.now(timezone.utc).isoformat()
    await agent.state_store.save_task(tenant_id, task_id, assignment.copy())

    task_payload = assignment.get("task_payload", {})
    if task_payload.get("simulate_failure"):
        raise RuntimeError("Simulated task failure")

    if assignment.get("task_type") == "automated":
        result_payload = await _execute_automated_task(agent, tenant_id, assignment)
        from workflow_actions.complete_task import handle_complete_task

        result = await handle_complete_task(agent, tenant_id, task_id, result_payload)
        return result
    if assignment.get("task_type") == "logic_app":
        await agent._invoke_logic_app(tenant_id, assignment)
        from workflow_actions.complete_task import handle_complete_task

        result = await handle_complete_task(
            agent, tenant_id, task_id, {"status": "logic_app_triggered"}
        )
        return result

    assignment["status"] = "assigned"
    assignment["assigned_at"] = datetime.now(timezone.utc).isoformat()
    await agent.state_store.save_task(tenant_id, task_id, assignment.copy())
    return {"task_id": task_id, "status": "assigned"}


async def mark_task_failed(
    agent: WorkflowEngineAgent,
    tenant_id: str,
    task_id: str,
    instance_id: str,
    reason: str,
) -> None:
    assignment = await agent._load_task_assignment(tenant_id, task_id)
    if assignment:
        assignment["status"] = "failed"
        assignment["failed_at"] = datetime.now(timezone.utc).isoformat()
        assignment["failure_reason"] = reason
        retry_policy = assignment.get("retry_policy") or {}
        retry_count = assignment.get("retry_count", 0)
        max_attempts = retry_policy.get("max_attempts", agent.max_retry_attempts)
        backoff_seconds = retry_policy.get("backoff_seconds", 0)
        # simulate_failure tasks are permanently failed - no retries
        if assignment.get("task_payload", {}).get("simulate_failure"):
            max_attempts = 0
        if retry_count < max_attempts:
            assignment["retry_count"] = retry_count + 1
            assignment["status"] = "retrying"
            if backoff_seconds:
                assignment["next_retry_at"] = (
                    datetime.now(timezone.utc) + timedelta(seconds=int(backoff_seconds))
                ).isoformat()
            await agent.state_store.save_task(tenant_id, task_id, assignment.copy())
            await agent._send_notification(
                tenant_id,
                "workflow.task.retrying",
                {
                    "task_id": task_id,
                    "instance_id": instance_id,
                    "retry_count": assignment["retry_count"],
                },
            )
            await agent.task_queue.publish_task(
                build_task_message(
                    tenant_id=tenant_id,
                    instance_id=instance_id,
                    task_id=task_id,
                    task_type=assignment.get("task_type"),
                    payload=assignment.get("task_payload", {}),
                )
            )
        else:
            await agent.state_store.save_task(tenant_id, task_id, assignment.copy())
            await agent._send_notification(
                tenant_id,
                "workflow.task.failed",
                {
                    "task_id": task_id,
                    "instance_id": instance_id,
                    "reason": reason,
                },
            )

    instance = await agent._load_instance(tenant_id, instance_id)
    if instance:
        instance.setdefault("failed_tasks", []).append(task_id)
        instance.setdefault("checkpoints", []).append(
            {
                "task_id": task_id,
                "status": "failed",
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        instance["last_checkpoint"] = task_id
        if assignment and assignment.get("status") == "retrying":
            instance["status"] = "retrying"
        else:
            instance["status"] = "failed"
        await agent.state_store.save_instance(tenant_id, instance_id, instance.copy())
        if instance["status"] == "failed":
            await agent._trigger_compensation(tenant_id, instance, reason=reason)
            await agent._send_notification(
                tenant_id,
                "workflow.failed",
                {"instance_id": instance_id, "reason": reason},
            )


async def _execute_automated_task(
    agent: WorkflowEngineAgent, tenant_id: str, assignment: dict[str, Any]
) -> dict[str, Any]:
    task_payload = assignment.get("task_payload", {})
    if task_payload.get("callable") or task_payload.get("script"):
        result = await _execute_script_task(agent, tenant_id, assignment)
        return {"status": "script_completed", "result": result}
    return {"status": "auto_completed"}


async def _execute_script_task(
    agent: WorkflowEngineAgent, tenant_id: str, assignment: dict[str, Any]
) -> dict[str, Any]:
    callable_path = assignment.get("task_payload", {}).get("callable")
    if not callable_path:
        raise ValueError("Script task requires callable path")
    module_name, _, function_name = callable_path.partition(":")
    if not module_name or not function_name:
        raise ValueError("Callable must be in 'module:function' format")
    module = importlib.import_module(module_name)
    func = getattr(module, function_name, None)
    if not callable(func):
        raise ValueError(f"Callable {callable_path} not found")
    return func(
        {
            "tenant_id": tenant_id,
            "instance_id": assignment.get("instance_id"),
            "task_id": assignment.get("task_id"),
            "payload": assignment.get("task_payload", {}),
            "variables": assignment.get("task_payload", {}).get("variables", {}),
        }
    )
