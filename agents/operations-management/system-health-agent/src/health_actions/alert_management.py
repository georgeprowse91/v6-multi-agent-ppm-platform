"""Action handlers for alert management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from health_integrations import notify_alert_integrations, trigger_scaling_actions
from health_utils import generate_alert_id, sanitize_text

if TYPE_CHECKING:
    from system_health_agent import SystemHealthAgent


async def create_alert(
    agent: SystemHealthAgent, tenant_id: str, alert_config: dict[str, Any]
) -> dict[str, Any]:
    """Create monitoring alert.  Returns alert ID and configuration."""
    alert_name = sanitize_text(alert_config.get("name", ""))
    agent.logger.info("Creating alert: %s", alert_name)

    alert_id = await generate_alert_id()

    alert = {
        "alert_id": alert_id,
        "name": alert_name,
        "description": sanitize_text(alert_config.get("description", "")),
        "severity": alert_config.get("severity", "warning"),
        "service_name": alert_config.get("service_name"),
        "condition": alert_config.get("condition"),
        "threshold": alert_config.get("threshold"),
        "notification_channels": alert_config.get("notification_channels", []),
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    agent.alerts[alert_id] = alert
    agent.alert_store.upsert(tenant_id, alert_id, alert.copy())

    if alert.get("severity") == "critical":
        await notify_alert_integrations(agent, alert)

    return {
        "alert_id": alert_id,
        "name": alert["name"],
        "severity": alert["severity"],
        "status": "active",
    }


async def get_alerts(agent: SystemHealthAgent, filters: dict[str, Any]) -> dict[str, Any]:
    """Get alerts with filters.  Returns filtered alerts."""
    agent.logger.info("Retrieving alerts")

    filtered = []
    for alert_id, alert in agent.alerts.items():
        if await _matches_alert_filters(alert, filters):
            filtered.append(
                {
                    "alert_id": alert_id,
                    "name": alert.get("name"),
                    "severity": alert.get("severity"),
                    "service_name": alert.get("service_name"),
                    "status": alert.get("status"),
                    "created_at": alert.get("created_at"),
                }
            )

    filtered.sort(
        key=lambda x: (
            (0 if x.get("severity") == "critical" else 1 if x.get("severity") == "warning" else 2),
            x.get("created_at", ""),
        )
    )

    return {"total_alerts": len(filtered), "alerts": filtered, "filters": filters}


async def acknowledge_alert(
    agent: SystemHealthAgent, tenant_id: str, alert_id: str, acknowledged_by: str
) -> dict[str, Any]:
    """Acknowledge alert.  Returns acknowledgment confirmation."""
    agent.logger.info("Acknowledging alert: %s", alert_id)

    alert = agent.alerts.get(alert_id)
    if not alert:
        raise ValueError(f"Alert not found: {alert_id}")

    alert["acknowledged"] = True
    alert["acknowledged_by"] = sanitize_text(acknowledged_by)
    alert["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
    agent.alert_store.upsert(tenant_id, alert_id, alert.copy())

    return {
        "alert_id": alert_id,
        "acknowledged": True,
        "acknowledged_by": acknowledged_by,
        "acknowledged_at": alert["acknowledged_at"],
    }


async def check_metric_thresholds(
    agent: SystemHealthAgent, tenant_id: str, service_name: str, metrics_data: dict[str, Any]
) -> list[str]:
    """Check metrics against alert thresholds."""
    alert_ids: list[str] = []

    error_rate = metrics_data.get("error_rate", 0)
    if error_rate > agent.alert_threshold_error_rate:
        response = await create_alert(
            agent,
            tenant_id,
            {
                "name": f"{service_name} error rate threshold exceeded",
                "description": (
                    f"Error rate {error_rate:.2%} exceeded threshold "
                    f"{agent.alert_threshold_error_rate:.2%}."
                ),
                "severity": "critical",
                "service_name": service_name,
                "condition": "error_rate",
                "threshold": agent.alert_threshold_error_rate,
            },
        )
        alert_ids.append(response["alert_id"])

    response_time = metrics_data.get("response_time_ms", 0)
    if response_time > agent.alert_threshold_response_time_ms:
        response = await create_alert(
            agent,
            tenant_id,
            {
                "name": f"{service_name} response time threshold exceeded",
                "description": (
                    f"Response time {response_time:.0f}ms exceeded threshold "
                    f"{agent.alert_threshold_response_time_ms:.0f}ms."
                ),
                "severity": "warning",
                "service_name": service_name,
                "condition": "response_time_ms",
                "threshold": agent.alert_threshold_response_time_ms,
            },
        )
        alert_ids.append(response["alert_id"])

    await trigger_scaling_actions(agent, service_name, metrics_data)

    return alert_ids


async def _matches_alert_filters(alert: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Check if alert matches filters."""
    if "severity" in filters and alert.get("severity") != filters["severity"]:
        return False
    if "status" in filters and alert.get("status") != filters["status"]:
        return False
    return True
