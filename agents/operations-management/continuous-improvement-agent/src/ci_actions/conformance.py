"""Conformance checking, bottleneck and deviation detection action handlers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mining_models import MiningAgentProtocol
from mining_utils import (
    build_traces,
    calculate_compliance_rate,
    get_process_events,
    pairwise,
    safe_parse_timestamp,
)

from ci_actions.discovery import discover_process


async def check_conformance(
    agent: MiningAgentProtocol,
    tenant_id: str,
    process_id: str,
    expected_model: dict[str, Any],
) -> dict[str, Any]:
    """Compare actual traces against expected process model."""
    agent.logger.info("Checking conformance for process: %s", process_id)

    events = await get_process_events(process_id, agent.event_logs, agent.event_log_store)
    if not events:
        raise ValueError(f"No events found for process: {process_id}")

    traces = await build_traces(events)
    expected_activities = set(expected_model.get("activities", []))
    expected_transitions = {
        (edge.get("from"), edge.get("to")) for edge in expected_model.get("transitions", [])
    }

    deviations: list[dict[str, Any]] = []
    compliant_traces = 0

    for case_id, activities in traces.items():
        trace_deviations: list[dict[str, Any]] = []
        if expected_activities and not set(activities).issubset(expected_activities):
            extra = set(activities) - expected_activities
            trace_deviations.append(
                {"case_id": case_id, "category": "extra_activities", "activities": list(extra)}
            )
        for left, right in pairwise(activities):
            if expected_transitions and (left, right) not in expected_transitions:
                trace_deviations.append(
                    {
                        "case_id": case_id,
                        "category": "unexpected_transition",
                        "from": left,
                        "to": right,
                    }
                )
        if trace_deviations:
            deviations.extend(trace_deviations)
        else:
            compliant_traces += 1

    compliance_rate = (compliant_traces / len(traces)) * 100 if traces else 0.0
    report = {
        "process_id": process_id,
        "expected_model": expected_model,
        "total_traces": len(traces),
        "compliant_traces": compliant_traces,
        "compliance_rate": compliance_rate,
        "deviations": deviations,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.conformance_store.upsert(tenant_id, process_id, report)
    await _emit_deviation_alert(agent, process_id, report)
    return report


async def detect_bottlenecks(
    agent: MiningAgentProtocol, tenant_id: str, process_id: str
) -> dict[str, Any]:
    """
    Detect bottlenecks in process execution.

    Returns bottleneck analysis.
    """
    agent.logger.info("Detecting bottlenecks for process: %s", process_id)

    process_model = agent.process_models.get(process_id) or agent.process_model_store.get(
        tenant_id, process_id
    )
    if not process_model:
        await discover_process(agent, tenant_id, process_id)
        process_model = agent.process_models.get(process_id) or agent.process_model_store.get(
            tenant_id, process_id
        )

    waiting_times = await _analyze_waiting_times(agent, process_id)
    throughput = await _analyze_throughput(agent, process_id)

    bottlenecks: list[dict[str, Any]] = []
    for activity, metrics in waiting_times.items():
        avg_wait_time = float(metrics.get("avg_waiting_time", 0))
        if avg_wait_time > agent.bottleneck_threshold * 100:
            bottlenecks.append(
                {
                    "activity": activity,
                    "avg_waiting_time": avg_wait_time,
                    "frequency": metrics.get("frequency"),
                    "severity": "high" if avg_wait_time > 50 else "medium",
                }
            )

    recommendations = await _generate_bottleneck_recommendations(bottlenecks)

    return {
        "process_id": process_id,
        "bottlenecks_detected": len(bottlenecks),
        "bottlenecks": bottlenecks,
        "recommendations": recommendations,
        "overall_throughput": throughput,
    }


async def detect_deviations(
    agent: MiningAgentProtocol, tenant_id: str, process_id: str
) -> dict[str, Any]:
    """
    Detect deviations from designed process.

    Returns deviation analysis.
    """
    agent.logger.info("Detecting deviations for process: %s", process_id)

    designed_model = await _get_designed_process_model(agent, tenant_id, process_id)

    actual_model = agent.process_models.get(process_id) or agent.process_model_store.get(
        tenant_id, process_id
    )
    if not actual_model:
        await discover_process(agent, tenant_id, process_id)
        actual_model = agent.process_models.get(process_id) or agent.process_model_store.get(
            tenant_id, process_id
        )

    assert actual_model is not None, "Failed to discover process model"

    deviations = await _compare_process_models(designed_model, actual_model.get("model"))

    events = await get_process_events(process_id, agent.event_logs, agent.event_log_store)
    total_cases = len({str(event.get("case_id")) for event in events if event.get("case_id")})
    designed_activities_count = len(designed_model.get("activities", []))

    categorized_deviations: dict[str, list[dict[str, Any]]] = {
        "skipped_activities": [],
        "extra_activities": [],
        "wrong_sequence": [],
        "excessive_loops": [],
    }

    for deviation in deviations:
        category = deviation.get("category")
        if category in categorized_deviations:
            categorized_deviations[category].append(deviation)

    report = {
        "process_id": process_id,
        "total_deviations": len(deviations),
        "deviations": categorized_deviations,
        "compliance_rate": await calculate_compliance_rate(
            deviations,
            total_expected_activities=designed_activities_count,
            total_cases=total_cases,
        ),
    }
    await _emit_deviation_alert(agent, process_id, report)
    return report


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _analyze_waiting_times(
    agent: MiningAgentProtocol, process_id: str
) -> dict[str, dict[str, Any]]:
    """Analyze waiting times per activity."""
    events = await get_process_events(process_id, agent.event_logs, agent.event_log_store)
    if not events:
        return {}
    traces = await build_traces(events)
    activity_waits: dict[str, list[float]] = {}
    activity_counts: dict[str, int] = {}

    for case_id, activity_sequence in traces.items():
        case_events = [e for e in events if e.get("case_id") == case_id and e.get("timestamp")]
        case_events = sorted(
            case_events,
            key=lambda e: safe_parse_timestamp(e.get("timestamp")) or datetime.min,
        )
        for idx in range(1, len(case_events)):
            prev = case_events[idx - 1]
            current = case_events[idx]
            prev_ts = safe_parse_timestamp(prev.get("timestamp"))
            curr_ts = safe_parse_timestamp(current.get("timestamp"))
            if not prev_ts or not curr_ts:
                continue
            wait_time = (curr_ts - prev_ts).total_seconds() / 3600
            activity = activity_sequence[idx]
            activity_waits.setdefault(activity, []).append(wait_time)
            activity_counts[activity] = activity_counts.get(activity, 0) + 1

    results: dict[str, dict[str, Any]] = {}
    for activity, waits in activity_waits.items():
        if waits:
            results[activity] = {
                "avg_waiting_time": round(sum(waits) / len(waits), 2),
                "frequency": activity_counts.get(activity, 0),
            }
    return results


async def _analyze_throughput(agent: MiningAgentProtocol, process_id: str) -> float:
    """Analyze overall process throughput."""
    events = await get_process_events(process_id, agent.event_logs, agent.event_log_store)
    if not events:
        return 0.0
    traces = await build_traces(events)
    timestamps = [safe_parse_timestamp(e.get("timestamp")) for e in events if e.get("timestamp")]
    timestamps = [ts for ts in timestamps if ts]
    if len(timestamps) < 2:
        return float(len(traces))
    duration_days = (max(timestamps) - min(timestamps)).total_seconds() / 86400
    if duration_days <= 0:
        return float(len(traces))
    return round(len(traces) / duration_days, 2)


async def _generate_bottleneck_recommendations(
    bottlenecks: list[dict[str, Any]],
) -> list[str]:
    """Generate recommendations for bottlenecks."""
    recommendations: list[str] = []
    for bottleneck in bottlenecks:
        recommendations.append(
            f"Optimize {bottleneck.get('activity')} to reduce waiting time by automation or resource allocation"
        )
    return recommendations


async def _get_designed_process_model(
    agent: MiningAgentProtocol, tenant_id: str, process_id: str
) -> dict[str, Any]:
    """Get designed process model."""
    if agent.approval_workflow_agent:
        response = await agent.approval_workflow_agent.process(
            {"action": "get_process_model", "process_id": process_id}
        )
        if isinstance(response, dict) and response.get("model"):
            return response["model"]
    stored = agent.process_model_store.get(tenant_id, process_id)
    if stored:
        return stored.get("model", {})
    return {"activities": [], "transitions": []}


async def _compare_process_models(
    designed: dict[str, Any], actual: dict[str, Any]
) -> list[dict[str, Any]]:
    """Compare designed vs actual process models."""
    deviations: list[dict[str, Any]] = []

    designed_activities = set(designed.get("activities", []))
    actual_activities = set(actual.get("activities", []))

    skipped = designed_activities - actual_activities
    for activity in skipped:
        deviations.append(
            {"category": "skipped_activities", "activity": activity, "severity": "medium"}
        )

    extra = actual_activities - designed_activities
    for activity in extra:
        deviations.append({"category": "extra_activities", "activity": activity, "severity": "low"})

    return deviations


async def _emit_deviation_alert(
    agent: MiningAgentProtocol, process_id: str, report: dict[str, Any]
) -> None:
    total_deviations = report.get("total_deviations") or len(report.get("deviations", []))
    if total_deviations < agent.max_deviation_alerts:
        return
    event_payload = {
        "event_type": "process.deviation.alert",
        "data": {
            "process_id": process_id,
            "total_deviations": total_deviations,
            "report": report,
        },
    }
    if agent.event_bus:
        await agent.event_bus.publish("process.deviation.alert", event_payload)
