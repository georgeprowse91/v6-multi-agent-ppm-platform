"""Action handlers for infrastructure operations.

Covers Power BI, ETL orchestration/monitoring, ML model training,
analytics stack provisioning, source ingestion, and realtime event ingestion.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from analytics_utils import (
    fetch_source_payload,
    maybe_await,
    record_data_lineage,
    redact_payload,
    store_event_record,
)

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


async def handle_get_powerbi_report(
    agent: AnalyticsInsightsAgent, tenant_id: str, report_type: str | None, user_context: dict[str, Any]
) -> dict[str, Any]:
    """Return Power BI Embedded configuration."""
    if not report_type:
        raise ValueError("report_type is required")
    embed_config = await agent.power_bi_manager.get_embed_config(report_type, user_context)
    record_id = f"powerbi-{report_type}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    agent.analytics_output_store.upsert(tenant_id, record_id, embed_config.copy())
    return embed_config


async def handle_orchestrate_etl(
    agent: AnalyticsInsightsAgent, pipelines: list[str], parameters: dict[str, Any]
) -> dict[str, Any]:
    """Schedule Data Factory pipelines for source systems."""
    run_ids: dict[str, str] = {}
    for pipeline in pipelines:
        run_id = await agent.data_factory_manager.schedule_pipeline(pipeline, parameters)
        run_ids[pipeline] = run_id
    return {"pipelines": run_ids, "scheduled_at": datetime.now(timezone.utc).isoformat()}


async def handle_monitor_etl(
    agent: AnalyticsInsightsAgent, run_id: str
) -> dict[str, Any]:
    """Monitor Data Factory pipeline status."""
    return await agent.data_factory_manager.get_pipeline_status(run_id)


async def handle_train_kpi_model(
    agent: AnalyticsInsightsAgent, model_name: str | None, training_payload: dict[str, Any]
) -> dict[str, Any]:
    """Train KPI predictive model using Azure ML."""
    if not model_name:
        raise ValueError("model_name is required")
    result = await agent.ml_manager.train_model(model_name, training_payload)
    return {
        "model_name": model_name,
        "training_job": result,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }


async def handle_provision_analytics_stack(agent: AnalyticsInsightsAgent) -> dict[str, Any]:
    """Provision Synapse, Data Lake, and Data Factory pipelines."""
    synapse_details = await maybe_await(agent.synapse_manager.ensure_pools)
    data_lake_details = await maybe_await(agent.data_lake_manager.ensure_file_system)
    pipeline_details = await maybe_await(
        agent.data_factory_manager.ensure_pipelines, agent.data_factory_pipelines
    )
    return {
        "synapse": synapse_details,
        "data_lake": data_lake_details,
        "data_factory": pipeline_details,
        "provisioned_at": datetime.now(timezone.utc).isoformat(),
    }


async def handle_ingest_sources(
    agent: AnalyticsInsightsAgent,
    tenant_id: str,
    sources: list[str] | None,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Run ingestion pipelines for Planview, Jira, Workday, and SAP."""
    selected_sources = sources or list(agent.ingestion_sources)
    run_map: dict[str, str] = {}
    lake_paths: dict[str, dict[str, str]] = {}
    ingestion_payloads: dict[str, list[dict[str, Any]]] = {}
    for source in selected_sources:
        pipeline_name = f"{source}_ingest"
        run_id = await agent.data_factory_manager.schedule_pipeline(
            pipeline_name,
            {
                "source": source,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                **parameters,
            },
        )
        run_map[source] = run_id
        payload = await fetch_source_payload(source)
        ingestion_payloads[source] = payload
        lake_paths[source] = agent.data_lake_manager.store_dataset(
            source=source, domain="ingestion", payload=payload
        )

    lineage_id = await record_data_lineage(
        agent,
        tenant_id,
        selected_sources,
        [{"source": source, "run_id": run_map[source]} for source in selected_sources],
    )
    return {
        "sources": selected_sources,
        "pipelines": run_map,
        "data_lake_paths": lake_paths,
        "lineage_id": lineage_id,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


async def handle_ingest_realtime_event(
    agent: AnalyticsInsightsAgent, event: dict[str, Any] | None, event_type: str | None
) -> dict[str, Any]:
    """Publish event to Event Hub and Stream Analytics."""
    if not event:
        raise ValueError("event payload is required")
    payload_record = {"event_type": event_type or "realtime.event", "payload": event}
    await _handle_realtime_event(agent, payload_record)
    return {
        "event_type": payload_record["event_type"],
        "streamed_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _handle_realtime_event(agent: AnalyticsInsightsAgent, event: dict[str, Any]) -> None:
    """Stream real-time events through Event Hub and Stream Analytics."""
    from actions.compute_kpis import update_kpis_from_definitions

    payload = event.get("payload", event)
    event_type = event.get("event_type") or event.get("type") or "realtime.event"
    tenant_id = event.get("tenant_id") or payload.get("tenant_id") or "default"
    redacted = redact_payload(payload)
    await store_event_record(agent, tenant_id, event_type, redacted, event)
    await update_kpis_from_definitions(agent, tenant_id, event_type=event_type)
    await _stream_realtime_event(agent, event_type, redacted)


async def _stream_realtime_event(
    agent: AnalyticsInsightsAgent, event_type: str, payload: dict[str, Any]
) -> None:
    await agent.event_hub_manager.publish_event(event_type, payload)
    await agent.stream_analytics_manager.stream_events([payload])
