"""
Utility functions and helpers for the Schedule Planning Agent.

Contains publishing, persistence, external sync, risk adjustment,
resource normalization, and miscellaneous helper methods.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from observability.tracing import get_trace_id

try:
    from events import ScheduleBaselineLockedEvent, ScheduleDelayEvent
except Exception:
    from packages.contracts.src.events import ScheduleBaselineLockedEvent, ScheduleDelayEvent

from sqlalchemy.orm import Session

from integrations.services.integration import (
    EventEnvelope,
    SqlRepository,
)

if TYPE_CHECKING:
    from schedule_planning_agent import SchedulePlanningAgent


# ---------------------------------------------------------------------------
# Cache key helpers
# ---------------------------------------------------------------------------


def schedule_cache_key(tenant_id: str, schedule_id: str) -> str:
    return f"schedule:{tenant_id}:{schedule_id}"


def simulation_cache_key(schedule_id: str) -> str:
    return f"schedule:simulation:{schedule_id}"


def duration_cache_key(project_id: str, task_signature: str) -> str:
    return f"schedule:duration:{project_id}:{task_signature}"


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


async def generate_schedule_id(project_id: str) -> str:
    """Generate unique schedule ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{project_id}-SCH-{timestamp}"


async def generate_baseline_id(schedule_id: str) -> str:
    """Generate unique baseline ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{schedule_id}-BASELINE-{timestamp}"


# ---------------------------------------------------------------------------
# Event publishing helpers
# ---------------------------------------------------------------------------


async def publish_baseline_locked(
    agent: SchedulePlanningAgent,
    schedule: dict[str, Any],
    baseline: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> None:
    event = ScheduleBaselineLockedEvent(
        event_name="schedule.baseline.locked",
        event_id=f"evt-{uuid.uuid4().hex}",
        timestamp=datetime.now(timezone.utc),
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        trace_id=get_trace_id(),
        payload={
            "project_id": schedule.get("project_id", ""),
            "schedule_id": schedule.get("schedule_id", ""),
            "locked_at": datetime.fromisoformat(baseline.get("locked_at")),
            "baseline_version": baseline.get("baseline_id", ""),
        },
    )
    await agent.event_bus.publish("schedule.baseline.locked", event.model_dump())


async def publish_schedule_delay(
    agent: SchedulePlanningAgent,
    schedule: dict[str, Any],
    *,
    delay_days: int,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    event = ScheduleDelayEvent(
        event_name="schedule.delay",
        event_id=f"evt-{uuid.uuid4().hex}",
        timestamp=datetime.now(timezone.utc),
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        trace_id=get_trace_id(),
        payload={
            "project_id": schedule.get("project_id", ""),
            "schedule_id": schedule.get("schedule_id", ""),
            "delay_days": delay_days,
            "reason": "Baseline variance detected",
            "detected_at": datetime.now(timezone.utc),
        },
    )
    payload = event.model_dump()
    await agent.event_bus.publish("schedule.delay", payload)
    return payload


async def publish_schedule_created(agent: SchedulePlanningAgent, schedule: dict[str, Any]) -> None:
    if not agent.integration_event_bus and not agent.event_bus:
        return
    envelope = EventEnvelope(
        event_type="schedule.created",
        subject=f"schedule/{schedule.get('schedule_id')}",
        data={
            "schedule_id": schedule.get("schedule_id"),
            "project_id": schedule.get("project_id"),
            "task_count": len(schedule.get("tasks", [])),
            "status": schedule.get("status"),
        },
    )
    agent.integration_event_bus.publish_event(envelope)
    if agent.event_bus:
        await agent.event_bus.publish("schedule.created", envelope.to_payload())


async def publish_task_updated(
    agent: SchedulePlanningAgent,
    schedule: dict[str, Any],
    task: dict[str, Any],
    event_type: str = "task.updated",
) -> None:
    if not agent.integration_event_bus:
        return
    envelope = EventEnvelope(
        event_type=event_type,
        subject=f"schedule/{schedule.get('schedule_id')}/task/{task.get('task_id')}",
        data={
            "schedule_id": schedule.get("schedule_id"),
            "task_id": task.get("task_id"),
            "duration": task.get("duration"),
            "status": task.get("status", "planned"),
        },
    )
    agent.integration_event_bus.publish_event(envelope)


async def publish_schedule_updated(
    agent: SchedulePlanningAgent, schedule: dict[str, Any], event_type: str
) -> None:
    if not agent.integration_event_bus and not agent.event_bus:
        return
    envelope = EventEnvelope(
        event_type=event_type,
        subject=f"schedule/{schedule.get('schedule_id')}",
        data={
            "schedule_id": schedule.get("schedule_id"),
            "project_id": schedule.get("project_id"),
            "status": schedule.get("status"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    if agent.integration_event_bus:
        agent.integration_event_bus.publish_event(envelope)
    if agent.event_bus:
        await agent.event_bus.publish(event_type, envelope.to_payload())


async def publish_dependency_added(
    agent: SchedulePlanningAgent, schedule: dict[str, Any], dependency: dict[str, Any]
) -> None:
    if not agent.integration_event_bus and not agent.event_bus:
        return
    envelope = EventEnvelope(
        event_type="dependency.added",
        subject=f"schedule/{schedule.get('schedule_id')}/dependency/{dependency.get('predecessor')}-{dependency.get('successor')}",
        data={
            "schedule_id": schedule.get("schedule_id"),
            "predecessor": dependency.get("predecessor"),
            "successor": dependency.get("successor"),
            "type": dependency.get("type"),
            "lag": dependency.get("lag"),
        },
    )
    if agent.integration_event_bus:
        agent.integration_event_bus.publish_event(envelope)
    if agent.event_bus:
        await agent.event_bus.publish("dependency.added", envelope.to_payload())


async def publish_critical_path_changed(
    agent: SchedulePlanningAgent,
    schedule: dict[str, Any],
    previous: list[str],
    current: list[str],
) -> None:
    if not agent.integration_event_bus and not agent.event_bus:
        return
    envelope = EventEnvelope(
        event_type="critical_path.changed",
        subject=f"schedule/{schedule.get('schedule_id')}/critical-path",
        data={
            "schedule_id": schedule.get("schedule_id"),
            "previous": previous,
            "current": current,
        },
    )
    if agent.integration_event_bus:
        agent.integration_event_bus.publish_event(envelope)
    if agent.event_bus:
        await agent.event_bus.publish("critical_path.changed", envelope.to_payload())


async def publish_schedule_simulated(
    agent: SchedulePlanningAgent,
    schedule: dict[str, Any],
    iterations: int,
    p50: float,
    p80: float,
    p90: float,
    p95: float,
    risk_score: float,
) -> None:
    if not agent.integration_event_bus and not agent.event_bus:
        return
    envelope = EventEnvelope(
        event_type="schedule.simulated",
        subject=f"schedule/{schedule.get('schedule_id')}/simulation",
        data={
            "schedule_id": schedule.get("schedule_id"),
            "iterations": iterations,
            "p50_duration": p50,
            "p80_duration": p80,
            "p90_duration": p90,
            "p95_duration": p95,
            "risk_score": risk_score,
        },
    )
    if agent.integration_event_bus:
        agent.integration_event_bus.publish_event(envelope)
    if agent.event_bus:
        await agent.event_bus.publish("schedule.simulated", envelope.to_payload())


# ---------------------------------------------------------------------------
# Change request submission
# ---------------------------------------------------------------------------


async def submit_change_request(
    agent: SchedulePlanningAgent,
    schedule: dict[str, Any],
    baseline: dict[str, Any],
    *,
    variance_days: float,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    if not agent.change_agent:
        return {"status": "skipped", "reason": "change_agent_not_configured"}
    return await agent.change_agent.process(
        {
            "action": "submit_change_request",
            "change": {
                "title": "Schedule variance exceeds threshold",
                "description": "Baseline variance exceeded threshold; review schedule baseline.",
                "requester": "schedule-planning-agent",
                "project_id": schedule.get("project_id"),
                "priority": "medium",
                "impact_summary": {
                    "variance_days": variance_days,
                    "baseline_id": baseline.get("baseline_id"),
                },
            },
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
        }
    )


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


async def persist_schedule(agent: SchedulePlanningAgent, schedule: dict[str, Any]) -> None:
    if not agent._sql_engine:
        return
    with Session(agent._sql_engine) as session:
        repo = SqlRepository(session)
        start_date = parse_datetime(schedule.get("start_date"))
        end_date = parse_datetime(schedule.get("end_date"))
        schedule_row = repo.upsert_schedule(
            schedule_key=schedule.get("schedule_id", "schedule"),
            name=schedule.get("schedule_id", "schedule"),
            status=schedule.get("status", "draft"),
            project_id=schedule.get("project_id", ""),
            start_date=start_date,
            end_date=end_date,
        )

        repo.clear_schedule_children(schedule_row.id)

        for task in schedule.get("tasks", []):
            repo.add_task(
                schedule_id=schedule_row.id,
                task_key=task.get("task_id", ""),
                name=task.get("name", ""),
                duration_days=float(task.get("duration", 0) or 0),
                status=task.get("status", "planned"),
            )
            await publish_task_updated(agent, schedule, task)
            for resource in task.get("resources", []):
                repo.add_resource_allocation(
                    schedule_id=schedule_row.id,
                    task_key=task.get("task_id", ""),
                    resource_id=resource.get("id", "default"),
                    skill=resource.get("skill", ""),
                    units=float(resource.get("units", 1.0)),
                    performance_score=float(resource.get("performance", 1.0)),
                )

        for dependency in schedule.get("dependencies", []):
            repo.add_dependency(
                schedule_id=schedule_row.id,
                predecessor_task_key=dependency.get("predecessor", ""),
                successor_task_key=dependency.get("successor", ""),
                dependency_type=dependency.get("type", "FS"),
                lag_days=float(dependency.get("lag", 0) or 0),
            )


async def persist_simulation(
    agent: SchedulePlanningAgent,
    schedule: dict[str, Any],
    iterations: int,
    p50: float,
    p80: float,
    p90: float,
    p95: float,
    risk_score: float,
    distribution: dict[str, Any],
) -> None:
    if not agent._sql_engine:
        return
    with Session(agent._sql_engine) as session:
        repo = SqlRepository(session)
        schedule_row = repo.get_schedule_by_key(schedule.get("schedule_id", "schedule"))
        if not schedule_row:
            return
        repo.add_simulation_record(
            schedule_id=schedule_row.id,
            iterations=iterations,
            p50=p50,
            p80=p80,
            p90=p90,
            p95=p95,
            risk_score=risk_score,
            distribution=distribution,
        )


async def persist_earned_value(
    agent: SchedulePlanningAgent, schedule: dict[str, Any], earned_value: dict[str, Any]
) -> None:
    if not agent._sql_engine:
        return
    with Session(agent._sql_engine) as session:
        repo = SqlRepository(session)
        schedule_row = repo.get_schedule_by_key(schedule.get("schedule_id", "schedule"))
        if not schedule_row:
            return
        repo.add_earned_value_record(
            schedule_id=schedule_row.id,
            planned_value=float(earned_value.get("planned_value", 0)),
            earned_value=float(earned_value.get("earned_value", 0)),
            actual_cost=float(earned_value.get("actual_cost", 0)),
            spi=float(earned_value.get("schedule_performance_index", 1.0)),
            cpi=float(earned_value.get("cost_performance_index", 1.0)),
        )


async def load_schedule_from_db(
    agent: SchedulePlanningAgent, schedule_id: str
) -> dict[str, Any] | None:
    if not agent._sql_engine:
        return None
    with Session(agent._sql_engine) as session:
        repo = SqlRepository(session)
        schedule_row = repo.get_schedule_by_key(schedule_id)
        if not schedule_row:
            return None
        tasks = [
            {
                "task_id": record.task_key,
                "name": record.name,
                "duration": record.duration_days,
                "status": record.status,
            }
            for record in repo.get_tasks(schedule_row.id)
        ]
        dependencies = [
            {
                "predecessor": dep.predecessor_task_key,
                "successor": dep.successor_task_key,
                "type": dep.dependency_type,
                "lag": dep.lag_days,
            }
            for dep in repo.get_dependencies(schedule_row.id)
        ]
        allocations: dict[str, list[dict[str, Any]]] = {}
        for allocation in repo.get_resource_allocations(schedule_row.id):
            allocations.setdefault(allocation.task_key, []).append(
                {
                    "id": allocation.resource_id,
                    "skill": allocation.skill,
                    "units": allocation.units,
                    "performance": allocation.performance_score,
                }
            )
        for task in tasks:
            task["resources"] = allocations.get(task["task_id"], [])

        return {
            "schedule_id": schedule_row.schedule_key,
            "project_id": schedule_row.project_id,
            "status": schedule_row.status,
            "tasks": tasks,
            "dependencies": dependencies,
            "start_date": (
                schedule_row.start_date.isoformat() if schedule_row.start_date else None
            ),
            "end_date": schedule_row.end_date.isoformat() if schedule_row.end_date else None,
            "loaded_from_db": True,
        }


# ---------------------------------------------------------------------------
# External sync helpers
# ---------------------------------------------------------------------------


async def sync_external_tools(agent: SchedulePlanningAgent, schedule: dict[str, Any]) -> None:
    if not agent.external_sync_client:
        return
    if agent.enable_external_sync:
        agent.external_sync_client.push_schedule(
            schedule.get("schedule_id", ""),
            {
                "tasks": schedule.get("tasks", []),
                "dependencies": schedule.get("dependencies", []),
                "milestones": schedule.get("milestones", []),
            },
        )
        await pull_external_updates(agent, schedule)
    if agent.enable_calendar_sync:
        agent.external_sync_client.sync_calendar(
            schedule.get("schedule_id", ""),
            schedule.get("milestones", []),
        )


async def pull_external_updates(agent: SchedulePlanningAgent, schedule: dict[str, Any]) -> None:
    if not agent.external_sync_client:
        return
    updates = agent.external_sync_client.pull_updates(schedule.get("schedule_id", ""))
    if not updates:
        return
    conflicts: list[dict[str, Any]] = []
    for update in updates:
        payload = update.payload
        conflicts.extend(apply_external_update(schedule, payload, update.timestamp.isoformat()))

    schedule.setdefault("external_sync", {})
    schedule["external_sync"]["last_synced_at"] = datetime.now(timezone.utc).isoformat()
    schedule["external_sync"]["conflicts"] = conflicts

    if agent.enable_persistence and agent._sql_engine:
        await persist_schedule(agent, schedule)

    if conflicts:
        await publish_schedule_updated(agent, schedule, "schedule.sync.conflict")
    else:
        await publish_schedule_updated(agent, schedule, "schedule.synced")


def apply_external_update(
    schedule: dict[str, Any], payload: dict[str, Any], timestamp: str
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    tasks = schedule.get("tasks", [])
    task_map = {task.get("task_id"): task for task in tasks}
    for incoming in payload.get("tasks", []):
        task_id = incoming.get("task_id")
        if not task_id:
            continue
        existing = task_map.get(task_id)
        if not existing:
            tasks.append(incoming)
            continue
        if existing.get("duration") != incoming.get("duration"):
            conflicts.append(
                {
                    "task_id": task_id,
                    "field": "duration",
                    "local": existing.get("duration"),
                    "external": incoming.get("duration"),
                    "resolved_at": timestamp,
                    "resolution": "external",
                }
            )
        existing.update(incoming)
    schedule["tasks"] = tasks
    for milestone in payload.get("milestones", []):
        schedule.setdefault("milestones", [])
        schedule["milestones"].append(milestone)
    return conflicts


# ---------------------------------------------------------------------------
# Risk adjustment helpers
# ---------------------------------------------------------------------------


def resolve_risk_data(
    risk_data: dict[str, Any] | None,
    dependency_results: dict[str, Any] | None,
    context: dict[str, Any] | None,
    fallback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(risk_data, dict) and risk_data:
        return risk_data
    if isinstance(context, dict) and isinstance(context.get("risk_data"), dict):
        return context["risk_data"]
    dep_results = dependency_results or {}
    for result in dep_results.values():
        if not isinstance(result, dict):
            continue
        data = result.get("data", result)
        if isinstance(data, dict) and isinstance(data.get("risk_data"), dict):
            return data["risk_data"]
    return fallback or {}


def apply_risk_adjustments_to_tasks(
    agent: SchedulePlanningAgent,
    tasks: list[dict[str, Any]],
    risk_data: dict[str, Any],
) -> list[dict[str, Any]]:
    task_risks = {
        str(item.get("task_id")): str(item.get("risk_level", "")).lower()
        for item in risk_data.get("task_risks", [])
        if isinstance(item, dict) and item.get("task_id")
    }
    project_level = str(risk_data.get("project_risk_level", "")).lower()
    adjusted: list[dict[str, Any]] = []
    for task in tasks:
        level = task_risks.get(str(task.get("task_id")), project_level or "default")
        adjustment = agent.risk_adjustments.get(level, agent.risk_adjustments["default"])
        base_duration = float(task.get("base_duration", task.get("duration", 0)) or 0)
        buffered_duration = base_duration * (1 + adjustment.get("schedule_buffer_pct", 0.0))
        next_task = dict(task)
        next_task["base_duration"] = base_duration
        next_task["duration"] = buffered_duration
        next_task["risk_level"] = level
        next_task["risk_buffer_pct"] = adjustment.get("schedule_buffer_pct", 0.0)
        adjusted.append(next_task)
    return adjusted


# ---------------------------------------------------------------------------
# Resource normalization helpers
# ---------------------------------------------------------------------------


def normalize_resource_availability(resources: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for resource_id, raw in resources.items():
        if not isinstance(resource_id, str):
            continue
        if isinstance(raw, dict):
            capacity = raw.get("capacity", 1.0)
            try:
                parsed_capacity = float(capacity)
            except (TypeError, ValueError):
                parsed_capacity = 1.0
            period_values = (
                raw.get("period_availability") or raw.get("availability_by_period") or {}
            )
            parsed_periods = parse_period_availability(period_values)
            normalized[resource_id] = {
                "capacity": max(0.0, parsed_capacity),
                "period_availability": parsed_periods,
            }
            if "warning" in raw:
                normalized[resource_id]["warning"] = raw.get("warning")
            if "warning_details" in raw:
                normalized[resource_id]["warning_details"] = raw.get("warning_details")
        else:
            try:
                parsed_capacity = float(raw)
            except (TypeError, ValueError):
                parsed_capacity = 1.0
            normalized[resource_id] = {
                "capacity": max(0.0, parsed_capacity),
                "period_availability": {},
            }
    return normalized


def parse_period_availability(raw_periods: Any) -> dict[int, float]:
    if not isinstance(raw_periods, dict):
        return {}
    parsed: dict[int, float] = {}
    for period_key, period_capacity in raw_periods.items():
        try:
            period_index = int(period_key)
            parsed[period_index] = max(0.0, float(period_capacity))
        except (TypeError, ValueError):
            continue
    return parsed


def merge_external_resource_availability(
    resource_id: str,
    current: dict[str, Any],
    external_response: Any,
) -> dict[str, Any]:
    merged = {
        "capacity": float(current.get("capacity", 1.0)),
        "period_availability": dict(current.get("period_availability", {})),
    }
    if not isinstance(external_response, dict):
        merged["warning"] = "resource_capacity_malformed_response"
        return merged

    external_resource_id = external_response.get("resource_id")
    if external_resource_id and external_resource_id != resource_id:
        merged["warning"] = "resource_capacity_id_mismatch"
        merged["warning_details"] = f"expected={resource_id}, actual={external_resource_id}"

    availability = external_response.get("availability_by_day", [])
    if not isinstance(availability, list):
        merged["warning"] = "resource_capacity_malformed_response"
        return merged

    period_availability: dict[int, float] = {}
    for index, entry in enumerate(availability):
        if not isinstance(entry, dict):
            continue
        available_hours = entry.get("available_hours")
        if available_hours is None:
            continue
        try:
            period_availability[index] = max(0.0, float(available_hours))
        except (TypeError, ValueError):
            continue

    average_availability = external_response.get("average_availability")
    if period_availability:
        merged["period_availability"] = period_availability
        merged["capacity"] = max(
            0.0,
            (
                float(average_availability)
                if average_availability is not None
                else max(period_availability.values())
            ),
        )
    elif average_availability is not None:
        try:
            merged["capacity"] = max(0.0, float(average_availability))
            merged["warning"] = "resource_capacity_partial_data"
        except (TypeError, ValueError):
            merged["warning"] = "resource_capacity_malformed_response"
    else:
        merged["warning"] = "resource_capacity_missing_data"

    return merged


# ---------------------------------------------------------------------------
# Schedule state helpers
# ---------------------------------------------------------------------------


async def get_schedule_state(
    agent: SchedulePlanningAgent, tenant_id: str, schedule_id: str
) -> dict[str, Any] | None:
    schedule = None
    if agent.cache_client:
        cached = agent.cache_client.get(schedule_cache_key(tenant_id, schedule_id))
        if cached:
            agent.schedules[schedule_id] = cached
            return cached

    schedule = agent.schedules.get(schedule_id)
    if not schedule:
        schedule = agent.schedule_store.get(tenant_id, schedule_id)
        if schedule:
            agent.schedules[schedule_id] = schedule
            if agent.cache_client:
                agent.cache_client.set(
                    schedule_cache_key(tenant_id, schedule_id),
                    schedule,
                    ttl_seconds=agent.cache_ttl_seconds,
                )
    if not schedule and agent.enable_persistence and agent._sql_engine:
        schedule = await load_schedule_from_db(agent, schedule_id)
        if schedule:
            agent.schedules[schedule_id] = schedule
            if agent.cache_client:
                agent.cache_client.set(
                    schedule_cache_key(tenant_id, schedule_id),
                    schedule,
                    ttl_seconds=agent.cache_ttl_seconds,
                )
    return schedule


# ---------------------------------------------------------------------------
# Financial helpers
# ---------------------------------------------------------------------------


async def fetch_financial_actuals(
    agent: SchedulePlanningAgent, project_id: str, *, tenant_id: str
) -> dict[str, Any]:
    if agent.financial_agent:
        response = await agent.financial_agent.process(
            {
                "action": "calculate_evm",
                "project_id": project_id,
                "tenant_id": tenant_id,
                "context": {"tenant_id": tenant_id},
            }
        )
        return {
            "budget_at_completion": response.get("budget_at_completion", 0),
            "actual_cost": response.get("actual_cost", 0),
        }
    return {"budget_at_completion": 0.0, "actual_cost": 0.0}


async def fetch_schedule_progress(
    schedule: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, float]:
    tasks = schedule.get("tasks", [])
    if not tasks:
        return {"percent_complete": 0.0, "planned_percent": 0.0}
    complete = sum(1 for task in tasks if task.get("status") in {"done", "completed"})
    percent_complete = complete / len(tasks)
    planned_duration = baseline.get("project_duration_days", 0) or 1
    actual_duration = schedule.get("project_duration_days", 0) or 1
    planned_percent = min(1.0, actual_duration / planned_duration)
    return {
        "percent_complete": percent_complete,
        "planned_percent": planned_percent,
    }
