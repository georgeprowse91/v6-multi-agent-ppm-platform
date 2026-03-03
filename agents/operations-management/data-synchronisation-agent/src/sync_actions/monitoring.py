"""
Action handlers for sync monitoring, metrics, quality reporting, and dashboard.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sync_utils import compute_quality_dimensions, quality_record_key

if TYPE_CHECKING:
    from data_sync_agent import DataSyncAgent


async def handle_get_sync_status(
    agent: DataSyncAgent, filters: dict[str, Any]
) -> dict[str, Any]:
    """
    Get synchronization status.

    Returns sync statistics.
    """
    agent.logger.info("Retrieving sync status")

    # Calculate sync statistics
    total_events = len(agent.sync_events)
    successful_syncs = sum(
        1 for event in agent.sync_events.values() if event.get("status") == "success"
    )
    failed_syncs = total_events - successful_syncs

    # Get recent events
    recent_events = sorted(
        agent.sync_events.values(), key=lambda x: x.get("timestamp", ""), reverse=True
    )[:10]

    # Get conflict and duplicate counts
    pending_conflicts = sum(
        1 for conflict in agent.conflicts.values() if conflict.get("status") == "pending"
    )
    avg_latency = (
        sum(record["latency_seconds"] for record in agent.latency_records)
        / len(agent.latency_records)
        if agent.latency_records
        else 0.0
    )

    return {
        "total_sync_events": total_events,
        "successful_syncs": successful_syncs,
        "failed_syncs": failed_syncs,
        "success_rate": (successful_syncs / total_events * 100) if total_events > 0 else 0,
        "failure_rate": (failed_syncs / total_events * 100) if total_events > 0 else 0,
        "pending_conflicts": pending_conflicts,
        "recent_events": recent_events,
        "avg_latency_seconds": avg_latency,
    }


async def handle_get_metrics(
    agent: DataSyncAgent, tenant_id: str
) -> dict[str, Any]:
    """Expose latency metrics and event bus statistics."""
    records = [record for record in agent.latency_records if record["tenant_id"] == tenant_id]
    avg_latency = (
        sum(record["latency_seconds"] for record in records) / len(records) if records else 0.0
    )
    return {
        "tenant_id": tenant_id,
        "latency_records": records[-25:],
        "average_latency_seconds": avg_latency,
        "event_bus_metrics": agent.event_bus.get_metrics() if agent.event_bus else {},
    }


async def handle_get_quality_report(
    agent: DataSyncAgent, tenant_id: str, entity_type: str | None
) -> dict[str, Any]:
    records = [
        record
        for record in agent.quality_records
        if record["tenant_id"] == tenant_id
        and (entity_type is None or record["entity_type"] == entity_type)
    ]
    total = len(records)
    valid_count = sum(1 for record in records if record.get("valid"))
    error_rate = (total - valid_count) / total if total else 0.0
    avg_completeness = (
        sum(record.get("completeness_score", 0.0) for record in records) / total
        if total
        else 0.0
    )
    avg_consistency = (
        sum(record.get("consistency_score", 0.0) for record in records) / total
        if total
        else 0.0
    )
    avg_timeliness = (
        sum(record.get("timeliness_score", 0.0) for record in records) / total if total else 0.0
    )
    quality_score = (avg_completeness + avg_consistency + avg_timeliness) / 3 if total else 0.0
    return {
        "tenant_id": tenant_id,
        "entity_type": entity_type,
        "total_records": total,
        "valid_records": valid_count,
        "error_rate": error_rate,
        "avg_completeness_score": avg_completeness,
        "avg_consistency_score": avg_consistency,
        "avg_timeliness_score": avg_timeliness,
        "quality_score": quality_score,
        "records": records[-25:],
    }


async def handle_get_dashboard(
    agent: DataSyncAgent, tenant_id: str
) -> dict[str, Any]:
    sync_status = await handle_get_sync_status(agent, {})
    quality_report = await handle_get_quality_report(agent, tenant_id, None)
    state_records = agent.sync_state_store.list(tenant_id)
    lag_seconds = []
    for payload in state_records:
        last_synced = payload.get("last_synced_at")
        if last_synced:
            try:
                last_synced_dt = datetime.fromisoformat(last_synced)
                lag_seconds.append(
                    (datetime.now(timezone.utc) - last_synced_dt).total_seconds()
                )
            except ValueError:
                continue
    average_lag = sum(lag_seconds) / len(lag_seconds) if lag_seconds else 0.0
    return {
        "sync_status": sync_status,
        "quality_report": quality_report,
        "average_sync_lag_seconds": average_lag,
        "sync_state": state_records,
        "sync_logs": agent.sync_logs[-25:],
    }


async def record_quality_metrics(
    agent: DataSyncAgent,
    tenant_id: str,
    entity_type: str,
    source_system: str,
    validation_result: dict[str, Any],
) -> None:
    completeness_score, consistency_score, timeliness_score, age_seconds = (
        compute_quality_dimensions(
            entity_type,
            validation_result,
            agent.schema_registry,
            agent.validation_rules,
            agent.sync_latency_sla_seconds,
        )
    )
    quality_score = (completeness_score + consistency_score + timeliness_score) / 3
    record = {
        "tenant_id": tenant_id,
        "entity_type": entity_type,
        "source_system": source_system,
        "valid": validation_result.get("valid", False),
        "error_count": len(validation_result.get("errors", [])),
        "warning_count": len(validation_result.get("warnings", [])),
        "validated_at": validation_result.get("validated_at"),
        "completeness_score": completeness_score,
        "consistency_score": consistency_score,
        "timeliness_score": timeliness_score,
        "quality_score": quality_score,
        "age_seconds": age_seconds,
    }
    agent.quality_records.append(record)
    await agent._store_record("data_quality_metrics", quality_record_key(record), record)
    await agent._ingest_quality_metric(record)
    await store_quality_report(agent, tenant_id, entity_type)
    await evaluate_quality_thresholds(agent, tenant_id, entity_type)


async def store_quality_report(
    agent: DataSyncAgent, tenant_id: str, entity_type: str
) -> None:
    report = await handle_get_quality_report(agent, tenant_id, entity_type)
    report_id = f"{tenant_id}-{entity_type}-{datetime.now(timezone.utc).isoformat().replace(':', '-')}"
    await agent._store_record("data_quality_reports", report_id, report)


async def evaluate_quality_thresholds(
    agent: DataSyncAgent, tenant_id: str, entity_type: str
) -> None:
    threshold_config = agent.quality_thresholds.get(
        entity_type, agent.quality_thresholds.get("default", 0.9)
    )
    report = await handle_get_quality_report(agent, tenant_id, entity_type)
    if report["total_records"] == 0:
        return
    breaches = []
    if isinstance(threshold_config, dict):
        overall_threshold = threshold_config.get("overall")
        if overall_threshold is not None and report["quality_score"] < overall_threshold:
            breaches.append("overall")
        for metric in ("completeness", "consistency", "timeliness"):
            metric_threshold = threshold_config.get(metric)
            metric_key = f"avg_{metric}_score"
            if metric_threshold is not None and report.get(metric_key, 1.0) < metric_threshold:
                breaches.append(metric)
    else:
        overall_threshold = float(threshold_config)
        if report["quality_score"] < overall_threshold:
            breaches.append("overall")
    if breaches:
        await agent._publish_event(
            "data_quality.alert",
            {
                "tenant_id": tenant_id,
                "entity_type": entity_type,
                "quality_score": report["quality_score"],
                "thresholds": threshold_config,
                "breaches": breaches,
                "completeness_score": report.get("avg_completeness_score"),
                "consistency_score": report.get("avg_consistency_score"),
                "timeliness_score": report.get("avg_timeliness_score"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
