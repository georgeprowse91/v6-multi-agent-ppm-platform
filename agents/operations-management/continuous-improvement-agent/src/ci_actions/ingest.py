"""Event-log and analytics-report ingestion action handlers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from mining_models import MiningAgentProtocol
from mining_utils import (
    calculate_time_range,
    generate_improvement_id,
    generate_log_id,
    map_events_to_cases,
    resolve_improvement_owner,
    validate_events,
)


async def ingest_event_log(
    agent: MiningAgentProtocol, tenant_id: str, events: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Ingest event log data for process mining.

    Returns ingestion statistics.
    """
    agent.logger.info("Ingesting event log with %s events", len(events))

    valid_events = await validate_events(events)
    mapped_events = await map_events_to_cases(valid_events)

    log_id = await generate_log_id()
    log_record = {
        "log_id": log_id,
        "events": mapped_events,
        "event_count": len(mapped_events),
        "case_count": len(set(e.get("case_id") for e in mapped_events)),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.event_logs[log_id] = log_record
    agent.event_log_store.upsert(tenant_id, log_id, log_record)
    for event in mapped_events:
        case_id = str(event.get("case_id") or "unknown")
        agent.event_log_index.setdefault(case_id, []).append(event)

    await _publish_event(
        agent,
        "events.ingested",
        {
            "tenant_id": tenant_id,
            "log_id": log_id,
            "event_count": len(mapped_events),
            "case_count": len(set(e.get("case_id") for e in mapped_events)),
            "ingested_at": log_record["ingested_at"],
        },
    )

    return {
        "log_id": log_id,
        "events_ingested": len(mapped_events),
        "cases_identified": len(set(e.get("case_id") for e in mapped_events)),
        "time_range": await calculate_time_range(mapped_events),
    }


async def ingest_analytics_report(
    agent: MiningAgentProtocol, tenant_id: str, analytics_report: dict[str, Any]
) -> dict[str, Any]:
    """Ingest analytics insights and create prioritized improvement backlog items."""
    recommendations = analytics_report.get("recommendations", [])
    anomalies = analytics_report.get("anomalies", [])
    trends = analytics_report.get("trends", [])
    created_items: list[dict[str, Any]] = []

    for index, recommendation in enumerate(recommendations):
        feasibility = "high"
        impact = "medium"
        lowered = str(recommendation).lower()
        if "scope" in lowered or "budget" in lowered:
            impact = "high"
            feasibility = "medium"
        if "training" in lowered or "monitoring" in lowered:
            feasibility = "high"
        due_days = 14 if impact == "high" else 30
        improvement_id = await generate_improvement_id()
        priority_score = 90 - (index * 5)
        target_due_date = (datetime.now(timezone.utc) + timedelta(days=due_days)).replace(
            microsecond=0
        )
        item = {
            "improvement_id": improvement_id,
            "title": recommendation,
            "description": f"Derived from analytics report {analytics_report.get('report_id')}",
            "category": "analytics_feedback",
            "process_id": analytics_report.get("period", "portfolio"),
            "expected_benefits": {"impact": impact},
            "feasibility": {"level": feasibility},
            "priority_score": priority_score,
            "owner": resolve_improvement_owner(
                recommendation, index, agent.default_improvement_owner
            ),
            "target_date": target_due_date.date().isoformat(),
            "target_due_date": target_due_date.isoformat(),
            "status": "Planned",
            "source_report_id": analytics_report.get("report_id"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        agent.improvement_backlog[improvement_id] = item
        agent.improvement_backlog_store.upsert(tenant_id, improvement_id, item.copy())
        created_items.append(item)

    prioritized = sorted(created_items, key=lambda i: i.get("priority_score", 0), reverse=True)
    await _publish_improvement_backlog(agent, tenant_id, prioritized)
    await _notify_stakeholders(
        agent,
        tenant_id,
        "improvement.backlog.updated",
        {
            "source_report_id": analytics_report.get("report_id"),
            "item_count": len(prioritized),
            "anomalies": len(anomalies),
            "trends": len(trends),
        },
    )

    return {
        "source_report_id": analytics_report.get("report_id"),
        "created_items": len(prioritized),
        "prioritized_backlog": prioritized,
    }


# ---------------------------------------------------------------------------
# Internal helpers (shared with improvement module via re-export)
# ---------------------------------------------------------------------------


async def _publish_event(agent: MiningAgentProtocol, topic: str, payload: dict[str, Any]) -> None:
    if agent.event_bus:
        await agent.event_bus.publish(topic, payload)


async def _publish_improvement_backlog(
    agent: MiningAgentProtocol, tenant_id: str, prioritized_items: list[dict[str, Any]]
) -> None:
    payload = {
        "tenant_id": tenant_id,
        "category": "improvement_backlog",
        "items": prioritized_items,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if agent.knowledge_agent:
        await agent.knowledge_agent.process(
            {
                "action": "ingest_agent_output",
                "tenant_id": tenant_id,
                "payload": payload,
            }
        )
        return
    if agent.event_bus:
        await agent.event_bus.publish("knowledge.improvement_backlog.published", payload)


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
