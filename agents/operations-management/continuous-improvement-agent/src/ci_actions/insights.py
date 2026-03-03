"""Insights, reporting and KPI action handlers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from mining_models import MiningAgentProtocol
from mining_utils import (
    build_traces,
    calculate_average_waiting_time,
    extract_dimension,
    get_process_events,
    load_all_event_logs,
    safe_parse_timestamp,
)

from ci_actions.conformance import (
    check_conformance,
    detect_bottlenecks,
    detect_deviations,
)
from ci_actions.conformance import _get_designed_process_model
from ci_actions.discovery import discover_process


async def get_process_insights(
    agent: MiningAgentProtocol, tenant_id: str, process_id: str
) -> dict[str, Any]:
    """
    Get comprehensive process insights.

    Returns process analysis.
    """
    agent.logger.info("Generating insights for process: %s", process_id)

    process_model = agent.process_models.get(process_id) or agent.process_model_store.get(
        tenant_id, process_id
    )
    if not process_model:
        await discover_process(agent, tenant_id, process_id)
        process_model = agent.process_models.get(process_id) or agent.process_model_store.get(
            tenant_id, process_id
        )

    metrics = process_model.get("metrics", {})  # type: ignore

    bottlenecks_result = await detect_bottlenecks(agent, tenant_id, process_id)
    deviations_result = await detect_deviations(agent, tenant_id, process_id)

    recommendations = await _generate_process_recommendations(
        metrics, bottlenecks_result, deviations_result
    )
    await _store_recommendations(
        agent,
        tenant_id,
        process_id,
        recommendations,
        context={
            "metrics": metrics,
            "bottlenecks": bottlenecks_result.get("bottlenecks", []),
            "deviations": deviations_result.get("deviations", {}),
        },
    )
    return {
        "process_id": process_id,
        "metrics": metrics,
        "bottlenecks": bottlenecks_result.get("bottlenecks", []),
        "deviations": deviations_result.get("total_deviations", 0),
        "compliance_rate": deviations_result.get("compliance_rate", 100),
        "recommendations": recommendations,
    }


async def get_process_model(
    agent: MiningAgentProtocol, tenant_id: str, process_id: str
) -> dict[str, Any]:
    """Return stored process model for API consumers."""
    model = agent.process_models.get(process_id) or agent.process_model_store.get(
        tenant_id, process_id
    )
    if not model:
        await discover_process(agent, tenant_id, process_id)
        model = agent.process_models.get(process_id) or agent.process_model_store.get(
            tenant_id, process_id
        )
    return model or {}


async def get_conformance_report(
    agent: MiningAgentProtocol, tenant_id: str, process_id: str
) -> dict[str, Any]:
    """Return conformance report for API consumers."""
    report = agent.conformance_store.get(tenant_id, process_id)
    if not report:
        expected_model = await _get_designed_process_model(agent, tenant_id, process_id)
        report = await check_conformance(agent, tenant_id, process_id, expected_model)
    return report


async def get_recommendations(
    agent: MiningAgentProtocol, tenant_id: str, process_id: str
) -> dict[str, Any]:
    """Return stored recommendations for API consumers."""
    stored = agent.recommendations_store.get(tenant_id, process_id)
    if stored:
        return stored
    insights = await get_process_insights(agent, tenant_id, process_id)
    return {
        "process_id": process_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "recommendations": insights.get("recommendations", []),
    }


async def get_kpi_report(
    agent: MiningAgentProtocol, filters: dict[str, Any]
) -> dict[str, Any]:
    """Compute KPI rollups across projects and programs."""
    all_events: list[dict[str, Any]] = []
    if not agent.event_logs:
        stored_logs = await load_all_event_logs(agent.event_log_store)
        for log in stored_logs:
            all_events.extend(log.get("events", []))
    else:
        for log in agent.event_logs.values():
            all_events.extend(log.get("events", []))

    if filters.get("process_id"):
        all_events = [
            event for event in all_events if event.get("process_id") == filters["process_id"]
        ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": filters,
        "process_kpis": await _calculate_grouped_kpis(all_events, "process_id"),
        "project_kpis": await _calculate_grouped_kpis(all_events, "project_id"),
        "program_kpis": await _calculate_grouped_kpis(all_events, "program_id"),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _calculate_basic_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate basic performance metrics without a process model."""
    traces = await build_traces(events)
    cycle_times: list[float] = []
    for case_id in traces:
        case_events = [e for e in events if e.get("case_id") == case_id]
        timestamps = [
            safe_parse_timestamp(e.get("timestamp"))
            for e in case_events
            if e.get("timestamp")
        ]
        timestamps = [ts for ts in timestamps if ts]
        if timestamps:
            cycle_times.append((max(timestamps) - min(timestamps)).total_seconds() / 3600)

    median_cycle_time = sorted(cycle_times)[len(cycle_times) // 2] if cycle_times else 0.0
    return {
        "median_cycle_time": round(median_cycle_time, 2),
        "throughput": len(traces),
        "avg_waiting_time": await calculate_average_waiting_time(events),
        "trace_count": len(traces),
    }


async def _calculate_grouped_kpis(
    events: list[dict[str, Any]], key: str
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        dimension = extract_dimension(event, key)
        if dimension is None:
            continue
        grouped.setdefault(dimension, []).append(event)

    results: list[dict[str, Any]] = []
    for dimension, group_events in grouped.items():
        metrics = await _calculate_basic_metrics(group_events)
        results.append(
            {
                "dimension": dimension,
                "event_count": len(group_events),
                "metrics": metrics,
            }
        )
    return sorted(results, key=lambda item: item["event_count"], reverse=True)


async def _generate_process_recommendations(
    metrics: dict[str, Any], bottlenecks: dict[str, Any], deviations: dict[str, Any]
) -> list[str]:
    """Generate comprehensive process recommendations."""
    recommendations: list[str] = []

    if bottlenecks.get("bottlenecks_detected", 0) > 0:
        recommendations.append("Address identified bottlenecks to improve throughput")

    if deviations.get("total_deviations", 0) > 5:
        recommendations.append("Improve process compliance through training and automation")

    if not recommendations:
        recommendations.append("Process is performing well - maintain current practices")

    return recommendations


async def _store_recommendations(
    agent: MiningAgentProtocol,
    tenant_id: str,
    process_id: str,
    recommendations: list[str],
    context: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "process_id": process_id,
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if context:
        payload["context"] = context
    agent.recommendations_store.upsert(tenant_id, process_id, payload)
    if agent.event_bus:
        await agent.event_bus.publish(
            "process.recommendations.generated",
            {"event_type": "process.recommendations.generated", "data": payload},
        )
    await _publish_lessons_learned(agent, tenant_id, payload)


async def _publish_lessons_learned(
    agent: MiningAgentProtocol, tenant_id: str, payload: dict[str, Any]
) -> None:
    knowledge_payload = {
        "source_agent": agent.agent_id,
        "title": f"Process improvement recommendations for {payload.get('process_id')}",
        "summary": "\n".join(payload.get("recommendations", [])),
        "content": json.dumps(payload, indent=2),
        "tags": ["process_mining", "continuous_improvement", "lessons_learned"],
        "metadata": {
            "process_id": payload.get("process_id"),
            "generated_at": payload.get("generated_at"),
        },
    }
    if agent.knowledge_agent:
        await agent.knowledge_agent.process(
            {
                "action": "ingest_agent_output",
                "tenant_id": tenant_id,
                "payload": knowledge_payload,
            }
        )
        return
    if agent.event_bus:
        await agent.event_bus.publish(
            agent.knowledge_event_topic,
            {"tenant_id": tenant_id, **knowledge_payload},
        )
