"""Action handlers for schedule optimisation and applying accepted optimisations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from schedule_planning_agent import SchedulePlanningAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# optimize_schedule — analyse and return recommendations
# ---------------------------------------------------------------------------


async def optimize_schedule(agent: SchedulePlanningAgent, schedule_id: str) -> dict[str, Any]:
    """
    Optimise schedule to minimise duration.

    Returns optimised schedule with recommendations.
    """
    agent.logger.info("Optimizing schedule: %s", schedule_id)

    schedule = agent.schedules.get(schedule_id)
    if not schedule:
        raise ValueError(f"Schedule not found: {schedule_id}")

    opportunities = await identify_optimization_opportunities(schedule)
    optimized_schedule = await apply_optimizations(schedule, opportunities)
    improvements = await calculate_improvements(schedule, optimized_schedule)

    return {
        "schedule_id": schedule_id,
        "original_duration": schedule.get("project_duration_days", 0),
        "optimized_duration": optimized_schedule.get("project_duration_days", 0),
        "duration_reduction": improvements.get("duration_reduction", 0),
        "optimizations_applied": opportunities,
        "recommendations": await generate_optimization_recommendations(opportunities),
    }


# ---------------------------------------------------------------------------
# apply_optimization — accept a single recommendation and mutate schedule
# ---------------------------------------------------------------------------


async def apply_optimization(
    agent: SchedulePlanningAgent,
    schedule_id: str,
    optimization_id: str,
    optimization_type: str,
) -> dict[str, Any]:
    """Apply one accepted optimisation to the schedule.

    Args:
        agent: The schedule planning agent instance.
        schedule_id: ID of the schedule to mutate.
        optimization_id: Unique ID of the accepted suggestion.
        optimization_type: One of 'parallel_tasks', 'fast_track', 'crash',
                           'resource_level'.

    Returns:
        Updated schedule fragment with the optimisation applied.
    """
    agent.logger.info(
        "Applying optimization %s (%s) to schedule %s",
        optimization_id,
        optimization_type,
        schedule_id,
    )

    schedule = agent.schedules.get(schedule_id)
    if not schedule:
        raise ValueError(f"Schedule not found: {schedule_id}")

    tasks: list[dict[str, Any]] = list(schedule.get("tasks", []))
    task_map: dict[str, dict[str, Any]] = {t["id"]: t for t in tasks}

    if optimization_type == "parallel_tasks":
        tasks = _apply_parallel_tasks(tasks, task_map)
    elif optimization_type == "fast_track":
        tasks = _apply_fast_track(tasks, task_map)
    elif optimization_type == "crash":
        tasks = _apply_crash(tasks, task_map)
    elif optimization_type == "resource_level":
        tasks = _apply_resource_leveling(tasks, task_map)
    else:
        raise ValueError(f"Unknown optimization type: {optimization_type}")

    # Recalculate project duration
    if tasks:
        end_dates = [t.get("end_date", t.get("endDate", "")) for t in tasks]
        end_dates = [d for d in end_dates if d]
        if end_dates:
            schedule["project_duration_days"] = _date_span_days(
                min(
                    t.get("start_date", t.get("startDate", ""))
                    for t in tasks
                    if t.get("start_date") or t.get("startDate")
                ),
                max(end_dates),
            )

    schedule["tasks"] = tasks
    agent.schedules[schedule_id] = schedule

    return {
        "schedule_id": schedule_id,
        "optimization_id": optimization_id,
        "optimization_type": optimization_type,
        "status": "applied",
        "updated_task_count": len(tasks),
        "new_duration_days": schedule.get("project_duration_days", 0),
    }


# ---------------------------------------------------------------------------
# Optimisation strategies
# ---------------------------------------------------------------------------


def _apply_parallel_tasks(
    tasks: list[dict[str, Any]],
    task_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find tasks with no mutual dependencies and align start dates."""
    dep_sets: dict[str, set[str]] = {}
    for t in tasks:
        deps = set(t.get("dependencies", []))
        dep_sets[t["id"]] = deps

    for t in tasks:
        if dep_sets[t["id"]]:
            continue
        # Independent task — start as early as possible
        earliest = min(
            (
                tk.get("start_date", tk.get("startDate", "9999"))
                for tk in tasks
                if tk.get("start_date") or tk.get("startDate")
            ),
            default=t.get("start_date", t.get("startDate", "")),
        )
        duration = _task_duration_days(t)
        if earliest:
            t["start_date"] = earliest
            t["startDate"] = earliest
            t["end_date"] = _add_days(earliest, duration)
            t["endDate"] = _add_days(earliest, duration)
    return tasks


def _apply_fast_track(
    tasks: list[dict[str, Any]],
    task_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Overlap sequential critical-path tasks by 30 %."""
    for t in tasks:
        deps = t.get("dependencies", [])
        if not deps:
            continue
        for dep_id in deps:
            pred = task_map.get(dep_id)
            if not pred:
                continue
            pred_end = pred.get("end_date", pred.get("endDate", ""))
            if not pred_end:
                continue
            pred_dur = _task_duration_days(pred)
            overlap_days = max(int(pred_dur * 0.3), 1)
            new_start = _add_days(pred_end, -overlap_days)
            duration = _task_duration_days(t)
            t["start_date"] = new_start
            t["startDate"] = new_start
            t["end_date"] = _add_days(new_start, duration)
            t["endDate"] = _add_days(new_start, duration)
            break  # Only overlap with first predecessor
    return tasks


def _apply_crash(
    tasks: list[dict[str, Any]],
    task_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reduce critical-path task durations by 20 % (simulated crashing)."""
    for t in tasks:
        dur = _task_duration_days(t)
        if dur <= 1:
            continue
        crashed = max(int(dur * 0.8), 1)
        start = t.get("start_date", t.get("startDate", ""))
        if start:
            t["end_date"] = _add_days(start, crashed)
            t["endDate"] = _add_days(start, crashed)
    return tasks


def _apply_resource_leveling(
    tasks: list[dict[str, Any]],
    task_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Spread resource-overloaded tasks across available capacity windows."""
    resource_usage: dict[str, list[str]] = {}
    for t in tasks:
        res = t.get("resource_id", t.get("resourceId", ""))
        if res:
            resource_usage.setdefault(res, []).append(t["id"])

    for res_id, task_ids in resource_usage.items():
        if len(task_ids) <= 1:
            continue
        sorted_tasks = sorted(
            (task_map[tid] for tid in task_ids if tid in task_map),
            key=lambda x: x.get("start_date", x.get("startDate", "")),
        )
        cursor = sorted_tasks[0].get("start_date", sorted_tasks[0].get("startDate", ""))
        for t in sorted_tasks:
            dur = _task_duration_days(t)
            t["start_date"] = cursor
            t["startDate"] = cursor
            t["end_date"] = _add_days(cursor, dur)
            t["endDate"] = _add_days(cursor, dur)
            cursor = t["end_date"]
    return tasks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_duration_days(task: dict[str, Any]) -> int:
    start = task.get("start_date", task.get("startDate", ""))
    end = task.get("end_date", task.get("endDate", ""))
    return max(_date_span_days(start, end), 1) if start and end else 5


def _date_span_days(start: str, end: str) -> int:
    from datetime import date as _date

    try:
        s = _date.fromisoformat(start[:10])
        e = _date.fromisoformat(end[:10])
        return max((e - s).days, 0)
    except (ValueError, TypeError):
        return 0


def _add_days(iso: str, n: int) -> str:
    from datetime import date as _date
    from datetime import timedelta

    try:
        d = _date.fromisoformat(iso[:10]) + timedelta(days=n)
        return d.isoformat()
    except (ValueError, TypeError):
        return iso


async def identify_optimization_opportunities(
    schedule: dict[str, Any],
) -> list[dict[str, Any]]:
    """Identify schedule optimisation opportunities by analysing task graph."""
    tasks = schedule.get("tasks", [])
    opportunities: list[dict[str, Any]] = []

    # Detect independent tasks that could run in parallel
    dep_ids: set[str] = set()
    for t in tasks:
        dep_ids.update(t.get("dependencies", []))
    independent = [t for t in tasks if t["id"] not in dep_ids and not t.get("dependencies")]
    if len(independent) > 1:
        opportunities.append(
            {
                "type": "parallel_tasks",
                "description": f"Parallelise {len(independent)} independent tasks to reduce total duration",
                "affected_task_ids": [t["id"] for t in independent],
                "projected_saving_days": max(
                    sum(_task_duration_days(t) for t in independent)
                    - max(_task_duration_days(t) for t in independent),
                    1,
                ),
            }
        )

    # Detect sequential chains that could be fast-tracked
    chains = [t for t in tasks if t.get("dependencies")]
    if chains:
        saving = sum(max(int(_task_duration_days(t) * 0.3), 1) for t in chains[:3])
        opportunities.append(
            {
                "type": "fast_track",
                "description": f"Fast-track {len(chains)} dependent tasks with 30% overlap",
                "affected_task_ids": [t["id"] for t in chains],
                "projected_saving_days": saving,
            }
        )

    # Crash opportunity if project is long
    total_dur = schedule.get("project_duration_days", 0)
    if total_dur > 10:
        opportunities.append(
            {
                "type": "crash",
                "description": "Crash critical path by adding resources to reduce task durations by 20%",
                "affected_task_ids": [t["id"] for t in tasks],
                "projected_saving_days": max(int(total_dur * 0.2), 1),
            }
        )

    # Resource levelling
    resource_usage: dict[str, int] = {}
    for t in tasks:
        res = t.get("resource_id", t.get("resourceId", ""))
        if res:
            resource_usage[res] = resource_usage.get(res, 0) + 1
    overloaded = {k: v for k, v in resource_usage.items() if v > 2}
    if overloaded:
        opportunities.append(
            {
                "type": "resource_level",
                "description": f"Level {len(overloaded)} over-allocated resources to avoid burnout",
                "affected_task_ids": [
                    t["id"]
                    for t in tasks
                    if t.get("resource_id", t.get("resourceId", "")) in overloaded
                ],
                "projected_saving_days": 0,
            }
        )

    return opportunities


async def apply_optimizations(
    schedule: dict[str, Any], opportunities: list[dict[str, Any]]
) -> dict[str, Any]:
    """Apply all identified optimisations and return the modified schedule."""
    import copy

    result = copy.deepcopy(schedule)
    tasks = list(result.get("tasks", []))
    task_map = {t["id"]: t for t in tasks}

    for opp in opportunities:
        opt_type = opp.get("type", "")
        if opt_type == "parallel_tasks":
            tasks = _apply_parallel_tasks(tasks, task_map)
        elif opt_type == "fast_track":
            tasks = _apply_fast_track(tasks, task_map)
        elif opt_type == "crash":
            tasks = _apply_crash(tasks, task_map)
        elif opt_type == "resource_level":
            tasks = _apply_resource_leveling(tasks, task_map)

    result["tasks"] = tasks

    if tasks:
        end_dates = [t.get("end_date", t.get("endDate", "")) for t in tasks]
        end_dates = [d for d in end_dates if d]
        start_dates = [t.get("start_date", t.get("startDate", "")) for t in tasks]
        start_dates = [d for d in start_dates if d]
        if end_dates and start_dates:
            result["project_duration_days"] = _date_span_days(min(start_dates), max(end_dates))

    return result


async def calculate_improvements(
    original: dict[str, Any], optimized: dict[str, Any]
) -> dict[str, Any]:
    """Calculate improvements from optimisation."""
    return {
        "duration_reduction": original.get("project_duration_days", 0)
        - optimized.get("project_duration_days", 0)
    }


async def generate_optimization_recommendations(
    opportunities: list[dict[str, Any]],
) -> list[str]:
    """Generate human-readable optimisation recommendations."""
    return [opp.get("description", "") for opp in opportunities]
