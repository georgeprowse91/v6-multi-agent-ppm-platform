"""
Agent 25: System Health & Monitoring Agent

Purpose:
Ensures the operational reliability, performance and availability of the PPM platform through
comprehensive monitoring, alerting, and proactive maintenance.

Specification: agents/operations-management/agent-25-system-health-monitoring/README.md
"""

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from observability.metrics import build_kpi_handles, configure_metrics
from observability.tracing import configure_tracing, start_agent_span

from agents.runtime import BaseAgent
from agents.runtime.src.state_store import TenantStateStore


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
        self._pii_patterns = {
            "email": re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
            "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "phone": re.compile(r"\+?\d[\d\s().-]{7,}\d"),
        }

    async def initialize(self) -> None:
        """Initialize monitoring infrastructure and integrations."""
        await super().initialize()
        self.logger.info("Initializing System Health & Monitoring Agent...")

        configure_tracing(self.agent_id)
        configure_metrics(self.agent_id)
        self._kpi_handles = build_kpi_handles(self.agent_id)

        # Future work: Initialize Azure Monitor for infrastructure monitoring
        # Future work: Set up Application Insights for application telemetry
        # Future work: Connect to Azure Log Analytics for log aggregation
        # Future work: Initialize OpenTelemetry for distributed tracing
        # Future work: Set up Azure Alerts with action groups
        # Future work: Connect to PagerDuty/OpsGenie for incident management
        # Future work: Initialize Azure Dashboards for visualization
        # Future work: Set up Azure Automation for scaling actions
        # Future work: Connect to all agents for health check endpoints
        # Future work: Initialize anomaly detection models
        # Future work: Set up Azure Event Hub for telemetry ingestion
        # Future work: Connect to ServiceNow for incident tracking

        self.logger.info("System Health & Monitoring Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "collect_metrics",
            "check_health",
            "create_alert",
            "detect_anomalies",
            "create_incident",
            "analyze_root_cause",
            "get_system_status",
            "get_metrics",
            "get_alerts",
            "get_capacity_recommendations",
            "acknowledge_alert",
            "resolve_incident",
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

        elif action == "check_health":
            return await self._check_health(input_data.get("service_name"))

        elif action == "create_alert":
            return await self._create_alert(tenant_id, input_data.get("alert", {}))

        elif action == "detect_anomalies":
            return await self._detect_anomalies(
                input_data.get("service_name"), input_data.get("time_range", {})  # type: ignore
            )

        elif action == "create_incident":
            return await self._create_incident(tenant_id, input_data.get("incident", {}))

        elif action == "analyze_root_cause":
            return await self._analyze_root_cause(input_data.get("incident_id"))  # type: ignore

        elif action == "get_system_status":
            return await self._get_system_status()

        elif action == "get_metrics":
            return await self._get_metrics(
                input_data.get("service_name"),  # type: ignore
                input_data.get("metric_name"),  # type: ignore
                input_data.get("time_range", {}),
            )

        elif action == "get_alerts":
            return await self._get_alerts(input_data.get("filters", {}))

        elif action == "get_capacity_recommendations":
            return await self._get_capacity_recommendations(input_data.get("service_name"))

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

        # Future work: Store in Azure Monitor
        # Future work: Emit to Application Insights

        return {
            "metric_id": metric_id,
            "service_name": service_name,
            "metrics_collected": len(metrics_data),
            "timestamp": timestamp,
            "alerts_triggered": alerts_triggered,
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

        # Future work: Create in Azure Monitor Alerts
        # Future work: Configure action group

        return {
            "alert_id": alert_id,
            "name": alert["name"],
            "severity": alert["severity"],
            "status": "active",
        }

    async def _detect_anomalies(
        self, service_name: str, time_range: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Detect anomalies in service metrics.

        Returns detected anomalies.
        """
        self.logger.info(f"Detecting anomalies for service: {service_name}")

        # Get metrics for time range
        metrics = await self._get_service_metrics(service_name, time_range)

        # Apply anomaly detection
        # Future work: Use Azure ML or statistical models
        anomalies = await self._apply_anomaly_detection(metrics)

        # Store anomalies
        for anomaly in anomalies:
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

        # Future work: Create in PagerDuty/ServiceNow
        # Future work: Notify on-call team
        # Future work: Publish incident.created event

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
        # Future work: Query from Azure Monitor
        metric_values = await self._query_metrics(service_name, metric_name, time_range)

        return {
            "service_name": service_name,
            "metric_name": metric_name,
            "time_range": time_range,
            "values": metric_values,
            "retrieved_at": datetime.utcnow().isoformat(),
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

        # Future work: Update in monitoring system
        # Future work: Publish alert.acknowledged event

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

        # Future work: Update in incident management system
        # Future work: Publish incident.resolved event

        return {
            "incident_id": incident_id,
            "status": "resolved",
            "resolution_time_minutes": resolution_time,
            "resolved_at": incident["resolved_at"],
        }

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

        return alert_ids

    async def _check_service_health(self, service_name: str) -> dict[str, Any]:
        """Check health of specific service."""
        # Future work: Call service health endpoint
        return {"healthy": True, "response_time_ms": 50, "status_code": 200}

    async def _check_all_services_health(self) -> dict[str, dict[str, Any]]:
        """Check health of all services."""
        # Future work: Check all registered services
        services = {
            "api_gateway": {"healthy": True, "response_time_ms": 45},
            "database": {"healthy": True, "response_time_ms": 10},
            "cache": {"healthy": True, "response_time_ms": 5},
        }
        return services

    async def _get_service_metrics(
        self, service_name: str, time_range: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get metrics for service in time range."""
        # Future work: Query from metrics store
        return []

    async def _apply_anomaly_detection(self, metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply anomaly detection to metrics."""
        # Future work: Use ML model for anomaly detection
        return []

    async def _collect_incident_metrics(self, affected_services: list[str]) -> dict[str, Any]:
        """Collect metrics related to incident."""
        # Future work: Collect metrics from Azure Monitor
        return {}

    async def _collect_incident_logs(self, affected_services: list[str]) -> list[dict[str, Any]]:
        """Collect logs related to incident."""
        # Future work: Collect logs from Log Analytics
        return []

    async def _collect_incident_traces(self, affected_services: list[str]) -> list[dict[str, Any]]:
        """Collect traces related to incident."""
        # Future work: Collect traces from Application Insights
        return []

    async def _correlate_incident_data(
        self, metrics: dict[str, Any], logs: list[dict[str, Any]], traces: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Correlate incident data sources."""
        # Future work: Implement correlation logic
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
        # Future work: Query from Azure Monitor
        return []

    async def _matches_alert_filters(self, alert: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if alert matches filters."""
        if "severity" in filters and alert.get("severity") != filters["severity"]:
            return False

        if "status" in filters and alert.get("status") != filters["status"]:
            return False

        return True

    async def _analyze_utilization_trends(self, service_name: str | None) -> dict[str, Any]:
        """Analyze resource utilization trends."""
        # Future work: Analyze historical metrics
        return {"cpu_trend": "increasing", "memory_trend": "stable", "storage_trend": "increasing"}

    async def _forecast_capacity_needs(self, trends: dict[str, Any]) -> dict[str, Any]:
        """Forecast future capacity needs."""
        # Future work: Use forecasting models
        return {"cpu_forecast_30d": 75.0, "memory_forecast_30d": 60.0, "storage_forecast_30d": 85.0}

    async def _generate_capacity_recommendations(self, forecasts: dict[str, Any]) -> list[str]:
        """Generate capacity recommendations."""
        recommendations = []

        if forecasts.get("cpu_forecast_30d", 0) > 80:
            recommendations.append("Consider scaling up CPU resources within 30 days")

        if forecasts.get("storage_forecast_30d", 0) > 80:
            recommendations.append("Plan for storage expansion within 30 days")

        if not recommendations:
            recommendations.append("Current capacity is adequate for forecasted needs")

        return recommendations

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
        # Future work: Close monitoring connections
        # Future work: Flush pending metrics
        # Future work: Close incident management connections

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
        ]
