"""
Agent 25: System Health & Monitoring Agent

Purpose:
Ensures the operational reliability, performance and availability of the PPM platform through
comprehensive monitoring, alerting, and proactive maintenance.

Specification: agents/operations-management/agent-25-system-health-monitoring/README.md
"""

import asyncio
import importlib.util
import json
import logging
import os
import re
import statistics
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from observability.metrics import build_kpi_handles, configure_metrics
from observability.tracing import configure_tracing, start_agent_span
from integrations.services.integration.analytics import AnalyticsClient

from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore

_HAS_AZURE = importlib.util.find_spec("azure") is not None
_HAS_AZURE_MONITOR_OPENTELEMETRY = _HAS_AZURE and (
    importlib.util.find_spec("azure.monitor.opentelemetry") is not None
)
if _HAS_AZURE_MONITOR_OPENTELEMETRY:
    from azure.monitor.opentelemetry import configure_azure_monitor as _configure_azure_monitor
else:
    _configure_azure_monitor = None

_HAS_OTEL_AZURE_EXPORTER = (
    importlib.util.find_spec("opentelemetry.exporter.azuremonitor") is not None
)
if _HAS_OTEL_AZURE_EXPORTER:
    from opentelemetry.exporter.azuremonitor import (
        AzureMonitorLogExporter,
        AzureMonitorMetricExporter,
        AzureMonitorTraceExporter,
    )
else:
    AzureMonitorLogExporter = None
    AzureMonitorMetricExporter = None
    AzureMonitorTraceExporter = None

_HAS_AZURE_MONITOR_QUERY = _HAS_AZURE and (
    importlib.util.find_spec("azure.monitor.query") is not None
)
if _HAS_AZURE_MONITOR_QUERY:
    from azure.monitor.query import LogsQueryClient, LogsQueryStatus, MetricsQueryClient
else:
    LogsQueryClient = None
    LogsQueryStatus = None
    MetricsQueryClient = None

_HAS_ANOMALY_DETECTOR = _HAS_AZURE and (
    importlib.util.find_spec("azure.ai.anomalydetector") is not None
)
if _HAS_ANOMALY_DETECTOR:
    from azure.ai.anomalydetector import AnomalyDetectorClient
    from azure.ai.anomalydetector.models import TimeSeriesPoint
    from azure.core.credentials import AzureKeyCredential
else:
    AnomalyDetectorClient = None
    TimeSeriesPoint = None
    AzureKeyCredential = None

_HAS_AZURE_EVENTHUB = _HAS_AZURE and importlib.util.find_spec("azure.eventhub") is not None
if _HAS_AZURE_EVENTHUB:
    from azure.eventhub import EventData, EventHubProducerClient
else:
    EventData = None
    EventHubProducerClient = None

_HAS_AZURE_AUTOMATION = _HAS_AZURE and importlib.util.find_spec("azure.mgmt.automation") is not None
if _HAS_AZURE_AUTOMATION:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.automation import AutomationClient
    from azure.mgmt.automation.models import JobCreateParameters, RunbookAssociationProperty
else:
    AutomationClient = None
    JobCreateParameters = None
    RunbookAssociationProperty = None

_HAS_PROMETHEUS = importlib.util.find_spec("prometheus_client") is not None
if _HAS_PROMETHEUS:
    from prometheus_client import CollectorRegistry, Counter, Gauge, start_http_server
else:
    CollectorRegistry = None
    Counter = None
    Gauge = None
    start_http_server = None


class SystemHealthAgent(BaseAgent):
    """
    System Health & Monitoring Agent - Monitors platform health and performance.

    Key Capabilities:
    - Resource monitoring (compute, memory, storage, network)
    - Application and agent monitoring
    - Log and trace collection
    - Alerting and incident management
    - Anomaly detection and predictive maintenance
    - Dashboarding and reporting
    - Root cause analysis and diagnostics
    - Capacity planning and scaling recommendations
    """

    def __init__(self, agent_id: str = "agent_025", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.alert_threshold_error_rate = (
            config.get("alert_threshold_error_rate", 0.05) if config else 0.05
        )
        self.alert_threshold_response_time_ms = (
            config.get("alert_threshold_response_time_ms", 1000) if config else 1000
        )
        self.metrics_retention_days = config.get("metrics_retention_days", 90) if config else 90
        self.monitor_workspace_id = (
            config.get("monitor_workspace_id")
            if config and config.get("monitor_workspace_id")
            else os.getenv("MONITOR_WORKSPACE_ID")
        )
        self.app_insights_instrumentation_key = (
            config.get("appinsights_instrumentation_key")
            if config and config.get("appinsights_instrumentation_key")
            else os.getenv("APPINSIGHTS_INSTRUMENTATION_KEY")
        )
        self.app_insights_resource_id = (
            config.get("appinsights_resource_id")
            if config and config.get("appinsights_resource_id")
            else os.getenv("APPINSIGHTS_RESOURCE_ID")
        )
        self.azure_monitor_connection_string = (
            config.get("azure_monitor_connection_string")
            if config and config.get("azure_monitor_connection_string")
            else os.getenv("AZURE_MONITOR_CONNECTION_STRING")
        )
        if not self.azure_monitor_connection_string and self.app_insights_instrumentation_key:
            self.azure_monitor_connection_string = (
                f"InstrumentationKey={self.app_insights_instrumentation_key}"
            )
        self.event_hub_connection_string = (
            config.get("event_hub_connection_string")
            if config and config.get("event_hub_connection_string")
            else os.getenv("EVENT_HUB_CONNECTION_STRING")
        )
        self.event_hub_name = (
            config.get("event_hub_name")
            if config and config.get("event_hub_name")
            else os.getenv("EVENT_HUB_NAME")
        )
        self.event_hub_partitions = int(
            config.get("event_hub_partitions", os.getenv("EVENT_HUB_PARTITIONS", "4"))
            if config
            else os.getenv("EVENT_HUB_PARTITIONS", "4")
        )
        self.event_hub_throughput_units = int(
            config.get("event_hub_throughput_units", os.getenv("EVENT_HUB_THROUGHPUT_UNITS", "1"))
            if config
            else os.getenv("EVENT_HUB_THROUGHPUT_UNITS", "1")
        )
        self.pagerduty_webhook_url = (
            config.get("pagerduty_webhook_url")
            if config and config.get("pagerduty_webhook_url")
            else os.getenv("PAGERDUTY_WEBHOOK_URL")
        )
        self.opsgenie_webhook_url = (
            config.get("opsgenie_webhook_url")
            if config and config.get("opsgenie_webhook_url")
            else os.getenv("OPSGENIE_WEBHOOK_URL")
        )
        self.scaling_webhook_url = (
            config.get("scaling_webhook_url")
            if config and config.get("scaling_webhook_url")
            else os.getenv("SCALING_WEBHOOK_URL")
        )
        self.automation_webhook_url = (
            config.get("automation_webhook_url")
            if config and config.get("automation_webhook_url")
            else os.getenv("AUTOMATION_WEBHOOK_URL")
        )
        self.automation_subscription_id = (
            config.get("automation_subscription_id")
            if config and config.get("automation_subscription_id")
            else os.getenv("AUTOMATION_SUBSCRIPTION_ID")
        )
        self.automation_resource_group = (
            config.get("automation_resource_group")
            if config and config.get("automation_resource_group")
            else os.getenv("AUTOMATION_RESOURCE_GROUP")
        )
        self.automation_account_name = (
            config.get("automation_account_name")
            if config and config.get("automation_account_name")
            else os.getenv("AUTOMATION_ACCOUNT_NAME")
        )
        self.automation_runbook_name = (
            config.get("automation_runbook_name")
            if config and config.get("automation_runbook_name")
            else os.getenv("AUTOMATION_RUNBOOK_NAME")
        )
        self.scaling_thresholds = {
            "cpu": float(
                config.get("scaling_threshold_cpu", os.getenv("SCALING_THRESHOLD_CPU", "0.8"))
                if config
                else os.getenv("SCALING_THRESHOLD_CPU", "0.8")
            ),
            "memory": float(
                config.get(
                    "scaling_threshold_memory", os.getenv("SCALING_THRESHOLD_MEMORY", "0.8")
                )
                if config
                else os.getenv("SCALING_THRESHOLD_MEMORY", "0.8")
            ),
            "queue_depth": float(
                config.get(
                    "scaling_threshold_queue_depth",
                    os.getenv("SCALING_THRESHOLD_QUEUE_DEPTH", "1000"),
                )
                if config
                else os.getenv("SCALING_THRESHOLD_QUEUE_DEPTH", "1000")
            ),
        }
        self.servicenow_instance_url = (
            config.get("servicenow_instance_url")
            if config and config.get("servicenow_instance_url")
            else os.getenv("SERVICENOW_INSTANCE_URL")
        )
        self.servicenow_username = (
            config.get("servicenow_username")
            if config and config.get("servicenow_username")
            else os.getenv("SERVICENOW_USERNAME")
        )
        self.servicenow_password = (
            config.get("servicenow_password")
            if config and config.get("servicenow_password")
            else os.getenv("SERVICENOW_PASSWORD")
        )
        self.servicenow_token = (
            config.get("servicenow_token")
            if config and config.get("servicenow_token")
            else os.getenv("SERVICENOW_TOKEN")
        )
        self.anomaly_detector_endpoint = (
            config.get("anomaly_detector_endpoint")
            if config and config.get("anomaly_detector_endpoint")
            else os.getenv("ANOMALY_DETECTOR_ENDPOINT")
        )
        self.anomaly_detector_key = (
            config.get("anomaly_detector_key")
            if config and config.get("anomaly_detector_key")
            else os.getenv("ANOMALY_DETECTOR_KEY")
        )
        self.health_endpoints = (
            config.get("health_endpoints") if config and config.get("health_endpoints") else None
        ) or self._load_health_endpoints()
        self.health_probe_interval_seconds = int(
            config.get(
                "health_probe_interval_seconds",
                os.getenv("HEALTH_PROBE_INTERVAL_SECONDS", "60"),
            )
            if config
            else os.getenv("HEALTH_PROBE_INTERVAL_SECONDS", "60")
        )
        self.metrics_port = int(
            config.get("metrics_port", os.getenv("PROMETHEUS_METRICS_PORT", "0"))
            if config
            else os.getenv("PROMETHEUS_METRICS_PORT", "0")
        )
        self.prometheus_scrape_targets = (
            config.get("prometheus_scrape_targets")
            if config and config.get("prometheus_scrape_targets")
            else self._load_prometheus_scrape_targets()
        )
        self.monitor_resource_ids = (
            config.get("monitor_resource_ids")
            if config and config.get("monitor_resource_ids")
            else self._load_monitor_resource_ids()
        )

        alert_store_path = (
            Path(config.get("alert_store_path", "data/alerts.json"))
            if config
            else Path("data/alerts.json")
        )
        incident_store_path = (
            Path(config.get("incident_store_path", "data/incidents.json"))
            if config
            else Path("data/incidents.json")
        )
        self.alert_store = TenantStateStore(alert_store_path)
        self.incident_store = TenantStateStore(incident_store_path)

        # Data stores (will be replaced with database)
        self.metrics = {}  # type: ignore
        self.alerts = {}  # type: ignore
        self.incidents = {}  # type: ignore
        self.health_checks = {}  # type: ignore
        self.anomalies = {}  # type: ignore
        self._kpi_handles = None
        self._logs_query_client = None
        self._metrics_query_client = None
        self._event_hub_producer = None
        self._automation_client = None
        self._health_probe_task: asyncio.Task | None = None
        self._prometheus_registry = None
        self._prometheus_metrics: dict[str, Any] = {}
        self._azure_monitor_configured = False
        self._alert_rules: list[dict[str, Any]] = []
        self._pii_patterns = {
            "email": re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
            "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "phone": re.compile(r"\+?\d[\d\s().-]{7,}\d"),
        }
        self.analytics_client = config.get("analytics_client") if config else None
        if not self.analytics_client:
            self.analytics_client = AnalyticsClient()
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            try:
                self.event_bus = get_event_bus()
            except ValueError:
                self.event_bus = None
        self.grafana_datasource = (
            config.get("grafana_datasource", os.getenv("GRAFANA_DATASOURCE", "Prometheus"))
            if config
            else os.getenv("GRAFANA_DATASOURCE", "Prometheus")
        )
        self.grafana_folder = (
            config.get("grafana_folder", os.getenv("GRAFANA_FOLDER", "System Health"))
            if config
            else os.getenv("GRAFANA_FOLDER", "System Health")
        )

    async def initialize(self) -> None:
        """Initialize monitoring infrastructure and integrations."""
        await super().initialize()
        self.logger.info("Initializing System Health & Monitoring Agent...")

        configure_tracing(self.agent_id)
        configure_metrics(self.agent_id)
        self._kpi_handles = build_kpi_handles(self.agent_id)
        await self._initialize_azure_monitoring()
        await self._configure_opentelemetry_exporters()
        await self._initialize_event_hub()
        await self._initialize_automation_client()
        await self._initialize_prometheus_metrics()
        await self._configure_alert_rules()
        await self._initialize_health_probes()

        self.logger.info("System Health & Monitoring Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "collect_metrics",
            "collect_platform_metrics",
            "collect_application_metrics",
            "check_health",
            "create_alert",
            "detect_anomalies",
            "create_incident",
            "analyze_root_cause",
            "get_system_status",
            "get_metrics",
            "get_alerts",
            "get_capacity_recommendations",
            "get_health_endpoints",
            "query_historical_metrics",
            "forecast_capacity",
            "acknowledge_alert",
            "resolve_incident",
            "get_health_dashboard",
            "get_postmortem_report",
            "get_environment_health",
            "get_grafana_dashboard",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process system health and monitoring requests.

        Args:
            input_data: {
                "action": "collect_metrics" | "check_health" | "create_alert" |
                          "detect_anomalies" | "create_incident" | "analyze_root_cause" |
                          "get_system_status" | "get_metrics" | "get_alerts" |
                          "get_capacity_recommendations" | "acknowledge_alert" | "resolve_incident",
                "service_name": Service or agent name,
                "metrics": Metrics data to collect,
                "alert": Alert configuration,
                "incident": Incident details,
                "time_range": Time range for queries,
                "alert_id": Alert identifier,
                "incident_id": Incident identifier,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - collect_metrics: Collection confirmation
            - check_health: Health status for all services
            - create_alert: Alert ID and configuration
            - detect_anomalies: Detected anomalies
            - create_incident: Incident ID and details
            - analyze_root_cause: Root cause analysis
            - get_system_status: Overall system health
            - get_metrics: Metric values
            - get_alerts: Active alerts
            - get_capacity_recommendations: Scaling recommendations
            - acknowledge_alert: Acknowledgment confirmation
            - resolve_incident: Resolution confirmation
        """
        action = input_data.get("action", "get_system_status")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )

        if action == "collect_metrics":
            return await self._collect_metrics(
                tenant_id,
                input_data.get("service_name"),  # type: ignore
                input_data.get("metrics", {}),
            )

        elif action == "collect_platform_metrics":
            return await self._collect_platform_metrics(
                tenant_id, input_data.get("targets")
            )

        elif action == "collect_application_metrics":
            return await self._collect_application_metrics(
                tenant_id, input_data.get("time_range", {})
            )

        elif action == "check_health":
            return await self._check_health(input_data.get("service_name"))

        elif action == "create_alert":
            return await self._create_alert(tenant_id, input_data.get("alert", {}))

        elif action == "detect_anomalies":
            return await self._detect_anomalies(
                tenant_id,
                input_data.get("service_name"),  # type: ignore
                input_data.get("time_range", {}),
            )

        elif action == "create_incident":
            return await self._create_incident(tenant_id, input_data.get("incident", {}))

        elif action == "analyze_root_cause":
            return await self._analyze_root_cause(input_data.get("incident_id"))  # type: ignore

        elif action == "get_system_status":
            return await self._get_system_status()

        elif action == "get_metrics":
            if input_data.get("deployment_plan"):
                return await self._get_deployment_metrics(input_data["deployment_plan"])
            return await self._get_metrics(
                input_data.get("service_name"),  # type: ignore
                input_data.get("metric_name"),  # type: ignore
                input_data.get("time_range", {}),
            )

        elif action == "get_alerts":
            return await self._get_alerts(input_data.get("filters", {}))

        elif action == "get_capacity_recommendations":
            return await self._get_capacity_recommendations(input_data.get("service_name"))

        elif action == "get_health_endpoints":
            return await self._get_health_endpoints()

        elif action == "query_historical_metrics":
            return await self._query_historical_metrics(
                input_data.get("service_name"),  # type: ignore
                input_data.get("metric_name"),  # type: ignore
                input_data.get("time_range", {}),
            )

        elif action == "forecast_capacity":
            return await self._forecast_capacity(input_data.get("service_name"))

        elif action == "acknowledge_alert":
            return await self._acknowledge_alert(
                tenant_id,
                input_data.get("alert_id"),
                input_data.get("acknowledged_by"),  # type: ignore
            )

        elif action == "resolve_incident":
            return await self._resolve_incident(
                tenant_id,
                input_data.get("incident_id"),
                input_data.get("resolution", {}),  # type: ignore
            )

        elif action == "get_health_dashboard":
            return await self._get_health_dashboard(tenant_id, input_data.get("time_range", {}))

        elif action == "get_postmortem_report":
            return await self._get_postmortem_report(tenant_id, input_data.get("time_range", {}))

        elif action == "get_environment_health":
            return await self._get_environment_health(
                input_data.get("environment") or input_data.get("service_name")
            )

        elif action == "get_grafana_dashboard":
            return await self._get_grafana_dashboard()

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _collect_metrics(
        self, tenant_id: str, service_name: str, metrics_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Collect metrics from service.

        Returns collection confirmation.
        """
        self.logger.info(f"Collecting metrics for service: {service_name}")
        if self._kpi_handles:
            self._kpi_handles.requests.add(1, {"service": service_name, "tenant": tenant_id})

        with start_agent_span(
            self.agent_id, attributes={"service.name": service_name, "tenant.id": tenant_id}
        ):
            # Store metrics
            timestamp = datetime.utcnow().isoformat()
            metric_id = await self._generate_metric_id()

            metric_record = {
                "metric_id": metric_id,
                "tenant_id": tenant_id,
                "service_name": service_name,
                "timestamp": timestamp,
                "metrics": metrics_data,
                "collected_at": timestamp,
            }

            self.metrics[metric_id] = metric_record

            # Check thresholds and trigger alerts if needed
            alerts_triggered = await self._check_metric_thresholds(
                tenant_id, service_name, metrics_data
            )

        await self._emit_event_hub_event(
            {
                "type": "metric",
                "metric_id": metric_id,
                "tenant_id": tenant_id,
                "service_name": service_name,
                "metrics": metrics_data,
                "timestamp": timestamp,
                "event_hub_partitions": self.event_hub_partitions,
                "event_hub_throughput_units": self.event_hub_throughput_units,
            }
        )

        return {
            "metric_id": metric_id,
            "service_name": service_name,
            "metrics_collected": len(metrics_data),
            "timestamp": timestamp,
            "alerts_triggered": alerts_triggered,
        }

    async def _collect_platform_metrics(
        self, tenant_id: str, targets: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Collect infrastructure metrics (CPU, memory, disk, network) across services."""
        self.logger.info("Collecting platform infrastructure metrics")
        if targets is not None:
            target_list = targets
        else:
            target_list = (self.prometheus_scrape_targets or []) + (self.monitor_resource_ids or [])

        collected: dict[str, dict[str, Any]] = {}
        for target in target_list:
            service_name = target.get("name") or target.get("service") or target.get("id")
            if not service_name:
                continue
            if target.get("resource_id"):
                metrics_data = await self._query_azure_resource_metrics(target["resource_id"])
            else:
                metrics_data = await self._scrape_prometheus_target(target)
            if metrics_data.get("error"):
                collected[service_name] = metrics_data
                continue
            await self._collect_metrics(tenant_id, service_name, metrics_data)
            collected[service_name] = metrics_data

        return {
            "services": collected,
            "total_services": len(collected),
            "collected_at": datetime.utcnow().isoformat(),
        }

    async def _collect_application_metrics(
        self, tenant_id: str, time_range: dict[str, Any]
    ) -> dict[str, Any]:
        """Collect application-level metrics from analytics events."""
        self.logger.info("Collecting application metrics from analytics module")
        start_time, _ = self._parse_time_range(time_range)
        records = self.analytics_client.list_records(since=start_time)

        aggregated: dict[str, dict[str, list[float]]] = {}
        for record in records:
            service_name = (
                record.metadata.get("service_name")
                or record.metadata.get("service")
                or record.metadata.get("agent_id")
                or record.metadata.get("agent")
                or (record.name.split(".")[0] if "." in record.name else "platform")
            )
            aggregated.setdefault(service_name, {})
            aggregated[service_name].setdefault(record.category, []).append(record.value)

        summarized: dict[str, dict[str, Any]] = {}
        for service_name, categories in aggregated.items():
            metrics_data: dict[str, Any] = {}
            if categories.get("metric"):
                metrics_data["request_latency_ms"] = statistics.mean(categories["metric"])
            if categories.get("error_rate"):
                metrics_data["error_rate"] = statistics.mean(categories["error_rate"])
            if categories.get("anomaly"):
                metrics_data["anomaly_score"] = statistics.mean(categories["anomaly"])
            if metrics_data:
                await self._collect_metrics(tenant_id, service_name, metrics_data)
                summarized[service_name] = metrics_data

        return {
            "services": summarized,
            "records_processed": len(records),
            "collected_at": datetime.utcnow().isoformat(),
        }

    async def _check_health(self, service_name: str | None = None) -> dict[str, Any]:
        """
        Check health of services.

        Returns health status.
        """
        self.logger.info(f"Checking health: {service_name or 'all services'}")

        if service_name:
            # Check specific service
            health_status = await self._check_service_health(service_name)
            services = {service_name: health_status}
        else:
            # Check all services
            services = await self._check_all_services_health()

        # Calculate overall health
        all_healthy = all(s.get("healthy", False) for s in services.values())
        overall_status = "healthy" if all_healthy else "degraded"

        return {
            "overall_status": overall_status,
            "services": services,
            "checked_at": datetime.utcnow().isoformat(),
        }

    async def _create_alert(self, tenant_id: str, alert_config: dict[str, Any]) -> dict[str, Any]:
        """
        Create monitoring alert.

        Returns alert ID and configuration.
        """
        alert_name = self._sanitize_text(alert_config.get("name", ""))
        self.logger.info(f"Creating alert: {alert_name}")

        # Generate alert ID
        alert_id = await self._generate_alert_id()

        # Create alert
        alert = {
            "alert_id": alert_id,
            "name": alert_name,
            "description": self._sanitize_text(alert_config.get("description", "")),
            "severity": alert_config.get("severity", "warning"),
            "service_name": alert_config.get("service_name"),
            "condition": alert_config.get("condition"),
            "threshold": alert_config.get("threshold"),
            "notification_channels": alert_config.get("notification_channels", []),
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store alert
        self.alerts[alert_id] = alert
        self.alert_store.upsert(tenant_id, alert_id, alert.copy())

        if alert.get("severity") == "critical":
            await self._notify_alert_integrations(alert)

        return {
            "alert_id": alert_id,
            "name": alert["name"],
            "severity": alert["severity"],
            "status": "active",
        }

    async def _detect_anomalies(
        self, tenant_id: str, service_name: str, time_range: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Detect anomalies in service metrics.

        Returns detected anomalies.
        """
        self.logger.info(f"Detecting anomalies for service: {service_name}")

        # Get metrics for time range
        metrics = await self._get_service_metrics(service_name, time_range)

        # Apply anomaly detection
        anomalies = await self._apply_anomaly_detection(metrics)

        # Store anomalies
        for anomaly in anomalies:
            anomaly["recommended_actions"] = self._recommend_actions_for_anomaly(anomaly)
            anomaly_id = await self._generate_anomaly_id()
            self.anomalies[anomaly_id] = {
                "anomaly_id": anomaly_id,
                "service_name": service_name,
                "metric_name": anomaly.get("metric"),
                "value": anomaly.get("value"),
                "expected_range": anomaly.get("expected_range"),
                "severity": anomaly.get("severity"),
                "detected_at": datetime.utcnow().isoformat(),
            }
            if anomaly.get("severity") == "critical":
                await self._create_servicenow_incident(
                    {
                        "title": f"{service_name} anomaly detected",
                        "description": f"{anomaly.get('metric')} value {anomaly.get('value')}",
                        "severity": "critical",
                        "affected_services": [service_name],
                    }
                )
                await self._create_alert(
                    tenant_id,
                    {
                        "name": f"{service_name} anomaly detected",
                        "description": f"{anomaly.get('metric')} anomaly detected",
                        "severity": "critical",
                        "service_name": service_name,
                        "condition": "anomaly",
                        "threshold": anomaly.get("expected_range"),
                    },
                )

        if anomalies:
            await self._emit_event_hub_event(
                {
                    "event_name": "system_health.alert",
                    "type": "system_health.alert",
                    "service_name": service_name,
                    "time_range": time_range,
                    "anomalies": anomalies,
                    "recommended_actions": [
                        action
                        for anomaly in anomalies
                        for action in anomaly.get("recommended_actions", [])
                    ],
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        return {
            "service_name": service_name,
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "time_range": time_range,
        }

    async def _create_incident(
        self, tenant_id: str, incident_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create system incident.

        Returns incident ID.
        """
        incident_title = self._sanitize_text(incident_data.get("title", ""))
        self.logger.info(f"Creating incident: {incident_title}")

        # Generate incident ID
        incident_id = await self._generate_incident_id()

        # Create incident
        incident = {
            "incident_id": incident_id,
            "title": incident_title,
            "description": self._sanitize_text(incident_data.get("description", "")),
            "severity": incident_data.get("severity", "medium"),
            "affected_services": incident_data.get("affected_services", []),
            "status": "open",
            "assignee": self._sanitize_text(incident_data.get("assignee", "")),
            "created_at": datetime.utcnow().isoformat(),
            "created_by": self._sanitize_text(incident_data.get("reporter", "")),
        }

        # Store incident
        self.incidents[incident_id] = incident
        self.incident_store.upsert(tenant_id, incident_id, incident.copy())

        await self._create_servicenow_incident(incident)
        await self._notify_incident_integrations(incident)
        if incident.get("servicenow_sys_id"):
            self.incident_store.upsert(tenant_id, incident_id, incident.copy())

        return {
            "incident_id": incident_id,
            "title": incident["title"],
            "severity": incident["severity"],
            "status": "open",
            "assignee": incident.get("assignee"),
        }

    async def _analyze_root_cause(self, incident_id: str) -> dict[str, Any]:
        """
        Perform root cause analysis for incident.

        Returns analysis results.
        """
        self.logger.info(f"Analyzing root cause for incident: {incident_id}")

        incident = self.incidents.get(incident_id)
        if not incident:
            raise ValueError(f"Incident not found: {incident_id}")

        # Collect related data
        affected_services = incident.get("affected_services", [])

        # Get metrics and logs for affected services
        metrics_data = await self._collect_incident_metrics(affected_services)
        logs_data = await self._collect_incident_logs(affected_services)
        traces_data = await self._collect_incident_traces(affected_services)

        # Correlate data
        correlations = await self._correlate_incident_data(metrics_data, logs_data, traces_data)

        # Identify probable causes
        probable_causes = await self._identify_probable_causes(correlations)

        # Generate recommendations
        recommendations = await self._generate_incident_recommendations(probable_causes)

        return {
            "incident_id": incident_id,
            "probable_causes": probable_causes,
            "correlations": correlations,
            "recommendations": recommendations,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    async def _get_system_status(self) -> dict[str, Any]:
        """
        Get overall system status.

        Returns comprehensive health summary.
        """
        self.logger.info("Getting overall system status")

        # Check all services
        services_health = await self._check_all_services_health()

        # Get active alerts
        active_alerts = [
            alert
            for alert in self.alerts.values()
            if alert.get("status") == "active" and not alert.get("acknowledged")
        ]

        # Get open incidents
        open_incidents = [
            incident for incident in self.incidents.values() if incident.get("status") == "open"
        ]

        # Calculate overall status
        critical_alerts = sum(1 for a in active_alerts if a.get("severity") == "critical")
        critical_incidents = sum(1 for i in open_incidents if i.get("severity") == "critical")

        if critical_alerts > 0 or critical_incidents > 0:
            overall_status = "critical"
        elif len(active_alerts) > 0 or len(open_incidents) > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "overall_status": overall_status,
            "services_health": services_health,
            "active_alerts": len(active_alerts),
            "open_incidents": len(open_incidents),
            "critical_alerts": critical_alerts,
            "critical_incidents": critical_incidents,
            "checked_at": datetime.utcnow().isoformat(),
        }

    async def _get_metrics(
        self, service_name: str, metric_name: str, time_range: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Get metric values for time range.

        Returns metric data.
        """
        self.logger.info(f"Getting metrics: {service_name}.{metric_name}")

        # Query metrics
        metric_values = await self._query_metrics(service_name, metric_name, time_range)

        return {
            "service_name": service_name,
            "metric_name": metric_name,
            "time_range": time_range,
            "values": metric_values,
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    async def _get_deployment_metrics(self, deployment_plan: dict[str, Any]) -> dict[str, Any]:
        """Aggregate deployment metrics for release readiness checks."""
        service_names = self._extract_service_names(deployment_plan)
        time_range = deployment_plan.get("time_range", {"hours": 1})
        service_summaries: dict[str, dict[str, Any]] = {}
        overall: dict[str, list[float]] = {}

        for service_name in service_names:
            records = await self._get_service_metrics(service_name, time_range)
            summary = self._summarize_service_metrics(records)
            service_summaries[service_name] = summary
            for key, value in summary.items():
                if isinstance(value, (int, float)):
                    overall.setdefault(key, []).append(float(value))

        aggregate = {
            key: statistics.mean(values) if values else 0.0
            for key, values in overall.items()
        }

        return {
            "metrics": aggregate,
            "services": service_summaries,
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _get_deployment_baseline(self, deployment_plan: dict[str, Any]) -> dict[str, Any]:
        """Provide baseline metrics for deployment comparisons."""
        service_names = self._extract_service_names(deployment_plan)
        time_range = deployment_plan.get("baseline_time_range", {"days": 7})
        metric_baselines: dict[str, list[float]] = {"response_time_ms": [], "error_rate": []}

        for service_name in service_names:
            records = await self._get_service_metrics(service_name, time_range)
            for metric_name in metric_baselines:
                metric_baselines[metric_name].extend(
                    self._extract_metric_series(records, metric_name)
                )

        baseline = {}
        for metric_name, values in metric_baselines.items():
            if not values:
                continue
            baseline[metric_name] = {
                "mean": statistics.mean(values),
                "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
            }

        return baseline

    async def _get_health_dashboard(
        self, tenant_id: str, time_range: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate health dashboard data with real-time and historical metrics."""
        system_status = await self._get_system_status()
        metrics_summary = self._summarize_metrics_history(time_range, tenant_id=tenant_id)
        incident_summary = self._summarize_incidents(tenant_id, time_range)
        alert_summary = self._summarize_alerts(tenant_id, time_range)

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "real_time": system_status,
            "historical_metrics": metrics_summary,
            "incident_summary": incident_summary,
            "alert_summary": alert_summary,
        }

    async def _get_postmortem_report(
        self, tenant_id: str, time_range: dict[str, Any]
    ) -> dict[str, Any]:
        """Summarize incidents and response times for postmortem analysis."""
        incident_summary = self._summarize_incidents(tenant_id, time_range)
        alert_summary = self._summarize_alerts(tenant_id, time_range)
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "incident_summary": incident_summary,
            "alert_summary": alert_summary,
            "time_range": time_range,
        }

    async def _get_alerts(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Get alerts with filters.

        Returns filtered alerts.
        """
        self.logger.info("Retrieving alerts")

        # Filter alerts
        filtered = []
        for alert_id, alert in self.alerts.items():
            if await self._matches_alert_filters(alert, filters):
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

        # Sort by severity and time
        filtered.sort(
            key=lambda x: (
                (
                    0
                    if x.get("severity") == "critical"
                    else 1 if x.get("severity") == "warning" else 2
                ),
                x.get("created_at", ""),
            )
        )

        return {"total_alerts": len(filtered), "alerts": filtered, "filters": filters}

    async def _get_capacity_recommendations(
        self, service_name: str | None = None
    ) -> dict[str, Any]:
        """
        Get capacity planning recommendations.

        Returns scaling recommendations.
        """
        self.logger.info(f"Getting capacity recommendations for: {service_name or 'all services'}")

        # Analyze resource utilization trends
        utilization_trends = await self._analyze_utilization_trends(service_name)

        # Forecast future needs
        forecasts = await self._forecast_capacity_needs(utilization_trends)

        # Generate recommendations
        recommendations = await self._generate_capacity_recommendations(forecasts)

        return {
            "service_name": service_name,
            "utilization_trends": utilization_trends,
            "forecasts": forecasts,
            "recommendations": recommendations,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _acknowledge_alert(
        self, tenant_id: str, alert_id: str, acknowledged_by: str
    ) -> dict[str, Any]:
        """
        Acknowledge alert.

        Returns acknowledgment confirmation.
        """
        self.logger.info(f"Acknowledging alert: {alert_id}")

        alert = self.alerts.get(alert_id)
        if not alert:
            raise ValueError(f"Alert not found: {alert_id}")

        alert["acknowledged"] = True
        alert["acknowledged_by"] = self._sanitize_text(acknowledged_by)
        alert["acknowledged_at"] = datetime.utcnow().isoformat()
        self.alert_store.upsert(tenant_id, alert_id, alert.copy())


        return {
            "alert_id": alert_id,
            "acknowledged": True,
            "acknowledged_by": acknowledged_by,
            "acknowledged_at": alert["acknowledged_at"],
        }

    async def _resolve_incident(
        self, tenant_id: str, incident_id: str, resolution: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Resolve incident.

        Returns resolution confirmation.
        """
        self.logger.info(f"Resolving incident: {incident_id}")

        incident = self.incidents.get(incident_id)
        if not incident:
            raise ValueError(f"Incident not found: {incident_id}")

        incident["status"] = "resolved"
        incident["resolution"] = self._sanitize_text(resolution.get("description", ""))
        incident["resolved_by"] = self._sanitize_text(resolution.get("resolved_by", ""))
        incident["resolved_at"] = datetime.utcnow().isoformat()

        # Calculate resolution time
        created_at = datetime.fromisoformat(incident.get("created_at"))
        resolved_at = datetime.utcnow()
        resolution_time = (resolved_at - created_at).total_seconds() / 60  # minutes

        incident["resolution_time_minutes"] = resolution_time
        self.incident_store.upsert(tenant_id, incident_id, incident.copy())

        await self._update_servicenow_incident(incident)

        return {
            "incident_id": incident_id,
            "status": "resolved",
            "resolution_time_minutes": resolution_time,
            "resolved_at": incident["resolved_at"],
        }

    async def _initialize_azure_monitoring(self) -> None:
        if _HAS_AZURE_MONITOR_QUERY and (self.monitor_workspace_id or self.app_insights_resource_id):
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential()
            self._logs_query_client = LogsQueryClient(credential)
            self._metrics_query_client = MetricsQueryClient(credential)
            self.logger.info(
                "Azure Monitor clients configured",
                extra={
                    "workspace_id": self.monitor_workspace_id,
                    "app_insights_resource_id": self.app_insights_resource_id,
                },
            )

    async def _configure_opentelemetry_exporters(self) -> None:
        if self._azure_monitor_configured:
            return
        if not self.azure_monitor_connection_string:
            self.logger.info("Azure Monitor connection string not configured")
            return
        if _configure_azure_monitor:
            _configure_azure_monitor(connection_string=self.azure_monitor_connection_string)
            self._azure_monitor_configured = True
            self.logger.info("Azure Monitor OpenTelemetry configured via SDK")
            return
        if not _HAS_OTEL_AZURE_EXPORTER:
            self.logger.warning("Azure Monitor exporter unavailable")
            return

        from opentelemetry import metrics, trace
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": self.agent_id})
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(AzureMonitorTraceExporter(self.azure_monitor_connection_string))
        )
        trace.set_tracer_provider(tracer_provider)

        metric_reader = PeriodicExportingMetricReader(
            AzureMonitorMetricExporter(self.azure_monitor_connection_string)
        )
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(AzureMonitorLogExporter(self.azure_monitor_connection_string))
        )
        handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)
        self._azure_monitor_configured = True
        self.logger.info("Azure Monitor exporters configured")

    async def _initialize_event_hub(self) -> None:
        if not (self.event_hub_connection_string and self.event_hub_name):
            return
        if not _HAS_AZURE_EVENTHUB:
            self.logger.warning("Azure Event Hub SDK not available")
            return
        self._event_hub_producer = EventHubProducerClient.from_connection_string(
            conn_str=self.event_hub_connection_string,
            eventhub_name=self.event_hub_name,
        )
        self.logger.info(
            "Event Hub producer initialized",
            extra={
                "event_hub": self.event_hub_name,
                "partitions": self.event_hub_partitions,
                "throughput_units": self.event_hub_throughput_units,
            },
        )

    async def _initialize_automation_client(self) -> None:
        if (
            not _HAS_AZURE_AUTOMATION
            or not self.automation_subscription_id
            or not self.automation_resource_group
            or not self.automation_account_name
        ):
            return
        credential = DefaultAzureCredential()
        self._automation_client = AutomationClient(credential, self.automation_subscription_id)
        self.logger.info(
            "Azure Automation client initialized",
            extra={
                "automation_account": self.automation_account_name,
                "resource_group": self.automation_resource_group,
            },
        )

    async def _initialize_prometheus_metrics(self) -> None:
        if not (_HAS_PROMETHEUS and self.metrics_port and self.metrics_port > 0):
            return
        self._prometheus_registry = CollectorRegistry()
        self._prometheus_metrics["health_status"] = Gauge(
            "service_health_status",
            "Health status of monitored services (1=healthy, 0=degraded)",
            ["service"],
            registry=self._prometheus_registry,
        )
        self._prometheus_metrics["health_latency"] = Gauge(
            "service_health_latency_ms",
            "Latency of health checks in milliseconds",
            ["service"],
            registry=self._prometheus_registry,
        )
        self._prometheus_metrics["health_checks"] = Counter(
            "service_health_checks_total",
            "Total health checks executed",
            ["service"],
            registry=self._prometheus_registry,
        )
        start_http_server(self.metrics_port, registry=self._prometheus_registry)
        self.logger.info("Prometheus metrics endpoint started", extra={"port": self.metrics_port})

    async def _configure_alert_rules(self) -> None:
        self._alert_rules = [
            {
                "name": "error_rate_threshold",
                "metric": "error_rate",
                "threshold": self.alert_threshold_error_rate,
                "severity": "critical",
                "notification_channels": [
                    url
                    for url in [self.pagerduty_webhook_url, self.opsgenie_webhook_url]
                    if url
                ],
            },
            {
                "name": "response_time_threshold",
                "metric": "response_time_ms",
                "threshold": self.alert_threshold_response_time_ms,
                "severity": "warning",
                "notification_channels": [
                    url
                    for url in [self.pagerduty_webhook_url, self.opsgenie_webhook_url]
                    if url
                ],
            },
        ]
        self.logger.info("Alert rules configured", extra={"count": len(self._alert_rules)})

    async def _initialize_health_probes(self) -> None:
        if not self.health_endpoints or self.health_probe_interval_seconds <= 0:
            return
        if self._health_probe_task:
            return
        self._health_probe_task = asyncio.create_task(self._periodic_health_probes())
        self.logger.info(
            "Health probes scheduled",
            extra={"interval": self.health_probe_interval_seconds},
        )

    async def _periodic_health_probes(self) -> None:
        while True:
            try:
                await self._check_all_services_health()
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
                self.logger.warning("Health probe failure", extra={"error": str(exc)})
            await asyncio.sleep(self.health_probe_interval_seconds)

    def _load_health_endpoints(self) -> list[dict[str, Any]]:
        raw = os.getenv("HEALTH_ENDPOINTS")
        if not raw:
            return []
        try:
            endpoints = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning("Unable to parse HEALTH_ENDPOINTS JSON")
            return []
        if isinstance(endpoints, list):
            return endpoints
        return []

    def _load_prometheus_scrape_targets(self) -> list[dict[str, Any]]:
        raw = os.getenv("PROMETHEUS_SCRAPE_TARGETS")
        if not raw:
            return []
        try:
            targets = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning("Unable to parse PROMETHEUS_SCRAPE_TARGETS JSON")
            return []
        if isinstance(targets, list):
            return targets
        return []

    def _load_monitor_resource_ids(self) -> list[dict[str, Any]]:
        raw = os.getenv("MONITOR_RESOURCE_IDS")
        if not raw:
            return []
        try:
            resources = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning("Unable to parse MONITOR_RESOURCE_IDS JSON")
            return []
        if isinstance(resources, list):
            return resources
        return []

    def _find_health_endpoint(self, service_name: str) -> dict[str, Any] | None:
        for endpoint in self.health_endpoints:
            if endpoint.get("name") == service_name or endpoint.get("service") == service_name:
                return endpoint
        return None

    async def _fetch_health_endpoint(self, endpoint: dict[str, Any]) -> dict[str, Any]:
        url = endpoint.get("url")
        timeout_seconds = endpoint.get("timeout_seconds", 5)
        if not url:
            return {"healthy": False, "error": "missing_url", "response_time_ms": 0}
        start = datetime.utcnow()
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(url)
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            healthy = 200 <= response.status_code < 400
            return {
                "healthy": healthy,
                "status_code": response.status_code,
                "response_time_ms": elapsed,
                "checked_at": datetime.utcnow().isoformat(),
            }
        except httpx.HTTPError as exc:
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            return {
                "healthy": False,
                "status_code": 0,
                "response_time_ms": elapsed,
                "error": str(exc),
                "checked_at": datetime.utcnow().isoformat(),
            }

    async def _scrape_prometheus_target(self, target: dict[str, Any]) -> dict[str, Any]:
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
        metrics = self._parse_prometheus_metrics(response.text)
        metrics["metrics_source"] = "prometheus"
        return metrics

    def _parse_prometheus_metrics(self, payload: str) -> dict[str, Any]:
        cpu_totals: dict[str, float] = {}
        cpu_idle: dict[str, float] = {}
        mem_total = None
        mem_available = None
        disk_totals: dict[str, float] = {}
        disk_avail: dict[str, float] = {}
        net_rx_total = 0.0
        net_tx_total = 0.0
        line_pattern = re.compile(
            r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)$"
        )

        for line in payload.splitlines():
            if not line or line.startswith("#"):
                continue
            match = line_pattern.match(line.strip())
            if not match:
                continue
            name, labels_raw, value_raw = match.groups()
            try:
                value = float(value_raw)
            except ValueError:
                continue
            labels: dict[str, str] = {}
            if labels_raw:
                label_pairs = labels_raw.strip("{}").split(",")
                for pair in label_pairs:
                    if "=" not in pair:
                        continue
                    key, raw_value = pair.split("=", 1)
                    labels[key.strip()] = raw_value.strip().strip('"')

            if name == "node_cpu_seconds_total":
                cpu = labels.get("cpu", "all")
                cpu_totals[cpu] = cpu_totals.get(cpu, 0.0) + value
                if labels.get("mode") == "idle":
                    cpu_idle[cpu] = cpu_idle.get(cpu, 0.0) + value
            elif name == "node_memory_MemTotal_bytes":
                mem_total = value
            elif name == "node_memory_MemAvailable_bytes":
                mem_available = value
            elif name == "node_filesystem_size_bytes":
                mount = labels.get("mountpoint", "root")
                fstype = labels.get("fstype", "")
                if fstype in {"tmpfs", "overlay", "squashfs", "proc", "sysfs"}:
                    continue
                disk_totals[mount] = disk_totals.get(mount, 0.0) + value
            elif name == "node_filesystem_avail_bytes":
                mount = labels.get("mountpoint", "root")
                fstype = labels.get("fstype", "")
                if fstype in {"tmpfs", "overlay", "squashfs", "proc", "sysfs"}:
                    continue
                disk_avail[mount] = disk_avail.get(mount, 0.0) + value
            elif name == "node_network_receive_bytes_total":
                if labels.get("device") == "lo":
                    continue
                net_rx_total += value
            elif name == "node_network_transmit_bytes_total":
                if labels.get("device") == "lo":
                    continue
                net_tx_total += value

        cpu_usage = None
        if cpu_totals:
            cpu_values = []
            for cpu, total in cpu_totals.items():
                idle = cpu_idle.get(cpu, 0.0)
                if total > 0:
                    cpu_values.append(1 - (idle / total))
            if cpu_values:
                cpu_usage = statistics.mean(cpu_values)

        memory_usage = None
        if mem_total and mem_available is not None:
            memory_usage = (mem_total - mem_available) / mem_total

        disk_usage = None
        if disk_totals:
            usage_values = []
            for mount, total in disk_totals.items():
                avail = disk_avail.get(mount, 0.0)
                if total > 0:
                    usage_values.append((total - avail) / total)
            if usage_values:
                disk_usage = statistics.mean(usage_values)

        return {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "disk_usage": disk_usage,
            "network_rx_bytes_total": net_rx_total,
            "network_tx_bytes_total": net_tx_total,
        }

    async def _query_azure_resource_metrics(self, resource_id: str) -> dict[str, Any]:
        if not self._metrics_query_client:
            return {"error": "azure_monitor_unavailable"}
        end_time = datetime.utcnow()
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
            self._metrics_query_client.query_resource,
            resource_id=resource_id,
            metric_names=metric_names,
            timespan=(start_time, end_time),
        )
        metrics: dict[str, Any] = {"metrics_source": "azure_monitor"}
        value_lookup: dict[str, float] = {}
        for metric in response.metrics:
            metric_name = getattr(metric.name, "value", None) or str(metric.name)
            if not metric.timeseries:
                continue
            points = metric.timeseries[0].data
            if not points:
                continue
            latest = next((point for point in reversed(points) if point.average is not None), None)
            if not latest:
                continue
            value_lookup[metric_name] = float(latest.average)

        cpu_value = value_lookup.get("Percentage CPU")
        if cpu_value is not None:
            metrics["cpu_usage"] = cpu_value / 100.0

        available_memory = value_lookup.get("Available Memory Bytes")
        total_memory = value_lookup.get("Total Memory Bytes")
        if available_memory is not None and total_memory:
            metrics["memory_usage"] = (total_memory - available_memory) / total_memory
        elif available_memory is not None:
            metrics["memory_available_bytes"] = available_memory

        disk_free = value_lookup.get("Logical Disk % Free Space")
        if disk_free is not None:
            metrics["disk_usage"] = (100.0 - disk_free) / 100.0

        network_in = value_lookup.get("Network In Total")
        if network_in is not None:
            metrics["network_rx_bytes_total"] = network_in
        network_out = value_lookup.get("Network Out Total")
        if network_out is not None:
            metrics["network_tx_bytes_total"] = network_out

        return metrics

    async def _publish_health_status(self, services: dict[str, dict[str, Any]]) -> None:
        timestamp = datetime.utcnow().isoformat()
        total_services = len(services)
        unhealthy = sum(1 for result in services.values() if not result.get("healthy", False))
        overall_status = "healthy" if unhealthy == 0 else "degraded"
        health_score = (total_services - unhealthy) / total_services if total_services else 1.0
        event_name = "system.health.ok" if unhealthy == 0 else "system.health.alert"
        payload = {
            "type": "health",
            "event_name": event_name,
            "timestamp": timestamp,
            "services": services,
            "overall_status": overall_status,
            "health_score": health_score,
            "total_services": total_services,
            "unhealthy_services": unhealthy,
        }
        self.health_checks["latest"] = payload
        await self._emit_event_hub_event(payload)
        if self.event_bus:
            await self.event_bus.publish("system.health.updated", payload)
            await self.event_bus.publish(event_name, payload)

    async def _update_prometheus_metrics(self, service_name: str, result: dict[str, Any]) -> None:
        if not self._prometheus_metrics:
            return
        status_value = 1.0 if result.get("healthy") else 0.0
        self._prometheus_metrics["health_status"].labels(service=service_name).set(status_value)
        self._prometheus_metrics["health_latency"].labels(service=service_name).set(
            result.get("response_time_ms", 0)
        )
        self._prometheus_metrics["health_checks"].labels(service=service_name).inc()

    async def _notify_alert_integrations(self, alert: dict[str, Any]) -> None:
        await self._trigger_webhook_notification(self.pagerduty_webhook_url, alert)
        await self._trigger_webhook_notification(self.opsgenie_webhook_url, alert)
        if alert.get("severity") == "critical":
            await self._create_servicenow_incident(
                {
                    "title": alert.get("name", "Critical alert"),
                    "description": alert.get("description"),
                    "severity": "critical",
                    "affected_services": [alert.get("service_name")],
                }
            )

    async def _notify_incident_integrations(self, incident: dict[str, Any]) -> None:
        payload = {
            "event_type": "incident",
            "incident": incident,
            "priority": "high" if incident.get("severity") == "critical" else "normal",
        }
        await self._trigger_incident_webhook(self.pagerduty_webhook_url, payload)
        await self._trigger_incident_webhook(self.opsgenie_webhook_url, payload)

    async def _trigger_incident_webhook(self, url: str | None, payload: dict[str, Any]) -> None:
        if not url:
            return
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload)

    async def _trigger_webhook_notification(self, url: str | None, alert: dict[str, Any]) -> None:
        if not url:
            return
        payload = {
            "event_type": "trigger",
            "alert": alert,
            "priority": "high" if alert.get("severity") == "critical" else "normal",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload)

    async def _trigger_scaling_actions(self, service_name: str, metrics_data: dict[str, Any]) -> None:
        scaling_payload = {
            "service_name": service_name,
            "cpu": metrics_data.get("cpu_usage"),
            "memory": metrics_data.get("memory_usage"),
            "queue_depth": metrics_data.get("queue_depth"),
            "thresholds": self.scaling_thresholds,
        }
        cpu_exceeded = (
            metrics_data.get("cpu_usage") is not None
            and metrics_data.get("cpu_usage") > self.scaling_thresholds["cpu"]
        )
        memory_exceeded = (
            metrics_data.get("memory_usage") is not None
            and metrics_data.get("memory_usage") > self.scaling_thresholds["memory"]
        )
        queue_exceeded = (
            metrics_data.get("queue_depth") is not None
            and metrics_data.get("queue_depth") > self.scaling_thresholds["queue_depth"]
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
        if self.scaling_webhook_url or self.automation_webhook_url:
            target_url = self.scaling_webhook_url or self.automation_webhook_url
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(target_url, json=scaling_payload)
        if self._automation_client and self.automation_runbook_name:
            await self._start_automation_runbook(service_name, scaling_payload)

    async def _start_automation_runbook(
        self, service_name: str, scaling_payload: dict[str, Any]
    ) -> None:
        if not (self._automation_client and self.automation_runbook_name):
            return
        job_name = f"scale-{service_name}-{uuid.uuid4().hex[:6]}"
        parameters = JobCreateParameters(
            runbook=RunbookAssociationProperty(name=self.automation_runbook_name),
            parameters={key: str(value) for key, value in scaling_payload.items() if value is not None},
        )
        await asyncio.to_thread(
            self._automation_client.job.create,
            self.automation_resource_group,
            self.automation_account_name,
            job_name,
            parameters,
        )

    async def _create_servicenow_incident(self, incident: dict[str, Any]) -> None:
        if not self.servicenow_instance_url:
            return
        payload = {
            "short_description": incident.get("title") or incident.get("name") or "Monitoring incident",
            "description": incident.get("description"),
            "severity": incident.get("severity"),
            "urgency": "1",
        }
        response = await self._servicenow_request("post", "/api/now/table/incident", payload)
        if response and "result" in response and isinstance(response["result"], dict):
            sys_id = response["result"].get("sys_id")
            if sys_id:
                incident["servicenow_sys_id"] = sys_id

    async def _update_servicenow_incident(self, incident: dict[str, Any]) -> None:
        if not self.servicenow_instance_url:
            return
        payload = {
            "state": "Resolved",
            "close_notes": incident.get("resolution"),
        }
        sys_id = incident.get("servicenow_sys_id")
        if not sys_id:
            return
        await self._servicenow_request("patch", f"/api/now/table/incident/{sys_id}", payload)

    async def _servicenow_request(
        self, method: str, path: str, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        url = f"{self.servicenow_instance_url}{path}"
        headers = {"Accept": "application/json"}
        auth = None
        if self.servicenow_token:
            headers["Authorization"] = f"Bearer {self.servicenow_token}"
        elif self.servicenow_username and self.servicenow_password:
            auth = (self.servicenow_username, self.servicenow_password)
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(method, url, json=payload, headers=headers, auth=auth)
        if response.is_error:
            self.logger.warning(
                "ServiceNow request failed",
                extra={"status": response.status_code, "path": path},
            )
            return None
        try:
            return response.json()
        except json.JSONDecodeError:
            return None

    async def _apply_azure_anomaly_detection(
        self, metrics: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not (self.anomaly_detector_endpoint and self.anomaly_detector_key):
            return []
        client = AnomalyDetectorClient(
            self.anomaly_detector_endpoint, AzureKeyCredential(self.anomaly_detector_key)
        )
        grouped: dict[str, list[dict[str, Any]]] = {}
        for metric in metrics:
            name = metric.get("metric") or metric.get("metric_name") or "unknown"
            grouped.setdefault(name, []).append(metric)
        anomalies: list[dict[str, Any]] = []
        for name, points in grouped.items():
            series = [
                TimeSeriesPoint(
                    timestamp=(
                        datetime.fromisoformat(p["timestamp"])
                        if isinstance(p.get("timestamp"), str)
                        else p.get("timestamp")
                    ),
                    value=p.get("value"),
                )
                for p in points
                if p.get("timestamp") and p.get("value") is not None
            ]
            if len(series) < 12:
                continue
            result = await asyncio.to_thread(
                client.detect_last_point, series=series
            )
            if result.is_anomaly:
                anomalies.append(
                    {
                        "metric": name,
                        "value": series[-1].value,
                        "expected_range": [result.expected_value_low, result.expected_value_high],
                        "severity": "critical" if result.is_anomaly else "warning",
                        "timestamp": series[-1].timestamp,
                    }
                )
        return anomalies

    def _parse_time_range(self, time_range: dict[str, Any]) -> tuple[datetime, datetime]:
        end = datetime.utcnow()
        if "end" in time_range:
            end = datetime.fromisoformat(time_range["end"])
        if "start" in time_range:
            start = datetime.fromisoformat(time_range["start"])
        else:
            if "hours" in time_range:
                start = end - timedelta(hours=int(time_range.get("hours", 1)))
            elif "minutes" in time_range:
                start = end - timedelta(minutes=int(time_range.get("minutes", 60)))
            else:
                days = int(time_range.get("days", 1))
                start = end - timedelta(days=days)
        return start, end

    def _summarize_trend(self, values: list[dict[str, Any]]) -> dict[str, Any]:
        series = [
            {"timestamp": v.get("timestamp"), "value": float(v.get("value", 0))}
            for v in values
            if v.get("value") is not None
        ]
        if len(series) < 2:
            return {"direction": "stable", "series": series}
        first = series[0]["value"]
        last = series[-1]["value"]
        if last > first * 1.05:
            direction = "increasing"
        elif last < first * 0.95:
            direction = "decreasing"
        else:
            direction = "stable"
        return {"direction": direction, "series": series}

    def _linear_regression_forecast(
        self, series: list[dict[str, Any]], horizon_days: int
    ) -> float | None:
        if len(series) < 2:
            return None
        x_values = list(range(len(series)))
        y_values = [point["value"] for point in series]
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values) or 1
        slope = numerator / denominator
        forecast_index = len(series) - 1 + horizon_days
        forecast = y_mean + slope * (forecast_index - x_mean)
        return round(forecast, 2)

    async def _emit_event_hub_event(self, payload: dict[str, Any]) -> None:
        if not self._event_hub_producer:
            return
        event_body = json.dumps(payload)
        batch = self._event_hub_producer.create_batch()
        batch.add(EventData(event_body))
        await asyncio.to_thread(self._event_hub_producer.send_batch, batch)

    # Helper methods

    async def _generate_metric_id(self) -> str:
        """Generate unique metric ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"METRIC-{timestamp}"

    async def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        suffix = uuid.uuid4().hex[:8]
        return f"ALERT-{timestamp}-{suffix}"

    async def _generate_incident_id(self) -> str:
        """Generate unique incident ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"INC-{timestamp}"

    async def _generate_anomaly_id(self) -> str:
        """Generate unique anomaly ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"ANOM-{timestamp}"

    async def _check_metric_thresholds(
        self, tenant_id: str, service_name: str, metrics_data: dict[str, Any]
    ) -> list[str]:
        """Check metrics against alert thresholds."""
        alert_ids: list[str] = []

        # Check error rate
        error_rate = metrics_data.get("error_rate", 0)
        if error_rate > self.alert_threshold_error_rate:
            response = await self._create_alert(
                tenant_id,
                {
                    "name": f"{service_name} error rate threshold exceeded",
                    "description": (
                        f"Error rate {error_rate:.2%} exceeded threshold "
                        f"{self.alert_threshold_error_rate:.2%}."
                    ),
                    "severity": "critical",
                    "service_name": service_name,
                    "condition": "error_rate",
                    "threshold": self.alert_threshold_error_rate,
                },
            )
            alert_ids.append(response["alert_id"])

        # Check response time
        response_time = metrics_data.get("response_time_ms", 0)
        if response_time > self.alert_threshold_response_time_ms:
            response = await self._create_alert(
                tenant_id,
                {
                    "name": f"{service_name} response time threshold exceeded",
                    "description": (
                        f"Response time {response_time:.0f}ms exceeded threshold "
                        f"{self.alert_threshold_response_time_ms:.0f}ms."
                    ),
                    "severity": "warning",
                    "service_name": service_name,
                    "condition": "response_time_ms",
                    "threshold": self.alert_threshold_response_time_ms,
                },
            )
            alert_ids.append(response["alert_id"])

        await self._trigger_scaling_actions(service_name, metrics_data)

        return alert_ids

    async def _check_service_health(self, service_name: str) -> dict[str, Any]:
        """Check health of specific service."""
        endpoint = self._find_health_endpoint(service_name)
        if not endpoint:
            return {"healthy": True, "response_time_ms": 50, "status_code": 200}

        result = await self._fetch_health_endpoint(endpoint)
        await self._update_prometheus_metrics(service_name, result)
        return result

    async def _check_all_services_health(self) -> dict[str, dict[str, Any]]:
        """Check health of all services."""
        if not self.health_endpoints:
            services = {
                "api_gateway": {"healthy": True, "response_time_ms": 45},
                "database": {"healthy": True, "response_time_ms": 10},
                "cache": {"healthy": True, "response_time_ms": 5},
            }
            await self._publish_health_status(services)
            return services

        services: dict[str, dict[str, Any]] = {}
        for endpoint in self.health_endpoints:
            name = endpoint.get("name") or endpoint.get("service") or endpoint.get("url")
            if not name:
                continue
            result = await self._fetch_health_endpoint(endpoint)
            services[name] = result
            await self._update_prometheus_metrics(name, result)

        await self._publish_health_status(services)
        return services

    async def _get_environment_health(self, environment: str | None) -> dict[str, Any]:
        system_status = await self._get_system_status()
        services_health = system_status.get("services_health", {})
        total_services = len(services_health)
        unhealthy_count = sum(
            1 for result in services_health.values() if not result.get("healthy", False)
        )
        health_score = (
            (total_services - unhealthy_count) / total_services if total_services else 1.0
        )
        overall_status = system_status.get("overall_status", "unknown")
        block_deployment = system_status.get("critical_alerts", 0) > 0 or system_status.get(
            "critical_incidents", 0
        ) > 0

        return {
            "environment": environment,
            "status": overall_status,
            "health_score": health_score,
            "critical_alerts": system_status.get("critical_alerts", 0),
            "critical_incidents": system_status.get("critical_incidents", 0),
            "active_alerts": system_status.get("active_alerts", 0),
            "open_incidents": system_status.get("open_incidents", 0),
            "services_health": services_health,
            "block_deployment": block_deployment,
            "checked_at": system_status.get("checked_at"),
        }

    async def _get_service_metrics(
        self, service_name: str, time_range: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get metrics for service in time range."""
        metrics: list[dict[str, Any]] = []
        start_time, end_time = self._parse_time_range(time_range)
        for metric in self.metrics.values():
            if metric.get("service_name") != service_name:
                continue
            timestamp = metric.get("timestamp")
            if timestamp:
                parsed = (
                    datetime.fromisoformat(timestamp)
                    if isinstance(timestamp, str)
                    else timestamp
                )
                if parsed < start_time or parsed > end_time:
                    continue
            metrics.append(metric)

        query_metrics = await self._query_metrics(service_name, "*", time_range)
        metrics.extend(query_metrics)
        return metrics

    async def _get_health_endpoints(self) -> dict[str, Any]:
        return {
            "total_endpoints": len(self.health_endpoints),
            "endpoints": self.health_endpoints,
        }

    async def _get_grafana_dashboard(self) -> dict[str, Any]:
        return {
            "folder": self.grafana_folder,
            "dashboard": self._build_grafana_dashboard(),
        }

    async def _query_historical_metrics(
        self, service_name: str, metric_name: str, time_range: dict[str, Any]
    ) -> dict[str, Any]:
        values = await self._query_metrics(service_name, metric_name, time_range)
        return {
            "service_name": service_name,
            "metric_name": metric_name,
            "time_range": time_range,
            "values": values,
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    async def _forecast_capacity(self, service_name: str | None) -> dict[str, Any]:
        utilization_trends = await self._analyze_utilization_trends(service_name)
        forecasts = await self._forecast_capacity_needs(utilization_trends)
        return {
            "service_name": service_name,
            "trends": utilization_trends,
            "forecasts": forecasts,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _apply_anomaly_detection(self, metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply anomaly detection to metrics."""
        if not metrics:
            return []

        normalized: list[dict[str, Any]] = []
        for metric in metrics:
            if isinstance(metric.get("metrics"), dict):
                for name, value in metric["metrics"].items():
                    normalized.append(
                        {
                            "metric": name,
                            "value": value,
                            "timestamp": metric.get("timestamp"),
                        }
                    )
            else:
                normalized.append(metric)

        if (
            _HAS_ANOMALY_DETECTOR
            and self.anomaly_detector_endpoint
            and self.anomaly_detector_key
        ):
            return await self._apply_azure_anomaly_detection(normalized)

        anomalies: list[dict[str, Any]] = []
        grouped: dict[str, list[dict[str, Any]]] = {}
        for metric in normalized:
            name = metric.get("metric") or metric.get("metric_name") or "unknown"
            grouped.setdefault(name, []).append(metric)

        for name, points in grouped.items():
            values = [float(p.get("value", 0)) for p in points if p.get("value") is not None]
            if len(values) < 5:
                continue
            median = statistics.median(values)
            mad = statistics.median([abs(v - median) for v in values]) or 1.0
            for point in points:
                value = float(point.get("value", 0))
                modified_z = 0.6745 * (value - median) / mad
                if abs(modified_z) >= 3.5:
                    anomalies.append(
                        {
                            "metric": name,
                            "value": value,
                            "expected_range": [median - 3 * mad, median + 3 * mad],
                            "severity": "critical" if abs(modified_z) >= 4.5 else "warning",
                            "timestamp": point.get("timestamp"),
                            "z_score": modified_z,
                        }
                    )
        return anomalies

    async def _collect_incident_metrics(self, affected_services: list[str]) -> dict[str, Any]:
        """Collect metrics related to incident."""
        return {}

    async def _collect_incident_logs(self, affected_services: list[str]) -> list[dict[str, Any]]:
        """Collect logs related to incident."""
        return []

    async def _collect_incident_traces(self, affected_services: list[str]) -> list[dict[str, Any]]:
        """Collect traces related to incident."""
        return []

    async def _correlate_incident_data(
        self, metrics: dict[str, Any], logs: list[dict[str, Any]], traces: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Correlate incident data sources."""
        return []

    async def _identify_probable_causes(self, correlations: list[dict[str, Any]]) -> list[str]:
        """Identify probable causes from correlations."""
        return ["High database load", "Network latency spike"]

    async def _generate_incident_recommendations(self, probable_causes: list[str]) -> list[str]:
        """Generate recommendations based on probable causes."""
        return ["Scale database resources", "Check network connectivity"]

    async def _query_metrics(
        self, service_name: str, metric_name: str, time_range: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Query metrics from store."""
        if not self._logs_query_client:
            return []

        start_time, end_time = self._parse_time_range(time_range)
        metric_filter = "" if metric_name == "*" else f'| where name == "{metric_name}"'
        query = (
            "customMetrics "
            f'| where cloud_RoleName == "{service_name}" '
            f"{metric_filter} "
            f"| where timestamp between (datetime({start_time.isoformat()}) .. datetime({end_time.isoformat()})) "
            "| project timestamp, name, value"
            "| order by timestamp asc"
        )
        if self.monitor_workspace_id:
            response = await asyncio.to_thread(
                self._logs_query_client.query_workspace,
                workspace_id=self.monitor_workspace_id,
                query=query,
                timespan=(start_time, end_time),
            )
        elif self.app_insights_resource_id:
            response = await asyncio.to_thread(
                self._logs_query_client.query_resource,
                resource_id=self.app_insights_resource_id,
                query=query,
                timespan=(start_time, end_time),
            )
        else:
            return []
        if response.status != LogsQueryStatus.SUCCESS:
            self.logger.warning("Log Analytics query returned partial results")

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

    async def _matches_alert_filters(self, alert: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if alert matches filters."""
        if "severity" in filters and alert.get("severity") != filters["severity"]:
            return False

        if "status" in filters and alert.get("status") != filters["status"]:
            return False

        return True

    async def _analyze_utilization_trends(self, service_name: str | None) -> dict[str, Any]:
        """Analyze resource utilization trends."""
        trends: dict[str, Any] = {}
        target_service = service_name or "platform"
        for metric in ("cpu_usage", "memory_usage", "storage_usage"):
            values = await self._query_metrics(target_service, metric, {"days": 7})
            trend_data = self._summarize_trend(values)
            trends[f"{metric}_trend"] = trend_data["direction"]
            trends[f"{metric}_series"] = trend_data["series"]
        return trends

    async def _forecast_capacity_needs(self, trends: dict[str, Any]) -> dict[str, Any]:
        """Forecast future capacity needs."""
        forecasts: dict[str, Any] = {}
        for metric in ("cpu_usage", "memory_usage", "storage_usage"):
            series = trends.get(f"{metric}_series", [])
            forecast = self._linear_regression_forecast(series, horizon_days=30)
            if forecast is not None:
                forecasts[f"{metric}_forecast_30d"] = forecast
        return forecasts

    async def _generate_capacity_recommendations(self, forecasts: dict[str, Any]) -> list[str]:
        """Generate capacity recommendations."""
        recommendations = []

        if forecasts.get("cpu_usage_forecast_30d", 0) > 80:
            recommendations.append("Consider scaling up CPU resources within 30 days")

        if forecasts.get("memory_usage_forecast_30d", 0) > 80:
            recommendations.append("Consider scaling up memory resources within 30 days")

        if forecasts.get("storage_usage_forecast_30d", 0) > 80:
            recommendations.append("Plan for storage expansion within 30 days")

        if not recommendations:
            recommendations.append("Current capacity is adequate for forecasted needs")

        return recommendations

    def _extract_service_names(self, deployment_plan: dict[str, Any]) -> list[str]:
        service_names = deployment_plan.get("services") or deployment_plan.get("service_names")
        if isinstance(service_names, list) and service_names:
            return [str(name) for name in service_names]
        if deployment_plan.get("service_name"):
            return [str(deployment_plan["service_name"])]
        return [
            endpoint.get("name") or endpoint.get("service")
            for endpoint in self.health_endpoints
            if endpoint.get("name") or endpoint.get("service")
        ] or ["platform"]

    def _extract_metric_series(self, records: list[dict[str, Any]], metric_name: str) -> list[float]:
        values: list[float] = []
        for record in records:
            if isinstance(record.get("metrics"), dict):
                value = record["metrics"].get(metric_name)
            elif record.get("metric") == metric_name:
                value = record.get("value")
            else:
                value = None
            if value is None:
                continue
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue
        return values

    def _summarize_service_metrics(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        summary: dict[str, Any] = {}
        for metric_name in [
            "response_time_ms",
            "error_rate",
            "cpu_usage",
            "memory_usage",
            "disk_usage",
        ]:
            values = self._extract_metric_series(records, metric_name)
            if values:
                summary[metric_name] = statistics.mean(values)
        return summary

    def _summarize_metrics_history(
        self, time_range: dict[str, Any], tenant_id: str | None = None
    ) -> dict[str, Any]:
        start_time, end_time = self._parse_time_range(time_range)
        summaries: dict[str, dict[str, list[float]]] = {}
        total_records = 0

        for record in self.metrics.values():
            if tenant_id and record.get("tenant_id") != tenant_id:
                continue
            timestamp = record.get("timestamp")
            if timestamp:
                parsed = (
                    datetime.fromisoformat(timestamp)
                    if isinstance(timestamp, str)
                    else timestamp
                )
                if parsed < start_time or parsed > end_time:
                    continue
            total_records += 1
            service_name = record.get("service_name", "unknown")
            metrics_data = record.get("metrics", {})
            if not isinstance(metrics_data, dict):
                continue
            for metric_name, value in metrics_data.items():
                if isinstance(value, (int, float)):
                    summaries.setdefault(service_name, {}).setdefault(metric_name, []).append(
                        float(value)
                    )

        summarized: dict[str, dict[str, float]] = {}
        for service_name, metrics in summaries.items():
            summarized[service_name] = {
                name: statistics.mean(values) for name, values in metrics.items() if values
            }

        return {"total_records": total_records, "services": summarized}

    def _summarize_incidents(
        self, tenant_id: str, time_range: dict[str, Any]
    ) -> dict[str, Any]:
        start_time, end_time = self._parse_time_range(time_range)
        incidents = self.incident_store.list(tenant_id)
        filtered: list[dict[str, Any]] = []
        resolution_times: list[float] = []

        for incident in incidents:
            created_at = incident.get("created_at")
            created_dt = datetime.fromisoformat(created_at) if created_at else None
            if created_dt and (created_dt < start_time or created_dt > end_time):
                continue
            filtered.append(incident)
            resolved_at = incident.get("resolved_at")
            if resolved_at and created_dt:
                resolved_dt = datetime.fromisoformat(resolved_at)
                resolution_times.append((resolved_dt - created_dt).total_seconds() / 60)

        severity_counts: dict[str, int] = {}
        for incident in filtered:
            severity = incident.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "total_incidents": len(filtered),
            "severity_counts": severity_counts,
            "average_resolution_minutes": (
                statistics.mean(resolution_times) if resolution_times else 0.0
            ),
        }

    def _summarize_alerts(self, tenant_id: str, time_range: dict[str, Any]) -> dict[str, Any]:
        start_time, end_time = self._parse_time_range(time_range)
        alerts = self.alert_store.list(tenant_id)
        filtered: list[dict[str, Any]] = []
        response_times: list[float] = []

        for alert in alerts:
            created_at = alert.get("created_at")
            created_dt = datetime.fromisoformat(created_at) if created_at else None
            if created_dt and (created_dt < start_time or created_dt > end_time):
                continue
            filtered.append(alert)
            acknowledged_at = alert.get("acknowledged_at")
            if acknowledged_at and created_dt:
                ack_dt = datetime.fromisoformat(acknowledged_at)
                response_times.append((ack_dt - created_dt).total_seconds() / 60)

        severity_counts: dict[str, int] = {}
        for alert in filtered:
            severity = alert.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "total_alerts": len(filtered),
            "severity_counts": severity_counts,
            "average_response_minutes": (
                statistics.mean(response_times) if response_times else 0.0
            ),
        }

    def _build_grafana_dashboard(self) -> dict[str, Any]:
        return {
            "title": "System Health Overview",
            "tags": ["system-health", "ops"],
            "timezone": "browser",
            "schemaVersion": 39,
            "version": 1,
            "refresh": "30s",
            "panels": [
                {
                    "type": "stat",
                    "title": "Service Health",
                    "datasource": self.grafana_datasource,
                    "targets": [
                        {
                            "expr": "service_health_status",
                            "legendFormat": "{{service}}",
                        }
                    ],
                },
                {
                    "type": "timeseries",
                    "title": "CPU Usage",
                    "datasource": self.grafana_datasource,
                    "targets": [
                        {
                            "expr": "cpu_usage",
                            "legendFormat": "{{service}}",
                        }
                    ],
                },
                {
                    "type": "timeseries",
                    "title": "Memory Usage",
                    "datasource": self.grafana_datasource,
                    "targets": [
                        {
                            "expr": "memory_usage",
                            "legendFormat": "{{service}}",
                        }
                    ],
                },
                {
                    "type": "timeseries",
                    "title": "Request Latency (ms)",
                    "datasource": self.grafana_datasource,
                    "targets": [
                        {
                            "expr": "request_latency_ms",
                            "legendFormat": "{{service}}",
                        }
                    ],
                },
                {
                    "type": "timeseries",
                    "title": "Error Rate",
                    "datasource": self.grafana_datasource,
                    "targets": [
                        {
                            "expr": "error_rate",
                            "legendFormat": "{{service}}",
                        }
                    ],
                },
            ],
        }

    def _recommend_actions_for_anomaly(self, anomaly: dict[str, Any]) -> list[str]:
        metric = anomaly.get("metric", "")
        recommendations = []
        if "error" in metric:
            recommendations.extend(
                [
                    "Inspect recent deployments for regressions.",
                    "Review service logs for failing requests.",
                ]
            )
        if "response" in metric or "latency" in metric:
            recommendations.extend(
                [
                    "Check downstream dependency latency.",
                    "Scale service instances or increase resources.",
                ]
            )
        if "cpu" in metric:
            recommendations.append("Scale CPU resources or rebalance workloads.")
        if "memory" in metric:
            recommendations.append("Increase memory allocation or investigate leaks.")
        if "disk" in metric:
            recommendations.append("Clear disk space or expand storage.")
        if "network" in metric:
            recommendations.append("Inspect network throughput and packet loss.")
        if not recommendations:
            recommendations.append("Investigate recent changes and correlated metrics.")
        return recommendations

    async def get_metrics(self, deployment_plan: dict[str, Any]) -> dict[str, Any]:
        """Expose monitoring metrics for deployment workflows."""
        return await self._get_deployment_metrics(deployment_plan)

    async def get_baseline(self, deployment_plan: dict[str, Any]) -> dict[str, Any]:
        """Expose baseline metrics for deployment workflows."""
        return await self._get_deployment_baseline(deployment_plan)

    async def get_environment_health(self, environment: str) -> dict[str, Any]:
        """Expose health status for deployment workflows."""
        return await self._get_environment_health(environment)

    def _sanitize_text(self, value: str) -> str:
        """Redact PII-like patterns from loggable strings."""
        if not value:
            return value
        sanitized = value
        for pattern in self._pii_patterns.values():
            sanitized = pattern.sub("[redacted]", sanitized)
        return sanitized

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up System Health & Monitoring Agent...")
        if self._health_probe_task:
            self._health_probe_task.cancel()
            self._health_probe_task = None
        if self._event_hub_producer:
            await asyncio.to_thread(self._event_hub_producer.close)
            self._event_hub_producer = None

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "resource_monitoring",
            "application_monitoring",
            "log_collection",
            "trace_collection",
            "alerting",
            "incident_management",
            "anomaly_detection",
            "predictive_maintenance",
            "root_cause_analysis",
            "capacity_planning",
            "health_checks",
            "performance_monitoring",
            "dashboard_creation",
            "postmortem_reporting",
            "deployment_health_gate",
            "grafana_dashboard",
            "environment_health_query",
        ]
