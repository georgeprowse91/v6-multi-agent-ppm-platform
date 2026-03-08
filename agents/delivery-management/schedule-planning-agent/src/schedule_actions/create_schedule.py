"""Action handler for create_schedule."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from schedule_utils import (
    apply_risk_adjustments_to_tasks,
    generate_schedule_id,
    persist_schedule,
    publish_dependency_added,
    publish_schedule_created,
    resolve_risk_data,
    schedule_cache_key,
    sync_external_tools,
)

if TYPE_CHECKING:
    from schedule_planning_agent import SchedulePlanningAgent


async def create_schedule(
    agent: SchedulePlanningAgent,
    project_id: str,
    wbs: dict[str, Any],
    methodology: str = "predictive",
    risk_data: dict[str, Any] | None = None,
    dependency_results: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Create project schedule from WBS.

    Returns schedule ID and Gantt chart data.
    """
    agent.logger.info("Creating schedule for project: %s", project_id)

    # Generate unique schedule ID
    schedule_id = await generate_schedule_id(project_id)

    # Convert WBS to task list
    tasks = await wbs_to_tasks(wbs)

    # Estimate durations for all tasks
    from schedule_actions.estimate_duration import estimate_duration

    duration_estimates = await estimate_duration(agent, tasks, {"project_id": project_id})

    # Apply duration estimates to tasks
    tasks_with_durations = await apply_duration_estimates(tasks, duration_estimates)
    resolved_risk_data = resolve_risk_data(risk_data, dependency_results, context)
    tasks_with_durations = apply_risk_adjustments_to_tasks(
        agent, tasks_with_durations, resolved_risk_data
    )

    # Define dependencies
    dependencies = await suggest_dependencies(agent, tasks_with_durations)
    for dependency in dependencies:
        await publish_dependency_added(agent, {"schedule_id": schedule_id}, dependency)

    # Calculate early/late start/finish dates using CPM
    from schedule_actions.critical_path import calculate_cpm_dates

    scheduled_tasks = await calculate_cpm_dates(agent, tasks_with_durations, dependencies)

    # Identify critical path
    critical_path = await identify_critical_path(scheduled_tasks, dependencies)

    # Calculate project duration
    project_duration = await calculate_project_duration(scheduled_tasks)

    # Generate Gantt chart data
    gantt_data = await generate_gantt_data(scheduled_tasks, dependencies)

    # Identify milestones
    milestones = await identify_milestones(scheduled_tasks)

    # Create schedule record
    schedule = {
        "schedule_id": schedule_id,
        "project_id": project_id,
        "methodology": methodology,
        "tasks": scheduled_tasks,
        "dependencies": dependencies,
        "critical_path": critical_path,
        "project_duration_days": project_duration,
        "start_date": await calculate_schedule_start(scheduled_tasks),
        "end_date": await calculate_schedule_end(scheduled_tasks),
        "milestones": milestones,
        "gantt_data": gantt_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "Draft",
        "risk_data": resolved_risk_data,
    }

    # Store schedule
    agent.schedules[schedule_id] = schedule
    agent.milestones[schedule_id] = milestones
    agent.schedule_store.upsert(tenant_id, schedule_id, schedule)

    if agent.enable_persistence and agent._sql_engine:
        await persist_schedule(agent, schedule)

    if agent.integration_event_bus:
        await publish_schedule_created(agent, schedule)

    if agent.analytics_client:
        agent.analytics_client.record_metric(
            "schedule.duration_days",
            float(project_duration),
            {"schedule_id": schedule_id, "project_id": project_id},
        )
        agent.analytics_client.record_metric(
            "schedule.critical_path_length",
            float(len(critical_path)),
            {"schedule_id": schedule_id, "project_id": project_id},
        )

    if agent.cache_client:
        cache_key = schedule_cache_key(tenant_id, schedule_id)
        agent.cache_client.set(cache_key, schedule, ttl_seconds=agent.cache_ttl_seconds)

    await sync_external_tools(agent, schedule)

    agent.logger.info("Created schedule: %s", schedule_id)

    return {
        "schedule_id": schedule_id,
        "project_duration_days": project_duration,
        "task_count": len(scheduled_tasks),
        "critical_path_tasks": len(critical_path),
        "milestones": milestones,
        "gantt_data": gantt_data,
        "next_steps": "Review schedule, then lock as baseline",
    }


# ---------------------------------------------------------------------------
# Helpers used by create_schedule
# ---------------------------------------------------------------------------


async def wbs_to_tasks(wbs: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert WBS to flat task list."""
    tasks = []
    # Baseline
    task_id = 1
    for key, value in wbs.items():
        tasks.append(
            {
                "task_id": f"T{task_id:03d}",
                "wbs_id": key,
                "name": value.get("name", f"Task {task_id}"),
                "complexity": "medium",
            }
        )
        task_id += 1
    return tasks


async def apply_duration_estimates(
    tasks: list[dict[str, Any]], estimates: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply duration estimates to tasks."""
    for task in tasks:
        task_id = task.get("task_id")
        if task_id in estimates:
            task["duration"] = estimates[task_id]["expected"]
            task["duration_estimate"] = estimates[task_id]
            task["optimistic_duration"] = estimates[task_id]["optimistic"]
            task["most_likely_duration"] = estimates[task_id]["most_likely"]
            task["pessimistic_duration"] = estimates[task_id]["pessimistic"]
    return tasks


async def suggest_dependencies(
    agent: SchedulePlanningAgent, tasks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Suggest dependencies between tasks."""
    if not tasks:
        return []

    def _priority(task: dict[str, Any]) -> float:
        name = (task.get("name") or "").lower()
        keywords = [
            ("init", 1),
            ("plan", 2),
            ("design", 3),
            ("build", 4),
            ("implement", 4),
            ("test", 5),
            ("deploy", 6),
            ("close", 7),
        ]
        base = 3.0
        for key, score in keywords:
            if key in name:
                base = float(score)
                break
        if agent.ai_model_service and agent.enable_dependency_ai and agent.ai_duration_model_id:
            features = {"weight": len(name) / 10 if name else 1.0, "complexity": base / 3}
            ai_score = agent.ai_model_service.predict(agent.ai_duration_model_id, features)
            return base + ai_score / 10
        return base

    ordered = sorted(tasks, key=_priority) if agent.enable_dependency_ai else tasks
    dependencies: list[dict[str, Any]] = []
    for i in range(len(ordered) - 1):
        dependencies.append(
            {
                "predecessor": ordered[i]["task_id"],
                "successor": ordered[i + 1]["task_id"],
                "type": "FS",
                "lag": 0,
            }
        )
    return dependencies


async def identify_critical_path(
    tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
) -> list[str]:
    """Identify critical path task IDs."""
    critical_tasks = [task for task in tasks if float(task.get("slack", 0)) == 0]
    return [task["task_id"] for task in critical_tasks]


async def calculate_project_duration(tasks: list[dict[str, Any]]) -> float:
    """Calculate total project duration."""
    if not tasks:
        return 0
    return max(
        float(task.get("resource_finish", task.get("late_finish", task.get("early_finish", 0))))
        for task in tasks
    )


async def generate_gantt_data(
    tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
) -> dict[str, Any]:
    """Generate Gantt chart visualization data."""
    return {
        "tasks": tasks,
        "dependencies": dependencies,
        "timeline": {
            "start": await calculate_schedule_start(tasks),
            "end": await calculate_schedule_end(tasks),
        },
    }


async def identify_milestones(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Identify project milestones."""
    milestones = []
    for task in tasks:
        if task.get("is_milestone") or task.get("duration", 0) == 0:
            milestones.append(
                {
                    "name": task.get("name"),
                    "date": task.get("early_finish"),
                    "status": "pending",
                }
            )
    return milestones


async def calculate_schedule_start(tasks: list[dict[str, Any]]) -> str:
    """Calculate schedule start date."""
    return datetime.now(timezone.utc).isoformat()


async def calculate_schedule_end(tasks: list[dict[str, Any]]) -> str:
    """Calculate schedule end date."""
    duration = await calculate_project_duration(tasks)
    end_date = datetime.now(timezone.utc) + timedelta(days=duration)
    return end_date.isoformat()
