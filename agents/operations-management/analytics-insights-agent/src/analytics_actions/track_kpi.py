"""Action handler for KPI tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from analytics_utils import (
    calculate_kpi_trend,
    calculate_kpi_value,
    check_kpi_thresholds,
    generate_kpi_id,
    get_kpi_history,
    store_kpi_history,
)

from agents.common.metrics_catalog import get_metric_value, normalize_metric_value

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


async def handle_track_kpi(
    agent: AnalyticsInsightsAgent, tenant_id: str, kpi_config: dict[str, Any]
) -> dict[str, Any]:
    """
    Track KPI metrics.

    Returns KPI values and trends.
    """
    agent.logger.info("Tracking KPI: %s", kpi_config.get("name"))

    # Generate KPI ID if new
    kpi_id = kpi_config.get("kpi_id") or await generate_kpi_id()

    metric_name = kpi_config.get("metric_name")
    if metric_name and kpi_config.get("project_id"):
        raw_value = await get_metric_value(
            metric_name,
            kpi_config.get("project_id"),
            tenant_id=tenant_id,
            agent_clients=agent.metric_agents,
            fallback=kpi_config.get("fallback", {}),
        )
        current_value = (
            normalize_metric_value(metric_name, raw_value)
            if kpi_config.get("normalize", False)
            else float(raw_value or 0.0)
        )
    else:
        # Calculate current value
        current_value = await calculate_kpi_value(agent, kpi_config)

    # Get historical values
    historical_values = await get_kpi_history(agent, tenant_id, kpi_id)

    # Calculate trend
    trend = await calculate_kpi_trend(
        historical_values, current_value, kpi_config.get("trend_direction")
    )

    # Check against thresholds
    threshold_status = await check_kpi_thresholds(current_value, kpi_config.get("thresholds", {}))

    # Update KPI record
    kpi_record = {
        "kpi_id": kpi_id,
        "name": kpi_config.get("name"),
        "current_value": current_value,
        "target_value": kpi_config.get("target"),
        "trend": trend,
        "threshold_status": threshold_status,
        "historical_values": historical_values,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.kpis[kpi_id] = kpi_record
    agent.analytics_output_store.upsert(tenant_id, kpi_id, kpi_record.copy())
    await store_kpi_history(agent, tenant_id, kpi_id, current_value)

    alerts_triggered: list[str] = []
    if threshold_status.get("breached"):
        alert_id = f"KPI-ALERT-{len(agent.kpi_alerts) + 1}"
        alert = {
            "alert_id": alert_id,
            "kpi_id": kpi_id,
            "name": kpi_config.get("name"),
            "current_value": current_value,
            "thresholds": kpi_config.get("thresholds", {}),
            "status": "active",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }
        agent.kpi_alerts[alert_id] = alert
        agent.analytics_alert_store.upsert(tenant_id, alert_id, alert.copy())
        alerts_triggered.append(alert_id)
        if agent.event_bus:
            await agent.event_bus.publish(
                "analytics.kpi.threshold_breached",
                {"tenant_id": tenant_id, "payload": alert},
            )

    return {
        "kpi_id": kpi_id,
        "name": kpi_config.get("name"),
        "current_value": current_value,
        "target_value": kpi_config.get("target"),
        "trend": trend,
        "threshold_status": threshold_status,
        "achievement_percentage": (
            (current_value / kpi_config.get("target", 1)) * 100 if kpi_config.get("target") else 0
        ),
        "alerts_triggered": alerts_triggered,
    }
