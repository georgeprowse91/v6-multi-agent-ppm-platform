"""Action handler for batch KPI computation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from actions.track_kpi import handle_track_kpi

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


async def handle_compute_kpis_batch(
    agent: AnalyticsInsightsAgent,
    tenant_id: str,
    event_type: str | None,
    kpis: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Compute KPI values in batch from aggregated events."""
    kpi_definitions = kpis or list(agent.kpi_definitions or [])
    results = await update_kpis_from_definitions(
        agent, tenant_id, event_type=event_type, kpi_definitions=kpi_definitions
    )
    return {
        "tenant_id": tenant_id,
        "kpis": results,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


async def update_kpis_from_definitions(
    agent: AnalyticsInsightsAgent,
    tenant_id: str,
    *,
    event_type: str | None = None,
    kpi_definitions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate KPI definitions and update values."""
    definitions = kpi_definitions or list(agent.kpi_definitions or [])
    results: list[dict[str, Any]] = []
    for kpi_definition in definitions:
        event_types = kpi_definition.get("event_types")
        if event_type and event_types and event_type not in event_types:
            continue
        kpi_payload = {**kpi_definition, "tenant_id": tenant_id}
        results.append(await handle_track_kpi(agent, tenant_id, kpi_payload))
    if results and agent.event_bus:
        await agent.event_bus.publish(
            "analytics.kpi.updated",
            {"tenant_id": tenant_id, "event_type": event_type, "kpis": results},
        )
    return results
