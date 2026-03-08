"""Improvement management action handlers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mining_models import MiningAgentProtocol
from mining_utils import generate_improvement_id


async def create_improvement(
    agent: MiningAgentProtocol, tenant_id: str, improvement_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Create improvement initiative.

    Returns improvement ID and details.
    """
    agent.logger.info("Creating improvement: %s", improvement_data.get("title"))

    improvement_id = await generate_improvement_id()

    expected_benefits = await _estimate_improvement_benefits(improvement_data)
    feasibility = await _assess_improvement_feasibility(improvement_data)
    priority_score = await _calculate_improvement_priority(
        expected_benefits, feasibility, improvement_data
    )

    improvement = {
        "improvement_id": improvement_id,
        "title": improvement_data.get("title"),
        "description": improvement_data.get("description"),
        "category": improvement_data.get("category"),
        "process_id": improvement_data.get("process_id"),
        "expected_benefits": expected_benefits,
        "feasibility": feasibility,
        "priority_score": priority_score,
        "owner": improvement_data.get("owner"),
        "status": "Idea",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    agent.improvement_backlog[improvement_id] = improvement
    agent.improvement_backlog_store.upsert(tenant_id, improvement_id, improvement.copy())
    agent.event_log_store.upsert(
        tenant_id,
        f"improvement-{improvement_id}",
        {
            "improvement_id": improvement_id,
            "process_id": improvement_data.get("process_id"),
            "created_at": improvement.get("created_at"),
        },
    )

    await _emit_improvement_recommendation(agent, tenant_id, improvement)

    await _publish_event(
        agent,
        "improvement.created",
        {
            "tenant_id": tenant_id,
            "improvement_id": improvement_id,
            "process_id": improvement.get("process_id"),
            "priority_score": priority_score,
            "status": improvement.get("status"),
            "created_at": improvement.get("created_at"),
        },
    )
    if agent.integration_clients.get("task_sync"):
        await agent.integration_clients["task_sync"].create_task(improvement)

    return {
        "improvement_id": improvement_id,
        "title": improvement["title"],
        "priority_score": priority_score,
        "expected_benefits": expected_benefits,
        "feasibility": feasibility,
        "next_steps": "Review and prioritize in improvement backlog",
    }


async def prioritize_improvements(agent: MiningAgentProtocol) -> dict[str, Any]:
    """
    Prioritize improvement backlog.

    Returns prioritized list.
    """
    agent.logger.info("Prioritizing improvement backlog")

    improvements = list(agent.improvement_backlog.values())

    prioritized = sorted(improvements, key=lambda x: x.get("priority_score", 0), reverse=True)

    by_status: dict[str, list[dict[str, Any]]] = {
        "Idea": [],
        "Planned": [],
        "In Progress": [],
        "Completed": [],
    }

    for improvement in prioritized:
        status = improvement.get("status")
        if status in by_status:
            by_status[status].append(improvement)

    return {
        "total_improvements": len(prioritized),
        "prioritized_list": [
            {
                "improvement_id": i.get("improvement_id"),
                "title": i.get("title"),
                "priority_score": i.get("priority_score"),
                "status": i.get("status"),
            }
            for i in prioritized
        ],
        "by_status": {k: len(v) for k, v in by_status.items()},
    }


async def track_benefits(
    agent: MiningAgentProtocol, improvement_id: str, tenant_id: str = ""
) -> dict[str, Any]:
    """
    Track benefit realization for improvement.

    Returns benefit metrics.
    """
    agent.logger.info("Tracking benefits for improvement: %s", improvement_id)

    improvement = agent.improvement_backlog.get(improvement_id)
    if not improvement:
        raise ValueError(f"Improvement not found: {improvement_id}")

    actual_benefits = await _measure_actual_benefits(improvement)
    expected_benefits = improvement.get("expected_benefits", {})
    realization = await _calculate_benefit_realization(expected_benefits, actual_benefits)

    agent.benefit_tracking[improvement_id] = {
        "improvement_id": improvement_id,
        "expected_benefits": expected_benefits,
        "actual_benefits": actual_benefits,
        "realization_percentage": realization,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }

    if agent.financial_agent:
        await agent.financial_agent.process(
            {
                "action": "update_forecast",
                "improvement_id": improvement_id,
                "benefits": actual_benefits,
            }
        )
    await _publish_event(
        agent,
        "benefits.realized",
        {
            "tenant_id": tenant_id,
            "improvement_id": improvement_id,
            "actual_benefits": actual_benefits,
            "realization_percentage": realization,
        },
    )

    return {
        "improvement_id": improvement_id,
        "expected_benefits": expected_benefits,
        "actual_benefits": actual_benefits,
        "realization_percentage": realization,
        "roi": await _calculate_improvement_roi(improvement, actual_benefits),
    }


async def complete_improvement(
    agent: MiningAgentProtocol,
    tenant_id: str,
    improvement_id: str,
    outcome: str,
    completed_by: str | None,
) -> dict[str, Any]:
    """Mark an improvement as completed and persist to history."""
    improvement = agent.improvement_backlog.get(
        improvement_id
    ) or agent.improvement_backlog_store.get(tenant_id, improvement_id)
    if not improvement:
        raise ValueError(f"Improvement not found: {improvement_id}")

    completed = {
        **improvement,
        "status": "Completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "completed_by": completed_by or improvement.get("owner") or agent.default_improvement_owner,
        "outcome": outcome,
    }
    agent.improvement_backlog[improvement_id] = completed
    agent.improvement_backlog_store.upsert(tenant_id, improvement_id, completed.copy())
    history_id = f"history-{improvement_id}-{int(datetime.now(timezone.utc).timestamp())}"
    agent.improvement_history_store.upsert(
        tenant_id,
        history_id,
        {
            "improvement_id": improvement_id,
            "date": completed["completed_at"],
            "owner": completed["completed_by"],
            "outcome": outcome,
        },
    )
    await _notify_stakeholders(
        agent,
        tenant_id,
        "improvement.completed",
        {
            "improvement_id": improvement_id,
            "owner": completed["completed_by"],
            "outcome": outcome,
        },
    )
    return completed


async def get_improvement_backlog(
    agent: MiningAgentProtocol, filters: dict[str, Any]
) -> dict[str, Any]:
    """
    Get improvement backlog with filters.

    Returns filtered backlog.
    """
    agent.logger.info("Retrieving improvement backlog")

    tenant_id = filters.get("tenant_id", "default")
    stored_improvements = agent.improvement_backlog_store.list(tenant_id)
    for record in stored_improvements:
        if isinstance(record, dict) and record.get("improvement_id"):
            agent.improvement_backlog.setdefault(record["improvement_id"], record)

    filtered: list[dict[str, Any]] = []
    for _improvement_id, improvement in agent.improvement_backlog.items():
        if await _matches_improvement_filters(improvement, filters):
            filtered.append(improvement)

    sorted_improvements = sorted(filtered, key=lambda x: x.get("priority_score", 0), reverse=True)

    return {
        "total_improvements": len(sorted_improvements),
        "improvements": sorted_improvements,
        "filters": filters,
    }


async def get_improvement_history(agent: MiningAgentProtocol, tenant_id: str) -> dict[str, Any]:
    """Return improvement history entries."""
    entries = agent.improvement_history_store.list(tenant_id)
    return {"tenant_id": tenant_id, "entries": entries, "count": len(entries)}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _estimate_improvement_benefits(
    improvement_data: dict[str, Any],
) -> dict[str, Any]:
    """Estimate expected benefits."""
    impact = improvement_data.get("expected_impact", "medium")
    multiplier = {"low": 0.5, "medium": 1.0, "high": 1.5}.get(str(impact), 1.0)
    return {
        "cycle_time_reduction": 10.0 * multiplier,
        "cost_savings": 20000 * multiplier,
        "quality_improvement": 8.0 * multiplier,
    }


async def _assess_improvement_feasibility(
    improvement_data: dict[str, Any],
) -> dict[str, Any]:
    """Assess improvement feasibility."""
    return {
        "technical_feasibility": 0.85,
        "resource_availability": 0.70,
        "estimated_effort": 40,
    }


async def _calculate_improvement_priority(
    benefits: dict[str, Any],
    feasibility: dict[str, Any],
    improvement_data: dict[str, Any],
) -> float:
    """Calculate improvement priority score."""
    benefit_score = benefits.get("cycle_time_reduction", 0) + (
        benefits.get("cost_savings", 0) / 1000
    )
    feasibility_score = feasibility.get("technical_feasibility", 0) * feasibility.get(
        "resource_availability", 0
    )
    return benefit_score * feasibility_score  # type: ignore


async def _measure_actual_benefits(improvement: dict[str, Any]) -> dict[str, Any]:
    """Measure actual benefits achieved."""
    expected = improvement.get("expected_benefits", {})
    return {
        "cycle_time_reduction": expected.get("cycle_time_reduction", 10.0) * 0.85,
        "cost_savings": expected.get("cost_savings", 20000) * 0.9,
        "quality_improvement": expected.get("quality_improvement", 8.0) * 0.9,
    }


async def _calculate_benefit_realization(expected: dict[str, Any], actual: dict[str, Any]) -> float:
    """Calculate benefit realization percentage."""
    if not expected:
        return 0.0
    realizations: list[float] = []
    for key in expected.keys():
        if key in actual and expected[key] > 0:
            realizations.append((actual[key] / expected[key]) * 100)
    return sum(realizations) / len(realizations) if realizations else 0.0


async def _calculate_improvement_roi(
    improvement: dict[str, Any], actual_benefits: dict[str, Any]
) -> float:
    """Calculate ROI for improvement."""
    cost_savings = actual_benefits.get("cost_savings", 0)
    effort_hours = improvement.get("feasibility", {}).get("estimated_effort", 40)
    cost = effort_hours * 100
    if cost == 0:
        return 0.0
    return ((cost_savings - cost) / cost) * 100  # type: ignore


async def _matches_improvement_filters(
    improvement: dict[str, Any], filters: dict[str, Any]
) -> bool:
    """Check if improvement matches filters."""
    if "status" in filters and improvement.get("status") != filters["status"]:
        return False
    if "category" in filters and improvement.get("category") != filters["category"]:
        return False
    return True


async def _emit_improvement_recommendation(
    agent: MiningAgentProtocol, tenant_id: str, improvement: dict[str, Any]
) -> None:
    """Emit improvement recommendation to the Approval Workflow agent."""
    event_payload = {
        "event_type": "workflow.improvement.recommendation",
        "data": {
            "tenant_id": tenant_id,
            "improvement_id": improvement.get("improvement_id"),
            "process_id": improvement.get("process_id"),
            "priority_score": improvement.get("priority_score"),
            "expected_benefits": improvement.get("expected_benefits"),
        },
    }
    if agent.approval_workflow_agent:
        await agent.approval_workflow_agent.process(
            {"action": "handle_event", "event": event_payload}
        )
        return
    if agent.event_bus:
        await agent.event_bus.publish("workflow.improvement.recommendation", event_payload)


async def _publish_event(agent: MiningAgentProtocol, topic: str, payload: dict[str, Any]) -> None:
    if agent.event_bus:
        await agent.event_bus.publish(topic, payload)


async def _notify_stakeholders(
    agent: MiningAgentProtocol, tenant_id: str, event_type: str, payload: dict[str, Any]
) -> None:
    message = {
        "tenant_id": tenant_id,
        "event_type": event_type,
        "payload": payload,
        "notified_at": datetime.now(timezone.utc).isoformat(),
    }
    if agent.integration_clients.get("notification_service"):
        await agent.integration_clients["notification_service"].send(message)
        return
    if agent.event_bus:
        await agent.event_bus.publish("notification.improvement", message)
