"""Action handlers: pause_workflow, resume_workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


async def handle_pause_workflow(
    agent: WorkflowEngineAgent, tenant_id: str, instance_id: str
) -> dict[str, Any]:
    """
    Pause workflow execution.

    Returns pause confirmation.
    """
    agent.logger.info("Pausing workflow: %s", instance_id)

    instance = await agent._load_instance(tenant_id, instance_id)
    if not instance:
        raise ValueError(f"Workflow instance not found: {instance_id}")

    instance["status"] = "paused"
    instance["paused_at"] = datetime.now(timezone.utc).isoformat()
    await agent.state_store.save_instance(tenant_id, instance_id, instance.copy())
    await agent._emit_workflow_event(tenant_id, "workflow.paused", {"instance_id": instance_id})
    await agent._send_notification(tenant_id, "workflow.paused", {"instance_id": instance_id})

    return {"instance_id": instance_id, "status": "paused", "paused_at": instance["paused_at"]}


async def handle_resume_workflow(
    agent: WorkflowEngineAgent, tenant_id: str, instance_id: str
) -> dict[str, Any]:
    """
    Resume paused workflow.

    Returns resume confirmation.
    """
    agent.logger.info("Resuming workflow: %s", instance_id)

    instance = await agent._load_instance(tenant_id, instance_id)
    if not instance:
        raise ValueError(f"Workflow instance not found: {instance_id}")

    if instance.get("status") not in {"paused", "failed", "retrying", "compensating"}:
        raise ValueError(f"Workflow is not paused or failed: {instance_id}")

    instance["status"] = "running"
    instance["resumed_at"] = datetime.now(timezone.utc).isoformat()
    await agent.state_store.save_instance(tenant_id, instance_id, instance.copy())
    await agent._emit_workflow_event(tenant_id, "workflow.resumed", {"instance_id": instance_id})
    await agent._send_notification(tenant_id, "workflow.resumed", {"instance_id": instance_id})

    if instance.get("failed_tasks"):
        workflow_id = instance.get("workflow_id")
        workflow = await agent._load_definition(tenant_id, workflow_id) if workflow_id else None
        if workflow:
            for task_id in list(instance.get("failed_tasks", [])):
                task = next(
                    (item for item in workflow.get("tasks", []) if item.get("task_id") == task_id),
                    None,
                )
                if task:
                    await agent._execute_task(tenant_id, instance_id, task)
            instance["failed_tasks"] = []
            await agent.state_store.save_instance(tenant_id, instance_id, instance.copy())
        await _resume_from_checkpoint(agent, tenant_id, instance)

    return {
        "instance_id": instance_id,
        "status": "running",
        "resumed_at": instance["resumed_at"],
    }


async def _resume_from_checkpoint(
    agent: WorkflowEngineAgent, tenant_id: str, instance: dict[str, Any]
) -> None:
    if instance.get("status") != "running":
        return
    if instance.get("current_tasks"):
        return
    workflow_id = instance.get("workflow_id")
    workflow = await agent._load_definition(tenant_id, workflow_id) if workflow_id else None
    if not workflow:
        return
    last_checkpoint = instance.get("last_checkpoint")
    if not last_checkpoint:
        return
    from workflow_actions.complete_task import determine_next_tasks

    next_tasks = await determine_next_tasks(agent, instance, last_checkpoint)
    for next_task in next_tasks:
        await agent._execute_task(tenant_id, instance["instance_id"], next_task)
