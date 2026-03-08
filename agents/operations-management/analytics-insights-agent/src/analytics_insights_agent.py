"""
Analytics & Insights Agent

Purpose:
Delivers comprehensive analytics, reporting and decision-support across the entire project
portfolio through advanced analytics and machine learning.

Specification: agents/operations-management/analytics-insights-agent/README.md
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Action handlers ---------------------------------------------------------
from analytics_actions.aggregate_data import handle_aggregate_data
from analytics_actions.compute_kpis import handle_compute_kpis_batch, update_kpis_from_definitions
from analytics_actions.create_dashboard import handle_create_dashboard
from analytics_actions.data_lineage import handle_update_data_lineage
from analytics_actions.generate_narrative import handle_generate_narrative
from analytics_actions.generate_report import handle_generate_report
from analytics_actions.infrastructure import (
    handle_get_powerbi_report,
    handle_ingest_realtime_event,
    handle_ingest_sources,
    handle_monitor_etl,
    handle_orchestrate_etl,
    handle_provision_analytics_stack,
    handle_train_kpi_model,
)
from analytics_actions.insights import handle_get_insights
from analytics_actions.periodic_report import handle_generate_periodic_report
from analytics_actions.query_data import (
    handle_get_dashboard,
    handle_natural_language_query,
    handle_query_data,
)
from analytics_actions.run_prediction import handle_run_prediction
from analytics_actions.scenario_analysis import handle_scenario_analysis
from analytics_actions.track_kpi import handle_track_kpi

# Service-manager / infrastructure classes --------------------------------
from analytics_models import (
    DataFactoryManager,
    DataLakeManager,
    EventHubManager,
    LanguageQueryService,
    MLModelManager,
    NarrativeService,
    PowerBIEmbedManager,
    ReportRepository,
    StreamAnalyticsManager,
    SynapseManager,
)

# Utility helpers ---------------------------------------------------------
from analytics_utils import (
    DEFAULT_ANALYTICS_EVENT_TOPICS,
    DEFAULT_DATA_FACTORY_PIPELINES,
    DEFAULT_INGESTION_SOURCES,
    DEFAULT_KPI_DEFINITIONS,
    VALID_ACTIONS,
    maybe_await,
    redact_payload,
    store_event_record,
)

from agents.common.scenario import ScenarioEngine
from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore


class AnalyticsInsightsAgent(BaseAgent):
    """
    Analytics & Insights Agent - Provides comprehensive analytics and reporting.

    Key Capabilities:
    - Data aggregation and modeling
    - Interactive dashboards and visualizations
    - Self-service analytics and ad hoc reporting
    - Predictive and prescriptive analytics
    - Scenario analysis and what-if modeling
    - Narrative generation
    - KPI and OKR management
    - Data governance and lineage
    - Portfolio health aggregation from lifecycle events
    """

    def __init__(
        self, agent_id: str = "analytics-insights-agent", config: dict[str, Any] | None = None
    ):
        super().__init__(agent_id, config)
        cfg = config or {}

        # Scalar configuration
        self.refresh_interval_minutes = cfg.get("refresh_interval_minutes", 60)
        self.prediction_confidence_threshold = cfg.get("prediction_confidence_threshold", 0.75)
        self.max_dashboard_widgets = cfg.get("max_dashboard_widgets", 20)
        self.scenario_engine = ScenarioEngine()
        self.metric_agents = cfg.get("metric_agents", {})
        self.analytics_event_topics = cfg.get("analytics_event_topics") or list(
            DEFAULT_ANALYTICS_EVENT_TOPICS
        )
        self.event_bus = (
            cfg.get("event_bus") if cfg.get("event_bus") is not None else get_event_bus()
        )

        # Azure Synapse
        self.synapse_workspace_name = os.getenv(
            "SYNAPSE_WORKSPACE_NAME", cfg.get("synapse_workspace_name", "")
        )
        self.synapse_sql_pool_name = os.getenv(
            "SYNAPSE_SQL_POOL_NAME", cfg.get("synapse_sql_pool_name", "")
        )
        self.synapse_spark_pool_name = cfg.get("synapse_spark_pool_name", "analytics-spark")
        self.synapse_manager = cfg.get("synapse_manager") or SynapseManager(
            self.synapse_workspace_name or None,
            self.synapse_sql_pool_name or None,
            self.synapse_spark_pool_name,
            cfg.get("synapse_client"),
        )

        # Data Lake
        self.data_lake_manager = cfg.get("data_lake_manager") or DataLakeManager(
            os.getenv("DATA_LAKE_FILE_SYSTEM", cfg.get("data_lake_file_system", "")) or None,
            cfg.get("data_lake_client"),
        )

        # ML / Power BI / Data Factory / Event Hub / Stream Analytics
        self.ml_manager = cfg.get("ml_manager") or MLModelManager(cfg.get("ml_client"))
        self.power_bi_manager = cfg.get("power_bi_manager") or PowerBIEmbedManager(
            cfg.get("power_bi_client")
        )
        self.data_factory_manager = cfg.get("data_factory_manager") or DataFactoryManager(
            cfg.get("data_factory_client")
        )
        self.data_factory_pipelines = cfg.get("data_factory_pipelines") or list(
            DEFAULT_DATA_FACTORY_PIPELINES
        )
        self.ingestion_sources = cfg.get("ingestion_sources") or list(DEFAULT_INGESTION_SOURCES)
        self.event_hub_manager = cfg.get("event_hub_manager") or EventHubManager(
            cfg.get("event_hub_producer"), cfg.get("event_hub_consumer")
        )
        self.stream_analytics_manager = (
            cfg.get("stream_analytics_manager") or StreamAnalyticsManager()
        )
        self.narrative_service = cfg.get("narrative_service") or NarrativeService(
            cfg.get("openai_client")
        )
        self.language_service = cfg.get("language_service") or LanguageQueryService(
            cfg.get("language_client")
        )
        self.report_repository = cfg.get("report_repository") or ReportRepository(
            cfg.get("postgres_conn"), cfg.get("cosmos_container")
        )

        # Tenant-scoped state stores
        self.analytics_output_store = TenantStateStore(
            Path(cfg.get("analytics_output_store_path", "data/analytics_outputs.json"))
        )
        self.analytics_alert_store = TenantStateStore(
            Path(cfg.get("analytics_alert_store_path", "data/analytics_alerts.json"))
        )
        self.analytics_lineage_store = TenantStateStore(
            Path(cfg.get("analytics_lineage_store_path", "data/analytics_lineage.json"))
        )
        self.analytics_event_store = TenantStateStore(
            Path(cfg.get("analytics_event_store_path", "data/analytics_events.json"))
        )
        self.kpi_history_store = TenantStateStore(
            Path(cfg.get("analytics_kpi_history_store_path", "data/analytics_kpi_history.json"))
        )
        self.health_snapshot_store = TenantStateStore(
            Path(cfg.get("health_snapshot_store_path", "data/health_snapshots.json"))
        )

        # In-memory data stores
        self.dashboards = {}  # type: ignore
        self.reports = {}  # type: ignore
        self.kpis = {}  # type: ignore
        self.kpi_alerts = {}  # type: ignore
        self.predictions = {}  # type: ignore
        self.scenarios = {}  # type: ignore
        self.data_lineage = {}  # type: ignore
        self.health_snapshots: dict[str, list[dict[str, Any]]] = {}
        self.event_history: dict[str, list[dict[str, Any]]] = {}
        self.kpi_definitions = cfg.get("kpi_definitions") or list(DEFAULT_KPI_DEFINITIONS)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize analytics services, ML models, and data sources."""
        await super().initialize()
        self.logger.info("Initializing Analytics & Insights Agent...")

        await maybe_await(self.synapse_manager.ensure_pools)
        await maybe_await(self.data_lake_manager.ensure_file_system)
        await maybe_await(self.data_factory_manager.ensure_pipelines, self.data_factory_pipelines)
        self.logger.info(
            "Synapse pools initialized",
            extra={
                "workspace": self.synapse_workspace_name,
                "sql_pool": self.synapse_sql_pool_name,
                "spark_pool": self.synapse_spark_pool_name,
            },
        )

        if self.event_bus and hasattr(self.event_bus, "subscribe"):
            self.event_bus.subscribe("project.health.updated", self._handle_health_updated)
            self.event_bus.subscribe(
                "project.health.report.generated", self._handle_health_report_generated
            )
            for topic in self.analytics_event_topics:
                self.event_bus.subscribe(topic, self._build_event_handler(topic))
            self.event_bus.subscribe(
                "project.updated", self._build_event_handler("project.updated")
            )
            self.event_bus.subscribe(
                "resource.updated", self._build_event_handler("resource.updated")
            )

        self.logger.info("Analytics & Insights Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")
        if not action:
            self.logger.warning("No action specified")
            return False
        if action not in VALID_ACTIONS:
            self.logger.warning("Invalid action: %s", action)
            return False

        required_fields: dict[str, str] = {
            "create_dashboard": "dashboard",
            "run_prediction": "model_type",
            "get_powerbi_report": "report_type",
            "orchestrate_etl": "pipelines",
            "monitor_etl": "run_id",
            "ingest_realtime_event": "event",
        }
        field = required_fields.get(action)
        if field and field not in input_data:
            self.logger.warning("Missing %s for %s", field, action)
            return False
        return True

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process analytics and insights requests.  Delegates to action handlers."""
        action = input_data.get("action", "get_insights")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )

        if action == "aggregate_data":
            return await handle_aggregate_data(self, tenant_id, input_data.get("data_sources", []))
        elif action == "create_dashboard":
            return await handle_create_dashboard(self, tenant_id, input_data.get("dashboard", {}))
        elif action == "generate_report":
            return await handle_generate_report(self, tenant_id, input_data.get("report", {}))
        elif action == "run_prediction":
            return await handle_run_prediction(self, tenant_id, input_data.get("model_type"), input_data.get("input_data", {}))  # type: ignore
        elif action == "scenario_analysis":
            return await handle_scenario_analysis(self, tenant_id, input_data.get("scenario", {}))
        elif action == "generate_narrative":
            return await handle_generate_narrative(self, tenant_id, input_data.get("data", {}))  # type: ignore
        elif action == "track_kpi":
            return await handle_track_kpi(self, tenant_id, input_data.get("kpi", {}))
        elif action == "query_data":
            return await handle_query_data(self, input_data.get("query"), input_data.get("filters", {}))  # type: ignore
        elif action == "natural_language_query":
            return await handle_natural_language_query(self, input_data.get("question"), input_data.get("context", {}))  # type: ignore
        elif action == "get_dashboard":
            return await handle_get_dashboard(self, input_data.get("dashboard_id"))  # type: ignore
        elif action == "get_insights":
            return await handle_get_insights(self, input_data.get("filters", {}))
        elif action == "update_data_lineage":
            return await handle_update_data_lineage(self, tenant_id, input_data.get("lineage", {}))
        elif action == "get_powerbi_report":
            return await handle_get_powerbi_report(
                self, tenant_id, input_data.get("report_type"), input_data.get("user_context", {})
            )
        elif action == "orchestrate_etl":
            return await handle_orchestrate_etl(
                self, input_data.get("pipelines", []), input_data.get("parameters", {})
            )
        elif action == "monitor_etl":
            return await handle_monitor_etl(self, input_data.get("run_id"))  # type: ignore
        elif action == "train_kpi_model":
            return await handle_train_kpi_model(
                self, input_data.get("model_name"), input_data.get("training_payload", {})
            )
        elif action == "provision_analytics_stack":
            return await handle_provision_analytics_stack(self)
        elif action == "ingest_sources":
            return await handle_ingest_sources(
                self, tenant_id, input_data.get("sources"), input_data.get("parameters", {})
            )
        elif action == "ingest_realtime_event":
            return await handle_ingest_realtime_event(
                self, input_data.get("event"), input_data.get("event_type")
            )
        elif action == "compute_kpis_batch":
            return await handle_compute_kpis_batch(
                self, tenant_id, input_data.get("event_type"), input_data.get("kpis")
            )
        elif action == "generate_periodic_report":
            return await handle_generate_periodic_report(
                self, tenant_id, input_data.get("period", "monthly"), input_data.get("filters", {})
            )
        else:
            raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Event handlers (kept on the class for event-bus subscriptions)
    # ------------------------------------------------------------------

    def _build_event_handler(self, topic: str) -> Callable[[dict[str, Any]], Any]:
        async def _handler(payload: dict[str, Any]) -> None:
            await self._handle_domain_event(payload, topic)

        return _handler

    async def _handle_domain_event(self, event: dict[str, Any], event_type: str) -> None:
        tenant_id = event.get("tenant_id") or event.get("payload", {}).get("tenant_id") or "default"
        raw_payload = event.get("payload", event)
        redacted = redact_payload(raw_payload)
        record = await store_event_record(self, tenant_id, event_type, redacted, event)
        await update_kpis_from_definitions(self, tenant_id, event_type=event_type)
        await self._publish_insights_event(tenant_id, event_type, record)
        await self._stream_realtime_event(event_type, redacted)

    async def _handle_health_updated(self, event: dict[str, Any]) -> None:
        """Handle project health updates from the lifecycle agent."""
        payload = event.get("payload", event)
        tenant_id = event.get("tenant_id", payload.get("tenant_id", "default"))
        health_data = payload.get("health_data", payload)
        project_id = health_data.get("project_id")
        if not project_id:
            return
        snapshots = self.health_snapshots.setdefault(tenant_id, [])
        snapshots.append(health_data)
        record_id = f"{project_id}-{health_data.get('monitored_at', datetime.now(timezone.utc).isoformat())}"
        self.health_snapshot_store.upsert(tenant_id, record_id, health_data.copy())

    async def _handle_health_report_generated(self, event: dict[str, Any]) -> None:
        """Handle generated health reports for downstream analytics."""
        payload = event.get("payload", event)
        tenant_id = event.get("tenant_id", payload.get("tenant_id", "default"))
        report = payload.get("report", payload)
        report_id = report.get(
            "report_id", f"health-report-{datetime.now(timezone.utc).isoformat()}"
        )
        self.reports[report_id] = report
        self.analytics_output_store.upsert(tenant_id, report_id, report.copy())

    async def _publish_insights_event(
        self, tenant_id: str, event_type: str, event_record: dict[str, Any]
    ) -> None:
        if not self.event_bus:
            return
        await self.event_bus.publish(
            "analytics.insights.event_ingested",
            {
                "tenant_id": tenant_id,
                "event_type": event_type,
                "event_id": event_record.get("event_id"),
                "received_at": event_record.get("received_at"),
            },
        )

    async def _stream_realtime_event(self, event_type: str, payload: dict[str, Any]) -> None:
        await self.event_hub_manager.publish_event(event_type, payload)
        await self.stream_analytics_manager.stream_events([payload])

    # ------------------------------------------------------------------
    # Delegate methods (allow direct calls & monkey-patching in tests)
    # ------------------------------------------------------------------

    async def _run_prediction(
        self, tenant_id: str, model_type: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        return await handle_run_prediction(self, tenant_id, model_type, input_data)

    async def _track_kpi(self, tenant_id: str, kpi_config: dict[str, Any]) -> dict[str, Any]:
        return await handle_track_kpi(self, tenant_id, kpi_config)

    async def _generate_report(self, tenant_id: str, report_spec: dict[str, Any]) -> dict[str, Any]:
        return await handle_generate_report(self, tenant_id, report_spec)

    async def _compute_kpis_batch(
        self, tenant_id: str, event_type: str | None, kpis: list[dict[str, Any]] | None
    ) -> dict[str, Any]:
        return await handle_compute_kpis_batch(self, tenant_id, event_type, kpis)

    async def _ingest_sources(
        self, tenant_id: str, sources: list[str] | None, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        return await handle_ingest_sources(self, tenant_id, sources, parameters)

    # ------------------------------------------------------------------
    # Cleanup / capabilities
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Analytics & Insights Agent...")

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "data_aggregation",
            "dashboard_creation",
            "report_generation",
            "predictive_analytics",
            "scenario_analysis",
            "narrative_generation",
            "kpi_tracking",
            "data_querying",
            "natural_language_query",
            "anomaly_detection",
            "pattern_recognition",
            "data_visualization",
            "self_service_analytics",
            "data_lineage",
            "ml_predictions",
            "powerbi_embedded",
            "synapse_analytics",
            "data_factory_orchestration",
            "event_stream_ingestion",
        ]
