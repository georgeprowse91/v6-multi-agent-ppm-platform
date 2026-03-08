"""Process discovery action handler."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mining_models import MiningAgentProtocol
from mining_utils import (
    build_traces,
    calculate_average_waiting_time,
    get_process_events,
    get_start_end_activities,
    pairwise,
    safe_parse_timestamp,
)


async def discover_process(
    agent: MiningAgentProtocol, tenant_id: str, process_id: str, algorithm: str = "heuristic_miner"
) -> dict[str, Any]:
    """
    Discover process model from event logs.

    Returns process model and visualization.
    """
    agent.logger.info("Discovering process %s using %s", process_id, algorithm)

    events = await get_process_events(process_id, agent.event_logs, agent.event_log_store)

    if not events:
        raise ValueError(f"No events found for process: {process_id}")

    process_model = await _apply_mining_algorithm(agent, events, algorithm)
    bpmn_model = await _build_bpmn_model(events, process_model)
    petri_net = await _build_petri_net(events, process_model)

    performance_metrics = await _calculate_process_metrics(events, process_model)

    visualization = await _generate_process_visualization(process_model, performance_metrics)

    model_record = {
        "process_id": process_id,
        "model": process_model,
        "bpmn": bpmn_model,
        "petri_net": petri_net,
        "algorithm": algorithm,
        "metrics": performance_metrics,
        "visualization": visualization,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.process_models[process_id] = model_record
    agent.process_model_store.upsert(tenant_id, process_id, model_record)

    await _publish_event(
        agent,
        "process.discovered",
        {
            "tenant_id": tenant_id,
            "process_id": process_id,
            "algorithm": algorithm,
            "metrics": performance_metrics,
            "discovered_at": model_record["discovered_at"],
        },
    )

    return {
        "process_id": process_id,
        "algorithm": algorithm,
        "activities": len(process_model.get("activities", [])),
        "transitions": len(process_model.get("transitions", [])),
        "bpmn": bpmn_model,
        "petri_net": petri_net,
        "metrics": performance_metrics,
        "visualization": visualization,
    }


# ---------------------------------------------------------------------------
# Mining algorithms
# ---------------------------------------------------------------------------


async def _apply_mining_algorithm(
    agent: MiningAgentProtocol, events: list[dict[str, Any]], algorithm: str
) -> dict[str, Any]:
    """Apply process mining algorithm."""
    traces = await build_traces(events)
    activities = sorted({activity for trace in traces.values() for activity in trace})
    transition_counts: dict[tuple[str, str], int] = {}

    for trace in traces.values():
        for left, right in pairwise(trace):
            transition_counts[(left, right)] = transition_counts.get((left, right), 0) + 1

    if algorithm == "alpha_miner":
        transitions = [
            {"from": left, "to": right, "frequency": count}
            for (left, right), count in transition_counts.items()
        ]
    elif algorithm == "inductive_miner":
        transitions = [
            {"from": left, "to": right, "frequency": count}
            for (left, right), count in transition_counts.items()
            if count >= agent.min_frequency_threshold
        ]
        activities = sorted(
            {
                activity
                for transition in transitions
                for activity in (transition["from"], transition["to"])
            }
        )
    else:
        transitions = [
            {"from": left, "to": right, "frequency": count}
            for (left, right), count in transition_counts.items()
        ]

    return {"activities": activities, "transitions": transitions, "algorithm": algorithm}


# ---------------------------------------------------------------------------
# Model representations
# ---------------------------------------------------------------------------


async def _build_bpmn_model(
    events: list[dict[str, Any]], process_model: dict[str, Any]
) -> dict[str, Any]:
    """Build a lightweight BPMN representation."""
    traces = await build_traces(events)
    start_activities, end_activities = get_start_end_activities(traces)
    tasks = [
        {"id": activity, "name": activity, "type": "task"}
        for activity in process_model.get("activities", [])
    ]
    flows = [
        {"id": f"{edge['from']}-{edge['to']}", "source": edge["from"], "target": edge["to"]}
        for edge in process_model.get("transitions", [])
    ]
    return {
        "type": "bpmn",
        "start_events": [
            {"id": f"start-{activity}", "name": "Start", "outgoing": activity}
            for activity in start_activities
        ],
        "end_events": [
            {"id": f"end-{activity}", "name": "End", "incoming": activity}
            for activity in end_activities
        ],
        "tasks": tasks,
        "sequence_flows": flows,
    }


async def _build_petri_net(
    events: list[dict[str, Any]], process_model: dict[str, Any]
) -> dict[str, Any]:
    """Build a simplified Petri net representation."""
    traces = await build_traces(events)
    start_activities, end_activities = get_start_end_activities(traces)
    transitions = [
        {"id": activity, "label": activity} for activity in process_model.get("activities", [])
    ]
    places: list[dict[str, str]] = [{"id": "p_start"}, {"id": "p_end"}]
    arcs: list[dict[str, str]] = []
    for activity in start_activities:
        arcs.append({"from": "p_start", "to": activity})
    for activity in end_activities:
        arcs.append({"from": activity, "to": "p_end"})

    for edge in process_model.get("transitions", []):
        place_id = f"p_{edge['from']}_to_{edge['to']}"
        places.append({"id": place_id})
        arcs.append({"from": edge["from"], "to": place_id})
        arcs.append({"from": place_id, "to": edge["to"]})

    return {"type": "petri_net", "places": places, "transitions": transitions, "arcs": arcs}


# ---------------------------------------------------------------------------
# Metrics & visualization
# ---------------------------------------------------------------------------


async def _calculate_process_metrics(
    events: list[dict[str, Any]], process_model: dict[str, Any]
) -> dict[str, Any]:
    """Calculate process performance metrics."""
    traces = await build_traces(events)
    cycle_times: list[float] = []
    for case_id in traces:
        case_events = [e for e in events if e.get("case_id") == case_id]
        timestamps = [
            safe_parse_timestamp(e.get("timestamp")) for e in case_events if e.get("timestamp")
        ]
        timestamps = [ts for ts in timestamps if ts]
        if timestamps:
            cycle_times.append((max(timestamps) - min(timestamps)).total_seconds() / 3600)

    median_cycle_time = sorted(cycle_times)[len(cycle_times) // 2] if cycle_times else 0.0
    return {
        "median_cycle_time": round(median_cycle_time, 2),
        "throughput": len(traces),
        "activity_count": len(process_model.get("activities", [])),
        "avg_waiting_time": await calculate_average_waiting_time(events),
    }


async def _generate_process_visualization(
    process_model: dict[str, Any], metrics: dict[str, Any]
) -> dict[str, Any]:
    """Generate process visualization data."""
    return {
        "type": "process_map",
        "nodes": process_model.get("activities", []),
        "edges": process_model.get("transitions", []),
        "metrics_overlay": metrics,
    }


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


async def _publish_event(agent: MiningAgentProtocol, topic: str, payload: dict[str, Any]) -> None:
    if agent.event_bus:
        await agent.event_bus.publish(topic, payload)
