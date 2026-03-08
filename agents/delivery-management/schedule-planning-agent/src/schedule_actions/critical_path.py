"""Action handler for calculate_critical_path and CPM helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from schedule_utils import (
    apply_risk_adjustments_to_tasks,
    persist_schedule,
    publish_critical_path_changed,
    publish_schedule_updated,
    resolve_risk_data,
)

if TYPE_CHECKING:
    from schedule_planning_agent import SchedulePlanningAgent


async def calculate_critical_path(
    agent: SchedulePlanningAgent,
    schedule_id: str,
    risk_data: dict[str, Any] | None = None,
    dependency_results: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Calculate critical path using CPM.

    Returns critical path and total project duration.
    """
    agent.logger.info("Calculating critical path for schedule: %s", schedule_id)

    schedule = agent.schedules.get(schedule_id)
    if not schedule:
        raise ValueError(f"Schedule not found: {schedule_id}")

    tasks = schedule.get("tasks", [])
    dependencies = schedule.get("dependencies", [])
    resolved_risk_data = resolve_risk_data(
        risk_data,
        dependency_results,
        context,
        fallback=schedule.get("risk_data"),
    )
    tasks = apply_risk_adjustments_to_tasks(agent, tasks, resolved_risk_data)

    # Perform forward pass (calculate early start/finish)
    tasks_with_early = await forward_pass(tasks, dependencies)

    # Perform backward pass (calculate late start/finish)
    tasks_with_late = await backward_pass(tasks_with_early, dependencies)

    # Calculate slack/float for each task
    tasks_with_slack = await calculate_slack(tasks_with_late)

    # Identify critical path (tasks with zero slack)
    critical_path_tasks = [task for task in tasks_with_slack if task.get("slack", 0) == 0]

    # Calculate total project duration
    project_duration = (
        max(task.get("late_finish", 0) for task in tasks_with_slack) if tasks_with_slack else 0
    )

    previous_path = schedule.get("critical_path", [])
    schedule["tasks"] = tasks_with_slack
    schedule["critical_path"] = [t["task_id"] for t in critical_path_tasks]
    schedule["project_duration_days"] = project_duration
    schedule["risk_data"] = resolved_risk_data

    if agent.enable_persistence and agent._sql_engine:
        await persist_schedule(agent, schedule)

    if previous_path != schedule["critical_path"]:
        await publish_critical_path_changed(
            agent, schedule, previous_path, schedule["critical_path"]
        )

    await publish_schedule_updated(agent, schedule, "schedule.updated")

    return {
        "schedule_id": schedule_id,
        "critical_path": critical_path_tasks,
        "project_duration_days": project_duration,
        "critical_path_task_count": len(critical_path_tasks),
        "total_slack_days": sum(t.get("slack", 0) for t in tasks_with_slack),
    }


# ---------------------------------------------------------------------------
# CPM calculation helpers
# ---------------------------------------------------------------------------


async def calculate_cpm_dates(
    agent: SchedulePlanningAgent,
    tasks: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Calculate CPM dates for tasks."""
    tasks_with_early = await forward_pass(tasks, dependencies)
    tasks_with_late = await backward_pass(tasks_with_early, dependencies)
    return await calculate_slack(tasks_with_late)


def forward_pass_sync(
    tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    task_map = {task["task_id"]: dict(task) for task in tasks}
    predecessors: dict[str, list[str]] = {task_id: [] for task_id in task_map}
    for dep in dependencies:
        pred = dep.get("predecessor")
        succ = dep.get("successor")
        if (
            isinstance(pred, str)
            and isinstance(succ, str)
            and pred in task_map
            and succ in task_map
        ):
            predecessors[succ].append(pred)

    in_degree = {task_id: len(preds) for task_id, preds in predecessors.items()}
    queue = [task_id for task_id, count in in_degree.items() if count == 0]
    ordered: list[str] = []
    while queue:
        current = queue.pop(0)
        ordered.append(current)
        for dep in dependencies:
            if dep.get("predecessor") == current:
                succ = dep.get("successor")
                if succ in in_degree:
                    in_degree[succ] -= 1
                    if in_degree[succ] == 0:
                        queue.append(succ)

    if len(ordered) != len(task_map):
        ordered = list(task_map.keys())

    for task_id in ordered:
        task = task_map[task_id]
        duration = float(task.get("duration", 0))
        if predecessors[task_id]:
            task["early_start"] = max(
                task_map[pred].get("early_finish", 0) for pred in predecessors[task_id]
            )
        else:
            task["early_start"] = 0
        task["early_finish"] = task["early_start"] + duration

    return list(task_map.values())


async def forward_pass(
    tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Perform CPM forward pass."""
    task_map = {task["task_id"]: task for task in tasks}
    predecessors: dict[str, list[str]] = {task["task_id"]: [] for task in tasks}
    for dep in dependencies:
        pred = dep.get("predecessor")
        succ = dep.get("successor")
        if (
            isinstance(pred, str)
            and isinstance(succ, str)
            and pred in task_map
            and succ in task_map
        ):
            predecessors[succ].append(pred)

    in_degree = {task_id: len(preds) for task_id, preds in predecessors.items()}
    queue = [task_id for task_id, count in in_degree.items() if count == 0]

    ordered = []
    while queue:
        current = queue.pop(0)
        ordered.append(current)
        for dep in dependencies:
            if dep.get("predecessor") == current:
                succ = dep.get("successor")
                if succ in in_degree:
                    in_degree[succ] -= 1
                    if in_degree[succ] == 0:
                        queue.append(succ)

    if len(ordered) != len(task_map):
        ordered = list(task_map.keys())

    for task_id in ordered:
        task = task_map[task_id]
        duration = float(task.get("duration", 0))
        if predecessors[task_id]:
            task["early_start"] = max(
                task_map[pred].get("early_finish", 0) for pred in predecessors[task_id]
            )
        else:
            task["early_start"] = 0
        task["early_finish"] = task["early_start"] + duration

    return list(task_map.values())


async def backward_pass(
    tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Perform CPM backward pass."""
    task_map = {task["task_id"]: task for task in tasks}
    successors: dict[str, list[str]] = {task["task_id"]: [] for task in tasks}
    for dep in dependencies:
        pred = dep.get("predecessor")
        succ = dep.get("successor")
        if (
            isinstance(pred, str)
            and isinstance(succ, str)
            and pred in task_map
            and succ in task_map
        ):
            successors[pred].append(succ)

    project_duration = max((t.get("early_finish", 0) for t in tasks), default=0)
    out_degree = {task_id: len(succs) for task_id, succs in successors.items()}
    queue = [task_id for task_id, count in out_degree.items() if count == 0]
    ordered = []
    while queue:
        current = queue.pop(0)
        ordered.append(current)
        for dep in dependencies:
            if dep.get("successor") == current:
                pred = dep.get("predecessor")
                if pred in out_degree:
                    out_degree[pred] -= 1
                    if out_degree[pred] == 0:
                        queue.append(pred)

    if len(ordered) != len(task_map):
        ordered = list(task_map.keys())

    for task_id in ordered:
        task = task_map[task_id]
        duration = float(task.get("duration", 0))
        if successors[task_id]:
            task["late_finish"] = min(
                task_map[succ].get("late_start", project_duration) for succ in successors[task_id]
            )
        else:
            task["late_finish"] = project_duration
        task["late_start"] = task["late_finish"] - duration

    return list(task_map.values())


async def calculate_slack(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calculate slack/float for tasks."""
    for task in tasks:
        task["slack"] = task.get("late_start", 0) - task.get("early_start", 0)
    return tasks
