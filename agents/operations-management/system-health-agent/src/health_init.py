"""
Initialization helpers for the System Health & Monitoring Agent.

Azure Monitor, Event Hub, Automation Client, Prometheus, alert rules,
health probes, and OpenTelemetry exporter configuration.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from health_utils import parse_time_range

if TYPE_CHECKING:
    from system_health_agent import SystemHealthAgent

# ---------------------------------------------------------------------------
# Lazy Azure / optional-dependency imports
# ---------------------------------------------------------------------------
import importlib.util


def _safe_find_spec(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ModuleNotFoundError, ValueError):
        return False


_HAS_AZURE = _safe_find_spec("azure")

_HAS_AZURE_MONITOR_OPENTELEMETRY = _HAS_AZURE and _safe_find_spec("azure.monitor.opentelemetry")
if _HAS_AZURE_MONITOR_OPENTELEMETRY:
    from azure.monitor.opentelemetry import configure_azure_monitor as _configure_azure_monitor
else:
    _configure_azure_monitor = None

_HAS_OTEL_AZURE_EXPORTER = _safe_find_spec("opentelemetry.exporter.azuremonitor")
if _HAS_OTEL_AZURE_EXPORTER:
    from opentelemetry.exporter.azuremonitor import (
        AzureMonitorLogExporter,
        AzureMonitorMetricExporter,
        AzureMonitorTraceExporter,
    )
else:
    AzureMonitorLogExporter = None  # type: ignore[assignment,misc]
    AzureMonitorMetricExporter = None  # type: ignore[assignment,misc]
    AzureMonitorTraceExporter = None  # type: ignore[assignment,misc]

_HAS_AZURE_MONITOR_QUERY = _HAS_AZURE and _safe_find_spec("azure.monitor.query")
if _HAS_AZURE_MONITOR_QUERY:
    from azure.monitor.query import LogsQueryClient, LogsQueryStatus, MetricsQueryClient
else:
    LogsQueryClient = None  # type: ignore[assignment,misc]
    LogsQueryStatus = None  # type: ignore[assignment,misc]
    MetricsQueryClient = None  # type: ignore[assignment,misc]

_HAS_AZURE_EVENTHUB = _HAS_AZURE and _safe_find_spec("azure.eventhub")
if _HAS_AZURE_EVENTHUB:
    from azure.eventhub import EventHubProducerClient
else:
    EventHubProducerClient = None  # type: ignore[assignment,misc]

_HAS_AZURE_AUTOMATION = _HAS_AZURE and _safe_find_spec("azure.mgmt.automation")
if _HAS_AZURE_AUTOMATION:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.automation import AutomationClient
else:
    AutomationClient = None  # type: ignore[assignment,misc]
    DefaultAzureCredential = None  # type: ignore[assignment,misc]

_HAS_PROMETHEUS = _safe_find_spec("prometheus_client")
if _HAS_PROMETHEUS:
    from prometheus_client import CollectorRegistry, Counter, Gauge, start_http_server
else:
    CollectorRegistry = None  # type: ignore[assignment,misc]
    Counter = None  # type: ignore[assignment,misc]
    Gauge = None  # type: ignore[assignment,misc]
    start_http_server = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Initialization methods (called from SystemHealthAgent.initialize)
# ---------------------------------------------------------------------------


async def initialize_azure_monitoring(agent: SystemHealthAgent) -> None:
    if _HAS_AZURE_MONITOR_QUERY and (agent.monitor_workspace_id or agent.app_insights_resource_id):
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        agent._logs_query_client = LogsQueryClient(credential)
        agent._metrics_query_client = MetricsQueryClient(credential)
        agent.logger.info(
            "Azure Monitor clients configured",
            extra={
                "workspace_id": agent.monitor_workspace_id,
                "app_insights_resource_id": agent.app_insights_resource_id,
            },
        )


async def configure_opentelemetry_exporters(agent: SystemHealthAgent) -> None:
    if agent._azure_monitor_configured:
        return
    if not agent.azure_monitor_connection_string:
        agent.logger.info("Azure Monitor connection string not configured")
        return
    # Look up _configure_azure_monitor from the main module at call time so that
    # tests can monkeypatch ``system_health_module._configure_azure_monitor``.
    import sys

    sha_module = sys.modules.get("system_health_agent")
    cfg_fn = (
        getattr(sha_module, "_configure_azure_monitor", None)
        if sha_module
        else _configure_azure_monitor
    )
    if cfg_fn is None:
        cfg_fn = _configure_azure_monitor
    if cfg_fn:
        cfg_fn(connection_string=agent.azure_monitor_connection_string)
        agent._azure_monitor_configured = True
        agent.logger.info("Azure Monitor OpenTelemetry configured via SDK")
        return
    if not _HAS_OTEL_AZURE_EXPORTER:
        agent.logger.warning("Azure Monitor exporter unavailable")
        return

    from opentelemetry import metrics as otel_metrics
    from opentelemetry import trace
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": agent.agent_id})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(AzureMonitorTraceExporter(agent.azure_monitor_connection_string))
    )
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        AzureMonitorMetricExporter(agent.azure_monitor_connection_string)
    )
    otel_metrics.set_meter_provider(
        MeterProvider(resource=resource, metric_readers=[metric_reader])
    )

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(AzureMonitorLogExporter(agent.azure_monitor_connection_string))
    )
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    agent._azure_monitor_configured = True
    agent.logger.info("Azure Monitor exporters configured")


async def initialize_event_hub(agent: SystemHealthAgent) -> None:
    if not (agent.event_hub_connection_string and agent.event_hub_name):
        return
    if not _HAS_AZURE_EVENTHUB:
        agent.logger.warning("Azure Event Hub SDK not available")
        return
    agent._event_hub_producer = EventHubProducerClient.from_connection_string(
        conn_str=agent.event_hub_connection_string,
        eventhub_name=agent.event_hub_name,
    )
    agent.logger.info(
        "Event Hub producer initialized",
        extra={
            "event_hub": agent.event_hub_name,
            "partitions": agent.event_hub_partitions,
            "throughput_units": agent.event_hub_throughput_units,
        },
    )


async def initialize_automation_client(agent: SystemHealthAgent) -> None:
    if (
        not _HAS_AZURE_AUTOMATION
        or not agent.automation_subscription_id
        or not agent.automation_resource_group
        or not agent.automation_account_name
    ):
        return
    credential = DefaultAzureCredential()
    agent._automation_client = AutomationClient(credential, agent.automation_subscription_id)
    agent.logger.info(
        "Azure Automation client initialized",
        extra={
            "automation_account": agent.automation_account_name,
            "resource_group": agent.automation_resource_group,
        },
    )


async def initialize_prometheus_metrics(agent: SystemHealthAgent) -> None:
    if not (_HAS_PROMETHEUS and agent.metrics_port and agent.metrics_port > 0):
        return
    agent._prometheus_registry = CollectorRegistry()
    agent._prometheus_metrics["health_status"] = Gauge(
        "service_health_status",
        "Health status of monitored services (1=healthy, 0=degraded)",
        ["service"],
        registry=agent._prometheus_registry,
    )
    agent._prometheus_metrics["health_latency"] = Gauge(
        "service_health_latency_ms",
        "Latency of health checks in milliseconds",
        ["service"],
        registry=agent._prometheus_registry,
    )
    agent._prometheus_metrics["health_checks"] = Counter(
        "service_health_checks_total",
        "Total health checks executed",
        ["service"],
        registry=agent._prometheus_registry,
    )
    start_http_server(agent.metrics_port, registry=agent._prometheus_registry)
    agent.logger.info("Prometheus metrics endpoint started", extra={"port": agent.metrics_port})


async def configure_alert_rules(agent: SystemHealthAgent) -> None:
    agent._alert_rules = [
        {
            "name": "error_rate_threshold",
            "metric": "error_rate",
            "threshold": agent.alert_threshold_error_rate,
            "severity": "critical",
            "notification_channels": [
                url for url in [agent.pagerduty_webhook_url, agent.opsgenie_webhook_url] if url
            ],
        },
        {
            "name": "response_time_threshold",
            "metric": "response_time_ms",
            "threshold": agent.alert_threshold_response_time_ms,
            "severity": "warning",
            "notification_channels": [
                url for url in [agent.pagerduty_webhook_url, agent.opsgenie_webhook_url] if url
            ],
        },
    ]
    agent.logger.info("Alert rules configured", extra={"count": len(agent._alert_rules)})


async def initialize_health_probes(agent: SystemHealthAgent) -> None:
    if not agent.health_endpoints or agent.health_probe_interval_seconds <= 0:
        return
    if agent._health_probe_task:
        return
    agent._health_probe_task = asyncio.create_task(periodic_health_probes(agent))
    agent.logger.info(
        "Health probes scheduled",
        extra={"interval": agent.health_probe_interval_seconds},
    )


async def periodic_health_probes(agent: SystemHealthAgent) -> None:
    from health_actions.check_health import check_all_services_health

    while True:
        try:
            await check_all_services_health(agent)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            agent.logger.warning("Health probe failure", extra={"error": str(exc)})
        await asyncio.sleep(agent.health_probe_interval_seconds)


# ---------------------------------------------------------------------------
# Azure query methods (used by action modules via agent._query_metrics etc.)
# ---------------------------------------------------------------------------


async def query_metrics(
    agent: SystemHealthAgent, service_name: str, metric_name: str, time_range: dict[str, Any]
) -> list[dict[str, Any]]:
    """Query metrics from store."""
    if not agent._logs_query_client:
        return []

    start_time, end_time = parse_time_range(time_range)
    metric_filter = "" if metric_name == "*" else f'| where name == "{metric_name}"'
    query = (
        "customMetrics "
        f'| where cloud_RoleName == "{service_name}" '
        f"{metric_filter} "
        f"| where timestamp between (datetime({start_time.isoformat()}) .. datetime({end_time.isoformat()})) "
        "| project timestamp, name, value"
        "| order by timestamp asc"
    )
    if agent.monitor_workspace_id:
        response = await asyncio.to_thread(
            agent._logs_query_client.query_workspace,
            workspace_id=agent.monitor_workspace_id,
            query=query,
            timespan=(start_time, end_time),
        )
    elif agent.app_insights_resource_id:
        response = await asyncio.to_thread(
            agent._logs_query_client.query_resource,
            resource_id=agent.app_insights_resource_id,
            query=query,
            timespan=(start_time, end_time),
        )
    else:
        return []
    if response.status != LogsQueryStatus.SUCCESS:
        agent.logger.warning("Log Analytics query returned partial results")

    table = response.tables[0] if response.tables else None
    if not table:
        return []

    values = []
    for row in table.rows:
        values.append(
            {
                "timestamp": row[0],
                "metric": row[1],
                "value": row[2],
            }
        )
    return values


async def get_service_metrics(
    agent: SystemHealthAgent, service_name: str, time_range: dict[str, Any]
) -> list[dict[str, Any]]:
    """Get metrics for service in time range."""
    metrics_list: list[dict[str, Any]] = []
    start_time, end_time = parse_time_range(time_range)
    for metric in agent.metrics.values():
        if metric.get("service_name") != service_name:
            continue
        timestamp = metric.get("timestamp")
        if timestamp:
            parsed = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
            if parsed < start_time or parsed > end_time:
                continue
        metrics_list.append(metric)

    query_results = await query_metrics(agent, service_name, "*", time_range)
    metrics_list.extend(query_results)
    return metrics_list


async def query_azure_resource_metrics(
    agent: SystemHealthAgent, resource_id: str
) -> dict[str, Any]:
    if not agent._metrics_query_client:
        return {"error": "azure_monitor_unavailable"}
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=5)
    metric_names = [
        "Percentage CPU",
        "Available Memory Bytes",
        "Total Memory Bytes",
        "Logical Disk % Free Space",
        "Network In Total",
        "Network Out Total",
    ]
    response = await asyncio.to_thread(
        agent._metrics_query_client.query_resource,
        resource_id=resource_id,
        metric_names=metric_names,
        timespan=(start_time, end_time),
    )
    result: dict[str, Any] = {"metrics_source": "azure_monitor"}
    value_lookup: dict[str, float] = {}
    for metric in response.metrics:
        mn = getattr(metric.name, "value", None) or str(metric.name)
        if not metric.timeseries:
            continue
        points = metric.timeseries[0].data
        if not points:
            continue
        latest = next((point for point in reversed(points) if point.average is not None), None)
        if not latest:
            continue
        value_lookup[mn] = float(latest.average)

    cpu_value = value_lookup.get("Percentage CPU")
    if cpu_value is not None:
        result["cpu_usage"] = cpu_value / 100.0
    available_memory = value_lookup.get("Available Memory Bytes")
    total_memory = value_lookup.get("Total Memory Bytes")
    if available_memory is not None and total_memory:
        result["memory_usage"] = (total_memory - available_memory) / total_memory
    elif available_memory is not None:
        result["memory_available_bytes"] = available_memory
    disk_free = value_lookup.get("Logical Disk % Free Space")
    if disk_free is not None:
        result["disk_usage"] = (100.0 - disk_free) / 100.0
    network_in = value_lookup.get("Network In Total")
    if network_in is not None:
        result["network_rx_bytes_total"] = network_in
    network_out = value_lookup.get("Network Out Total")
    if network_out is not None:
        result["network_tx_bytes_total"] = network_out
    return result
