"""Action handlers for manage_baseline and track_variance."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from schedule_utils import (
    fetch_financial_actuals,
    fetch_schedule_progress,
    get_schedule_state,
    persist_earned_value,
    publish_baseline_locked,
    publish_schedule_delay,
    submit_change_request,
)

if TYPE_CHECKING:
    from schedule_planning_agent import SchedulePlanningAgent


async def manage_baseline(
    agent: SchedulePlanningAgent,
    schedule_id: str,
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """
    Lock schedule as baseline.

    Returns baseline ID and locked schedule.
    """
    agent.logger.info("Creating baseline for schedule: %s", schedule_id)

    schedule = await get_schedule_state(agent, tenant_id, schedule_id)
    if not schedule:
        raise ValueError(f"Schedule not found: {schedule_id}")

    # Generate baseline ID
    from schedule_utils import generate_baseline_id

    baseline_id = await generate_baseline_id(schedule_id)

    # Create baseline snapshot
    baseline = {
        "baseline_id": baseline_id,
        "schedule_id": schedule_id,
        "tasks": schedule.get("tasks", []),
        "dependencies": schedule.get("dependencies", []),
        "milestones": schedule.get("milestones", []),
        "project_duration_days": schedule.get("project_duration_days", 0),
        "start_date": schedule.get("start_date"),
        "end_date": schedule.get("end_date"),
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "locked_by": "system",
        "status": "Locked",
    }

    # Store baseline
    agent.baselines[baseline_id] = baseline
    agent.baseline_store.upsert(tenant_id, baseline_id, baseline)

    # Update schedule status
    schedule["status"] = "Baselined"
    schedule["baseline_id"] = baseline_id
    agent.schedule_store.upsert(tenant_id, schedule_id, schedule)

    await publish_baseline_locked(
        agent,
        schedule,
        baseline,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    return {
        "baseline_id": baseline_id,
        "schedule_id": schedule_id,
        "locked_at": baseline["locked_at"],
        "task_count": len(baseline["tasks"]),
        "milestone_count": len(baseline["milestones"]),
    }


async def track_variance(
    agent: SchedulePlanningAgent,
    schedule_id: str,
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """
    Track schedule variance against baseline.

    Returns variance analysis.
    """
    agent.logger.info("Tracking variance for schedule: %s", schedule_id)

    schedule = await get_schedule_state(agent, tenant_id, schedule_id)
    if not schedule:
        raise ValueError(f"Schedule not found: {schedule_id}")

    baseline_id = schedule.get("baseline_id")
    if not baseline_id:
        return {
            "error": "No baseline exists for this schedule",
            "recommendation": "Create a baseline first",
        }

    baseline = agent.baselines.get(baseline_id) or agent.baseline_store.get(tenant_id, baseline_id)
    if not baseline:
        raise ValueError(f"Baseline not found: {baseline_id}")

    # Calculate schedule variance (SV)
    sv = await calculate_schedule_variance(schedule, baseline)
    baseline_duration = max(baseline.get("project_duration_days", 0), 1)
    schedule_variance_pct = sv / baseline_duration if baseline_duration else 0

    # Calculate schedule performance index (SPI)
    earned_value = await calculate_earned_value(agent, schedule, baseline, tenant_id=tenant_id)
    spi = earned_value.get("schedule_performance_index", 1.0)

    # Identify delayed tasks
    delayed_tasks = await identify_delayed_tasks(schedule, baseline)

    # Identify critical path changes
    critical_path_changes = await identify_critical_path_changes(schedule, baseline)

    change_request = None
    delay_event = None
    external_updates = []
    if sv < 0:
        delay_event = await publish_schedule_delay(
            agent,
            schedule,
            delay_days=abs(int(sv)),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

    if abs(sv) >= agent.baseline_approval_threshold * max(
        baseline.get("project_duration_days", 1), 1
    ):
        change_request = await submit_change_request(
            agent,
            schedule,
            baseline,
            variance_days=sv,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

    if agent.external_sync_client and agent.enable_external_sync:
        external_updates = [
            update.payload for update in agent.external_sync_client.pull_updates(schedule_id)
        ]

    if agent.analytics_client:
        agent.analytics_client.record_metric(
            "schedule.baseline_duration_days",
            float(baseline.get("project_duration_days", 0) or 0),
            {"schedule_id": schedule_id},
        )
        agent.analytics_client.record_metric(
            "schedule.actual_duration_days",
            float(schedule.get("project_duration_days", 0) or 0),
            {"schedule_id": schedule_id},
        )
        agent.analytics_client.record_metric(
            "schedule.variance_days",
            float(sv),
            {"schedule_id": schedule_id},
        )

    return {
        "schedule_id": schedule_id,
        "baseline_id": baseline_id,
        "schedule_variance_days": sv,
        "schedule_variance_pct": schedule_variance_pct,
        "schedule_performance_index": spi,
        "earned_value": earned_value,
        "variance_status": "Ahead" if sv > 0 else "Behind" if sv < 0 else "On Track",
        "delayed_tasks": delayed_tasks,
        "critical_path_changes": critical_path_changes,
        "forecast_completion": await forecast_completion_date(schedule, spi),
        "change_request": change_request,
        "delay_event": delay_event,
        "external_updates": external_updates,
    }


# ---------------------------------------------------------------------------
# EVM and variance helpers
# ---------------------------------------------------------------------------


async def calculate_schedule_variance(schedule: dict[str, Any], baseline: dict[str, Any]) -> float:
    """Calculate schedule variance in days."""
    planned = baseline.get("project_duration_days", 0)
    actual = schedule.get("project_duration_days", 0)
    return planned - actual  # type: ignore


async def calculate_earned_value(
    agent: SchedulePlanningAgent,
    schedule: dict[str, Any],
    baseline: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    project_id = schedule.get("project_id", "")
    financials = await fetch_financial_actuals(agent, project_id, tenant_id=tenant_id)
    progress = await fetch_schedule_progress(schedule, baseline)

    budget_at_completion = float(financials.get("budget_at_completion", 0))
    actual_cost = float(financials.get("actual_cost", 0))
    planned_value = budget_at_completion * float(progress.get("planned_percent", 0))
    ev = budget_at_completion * float(progress.get("percent_complete", 0))

    cpi = ev / actual_cost if actual_cost > 0 else 1.0
    spi = ev / planned_value if planned_value > 0 else 1.0

    result = {
        "budget_at_completion": budget_at_completion,
        "actual_cost": actual_cost,
        "planned_value": planned_value,
        "earned_value": ev,
        "percent_complete": progress.get("percent_complete", 0),
        "planned_percent": progress.get("planned_percent", 0),
        "cost_performance_index": cpi,
        "schedule_performance_index": spi,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }

    if agent.enable_persistence and agent._sql_engine:
        await persist_earned_value(agent, schedule, result)
    return result


async def identify_delayed_tasks(
    schedule: dict[str, Any], baseline: dict[str, Any]
) -> list[dict[str, Any]]:
    """Identify delayed tasks."""
    return []


async def identify_critical_path_changes(
    schedule: dict[str, Any], baseline: dict[str, Any]
) -> list[str]:
    """Identify changes to critical path."""
    return []


async def forecast_completion_date(schedule: dict[str, Any], spi: float) -> str:
    """Forecast completion date based on SPI."""
    return datetime.now(timezone.utc).isoformat()
