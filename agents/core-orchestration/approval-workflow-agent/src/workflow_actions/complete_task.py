"""Action handler: complete_task, with next-task resolution logic."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from engine_utils import evaluate_condition

if TYPE_CHECKING:
    from workflow_engine_agent import WorkflowEngineAgent


async def handle_complete_task(
    agent: WorkflowEngineAgent, tenant_id: str, task_id: str, task_result: dict[str, Any]
) -> dict[str, Any]:
    """
    Complete workflow task.

    Returns completion status and next steps.
    """
    agent.logger.info("Completing task: %s", task_id)

    # Find task assignment
    assignment = await agent._load_task_assignment(tenant_id, task_id)
    if not assignment:
        raise ValueError(f"Task assignment not found: {task_id}")

    # Update assignment
    assignment["status"] = "completed"
    assignment["completed_at"] = datetime.now(timezone.utc).isoformat()
    assignment["result"] = task_result
    await agent.state_store.save_task(tenant_id, task_id, assignment.copy())

    # Find workflow instance
    instance_id = assignment.get("instance_id")
    instance = None
    if instance_id:
        instance = await agent._load_instance(tenant_id, instance_id)
    next_tasks: list[dict[str, Any]] = []
    if instance:
        # Move task from current to completed
        if task_id in instance.get("current_tasks", []):
            instance["current_tasks"].remove(task_id)
        instance.get("completed_tasks", []).append(task_id)
        instance.setdefault("completed_steps", []).append(task_id)
        checkpoint = {
            "task_id": task_id,
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        instance.setdefault("checkpoints", []).append(checkpoint)
        instance["last_checkpoint"] = task_id

        # Update variables with task result
        instance.get("variables", {}).update(task_result)

        # Determine next tasks
        next_tasks = await determine_next_tasks(agent, instance, task_id)

        # Execute next tasks
        for next_task in next_tasks:
            await agent._execute_task(tenant_id, instance_id, next_task)

        # Check if workflow is complete
        if await is_workflow_complete(agent, instance):
            instance["status"] = "completed"
            instance["completed_at"] = datetime.now(timezone.utc).isoformat()
            await agent._emit_workflow_event(
                tenant_id,
                "workflow.completed",
                {"instance_id": instance_id, "workflow_id": instance.get("workflow_id")},
            )

    if instance_id and instance:
        await agent.state_store.save_instance(tenant_id, instance_id, instance.copy())
        await agent._emit_workflow_event(
            tenant_id,
            "workflow.task.completed",
            {"instance_id": instance_id, "task_id": task_id},
        )
        await agent._send_notification(
            tenant_id,
            "workflow.task.completed",
            {"instance_id": instance_id, "task_id": task_id},
        )

    return {
        "task_id": task_id,
        "status": "completed",
        "next_tasks": [t.get("task_id") for t in next_tasks] if next_tasks else [],
        "workflow_status": instance.get("status") if instance else "unknown",
    }


# ------------------------------------------------------------------
# Task resolution helpers
# ------------------------------------------------------------------


async def determine_next_tasks(
    agent: WorkflowEngineAgent, instance: dict[str, Any], completed_task_id: str
) -> list[dict[str, Any]]:
    """Determine next tasks to execute."""
    workflow_id = instance.get("workflow_id")
    tenant_id = instance.get("tenant_id") or "default"
    workflow = await agent._load_definition(tenant_id, workflow_id) if workflow_id else None
    if not workflow:
        return []
    transitions = workflow.get("transitions", [])
    tasks = workflow.get("tasks", [])
    task_map = {task.get("task_id"): task for task in tasks if task.get("task_id")}
    dependencies = workflow.get("dependencies", {})

    candidates = [
        transition for transition in transitions if transition.get("source") == completed_task_id
    ]
    next_task_ids: list[str] = []
    for transition in candidates:
        condition = transition.get("condition")
        if condition and not evaluate_condition(condition, instance.get("variables", {})):
            continue
        target = transition.get("target")
        if target:
            next_task_ids.extend(resolve_virtual_targets(target, task_map, transitions, instance))

    if not next_task_ids:
        sequence = workflow.get("task_sequence", [])
        if completed_task_id in sequence:
            index = sequence.index(completed_task_id)
            if index + 1 < len(sequence):
                next_task_ids = [sequence[index + 1]]

    completed_steps = set(instance.get("completed_steps", []))
    completed_steps.update(instance.get("completed_tasks", []))
    filtered = []
    for task_id in dict.fromkeys(next_task_ids):
        if task_id in instance.get("current_tasks", []):
            continue
        if task_id in completed_steps:
            continue
        deps = set(dependencies.get(task_id, []))
        if deps and not deps.issubset(completed_steps):
            continue
        task = task_map.get(task_id)
        if task:
            filtered.append(task)
    return filtered


def resolve_virtual_targets(
    target_id: str,
    task_map: dict[str, dict[str, Any]],
    transitions: list[dict[str, Any]],
    instance: dict[str, Any],
    depth: int = 0,
) -> list[str]:
    if depth > 8:
        return []
    target = task_map.get(target_id)
    if not target:
        return []
    if target.get("type") not in {"decision", "parallel", "loop"}:
        return [target_id]
    instance.setdefault("completed_steps", [])
    if target_id not in instance["completed_steps"]:
        instance["completed_steps"].append(target_id)
    next_ids = []
    for transition in transitions:
        if transition.get("source") != target_id:
            continue
        condition = transition.get("condition")
        if condition and not evaluate_condition(condition, instance.get("variables", {})):
            continue
        if transition.get("target"):
            next_ids.extend(
                resolve_virtual_targets(
                    transition["target"], task_map, transitions, instance, depth + 1
                )
            )
    return next_ids


async def is_workflow_complete(agent: WorkflowEngineAgent, instance: dict[str, Any]) -> bool:
    """Check if workflow is complete."""
    if instance.get("status") != "running":
        return False
    if instance.get("current_tasks"):
        return False
    workflow_id = instance.get("workflow_id")
    tenant_id = instance.get("tenant_id") or "default"
    workflow = await agent._load_definition(tenant_id, workflow_id) if workflow_id else None
    if not workflow:
        return False
    completed = set(instance.get("completed_tasks", []))
    task_ids = {
        task.get("task_id")
        for task in workflow.get("tasks", [])
        if task.get("task_id") and task.get("type") not in {"decision", "parallel", "loop"}
    }
    return bool(task_ids) and task_ids.issubset(completed)
