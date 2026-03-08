"""
External integration helpers for the System Health & Monitoring Agent.

Handles ServiceNow, webhook notifications, Event Hub streaming,
Azure Automation runbooks, and Prometheus metrics exposition.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Lazy Azure imports (same pattern as the original monolith)
# ---------------------------------------------------------------------------
import importlib.util


def _safe_find_spec(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ModuleNotFoundError, ValueError):
        return False


_HAS_AZURE = _safe_find_spec("azure")
_HAS_AZURE_EVENTHUB = _HAS_AZURE and _safe_find_spec("azure.eventhub")
if _HAS_AZURE_EVENTHUB:
    from azure.eventhub import EventData, EventHubProducerClient
else:
    EventData = None  # type: ignore[assignment,misc]
    EventHubProducerClient = None  # type: ignore[assignment,misc]

_HAS_AZURE_AUTOMATION = _HAS_AZURE and _safe_find_spec("azure.mgmt.automation")
if _HAS_AZURE_AUTOMATION:
    from azure.mgmt.automation import AutomationClient
    from azure.mgmt.automation.models import JobCreateParameters, RunbookAssociationProperty
else:
    AutomationClient = None  # type: ignore[assignment,misc]
    JobCreateParameters = None  # type: ignore[assignment,misc]
    RunbookAssociationProperty = None  # type: ignore[assignment,misc]

_HAS_PROMETHEUS = _safe_find_spec("prometheus_client")
if _HAS_PROMETHEUS:
    from prometheus_client import CollectorRegistry, Counter, Gauge, start_http_server
else:
    CollectorRegistry = None  # type: ignore[assignment,misc]
    Counter = None  # type: ignore[assignment,misc]
    Gauge = None  # type: ignore[assignment,misc]
    start_http_server = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# ServiceNow
# ---------------------------------------------------------------------------


async def servicenow_request(
    instance_url: str | None,
    token: str | None,
    username: str | None,
    password: str | None,
    method: str,
    path: str,
    payload: dict[str, Any],
    logger: logging.Logger | None = None,
) -> dict[str, Any] | None:
    if not instance_url:
        return None
    url = f"{instance_url}{path}"
    headers: dict[str, str] = {"Accept": "application/json"}
    auth = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif username and password:
        auth = (username, password)
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.request(method, url, json=payload, headers=headers, auth=auth)
    if response.is_error:
        if logger:
            logger.warning(
                "ServiceNow request failed",
                extra={"status": response.status_code, "path": path},
            )
        return None
    try:
        return response.json()
    except json.JSONDecodeError:
        return None


async def create_servicenow_incident(agent: Any, incident: dict[str, Any]) -> None:
    """Create a ServiceNow incident record.  Mutates *incident* in-place to add ``servicenow_sys_id``."""
    if not agent.servicenow_instance_url:
        return
    payload = {
        "short_description": incident.get("title") or incident.get("name") or "Monitoring incident",
        "description": incident.get("description"),
        "severity": incident.get("severity"),
        "urgency": "1",
    }
    response = await servicenow_request(
        agent.servicenow_instance_url,
        agent.servicenow_token,
        agent.servicenow_username,
        agent.servicenow_password,
        "post",
        "/api/now/table/incident",
        payload,
        logger=agent.logger,
    )
    if response and "result" in response and isinstance(response["result"], dict):
        sys_id = response["result"].get("sys_id")
        if sys_id:
            incident["servicenow_sys_id"] = sys_id


async def update_servicenow_incident(agent: Any, incident: dict[str, Any]) -> None:
    if not agent.servicenow_instance_url:
        return
    payload = {
        "state": "Resolved",
        "close_notes": incident.get("resolution"),
    }
    sys_id = incident.get("servicenow_sys_id")
    if not sys_id:
        return
    await servicenow_request(
        agent.servicenow_instance_url,
        agent.servicenow_token,
        agent.servicenow_username,
        agent.servicenow_password,
        "patch",
        f"/api/now/table/incident/{sys_id}",
        payload,
        logger=agent.logger,
    )


# ---------------------------------------------------------------------------
# Webhook notifications
# ---------------------------------------------------------------------------


async def trigger_webhook_notification(url: str | None, alert: dict[str, Any]) -> None:
    if not url:
        return
    payload = {
        "event_type": "trigger",
        "alert": alert,
        "priority": "high" if alert.get("severity") == "critical" else "normal",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json=payload)


async def trigger_incident_webhook(url: str | None, payload: dict[str, Any]) -> None:
    if not url:
        return
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json=payload)


async def notify_alert_integrations(agent: Any, alert: dict[str, Any]) -> None:
    await trigger_webhook_notification(agent.pagerduty_webhook_url, alert)
    await trigger_webhook_notification(agent.opsgenie_webhook_url, alert)
    if alert.get("severity") == "critical":
        await create_servicenow_incident(
            agent,
            {
                "title": alert.get("name", "Critical alert"),
                "description": alert.get("description"),
                "severity": "critical",
                "affected_services": [alert.get("service_name")],
            },
        )


async def notify_incident_integrations(agent: Any, incident: dict[str, Any]) -> None:
    payload = {
        "event_type": "incident",
        "incident": incident,
        "priority": "high" if incident.get("severity") == "critical" else "normal",
    }
    await trigger_incident_webhook(agent.pagerduty_webhook_url, payload)
    await trigger_incident_webhook(agent.opsgenie_webhook_url, payload)


# ---------------------------------------------------------------------------
# Scaling / Automation
# ---------------------------------------------------------------------------


async def trigger_scaling_actions(
    agent: Any, service_name: str, metrics_data: dict[str, Any]
) -> None:
    scaling_payload: dict[str, Any] = {
        "service_name": service_name,
        "cpu": metrics_data.get("cpu_usage"),
        "memory": metrics_data.get("memory_usage"),
        "queue_depth": metrics_data.get("queue_depth"),
        "thresholds": agent.scaling_thresholds,
    }
    cpu_exceeded = (
        metrics_data.get("cpu_usage") is not None
        and metrics_data.get("cpu_usage") > agent.scaling_thresholds["cpu"]
    )
    memory_exceeded = (
        metrics_data.get("memory_usage") is not None
        and metrics_data.get("memory_usage") > agent.scaling_thresholds["memory"]
    )
    queue_exceeded = (
        metrics_data.get("queue_depth") is not None
        and metrics_data.get("queue_depth") > agent.scaling_thresholds["queue_depth"]
    )
    if not (cpu_exceeded or memory_exceeded or queue_exceeded):
        return
    scaling_payload["reason"] = [
        name
        for name, exceeded in [
            ("cpu", cpu_exceeded),
            ("memory", memory_exceeded),
            ("queue_depth", queue_exceeded),
        ]
        if exceeded
    ]
    if agent.scaling_webhook_url or agent.automation_webhook_url:
        target_url = agent.scaling_webhook_url or agent.automation_webhook_url
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(target_url, json=scaling_payload)
    if agent._automation_client and agent.automation_runbook_name:
        await start_automation_runbook(agent, service_name, scaling_payload)


async def start_automation_runbook(
    agent: Any, service_name: str, scaling_payload: dict[str, Any]
) -> None:
    if not (agent._automation_client and agent.automation_runbook_name):
        return
    job_name = f"scale-{service_name}-{uuid.uuid4().hex[:6]}"
    parameters = JobCreateParameters(
        runbook=RunbookAssociationProperty(name=agent.automation_runbook_name),
        parameters={key: str(value) for key, value in scaling_payload.items() if value is not None},
    )
    await asyncio.to_thread(
        agent._automation_client.job.create,
        agent.automation_resource_group,
        agent.automation_account_name,
        job_name,
        parameters,
    )


# ---------------------------------------------------------------------------
# Event Hub
# ---------------------------------------------------------------------------


async def emit_event_hub_event(agent: Any, payload: dict[str, Any]) -> None:
    if not agent._event_hub_producer:
        return
    event_body = json.dumps(payload)
    batch = agent._event_hub_producer.create_batch()
    batch.add(EventData(event_body))
    await asyncio.to_thread(agent._event_hub_producer.send_batch, batch)


# ---------------------------------------------------------------------------
# Prometheus helpers
# ---------------------------------------------------------------------------


async def update_prometheus_metrics(
    prometheus_metrics: dict[str, Any], service_name: str, result: dict[str, Any]
) -> None:
    if not prometheus_metrics:
        return
    status_value = 1.0 if result.get("healthy") else 0.0
    prometheus_metrics["health_status"].labels(service=service_name).set(status_value)
    prometheus_metrics["health_latency"].labels(service=service_name).set(
        result.get("response_time_ms", 0)
    )
    prometheus_metrics["health_checks"].labels(service=service_name).inc()


# ---------------------------------------------------------------------------
# Health endpoint fetch
# ---------------------------------------------------------------------------


async def fetch_health_endpoint(endpoint: dict[str, Any]) -> dict[str, Any]:
    url = endpoint.get("url")
    timeout_seconds = endpoint.get("timeout_seconds", 5)
    if not url:
        return {"healthy": False, "error": "missing_url", "response_time_ms": 0}
    start = datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        healthy = 200 <= response.status_code < 400
        return {
            "healthy": healthy,
            "status_code": response.status_code,
            "response_time_ms": elapsed,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except httpx.HTTPError as exc:
        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return {
            "healthy": False,
            "status_code": 0,
            "response_time_ms": elapsed,
            "error": str(exc),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


async def scrape_prometheus_target(target: dict[str, Any]) -> dict[str, Any]:
    from health_utils import parse_prometheus_metrics

    url = target.get("url")
    timeout_seconds = target.get("timeout_seconds", 5)
    if not url:
        return {"error": "missing_url"}
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return {"error": str(exc)}
    metrics = parse_prometheus_metrics(response.text)
    metrics["metrics_source"] = "prometheus"
    return metrics
