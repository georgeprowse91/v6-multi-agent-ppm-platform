"""
System Health & Monitoring Agent

Purpose:
Ensures the operational reliability, performance and availability of the PPM platform through
comprehensive monitoring, alerting, and proactive maintenance.

Specification: agents/operations-management/system-health-agent/README.md
"""

import asyncio
import importlib.util
import os
import re
from pathlib import Path
from typing import Any

from observability.metrics import build_kpi_handles, configure_metrics
from observability.tracing import configure_tracing

from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore
from integrations.services.integration.analytics import AnalyticsClient

# ---------------------------------------------------------------------------
# Lazy optional-dependency sentinels (kept at module level so tests that
# ``monkeypatch.setattr(system_health_module, "_configure_azure_monitor", ...)``
# continue to work).
# ---------------------------------------------------------------------------


def _safe_find_spec(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ModuleNotFoundError, ValueError):
        return False


_HAS_AZURE = _safe_find_spec("azure")
_HAS_AZURE_MONITOR_OPENTELEMETRY = _HAS_AZURE and (_safe_find_spec("azure.monitor.opentelemetry"))
if _HAS_AZURE_MONITOR_OPENTELEMETRY:
    from azure.monitor.opentelemetry import configure_azure_monitor as _configure_azure_monitor
else:
    _configure_azure_monitor = None

# ---------------------------------------------------------------------------
# Action handler imports (delegated modules)
# ---------------------------------------------------------------------------
from actions import (  # noqa: E402
    acknowledge_alert,
    analyze_root_cause,
    apply_anomaly_detection,
    check_all_services_health,
    check_health,
    check_metric_thresholds,
    collect_application_metrics,
    collect_metrics,
    collect_platform_metrics,
    create_alert,
    create_incident,
    detect_anomalies,
    forecast_capacity,
    get_alerts,
    get_capacity_recommendations,
    get_deployment_baseline,
    get_deployment_metrics,
    get_environment_health,
    get_grafana_dashboard,
    get_health_dashboard,
    get_health_endpoints,
    get_metrics,
    get_postmortem_report,
    get_system_status,
    query_historical_metrics,
    resolve_incident,
)
from health_init import (  # noqa: E402
    configure_alert_rules,
    configure_opentelemetry_exporters,
    get_service_metrics,
    initialize_automation_client,
    initialize_azure_monitoring,
    initialize_event_hub,
    initialize_health_probes,
    initialize_prometheus_metrics,
    periodic_health_probes,
    query_azure_resource_metrics,
    query_metrics,
)
from health_utils import (  # noqa: E402
    load_health_endpoints,
    load_monitor_resource_ids,
    load_prometheus_scrape_targets,
    parse_prometheus_metrics,
    parse_time_range,
    sanitize_text,
)


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

    def __init__(self, agent_id: str = "system-health-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)
        self._init_config(config)
        self._init_stores(config)
        self._init_state(config)

    # ------------------------------------------------------------------
    # Config parsing (extracted for readability)
    # ------------------------------------------------------------------

    def _init_config(self, config: dict[str, Any] | None) -> None:  # noqa: C901
        c = config or {}
        self.alert_threshold_error_rate = c.get("alert_threshold_error_rate", 0.05)
        self.alert_threshold_response_time_ms = c.get("alert_threshold_response_time_ms", 1000)
        self.metrics_retention_days = c.get("metrics_retention_days", 90)
        self.monitor_workspace_id = c.get("monitor_workspace_id") or os.getenv("MONITOR_WORKSPACE_ID")
        self.app_insights_instrumentation_key = c.get("appinsights_instrumentation_key") or os.getenv("APPINSIGHTS_INSTRUMENTATION_KEY")
        self.app_insights_resource_id = c.get("appinsights_resource_id") or os.getenv("APPINSIGHTS_RESOURCE_ID")
        self.azure_monitor_connection_string = c.get("azure_monitor_connection_string") or os.getenv("AZURE_MONITOR_CONNECTION_STRING")
        if not self.azure_monitor_connection_string and self.app_insights_instrumentation_key:
            self.azure_monitor_connection_string = f"InstrumentationKey={self.app_insights_instrumentation_key}"
        self.event_hub_connection_string = c.get("event_hub_connection_string") or os.getenv("EVENT_HUB_CONNECTION_STRING")
        self.event_hub_name = c.get("event_hub_name") or os.getenv("EVENT_HUB_NAME")
        self.event_hub_partitions = int(c.get("event_hub_partitions", os.getenv("EVENT_HUB_PARTITIONS", "4")))
        self.event_hub_throughput_units = int(c.get("event_hub_throughput_units", os.getenv("EVENT_HUB_THROUGHPUT_UNITS", "1")))
        self.pagerduty_webhook_url = c.get("pagerduty_webhook_url") or os.getenv("PAGERDUTY_WEBHOOK_URL")
        self.opsgenie_webhook_url = c.get("opsgenie_webhook_url") or os.getenv("OPSGENIE_WEBHOOK_URL")
        self.scaling_webhook_url = c.get("scaling_webhook_url") or os.getenv("SCALING_WEBHOOK_URL")
        self.automation_webhook_url = c.get("automation_webhook_url") or os.getenv("AUTOMATION_WEBHOOK_URL")
        self.automation_subscription_id = c.get("automation_subscription_id") or os.getenv("AUTOMATION_SUBSCRIPTION_ID")
        self.automation_resource_group = c.get("automation_resource_group") or os.getenv("AUTOMATION_RESOURCE_GROUP")
        self.automation_account_name = c.get("automation_account_name") or os.getenv("AUTOMATION_ACCOUNT_NAME")
        self.automation_runbook_name = c.get("automation_runbook_name") or os.getenv("AUTOMATION_RUNBOOK_NAME")
        self.scaling_thresholds = {
            "cpu": float(c.get("scaling_threshold_cpu", os.getenv("SCALING_THRESHOLD_CPU", "0.8"))),
            "memory": float(c.get("scaling_threshold_memory", os.getenv("SCALING_THRESHOLD_MEMORY", "0.8"))),
            "queue_depth": float(c.get("scaling_threshold_queue_depth", os.getenv("SCALING_THRESHOLD_QUEUE_DEPTH", "1000"))),
        }
        self.servicenow_instance_url = c.get("servicenow_instance_url") or os.getenv("SERVICENOW_INSTANCE_URL")
        self.servicenow_username = c.get("servicenow_username") or os.getenv("SERVICENOW_USERNAME")
        self.servicenow_password = c.get("servicenow_password") or os.getenv("SERVICENOW_PASSWORD")
        self.servicenow_token = c.get("servicenow_token") or os.getenv("SERVICENOW_TOKEN")
        self.anomaly_detector_endpoint = c.get("anomaly_detector_endpoint") or os.getenv("ANOMALY_DETECTOR_ENDPOINT")
        self.anomaly_detector_key = c.get("anomaly_detector_key") or os.getenv("ANOMALY_DETECTOR_KEY")
        self.health_endpoints = c.get("health_endpoints") or load_health_endpoints(self.logger)
        self.health_probe_interval_seconds = int(c.get("health_probe_interval_seconds", os.getenv("HEALTH_PROBE_INTERVAL_SECONDS", "60")))
        self.metrics_port = int(c.get("metrics_port", os.getenv("PROMETHEUS_METRICS_PORT", "0")))
        self.prometheus_scrape_targets = c.get("prometheus_scrape_targets") or load_prometheus_scrape_targets(self.logger)
        self.monitor_resource_ids = c.get("monitor_resource_ids") or load_monitor_resource_ids(self.logger)
        self.grafana_datasource = c.get("grafana_datasource", os.getenv("GRAFANA_DATASOURCE", "Prometheus"))
        self.grafana_folder = c.get("grafana_folder", os.getenv("GRAFANA_FOLDER", "System Health"))

    def _init_stores(self, config: dict[str, Any] | None) -> None:
        c = config or {}
        alert_store_path = Path(c.get("alert_store_path", "data/alerts.json"))
        incident_store_path = Path(c.get("incident_store_path", "data/incidents.json"))
        self.alert_store = TenantStateStore(alert_store_path)
        self.incident_store = TenantStateStore(incident_store_path)

    def _init_state(self, config: dict[str, Any] | None) -> None:
        c = config or {}
        self.metrics = {}  # type: ignore[var-annotated]
        self.alerts = {}  # type: ignore[var-annotated]
        self.incidents = {}  # type: ignore[var-annotated]
        self.health_checks = {}  # type: ignore[var-annotated]
        self.anomalies = {}  # type: ignore[var-annotated]
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
        self.analytics_client = c.get("analytics_client") or AnalyticsClient()
        self.event_bus = c.get("event_bus")
        if self.event_bus is None:
            try:
                self.event_bus = get_event_bus()
            except ValueError:
                self.event_bus = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize monitoring infrastructure and integrations."""
        await super().initialize()
        self.logger.info("Initializing System Health & Monitoring Agent...")

        configure_tracing(self.agent_id)
        try:
            configure_metrics(self.agent_id)
        except ValueError:
            pass
        try:
            self._kpi_handles = build_kpi_handles(self.agent_id)
        except ValueError:
            self._kpi_handles = {}
        await initialize_azure_monitoring(self)
        await configure_opentelemetry_exporters(self)
        await initialize_event_hub(self)
        await initialize_automation_client(self)
        await initialize_prometheus_metrics(self)
        await configure_alert_rules(self)
        await initialize_health_probes(self)

        self.logger.info("System Health & Monitoring Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")
        if not action:
            self.logger.warning("No action specified")
            return False
        valid_actions = [
            "collect_metrics", "collect_platform_metrics", "collect_application_metrics",
            "check_health", "create_alert", "detect_anomalies", "create_incident",
            "analyze_root_cause", "get_system_status", "get_metrics", "get_alerts",
            "get_capacity_recommendations", "get_health_endpoints",
            "query_historical_metrics", "forecast_capacity", "acknowledge_alert",
            "resolve_incident", "get_health_dashboard", "get_postmortem_report",
            "get_environment_health", "get_grafana_dashboard",
        ]
        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False
        return True

    # ------------------------------------------------------------------
    # Process routing (delegates to extracted action modules)
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process system health and monitoring requests."""
        action = input_data.get("action", "get_system_status")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )

        if action == "collect_metrics":
            return await collect_metrics(self, tenant_id, input_data.get("service_name"), input_data.get("metrics", {}))  # type: ignore[arg-type]
        elif action == "collect_platform_metrics":
            return await collect_platform_metrics(self, tenant_id, input_data.get("targets"))
        elif action == "collect_application_metrics":
            return await collect_application_metrics(self, tenant_id, input_data.get("time_range", {}))
        elif action == "check_health":
            return await check_health(self, input_data.get("service_name"))
        elif action == "create_alert":
            return await create_alert(self, tenant_id, input_data.get("alert", {}))
        elif action == "detect_anomalies":
            return await detect_anomalies(self, tenant_id, input_data.get("service_name"), input_data.get("time_range", {}))  # type: ignore[arg-type]
        elif action == "create_incident":
            return await create_incident(self, tenant_id, input_data.get("incident", {}))
        elif action == "analyze_root_cause":
            return await analyze_root_cause(self, input_data.get("incident_id"))  # type: ignore[arg-type]
        elif action == "get_system_status":
            return await get_system_status(self)
        elif action == "get_metrics":
            if input_data.get("deployment_plan"):
                return await get_deployment_metrics(self, input_data["deployment_plan"])
            return await get_metrics(self, input_data.get("service_name"), input_data.get("metric_name"), input_data.get("time_range", {}))  # type: ignore[arg-type]
        elif action == "get_alerts":
            return await get_alerts(self, input_data.get("filters", {}))
        elif action == "get_capacity_recommendations":
            return await get_capacity_recommendations(self, input_data.get("service_name"))
        elif action == "get_health_endpoints":
            return await get_health_endpoints(self)
        elif action == "query_historical_metrics":
            return await query_historical_metrics(self, input_data.get("service_name"), input_data.get("metric_name"), input_data.get("time_range", {}))  # type: ignore[arg-type]
        elif action == "forecast_capacity":
            return await forecast_capacity(self, input_data.get("service_name"))
        elif action == "acknowledge_alert":
            return await acknowledge_alert(self, tenant_id, input_data.get("alert_id"), input_data.get("acknowledged_by"))  # type: ignore[arg-type]
        elif action == "resolve_incident":
            return await resolve_incident(self, tenant_id, input_data.get("incident_id"), input_data.get("resolution", {}))  # type: ignore[arg-type]
        elif action == "get_health_dashboard":
            return await get_health_dashboard(self, tenant_id, input_data.get("time_range", {}))
        elif action == "get_postmortem_report":
            return await get_postmortem_report(self, tenant_id, input_data.get("time_range", {}))
        elif action == "get_environment_health":
            return await get_environment_health(self, input_data.get("environment") or input_data.get("service_name"))
        elif action == "get_grafana_dashboard":
            return await get_grafana_dashboard(self)
        else:
            raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Thin wrappers (backward compat for tests and action modules)
    # ------------------------------------------------------------------

    async def _check_metric_thresholds(self, tenant_id: str, service_name: str, metrics_data: dict[str, Any]) -> list[str]:
        return await check_metric_thresholds(self, tenant_id, service_name, metrics_data)

    async def _get_service_metrics(self, service_name: str, time_range: dict[str, Any]) -> list[dict[str, Any]]:
        return await get_service_metrics(self, service_name, time_range)

    async def _query_metrics(self, service_name: str, metric_name: str, time_range: dict[str, Any]) -> list[dict[str, Any]]:
        return await query_metrics(self, service_name, metric_name, time_range)

    async def _query_azure_resource_metrics(self, resource_id: str) -> dict[str, Any]:
        return await query_azure_resource_metrics(self, resource_id)

    def _parse_prometheus_metrics(self, payload: str) -> dict[str, Any]:
        return parse_prometheus_metrics(payload)

    async def _apply_anomaly_detection(self, metrics_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return await apply_anomaly_detection(self, metrics_list)

    async def _collect_metrics(self, tenant_id: str, service_name: str, metrics_data: dict[str, Any]) -> dict[str, Any]:
        return await collect_metrics(self, tenant_id, service_name, metrics_data)

    async def _collect_application_metrics(self, tenant_id: str, time_range: dict[str, Any]) -> dict[str, Any]:
        return await collect_application_metrics(self, tenant_id, time_range)

    async def _create_alert(self, tenant_id: str, alert_config: dict[str, Any]) -> dict[str, Any]:
        return await create_alert(self, tenant_id, alert_config)

    async def _create_incident(self, tenant_id: str, incident_data: dict[str, Any]) -> dict[str, Any]:
        return await create_incident(self, tenant_id, incident_data)

    async def _get_system_status(self) -> dict[str, Any]:
        return await get_system_status(self)

    async def _get_environment_health(self, environment: str | None) -> dict[str, Any]:
        return await get_environment_health(self, environment)

    async def _get_deployment_metrics(self, deployment_plan: dict[str, Any]) -> dict[str, Any]:
        return await get_deployment_metrics(self, deployment_plan)

    async def _get_deployment_baseline(self, deployment_plan: dict[str, Any]) -> dict[str, Any]:
        return await get_deployment_baseline(self, deployment_plan)

    async def _emit_event_hub_event(self, payload: dict[str, Any]) -> None:
        from health_integrations import emit_event_hub_event
        await emit_event_hub_event(self, payload)

    async def _create_servicenow_incident(self, incident: dict[str, Any]) -> None:
        from health_integrations import create_servicenow_incident
        await create_servicenow_incident(self, incident)

    def _sanitize_text(self, value: str) -> str:
        return sanitize_text(value)

    # ------------------------------------------------------------------
    # Public convenience methods (called by other agents / orchestrator)
    # ------------------------------------------------------------------

    async def get_metrics(self, deployment_plan: dict[str, Any]) -> dict[str, Any]:
        """Expose monitoring metrics for deployment workflows."""
        return await get_deployment_metrics(self, deployment_plan)

    async def get_baseline(self, deployment_plan: dict[str, Any]) -> dict[str, Any]:
        """Expose baseline metrics for deployment workflows."""
        return await get_deployment_baseline(self, deployment_plan)

    async def get_environment_health(self, environment: str) -> dict[str, Any]:
        """Expose health status for deployment workflows."""
        return await get_environment_health(self, environment)

    # ------------------------------------------------------------------
    # Cleanup & capabilities
    # ------------------------------------------------------------------

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
            "resource_monitoring", "application_monitoring", "log_collection",
            "trace_collection", "alerting", "incident_management",
            "anomaly_detection", "predictive_maintenance", "root_cause_analysis",
            "capacity_planning", "health_checks", "performance_monitoring",
            "dashboard_creation", "postmortem_reporting", "deployment_health_gate",
            "grafana_dashboard", "environment_health_query",
        ]
