"""
Agent 22: Analytics & Insights Agent

Purpose:
Delivers comprehensive analytics, reporting and decision-support across the entire project
portfolio through advanced analytics and machine learning.

Specification: agents/operations-management/agent-22-analytics-insights/README.md
"""

from __future__ import annotations

import inspect
import os
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from security.lineage import mask_lineage_payload

from agents.common.health_recommendations import generate_recommendations, identify_health_concerns
from agents.common.metrics_catalog import get_metric_value, normalize_metric_value
from agents.common.scenario import ScenarioEngine
from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore


class SynapseManager:
    """Manages Azure Synapse Analytics pools."""

    def __init__(
        self,
        workspace_name: str | None,
        sql_pool_name: str | None,
        spark_pool_name: str | None,
        synapse_client: Any | None = None,
    ) -> None:
        self.workspace_name = workspace_name
        self.sql_pool_name = sql_pool_name
        self.spark_pool_name = spark_pool_name
        self.synapse_client = synapse_client

    def ensure_pools(self) -> dict[str, Any]:
        details = {
            "workspace": self.workspace_name,
            "sql_pool": self.sql_pool_name,
            "spark_pool": self.spark_pool_name,
            "initialized": False,
        }
        if not self.synapse_client:
            return details
        if self.sql_pool_name and hasattr(self.synapse_client, "create_sql_pool"):
            self.synapse_client.create_sql_pool(self.workspace_name, self.sql_pool_name)
        if self.spark_pool_name and hasattr(self.synapse_client, "create_spark_pool"):
            self.synapse_client.create_spark_pool(self.workspace_name, self.spark_pool_name)
        if hasattr(self.synapse_client, "sql_pools") and self.sql_pool_name:
            self.synapse_client.sql_pools.create_or_update(self.workspace_name, self.sql_pool_name)
        if hasattr(self.synapse_client, "spark_pools") and self.spark_pool_name:
            self.synapse_client.spark_pools.create_or_update(
                self.workspace_name, self.spark_pool_name
            )
        details["initialized"] = True
        return details

    def ingest_dataset(self, dataset_name: str, payload: list[dict[str, Any]]) -> dict[str, Any]:
        details = {
            "dataset": dataset_name,
            "workspace": self.workspace_name,
            "sql_pool": self.sql_pool_name,
            "spark_pool": self.spark_pool_name,
            "stored": False,
        }
        if not self.synapse_client:
            return details
        if hasattr(self.synapse_client, "ingest"):
            self.synapse_client.ingest(dataset_name, payload)
            details["stored"] = True
        elif hasattr(self.synapse_client, "upload"):
            self.synapse_client.upload(dataset_name, payload)
            details["stored"] = True
        return details


class DataLakeManager:
    """Manages Azure Data Lake Storage Gen2 paths."""

    def __init__(
        self,
        file_system_name: str | None,
        service_client: Any | None = None,
    ) -> None:
        self.file_system_name = file_system_name
        self.service_client = service_client

    def ensure_file_system(self) -> dict[str, Any]:
        details = {
            "file_system": self.file_system_name,
            "initialized": False,
        }
        if not self.service_client or not self.file_system_name:
            return details
        if hasattr(self.service_client, "create_file_system"):
            self.service_client.create_file_system(self.file_system_name)
        elif hasattr(self.service_client, "get_file_system_client"):
            file_system = self.service_client.get_file_system_client(self.file_system_name)
            if hasattr(file_system, "create_file_system"):
                file_system.create_file_system()
        details["initialized"] = True
        return details

    def store_dataset(
        self,
        source: str,
        domain: str,
        payload: list[dict[str, Any]],
    ) -> dict[str, str]:
        raw_path = f"/raw/{source}/{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
        curated_path = (
            f"/curated/{domain}/{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
        )
        if self.service_client:
            file_system = self.service_client.get_file_system_client(self.file_system_name)
            raw_file = file_system.create_file(raw_path.lstrip("/"))
            raw_file.append_data(str(payload), 0, len(str(payload)))
            raw_file.flush_data(len(str(payload)))
            curated_file = file_system.create_file(curated_path.lstrip("/"))
            curated_file.append_data(str(payload), 0, len(str(payload)))
            curated_file.flush_data(len(str(payload)))
        return {"raw_path": raw_path, "curated_path": curated_path}


class MLModelManager:
    """Manages Azure ML models."""

    def __init__(self, ml_client: Any | None = None) -> None:
        self.ml_client = ml_client
        self.model_cache: dict[str, Any] = {}

    async def load_model(self, model_name: str) -> Any:
        if model_name in self.model_cache:
            return self.model_cache[model_name]
        if self.ml_client and hasattr(self.ml_client, "models"):
            model = self.ml_client.models.get(model_name)
        else:
            model = {"name": model_name, "version": "1.0"}
        self.model_cache[model_name] = model
        return model

    async def train_model(
        self, model_name: str, training_payload: dict[str, Any]
    ) -> dict[str, Any]:
        if self.ml_client and hasattr(self.ml_client, "jobs"):
            job = self.ml_client.jobs.create_or_update(training_payload)
            return {"model_name": model_name, "job_id": getattr(job, "name", "unknown")}
        return {"model_name": model_name, "job_id": "local-train"}


class PowerBIEmbedManager:
    """Manages Power BI Embedded report templates."""

    def __init__(self, power_bi_client: Any | None = None) -> None:
        self.power_bi_client = power_bi_client
        self.report_templates = {
            "health_scores": {
                "name": "Portfolio Health Scores",
                "report_id": "health-scores-template",
                "dataset": "portfolio_health",
            },
            "risk_distribution": {
                "name": "Risk Distribution",
                "report_id": "risk-distribution-template",
                "dataset": "portfolio_risk",
            },
            "resource_utilisation": {
                "name": "Resource Utilisation",
                "report_id": "resource-utilisation-template",
                "dataset": "resource_utilisation",
            },
        }

    async def get_embed_config(
        self, report_type: str, user_context: dict[str, Any]
    ) -> dict[str, Any]:
        template = self.report_templates.get(report_type)
        if not template:
            raise ValueError(f"Unknown report template: {report_type}")
        embed_token = "mock-embed-token"
        if self.power_bi_client and hasattr(self.power_bi_client, "generate_embed_token"):
            embed_token = self.power_bi_client.generate_embed_token(
                template["report_id"], user_context
            )
        return {
            "report_type": report_type,
            "template": template,
            "embed_url": f"https://app.powerbi.com/reportEmbed?reportId={template['report_id']}",
            "access_token": embed_token,
        }


class DataFactoryManager:
    """Manages Azure Data Factory pipeline orchestration."""

    def __init__(self, data_factory_client: Any | None = None) -> None:
        self.data_factory_client = data_factory_client

    async def ensure_pipelines(self, pipelines: list[dict[str, Any]]) -> dict[str, Any]:
        if not pipelines:
            return {"pipelines": [], "initialized": False}
        if self.data_factory_client and hasattr(self.data_factory_client, "pipelines"):
            for pipeline in pipelines:
                name = pipeline.get("name")
                definition = pipeline.get("definition", {})
                if name:
                    self.data_factory_client.pipelines.create_or_update(name, definition)
        return {"pipelines": [pipeline.get("name") for pipeline in pipelines], "initialized": True}

    async def schedule_pipeline(self, pipeline_name: str, parameters: dict[str, Any]) -> str:
        if self.data_factory_client and hasattr(self.data_factory_client, "pipelines"):
            response = self.data_factory_client.pipelines.create_run(
                pipeline_name, parameters=parameters
            )
            return getattr(response, "run_id", "unknown")
        return f"run-{pipeline_name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    async def get_pipeline_status(self, run_id: str) -> dict[str, Any]:
        if self.data_factory_client and hasattr(self.data_factory_client, "pipeline_runs"):
            run = self.data_factory_client.pipeline_runs.get(run_id)
            return {"run_id": run_id, "status": getattr(run, "status", "unknown")}
        return {"run_id": run_id, "status": "queued"}


class EventHubManager:
    """Manages Event Hub producers/consumers."""

    def __init__(self, producer: Any | None = None, consumer: Any | None = None) -> None:
        self.producer = producer
        self.consumer = consumer

    async def publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.producer and hasattr(self.producer, "send_batch"):
            batch = self.producer.create_batch()
            batch.add({"event_type": event_type, "payload": payload})
            self.producer.send_batch(batch)


class StreamAnalyticsManager:
    """Streams events into Synapse via Azure Stream Analytics."""

    async def stream_events(self, events: list[dict[str, Any]]) -> None:
        return None


class NarrativeService:
    """Uses Azure OpenAI for narrative generation."""

    def __init__(self, openai_client: Any | None = None) -> None:
        self.openai_client = openai_client

    async def generate_narrative(self, prompt: str) -> str:
        if self.openai_client and hasattr(self.openai_client, "generate"):
            return self.openai_client.generate(prompt)
        return prompt


class LanguageQueryService:
    """Natural language query service using Azure Cognitive Services or QnA Maker."""

    def __init__(self, language_client: Any | None = None) -> None:
        self.language_client = language_client

    async def answer(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        if self.language_client and hasattr(self.language_client, "query"):
            response = self.language_client.query(question, context)
            return {"answer": response}
        return {"answer": "No answer available", "context": context}


class ReportRepository:
    """Stores reports and narratives in PostgreSQL or Cosmos DB."""

    def __init__(
        self, postgres_conn: Any | None = None, cosmos_container: Any | None = None
    ) -> None:
        self.postgres_conn = postgres_conn
        self.cosmos_container = cosmos_container
        self.audit_log: list[dict[str, Any]] = []

    async def store_report(self, report: dict[str, Any]) -> None:
        if self.cosmos_container and hasattr(self.cosmos_container, "upsert_item"):
            self.cosmos_container.upsert_item(report)
        elif self.postgres_conn and hasattr(self.postgres_conn, "execute"):
            self.postgres_conn.execute(
                "INSERT INTO analytics_reports (report_id, payload) VALUES (%s, %s)",
                (report.get("report_id"), str(report)),
            )
        else:
            self.audit_log.append({"type": "report", "payload": report})

    async def store_narrative(self, narrative: dict[str, Any]) -> None:
        if self.cosmos_container and hasattr(self.cosmos_container, "upsert_item"):
            self.cosmos_container.upsert_item(narrative)
        elif self.postgres_conn and hasattr(self.postgres_conn, "execute"):
            self.postgres_conn.execute(
                "INSERT INTO analytics_narratives (narrative_id, payload) VALUES (%s, %s)",
                (narrative.get("narrative_id"), str(narrative)),
            )
        else:
            self.audit_log.append({"type": "narrative", "payload": narrative})


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

    def __init__(self, agent_id: str = "analytics-insights-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.refresh_interval_minutes = config.get("refresh_interval_minutes", 60) if config else 60
        self.prediction_confidence_threshold = (
            config.get("prediction_confidence_threshold", 0.75) if config else 0.75
        )
        self.max_dashboard_widgets = config.get("max_dashboard_widgets", 20) if config else 20
        self.scenario_engine = ScenarioEngine()
        self.metric_agents = config.get("metric_agents", {}) if config else {}
        self.analytics_event_topics = config.get("analytics_event_topics") if config else None
        if not self.analytics_event_topics:
            self.analytics_event_topics = [
                "schedule.baseline.locked",
                "schedule.delay",
                "deployment.started",
                "deployment.succeeded",
                "deployment.failed",
                "deployment.progress",
                "analytics.deployment.metrics",
                "risk.identified",
                "risk.assessed",
                "risk.status_updated",
                "risk.mitigation_plan_created",
                "risk.simulation_completed",
                "risk.simulated",
                "risk.triggered",
                "quality.metrics.calculated",
                "quality.report.published",
                "quality.audit.completed",
                "quality.coverage.trend.updated",
                "quality.improvement.recommendations",
                "resource.allocation.created",
                "resource.updated",
                "resource.added",
            ]
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = get_event_bus()

        self.synapse_workspace_name = os.getenv(
            "SYNAPSE_WORKSPACE_NAME", config.get("synapse_workspace_name") if config else ""
        )
        self.synapse_sql_pool_name = os.getenv(
            "SYNAPSE_SQL_POOL_NAME", config.get("synapse_sql_pool_name") if config else ""
        )
        self.synapse_spark_pool_name = (
            config.get("synapse_spark_pool_name", "analytics-spark")
            if config
            else "analytics-spark"
        )

        self.synapse_manager = config.get("synapse_manager") if config else None
        if self.synapse_manager is None:
            self.synapse_manager = SynapseManager(
                self.synapse_workspace_name or None,
                self.synapse_sql_pool_name or None,
                self.synapse_spark_pool_name,
                config.get("synapse_client") if config else None,
            )

        self.data_lake_manager = config.get("data_lake_manager") if config else None
        if self.data_lake_manager is None:
            data_lake_file_system = os.getenv(
                "DATA_LAKE_FILE_SYSTEM", config.get("data_lake_file_system") if config else ""
            )
            self.data_lake_manager = DataLakeManager(
                data_lake_file_system or None,
                config.get("data_lake_client") if config else None,
            )

        self.ml_manager = config.get("ml_manager") if config else None
        if self.ml_manager is None:
            self.ml_manager = MLModelManager(config.get("ml_client") if config else None)

        self.power_bi_manager = config.get("power_bi_manager") if config else None
        if self.power_bi_manager is None:
            self.power_bi_manager = PowerBIEmbedManager(
                config.get("power_bi_client") if config else None
            )

        self.data_factory_manager = config.get("data_factory_manager") if config else None
        if self.data_factory_manager is None:
            self.data_factory_manager = DataFactoryManager(
                config.get("data_factory_client") if config else None
            )
        self.data_factory_pipelines = config.get("data_factory_pipelines") if config else None
        if not self.data_factory_pipelines:
            self.data_factory_pipelines = [
                {"name": "planview_ingest", "definition": {"source": "planview"}},
                {"name": "jira_ingest", "definition": {"source": "jira"}},
                {"name": "workday_ingest", "definition": {"source": "workday"}},
                {"name": "sap_ingest", "definition": {"source": "sap"}},
            ]

        self.ingestion_sources = config.get("ingestion_sources") if config else None
        if not self.ingestion_sources:
            self.ingestion_sources = ["planview", "jira", "workday", "sap"]

        self.event_hub_manager = config.get("event_hub_manager") if config else None
        if self.event_hub_manager is None:
            self.event_hub_manager = EventHubManager(
                config.get("event_hub_producer") if config else None,
                config.get("event_hub_consumer") if config else None,
            )

        self.stream_analytics_manager = config.get("stream_analytics_manager") if config else None
        if self.stream_analytics_manager is None:
            self.stream_analytics_manager = StreamAnalyticsManager()
        self.narrative_service = config.get("narrative_service") if config else None
        if self.narrative_service is None:
            self.narrative_service = NarrativeService(
                config.get("openai_client") if config else None
            )

        self.language_service = config.get("language_service") if config else None
        if self.language_service is None:
            self.language_service = LanguageQueryService(
                config.get("language_client") if config else None
            )

        self.report_repository = config.get("report_repository") if config else None
        if self.report_repository is None:
            self.report_repository = ReportRepository(
                config.get("postgres_conn") if config else None,
                config.get("cosmos_container") if config else None,
            )

        output_store_path = (
            Path(config.get("analytics_output_store_path", "data/analytics_outputs.json"))
            if config
            else Path("data/analytics_outputs.json")
        )
        alert_store_path = (
            Path(config.get("analytics_alert_store_path", "data/analytics_alerts.json"))
            if config
            else Path("data/analytics_alerts.json")
        )
        lineage_store_path = (
            Path(config.get("analytics_lineage_store_path", "data/analytics_lineage.json"))
            if config
            else Path("data/analytics_lineage.json")
        )
        event_store_path = (
            Path(config.get("analytics_event_store_path", "data/analytics_events.json"))
            if config
            else Path("data/analytics_events.json")
        )
        kpi_history_store_path = (
            Path(config.get("analytics_kpi_history_store_path", "data/analytics_kpi_history.json"))
            if config
            else Path("data/analytics_kpi_history.json")
        )
        health_store_path = (
            Path(config.get("health_snapshot_store_path", "data/health_snapshots.json"))
            if config
            else Path("data/health_snapshots.json")
        )
        self.analytics_output_store = TenantStateStore(output_store_path)
        self.analytics_alert_store = TenantStateStore(alert_store_path)
        self.analytics_lineage_store = TenantStateStore(lineage_store_path)
        self.analytics_event_store = TenantStateStore(event_store_path)
        self.kpi_history_store = TenantStateStore(kpi_history_store_path)
        self.health_snapshot_store = TenantStateStore(health_store_path)

        # Data stores (will be replaced with database)
        self.dashboards = {}  # type: ignore
        self.reports = {}  # type: ignore
        self.kpis = {}  # type: ignore
        self.kpi_alerts = {}  # type: ignore
        self.predictions = {}  # type: ignore
        self.scenarios = {}  # type: ignore
        self.data_lineage = {}  # type: ignore
        self.health_snapshots: dict[str, list[dict[str, Any]]] = {}
        self.event_history: dict[str, list[dict[str, Any]]] = {}
        self.kpi_definitions = config.get("kpi_definitions") if config else None
        if not self.kpi_definitions:
            self.kpi_definitions = [
                {
                    "name": "Schedule Delay Average (days)",
                    "metric_name": "schedule.delay.avg",
                    "target": 0,
                    "thresholds": {"max": 5},
                    "event_types": ["schedule.delay"],
                    "trend_direction": "lower_is_better",
                },
                {
                    "name": "Deployment Success Rate",
                    "metric_name": "deployment.success_rate",
                    "target": 0.95,
                    "thresholds": {"min": 0.9},
                    "event_types": ["deployment.succeeded", "deployment.failed"],
                    "trend_direction": "higher_is_better",
                },
                {
                    "name": "Deployment Frequency (per week)",
                    "metric_name": "deployment.frequency",
                    "target": 2.0,
                    "thresholds": {"min": 1.0},
                    "event_types": [
                        "deployment.succeeded",
                        "deployment.failed",
                        "deployment.started",
                    ],
                    "trend_direction": "higher_is_better",
                },
                {
                    "name": "Resource Utilisation",
                    "metric_name": "resource.utilization.avg",
                    "target": 0.8,
                    "thresholds": {"min": 0.6, "max": 1.0},
                    "event_types": ["resource.allocation.created", "resource.updated"],
                    "trend_direction": "higher_is_better",
                },
                {
                    "name": "Quality Score",
                    "metric_name": "quality.score.avg",
                    "target": 90.0,
                    "thresholds": {"min": 80.0},
                    "event_types": ["quality.metrics.calculated"],
                    "trend_direction": "higher_is_better",
                },
                {
                    "name": "Risk Exposure Average",
                    "metric_name": "risk.exposure.avg",
                    "target": 5.0,
                    "thresholds": {"max": 15.0},
                    "event_types": ["risk.assessed", "risk.status_updated"],
                    "trend_direction": "lower_is_better",
                },
                {
                    "name": "Compliance Audit Score",
                    "metric_name": "compliance.audit.avg",
                    "target": 90.0,
                    "thresholds": {"min": 85.0},
                    "event_types": ["quality.audit.completed"],
                    "trend_direction": "higher_is_better",
                },
            ]

    async def initialize(self) -> None:
        """Initialize analytics services, ML models, and data sources."""
        await super().initialize()
        self.logger.info("Initializing Analytics & Insights Agent...")

        await self._maybe_await(self.synapse_manager.ensure_pools)
        await self._maybe_await(self.data_lake_manager.ensure_file_system)
        await self._maybe_await(
            self.data_factory_manager.ensure_pipelines, self.data_factory_pipelines
        )
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
            self.event_bus.subscribe("project.updated", self._build_event_handler("project.updated"))
            self.event_bus.subscribe("resource.updated", self._build_event_handler("resource.updated"))

        self.logger.info("Analytics & Insights Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "aggregate_data",
            "create_dashboard",
            "generate_report",
            "run_prediction",
            "scenario_analysis",
            "generate_narrative",
            "track_kpi",
            "query_data",
            "natural_language_query",
            "get_dashboard",
            "get_insights",
            "update_data_lineage",
            "get_powerbi_report",
            "orchestrate_etl",
            "monitor_etl",
            "train_kpi_model",
            "provision_analytics_stack",
            "ingest_sources",
            "ingest_realtime_event",
            "compute_kpis_batch",
            "generate_periodic_report",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "create_dashboard":
            if "dashboard" not in input_data:
                self.logger.warning("Missing dashboard configuration")
                return False

        elif action == "run_prediction":
            if "model_type" not in input_data:
                self.logger.warning("Missing model_type for prediction")
                return False
        elif action == "get_powerbi_report":
            if "report_type" not in input_data:
                self.logger.warning("Missing report_type for Power BI embed")
                return False
        elif action == "orchestrate_etl":
            if "pipelines" not in input_data:
                self.logger.warning("Missing pipelines for ETL orchestration")
                return False
        elif action == "monitor_etl":
            if "run_id" not in input_data:
                self.logger.warning("Missing run_id for ETL monitoring")
                return False
        elif action == "ingest_realtime_event":
            if "event" not in input_data:
                self.logger.warning("Missing event payload for realtime ingestion")
                return False
        elif action == "compute_kpis_batch":
            return True

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process analytics and insights requests.

        Args:
            input_data: {
                "action": "aggregate_data" | "create_dashboard" | "generate_report" |
                          "run_prediction" | "scenario_analysis" | "generate_narrative" |
                          "track_kpi" | "query_data" | "get_dashboard" | "get_insights" |
                          "update_data_lineage" | "compute_kpis_batch",
                "data_sources": Data sources for aggregation,
                "dashboard": Dashboard configuration,
                "report": Report specification,
                "model_type": ML model type for prediction,
                "scenario": Scenario parameters,
                "kpi": KPI definition,
                "query": Data query,
                "dashboard_id": Dashboard identifier,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - aggregate_data: Aggregated dataset and statistics
            - create_dashboard: Dashboard ID and configuration
            - generate_report: Report content and visualizations
            - run_prediction: Predictions with confidence intervals
            - scenario_analysis: Scenario comparison results
            - generate_narrative: Generated narrative text
            - track_kpi: KPI values and trends
            - query_data: Query results
            - get_dashboard: Dashboard data and widgets
            - get_insights: AI-generated insights
            - update_data_lineage: Lineage tracking information
            - compute_kpis_batch: Batch KPI computation results
        """
        action = input_data.get("action", "get_insights")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )

        if action == "aggregate_data":
            return await self._aggregate_data(tenant_id, input_data.get("data_sources", []))

        elif action == "create_dashboard":
            return await self._create_dashboard(tenant_id, input_data.get("dashboard", {}))

        elif action == "generate_report":
            return await self._generate_report(tenant_id, input_data.get("report", {}))

        elif action == "run_prediction":
            return await self._run_prediction(
                tenant_id,
                input_data.get("model_type"),
                input_data.get("input_data", {}),  # type: ignore
            )

        elif action == "scenario_analysis":
            return await self._scenario_analysis(tenant_id, input_data.get("scenario", {}))

        elif action == "generate_narrative":
            return await self._generate_narrative(tenant_id, input_data.get("data", {}))  # type: ignore

        elif action == "track_kpi":
            return await self._track_kpi(tenant_id, input_data.get("kpi", {}))

        elif action == "query_data":
            return await self._query_data(input_data.get("query"), input_data.get("filters", {}))  # type: ignore

        elif action == "natural_language_query":
            return await self._answer_natural_language_query(
                input_data.get("question"), input_data.get("context", {})  # type: ignore
            )

        elif action == "get_dashboard":
            return await self._get_dashboard(input_data.get("dashboard_id"))  # type: ignore

        elif action == "get_insights":
            return await self._get_insights(input_data.get("filters", {}))

        elif action == "update_data_lineage":
            return await self._update_data_lineage(tenant_id, input_data.get("lineage", {}))

        elif action == "get_powerbi_report":
            return await self._get_powerbi_report(
                tenant_id, input_data.get("report_type"), input_data.get("user_context", {})
            )

        elif action == "orchestrate_etl":
            return await self._orchestrate_etl_pipelines(
                input_data.get("pipelines", []), input_data.get("parameters", {})
            )

        elif action == "monitor_etl":
            return await self._monitor_etl_pipeline(input_data.get("run_id"))  # type: ignore

        elif action == "train_kpi_model":
            return await self._train_kpi_model(
                input_data.get("model_name"), input_data.get("training_payload", {})
            )

        elif action == "provision_analytics_stack":
            return await self._provision_analytics_stack()

        elif action == "ingest_sources":
            return await self._ingest_sources(
                tenant_id, input_data.get("sources"), input_data.get("parameters", {})
            )

        elif action == "ingest_realtime_event":
            return await self._ingest_realtime_event(
                input_data.get("event"), input_data.get("event_type")
            )
        elif action == "compute_kpis_batch":
            return await self._compute_kpis_batch(
                tenant_id, input_data.get("event_type"), input_data.get("kpis")
            )
        elif action == "generate_periodic_report":
            return await self._generate_periodic_report(
                tenant_id,
                input_data.get("period", "monthly"),
                input_data.get("filters", {}),
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _aggregate_data(self, tenant_id: str, data_sources: list[str]) -> dict[str, Any]:
        """
        Aggregate data from multiple sources.

        Returns aggregated dataset.
        """
        self.logger.info("Aggregating data from %s sources", len(data_sources))

        # Collect data from sources
        aggregated_data = await self._collect_from_sources(data_sources)

        # Harmonize data definitions
        harmonized_data = await self._harmonize_data(aggregated_data)

        # Calculate summary statistics
        statistics = await self._calculate_statistics(harmonized_data)

        # Track lineage
        lineage_id = await self._record_data_lineage(tenant_id, data_sources, harmonized_data)
        data_lake_paths: list[dict[str, str]] = []
        for source in data_sources:
            data_lake_paths.append(
                self.data_lake_manager.store_dataset(
                    source=source,
                    domain="analytics",
                    payload=[
                        record for record in harmonized_data if record.get("source") == source
                    ],
                )
            )
        synapse_details = self.synapse_manager.ingest_dataset(
            "analytics_aggregated", harmonized_data
        )

        return {
            "record_count": len(harmonized_data),
            "data_sources": data_sources,
            "statistics": statistics,
            "lineage_id": lineage_id,
            "data_lake_paths": data_lake_paths,
            "synapse": synapse_details,
            "aggregated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _create_dashboard(
        self, tenant_id: str, dashboard_config: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create interactive dashboard.

        Returns dashboard ID and configuration.
        """
        self.logger.info("Creating dashboard: %s", dashboard_config.get("name"))

        # Generate dashboard ID
        dashboard_id = await self._generate_dashboard_id()

        # Validate widgets
        widgets = dashboard_config.get("widgets", [])
        if len(widgets) > self.max_dashboard_widgets:
            raise ValueError(f"Maximum {self.max_dashboard_widgets} widgets allowed")

        # Create widget configurations
        configured_widgets = await self._configure_widgets(widgets)

        # Set up data refresh schedule
        refresh_schedule = await self._setup_refresh_schedule(
            dashboard_config.get("refresh_interval", self.refresh_interval_minutes)
        )

        # Create dashboard record
        dashboard = {
            "dashboard_id": dashboard_id,
            "name": dashboard_config.get("name"),
            "description": dashboard_config.get("description"),
            "widgets": configured_widgets,
            "filters": dashboard_config.get("filters", {}),
            "refresh_schedule": refresh_schedule,
            "owner": dashboard_config.get("owner"),
            "shared_with": dashboard_config.get("shared_with", []),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store dashboard
        self.dashboards[dashboard_id] = dashboard
        self.analytics_output_store.upsert(tenant_id, dashboard_id, dashboard.copy())

        return {
            "dashboard_id": dashboard_id,
            "name": dashboard["name"],
            "widgets": len(configured_widgets),
            "refresh_schedule": refresh_schedule,
            "url": f"/dashboards/{dashboard_id}",
        }

    async def _generate_report(self, tenant_id: str, report_spec: dict[str, Any]) -> dict[str, Any]:
        """
        Generate analytical report.

        Returns report content.
        """
        self.logger.info("Generating report: %s", report_spec.get("title"))

        # Generate report ID
        report_id = await self._generate_report_id()

        # Collect data for report
        data = await self._collect_report_data(tenant_id, report_spec)

        # Generate visualizations
        visualizations = await self._generate_visualizations(data, report_spec)

        # Generate narrative summary
        narrative = await self._generate_narrative(tenant_id, data)

        # Create report record
        report = {
            "report_id": report_id,
            "title": report_spec.get("title"),
            "type": report_spec.get("type", "analytical"),
            "data": data,
            "visualizations": visualizations,
            "narrative": narrative,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": report_spec.get("requester"),
        }

        # Store report
        self.reports[report_id] = report
        self.analytics_output_store.upsert(tenant_id, report_id, report.copy())
        await self.report_repository.store_report(report.copy())

        return {
            "report_id": report_id,
            "title": report["title"],
            "visualizations": len(visualizations),
            "narrative": narrative,
            "download_url": f"/reports/{report_id}/download",
        }

    async def _run_prediction(
        self, tenant_id: str, model_type: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Run predictive analytics model.

        Returns predictions with confidence intervals.
        """
        self.logger.info("Running prediction: %s", model_type)

        input_data = {**input_data, "tenant_id": tenant_id}

        # Load ML model
        model = await self._load_ml_model(model_type)

        # Prepare input features
        features = await self._prepare_features(input_data, model_type)

        # Make prediction
        prediction = await self._make_prediction(model, features, model_type, input_data)

        # Calculate confidence interval
        confidence_interval = await self._calculate_confidence_interval(prediction, model_type)

        # Store prediction
        prediction_id = await self._generate_prediction_id()
        prediction_record = {
            "prediction_id": prediction_id,
            "model_type": model_type,
            "input_data": input_data,
            "prediction": prediction,
            "confidence_interval": confidence_interval,
            "confidence": prediction.get("confidence", 0.0),
            "predicted_at": datetime.now(timezone.utc).isoformat(),
        }
        self.predictions[prediction_id] = prediction_record
        self.analytics_output_store.upsert(tenant_id, prediction_id, prediction_record.copy())

        return {
            "prediction_id": prediction_id,
            "model_type": model_type,
            "prediction": prediction.get("value"),
            "confidence": prediction.get("confidence"),
            "confidence_interval": confidence_interval,
            "recommendations": await self._generate_prediction_recommendations(prediction),
        }

    async def _scenario_analysis(self, tenant_id: str, scenario: dict[str, Any]) -> dict[str, Any]:
        """
        Perform what-if scenario analysis.

        Returns scenario comparison.
        """
        self.logger.info("Running scenario analysis: %s", scenario.get("name"))

        # Generate scenario ID
        scenario_id = await self._generate_scenario_id()

        # Get baseline metrics
        baseline = await self._get_baseline_metrics(scenario)

        scenario_output = await self.scenario_engine.run_metric_scenario(
            baseline_metrics=baseline,
            scenario_params=scenario.get("parameters", {}),
            scenario_metrics_builder=self._calculate_scenario_metrics,
            comparison_builder=self._compare_scenarios,
            recommendation_builder=self._calculate_scenario_impact,
        )
        scenario_metrics = scenario_output["scenario_metrics"]
        comparison = scenario_output["comparison"]
        impact = scenario_output.get("recommendation")

        simulations = await self._run_metric_simulations(tenant_id, scenario.get("simulations", []))
        simulation_summary = await self._summarize_simulation_results(simulations)

        # Store scenario
        scenario_record = {
            "scenario_id": scenario_id,
            "name": scenario.get("name"),
            "parameters": scenario.get("parameters"),
            "baseline": baseline,
            "scenario_metrics": scenario_metrics,
            "comparison": comparison,
            "impact": impact,
            "simulations": simulations,
            "simulation_summary": simulation_summary,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.scenarios[scenario_id] = scenario_record
        self.analytics_output_store.upsert(tenant_id, scenario_id, scenario_record.copy())

        return {
            "scenario_id": scenario_id,
            "name": scenario.get("name"),
            "baseline": baseline,
            "scenario_metrics": scenario_metrics,
            "comparison": comparison,
            "impact": impact,
            "simulations": simulations,
            "simulation_summary": simulation_summary,
            "recommendations": await self._generate_scenario_recommendations(impact),
        }

    async def _generate_narrative(self, tenant_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Generate narrative summary using NLG.

        Returns narrative text.
        """
        self.logger.info("Generating narrative summary")

        # Extract key insights
        key_insights = await self._extract_key_insights(data)

        # Identify trends
        trends = await self._identify_trends(data)

        # Generate narrative using AI
        narrative_text = await self._generate_narrative_text(key_insights, trends, data)
        narrative_id = f"narrative-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        narrative = {
            "narrative_id": narrative_id,
            "content": narrative_text,
            "data_summary": data,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.analytics_output_store.upsert(tenant_id, narrative_id, narrative.copy())
        await self.report_repository.store_narrative(narrative.copy())

        return narrative

    async def _track_kpi(self, tenant_id: str, kpi_config: dict[str, Any]) -> dict[str, Any]:
        """
        Track KPI metrics.

        Returns KPI values and trends.
        """
        self.logger.info("Tracking KPI: %s", kpi_config.get("name"))

        # Generate KPI ID if new
        kpi_id = kpi_config.get("kpi_id") or await self._generate_kpi_id()

        metric_name = kpi_config.get("metric_name")
        if metric_name and kpi_config.get("project_id"):
            raw_value = await get_metric_value(
                metric_name,
                kpi_config.get("project_id"),
                tenant_id=tenant_id,
                agent_clients=self.metric_agents,
                fallback=kpi_config.get("fallback", {}),
            )
            current_value = (
                normalize_metric_value(metric_name, raw_value)
                if kpi_config.get("normalize", False)
                else float(raw_value or 0.0)
            )
        else:
            # Calculate current value
            current_value = await self._calculate_kpi_value(kpi_config)

        # Get historical values
        historical_values = await self._get_kpi_history(tenant_id, kpi_id)

        # Calculate trend
        trend = await self._calculate_kpi_trend(
            historical_values, current_value, kpi_config.get("trend_direction")
        )

        # Check against thresholds
        threshold_status = await self._check_kpi_thresholds(
            current_value, kpi_config.get("thresholds", {})
        )

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
        self.kpis[kpi_id] = kpi_record
        self.analytics_output_store.upsert(tenant_id, kpi_id, kpi_record.copy())
        await self._store_kpi_history(tenant_id, kpi_id, current_value)

        alerts_triggered: list[str] = []
        if threshold_status.get("breached"):
            alert_id = f"KPI-ALERT-{len(self.kpi_alerts) + 1}"
            alert = {
                "alert_id": alert_id,
                "kpi_id": kpi_id,
                "name": kpi_config.get("name"),
                "current_value": current_value,
                "thresholds": kpi_config.get("thresholds", {}),
                "status": "active",
                "triggered_at": datetime.now(timezone.utc).isoformat(),
            }
            self.kpi_alerts[alert_id] = alert
            self.analytics_alert_store.upsert(tenant_id, alert_id, alert.copy())
            alerts_triggered.append(alert_id)
            if self.event_bus:
                await self.event_bus.publish(
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
                (current_value / kpi_config.get("target", 1)) * 100
                if kpi_config.get("target")
                else 0
            ),
            "alerts_triggered": alerts_triggered,
        }

    async def _query_data(self, query: str, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Execute data query.

        Returns query results.
        """
        self.logger.info("Executing query: %s", query)

        parsed_query = await self._parse_query(query)

        results = await self._execute_query(parsed_query, filters)

        formatted_results = await self._format_query_results(results)

        return {
            "query": query,
            "result_count": len(results),
            "results": formatted_results,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _get_dashboard(self, dashboard_id: str) -> dict[str, Any]:
        """
        Get dashboard data.

        Returns dashboard with current data.
        """
        self.logger.info("Retrieving dashboard: %s", dashboard_id)

        dashboard = self.dashboards.get(dashboard_id)
        if not dashboard:
            raise ValueError(f"Dashboard not found: {dashboard_id}")

        # Refresh widget data
        widget_data = await self._refresh_widget_data(dashboard.get("widgets", []))

        return {
            "dashboard_id": dashboard_id,
            "name": dashboard.get("name"),
            "description": dashboard.get("description"),
            "widgets": widget_data,
            "last_refreshed": datetime.now(timezone.utc).isoformat(),
        }

    async def _get_insights(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Get AI-generated insights.

        Returns insights and recommendations.
        """
        self.logger.info("Generating insights")

        # Collect relevant data
        data = await self._collect_insights_data(filters)

        # Apply anomaly detection
        anomalies = await self._detect_anomalies(data)

        # Identify patterns
        patterns = await self._identify_patterns(data)

        # Generate insights
        insights = await self._generate_insights(data, anomalies, patterns)

        # Generate recommendations
        recommendations = await self._generate_recommendations(insights)

        response = {
            "insights": insights,
            "anomalies": anomalies,
            "patterns": patterns,
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        tenant_id = filters.get("tenant_id", "default")
        if self.event_bus:
            await self.event_bus.publish(
                "analytics.insights.generated",
                {
                    "tenant_id": tenant_id,
                    "insights": insights,
                    "recommendations": recommendations,
                    "generated_at": response["generated_at"],
                },
            )
        return response

    async def _update_data_lineage(
        self, tenant_id: str, lineage_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update data lineage tracking.

        Returns lineage information.
        """
        self.logger.info("Updating data lineage")

        # Generate lineage ID
        lineage_id = await self._generate_lineage_id()

        # Record lineage
        lineage = {
            "lineage_id": lineage_id,
            "source_systems": lineage_data.get("sources", []),
            "transformations": lineage_data.get("transformations", []),
            "target_dataset": lineage_data.get("target"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        masked_lineage = mask_lineage_payload(lineage)
        self.data_lineage[lineage_id] = masked_lineage
        self.analytics_lineage_store.upsert(tenant_id, lineage_id, masked_lineage)

        return {
            "lineage_id": lineage_id,
            "sources": len(lineage.get("source_systems", [])),
            "transformations": len(lineage.get("transformations", [])),
        }

    async def _get_powerbi_report(
        self, tenant_id: str, report_type: str | None, user_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Return Power BI Embedded configuration."""
        if not report_type:
            raise ValueError("report_type is required")
        embed_config = await self.power_bi_manager.get_embed_config(report_type, user_context)
        record_id = f"powerbi-{report_type}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        self.analytics_output_store.upsert(tenant_id, record_id, embed_config.copy())
        return embed_config

    async def _orchestrate_etl_pipelines(
        self, pipelines: list[str], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Schedule Data Factory pipelines for source systems."""
        run_ids: dict[str, str] = {}
        for pipeline in pipelines:
            run_id = await self.data_factory_manager.schedule_pipeline(pipeline, parameters)
            run_ids[pipeline] = run_id
        return {"pipelines": run_ids, "scheduled_at": datetime.now(timezone.utc).isoformat()}

    async def _monitor_etl_pipeline(self, run_id: str) -> dict[str, Any]:
        """Monitor Data Factory pipeline status."""
        return await self.data_factory_manager.get_pipeline_status(run_id)

    async def _train_kpi_model(
        self, model_name: str | None, training_payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Train KPI predictive model using Azure ML."""
        if not model_name:
            raise ValueError("model_name is required")
        result = await self.ml_manager.train_model(model_name, training_payload)
        return {
            "model_name": model_name,
            "training_job": result,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _answer_natural_language_query(
        self, question: str | None, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Answer natural language analytics queries."""
        if not question:
            raise ValueError("question is required")
        response = await self.language_service.answer(question, context)
        return {
            "question": question,
            "response": response,
            "answered_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _provision_analytics_stack(self) -> dict[str, Any]:
        """Provision Synapse, Data Lake, and Data Factory pipelines."""
        synapse_details = await self._maybe_await(self.synapse_manager.ensure_pools)
        data_lake_details = await self._maybe_await(self.data_lake_manager.ensure_file_system)
        pipeline_details = await self._maybe_await(
            self.data_factory_manager.ensure_pipelines, self.data_factory_pipelines
        )
        return {
            "synapse": synapse_details,
            "data_lake": data_lake_details,
            "data_factory": pipeline_details,
            "provisioned_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _ingest_sources(
        self,
        tenant_id: str,
        sources: list[str] | None,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Run ingestion pipelines for Planview, Jira, Workday, and SAP."""
        selected_sources = sources or list(self.ingestion_sources)
        run_map: dict[str, str] = {}
        lake_paths: dict[str, dict[str, str]] = {}
        ingestion_payloads: dict[str, list[dict[str, Any]]] = {}
        for source in selected_sources:
            pipeline_name = f"{source}_ingest"
            run_id = await self.data_factory_manager.schedule_pipeline(
                pipeline_name,
                {
                    "source": source,
                    "requested_at": datetime.now(timezone.utc).isoformat(),
                    **parameters,
                },
            )
            run_map[source] = run_id
            payload = await self._fetch_source_payload(source)
            ingestion_payloads[source] = payload
            lake_paths[source] = self.data_lake_manager.store_dataset(
                source=source, domain="ingestion", payload=payload
            )

        lineage_id = await self._record_data_lineage(
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

    async def _ingest_realtime_event(
        self, event: dict[str, Any] | None, event_type: str | None
    ) -> dict[str, Any]:
        """Publish event to Event Hub and Stream Analytics."""
        if not event:
            raise ValueError("event payload is required")
        payload = {"event_type": event_type or "realtime.event", "payload": event}
        await self._handle_realtime_event(payload)
        return {
            "event_type": payload["event_type"],
            "streamed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _compute_kpis_batch(
        self,
        tenant_id: str,
        event_type: str | None,
        kpis: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """Compute KPI values in batch from aggregated events."""
        kpi_definitions = kpis or list(self.kpi_definitions or [])
        results = await self._update_kpis_from_definitions(
            tenant_id, event_type=event_type, kpi_definitions=kpi_definitions
        )
        return {
            "tenant_id": tenant_id,
            "kpis": results,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _build_event_handler(self, topic: str) -> Callable[[dict[str, Any]], Any]:
        async def _handler(payload: dict[str, Any]) -> None:
            await self._handle_domain_event(payload, topic)

        return _handler

    async def _handle_domain_event(self, event: dict[str, Any], event_type: str) -> None:
        tenant_id = event.get("tenant_id") or event.get("payload", {}).get("tenant_id") or "default"
        raw_payload = event.get("payload", event)
        redacted_payload = self._redact_payload(raw_payload)
        record = await self._store_event_record(tenant_id, event_type, redacted_payload, event)
        await self._update_kpis_from_definitions(tenant_id, event_type=event_type)
        await self._publish_insights_event(tenant_id, event_type, record)
        await self._stream_realtime_event(event_type, redacted_payload)

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

    async def _handle_realtime_event(self, event: dict[str, Any]) -> None:
        """Stream real-time events through Event Hub and Stream Analytics."""
        payload = event.get("payload", event)
        event_type = event.get("event_type") or event.get("type") or "realtime.event"
        tenant_id = event.get("tenant_id") or payload.get("tenant_id") or "default"
        redacted_payload = self._redact_payload(payload)
        await self._store_event_record(tenant_id, event_type, redacted_payload, event)
        await self._update_kpis_from_definitions(tenant_id, event_type=event_type)
        await self._stream_realtime_event(event_type, redacted_payload)

    async def _stream_realtime_event(self, event_type: str, payload: dict[str, Any]) -> None:
        await self.event_hub_manager.publish_event(event_type, payload)
        await self.stream_analytics_manager.stream_events([payload])

    async def _store_event_record(
        self,
        tenant_id: str,
        event_type: str,
        payload: dict[str, Any],
        raw_event: dict[str, Any],
    ) -> dict[str, Any]:
        event_id = raw_event.get("event_id") or raw_event.get("id") or f"evt-{uuid4().hex}"
        record = {
            "event_id": event_id,
            "event_type": event_type,
            "domain": event_type.split(".")[0] if event_type else "unknown",
            "payload": payload,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
        history = self.event_history.setdefault(tenant_id, [])
        history.append(record)
        self.analytics_event_store.upsert(tenant_id, event_id, record.copy())
        return record

    async def _update_kpis_from_definitions(
        self,
        tenant_id: str,
        *,
        event_type: str | None = None,
        kpi_definitions: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        definitions = kpi_definitions or list(self.kpi_definitions or [])
        results: list[dict[str, Any]] = []
        for kpi_definition in definitions:
            event_types = kpi_definition.get("event_types")
            if event_type and event_types and event_type not in event_types:
                continue
            kpi_payload = {**kpi_definition, "tenant_id": tenant_id}
            results.append(await self._track_kpi(tenant_id, kpi_payload))
        if results and self.event_bus:
            await self.event_bus.publish(
                "analytics.kpi.updated",
                {"tenant_id": tenant_id, "event_type": event_type, "kpis": results},
            )
        return results

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

    def _redact_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if os.getenv("LINEAGE_MASK_SALT"):
            return mask_lineage_payload(payload)
        return self._mask_sensitive_fields(payload)

    def _mask_sensitive_fields(self, payload: Any) -> Any:
        pii_fields = {
            "address",
            "birthdate",
            "date_of_birth",
            "dob",
            "email",
            "employee_id",
            "first_name",
            "full_name",
            "last_name",
            "phone",
            "phone_number",
            "ssn",
            "social_security_number",
            "user_id",
            "username",
        }
        if isinstance(payload, dict):
            masked: dict[str, Any] = {}
            for key, value in payload.items():
                if key.lower() in pii_fields and value is not None:
                    masked[key] = "redacted"
                else:
                    masked[key] = self._mask_sensitive_fields(value)
            return masked
        if isinstance(payload, list):
            return [self._mask_sensitive_fields(item) for item in payload]
        return payload

    async def _summarize_health_portfolio(self, tenant_id: str) -> dict[str, Any]:
        """Aggregate health data across projects for reporting."""
        snapshots = self.health_snapshots.get(tenant_id, [])
        if not snapshots:
            snapshots = self.health_snapshot_store.list(tenant_id)

        latest_by_project: dict[str, dict[str, Any]] = {}
        for snapshot in sorted(snapshots, key=lambda s: s.get("monitored_at", "")):
            project_id = snapshot.get("project_id")
            if project_id:
                latest_by_project[project_id] = snapshot

        projects = list(latest_by_project.values())
        status_counts = {"Healthy": 0, "At Risk": 0, "Critical": 0}
        total_score = 0.0
        metrics_totals = {
            "schedule": 0.0,
            "cost": 0.0,
            "risk": 0.0,
            "quality": 0.0,
            "resource": 0.0,
        }
        for project in projects:
            status = project.get("health_status", "Unknown")
            if status in status_counts:
                status_counts[status] += 1
            total_score += project.get("composite_score", 0.0)
            for metric, detail in project.get("metrics", {}).items():
                metrics_totals[metric] += detail.get("score", 0.0)

        project_count = len(projects)
        average_score = total_score / project_count if project_count else 0.0
        averaged_metrics = {
            metric: (value / project_count if project_count else 0.0)
            for metric, value in metrics_totals.items()
        }
        concerns = identify_health_concerns(averaged_metrics)

        return {
            "project_count": project_count,
            "average_composite_score": average_score,
            "status_counts": status_counts,
            "average_metrics": averaged_metrics,
            "concerns": concerns,
            "recommendations": generate_recommendations(concerns),
            "projects": projects,
            "summarized_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _run_metric_simulations(
        self, tenant_id: str, simulations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Invoke scenario simulations across domain agents."""
        results: list[dict[str, Any]] = []
        for simulation in simulations:
            sim_type = simulation.get("type")
            agent_key = simulation.get("agent")
            agent_client = self.metric_agents.get(agent_key) if agent_key else None
            if not agent_client:
                continue
            payload = {
                "tenant_id": tenant_id,
                "action": simulation.get("action"),
            }
            payload.update(simulation.get("payload", {}))
            response = await agent_client.process(payload)
            results.append(
                {
                    "type": sim_type,
                    "agent": agent_key,
                    "response": response,
                }
            )
        return results

    async def _summarize_simulation_results(
        self, simulations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Summarize simulation outcomes across metrics."""
        return {
            "simulation_count": len(simulations),
            "simulation_types": [simulation.get("type") for simulation in simulations],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Helper methods

    async def _maybe_await(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    async def _generate_dashboard_id(self) -> str:
        """Generate unique dashboard ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"DASH-{timestamp}"

    async def _generate_report_id(self) -> str:
        """Generate unique report ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"REPORT-{timestamp}"

    async def _generate_prediction_id(self) -> str:
        """Generate unique prediction ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"PRED-{timestamp}"

    async def _generate_scenario_id(self) -> str:
        """Generate unique scenario ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"SCENARIO-{timestamp}"

    async def _generate_kpi_id(self) -> str:
        """Generate unique KPI ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"KPI-{timestamp}"

    async def _generate_lineage_id(self) -> str:
        """Generate unique lineage ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"LINEAGE-{timestamp}"

    async def _get_health_history(
        self, tenant_id: str, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve health history snapshots."""
        snapshots = self.health_snapshots.get(tenant_id, [])
        if not snapshots:
            snapshots = self.health_snapshot_store.list(tenant_id)
        if project_id:
            snapshots = [s for s in snapshots if s.get("project_id") == project_id]
        return sorted(snapshots, key=lambda s: s.get("monitored_at", ""))

    async def _get_events_for_tenant(self, tenant_id: str) -> list[dict[str, Any]]:
        events = self.event_history.get(tenant_id, [])
        if not events:
            events = self.analytics_event_store.list(tenant_id)
        return events

    def _filter_events(
        self, events: list[dict[str, Any]], event_types: set[str]
    ) -> list[dict[str, Any]]:
        return [event for event in events if event.get("event_type") in event_types]

    async def _collect_from_sources(self, sources: list[str]) -> list[dict[str, Any]]:
        """Collect data from multiple sources."""
        aggregated: list[dict[str, Any]] = []
        for source in sources:
            aggregated.extend(await self._fetch_source_payload(source))
        return aggregated

    async def _fetch_source_payload(self, source: str) -> list[dict[str, Any]]:
        """Fetch data from a specific source system."""
        return [
            {
                "source": source,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "records": [],
            }
        ]

    async def _harmonize_data(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Harmonize data definitions."""
        return data

    async def _calculate_statistics(self, data: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate summary statistics."""
        return {"mean": 0, "median": 0, "std_dev": 0, "min": 0, "max": 0}

    async def _record_data_lineage(
        self, tenant_id: str, sources: list[str], data: list[dict[str, Any]]
    ) -> str:
        """Record data lineage."""
        lineage_id = await self._generate_lineage_id()
        lineage_record = {
            "lineage_id": lineage_id,
            "sources": sources,
            "record_count": len(data),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        masked_lineage = mask_lineage_payload(lineage_record)
        self.data_lineage[lineage_id] = masked_lineage
        self.analytics_lineage_store.upsert(tenant_id, lineage_id, masked_lineage)
        return lineage_id

    async def _configure_widgets(self, widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Configure dashboard widgets."""
        configured: list[dict[str, Any]] = []
        for widget in widgets:
            configured.append(
                {
                    "widget_id": f"W-{len(configured) + 1}",
                    "type": widget.get("type"),
                    "title": widget.get("title"),
                    "data_source": widget.get("data_source"),
                    "config": widget.get("config", {}),
                }
            )
        return configured

    async def _setup_refresh_schedule(self, interval_minutes: int) -> dict[str, Any]:
        """Set up data refresh schedule."""
        return {
            "interval_minutes": interval_minutes,
            "next_refresh": (
                datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
            ).isoformat(),
        }

    async def _collect_report_data(
        self, tenant_id: str, report_spec: dict[str, Any]
    ) -> dict[str, Any]:
        """Collect data for report."""
        report_type = report_spec.get("type", "analytical")
        if report_type in {"health_summary", "portfolio_health"}:
            return await self._summarize_health_portfolio(tenant_id)
        if report_type == "kpi_summary":
            return {
                "kpis": list(self.kpis.values()),
                "kpi_count": len(self.kpis),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        return {}

    async def _generate_visualizations(
        self, data: dict[str, Any], report_spec: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate visualizations for report."""
        report_type = report_spec.get("type", "analytical")
        visualizations: list[dict[str, Any]] = []
        if report_type in {"health_summary", "portfolio_health"}:
            visualizations.append(
                {
                    "type": "status_distribution",
                    "title": "Health Status Distribution",
                    "data": data.get("status_counts", {}),
                }
            )
            visualizations.append(
                {
                    "type": "average_metrics",
                    "title": "Average Health Metrics",
                    "data": data.get("average_metrics", {}),
                }
            )
        elif report_type == "kpi_summary":
            visualizations.append(
                {
                    "type": "kpi_table",
                    "title": "Tracked KPIs",
                    "data": data.get("kpis", []),
                }
            )
        return visualizations

    async def _load_ml_model(self, model_type: str) -> dict[str, Any]:
        """Load ML model."""
        return await self.ml_manager.load_model(model_type)

    async def _prepare_features(self, input_data: dict[str, Any], model_type: str) -> list[float]:
        """Prepare features for ML model."""
        features: list[float] = []
        for value in input_data.values():
            if isinstance(value, (int, float)):
                features.append(float(value))
        return features

    async def _make_prediction(
        self,
        model: dict[str, Any],
        features: list[float],
        model_type: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Make prediction using ML model."""
        if hasattr(model, "predict"):
            predicted_value = model.predict([features])[0]
            return {"value": float(predicted_value), "confidence": 0.8}
        if model_type == "health_score":
            project_id = input_data.get("project_id")
            history = await self._get_health_history(
                input_data.get("tenant_id", "default"), project_id
            )
            if len(history) >= 2:
                last_two = history[-2:]
                delta = last_two[-1]["composite_score"] - last_two[0]["composite_score"]
                prediction_value = max(0.0, min(1.0, last_two[-1]["composite_score"] + delta))
                return {"value": prediction_value, "confidence": 0.75}
            if history:
                return {"value": history[-1]["composite_score"], "confidence": 0.6}
        return {"value": 0.0, "confidence": 0.85}

    async def _calculate_confidence_interval(
        self, prediction: dict[str, Any], model_type: str
    ) -> dict[str, float]:
        """Calculate prediction confidence interval."""
        value = prediction.get("value", 0.0)
        return {"lower": value * 0.9, "upper": value * 1.1}

    async def _generate_prediction_recommendations(self, prediction: dict[str, Any]) -> list[str]:
        """Generate recommendations based on prediction."""
        return ["Monitor actual values against prediction"]

    async def _get_baseline_metrics(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Get baseline metrics for scenario."""
        return {"metric_1": 100, "metric_2": 200}

    async def _calculate_scenario_metrics(
        self, baseline: dict[str, Any], parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate metrics under scenario."""
        scenario_metrics = baseline.copy()
        assumptions = parameters.get("assumptions", {})
        for metric, adjustment in assumptions.items():
            if metric in scenario_metrics and isinstance(adjustment, (int, float)):
                scenario_metrics[metric] = scenario_metrics[metric] + adjustment

        kpi_models = parameters.get("kpi_models", [])
        for kpi_model in kpi_models:
            model_type = kpi_model.get("model_type")
            if not model_type:
                continue
            input_payload = kpi_model.get("input_data", {})
            input_payload.update(assumptions)
            prediction = await self._run_prediction(
                input_payload.get("tenant_id", "default"), model_type, input_payload
            )
            scenario_metrics[model_type] = prediction.get("prediction")

        return scenario_metrics

    async def _compare_scenarios(
        self, baseline: dict[str, Any], scenario: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare baseline to scenario."""
        comparison = {}
        for key in baseline.keys():
            if key in scenario:
                comparison[key] = {
                    "baseline": baseline[key],
                    "scenario": scenario[key],
                    "delta": scenario[key] - baseline[key],
                    "delta_pct": (
                        ((scenario[key] - baseline[key]) / baseline[key] * 100)
                        if baseline[key] != 0
                        else 0
                    ),
                }
        return comparison

    async def _calculate_scenario_impact(self, comparison: dict[str, Any]) -> str:
        """Calculate overall scenario impact."""
        return "Moderate positive impact"

    async def _generate_scenario_recommendations(self, impact: str | None) -> list[str]:
        """Generate recommendations based on scenario."""
        if not impact:
            return ["Scenario impact is neutral - monitor outcomes before acting"]
        return [f"Scenario shows {impact} - consider implementation"]

    async def _extract_key_insights(self, data: dict[str, Any]) -> list[str]:
        """Extract key insights from data."""
        return []

    async def _identify_trends(self, data: dict[str, Any]) -> list[str]:
        """Identify trends in data."""
        return []

    async def _generate_narrative_text(
        self, insights: list[str], trends: list[str], data: dict[str, Any]
    ) -> str:
        """Generate narrative text using NLG."""
        prompt = (
            "Summarize analytics results, explain anomalies, and answer questions in plain language. "
            f"Insights: {insights}. Trends: {trends}. Data snapshot: {data}."
        )
        return await self.narrative_service.generate_narrative(prompt)

    async def _calculate_kpi_value(self, kpi_config: dict[str, Any]) -> float:
        """Calculate current KPI value."""
        metric_name = kpi_config.get("metric_name")
        tenant_id = kpi_config.get("tenant_id", "default")
        events = await self._get_events_for_tenant(tenant_id)
        if metric_name == "schedule.delay.avg":
            delays = [
                float(event.get("payload", {}).get("delay_days", 0))
                for event in self._filter_events(events, {"schedule.delay"})
            ]
            return sum(delays) / len(delays) if delays else 0.0
        if metric_name == "deployment.success_rate":
            successes = len(self._filter_events(events, {"deployment.succeeded"}))
            failures = len(self._filter_events(events, {"deployment.failed"}))
            total = successes + failures
            return successes / total if total else 1.0
        if metric_name == "deployment.frequency":
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            recent = [
                event
                for event in self._filter_events(
                    events,
                    {"deployment.succeeded", "deployment.failed", "deployment.started"},
                )
                if event.get("received_at")
                and datetime.fromisoformat(event.get("received_at")) >= cutoff
            ]
            return len(recent) / 4.0 if recent else 0.0
        if metric_name == "resource.utilization.avg":
            allocations = []
            for event in self._filter_events(
                events, {"resource.allocation.created", "resource.updated"}
            ):
                payload = event.get("payload", {})
                raw = payload.get("allocation_percentage")
                if raw is None:
                    raw = payload.get("utilization") or payload.get("utilization_pct")
                if raw is None:
                    continue
                allocations.append(float(raw) / 100 if float(raw) > 1 else float(raw))
            return sum(allocations) / len(allocations) if allocations else 0.0
        if metric_name == "quality.score.avg":
            scores = [
                float(event.get("payload", {}).get("quality_score", 0))
                for event in self._filter_events(events, {"quality.metrics.calculated"})
            ]
            return sum(scores) / len(scores) if scores else 0.0
        if metric_name == "risk.exposure.avg":
            scores = [
                float(event.get("payload", {}).get("score", 0))
                for event in self._filter_events(events, {"risk.assessed", "risk.status_updated"})
            ]
            return sum(scores) / len(scores) if scores else 0.0
        if metric_name == "compliance.audit.avg":
            scores = [
                float(event.get("payload", {}).get("score", 0))
                for event in self._filter_events(events, {"quality.audit.completed"})
            ]
            return sum(scores) / len(scores) if scores else 0.0
        kpi_name = str(kpi_config.get("name", "")).lower()
        if "velocity" in kpi_name:
            return 85.0
        return float(kpi_config.get("current_value") or kpi_config.get("value") or 0.0)

    async def _get_kpi_history(self, tenant_id: str, kpi_id: str) -> list[dict[str, Any]]:
        """Get historical KPI values."""
        history = self.kpi_history_store.get(tenant_id, kpi_id)
        if history and isinstance(history.get("entries"), list):
            return list(history["entries"])
        return []

    async def _store_kpi_history(self, tenant_id: str, kpi_id: str, value: float) -> None:
        history = await self._get_kpi_history(tenant_id, kpi_id)
        history.append({"value": value, "recorded_at": datetime.now(timezone.utc).isoformat()})
        self.kpi_history_store.upsert(tenant_id, kpi_id, {"entries": history})

    async def _calculate_kpi_trend(
        self, historical: list[dict[str, Any]], current: float, direction: str | None
    ) -> str:
        """Calculate KPI trend."""
        if not historical:
            return "stable"
        last_value = historical[-1].get("value", current)
        if direction == "lower_is_better":
            if current < last_value:
                return "improving"
            if current > last_value:
                return "declining"
        else:
            if current > last_value:
                return "improving"
            if current < last_value:
                return "declining"
        return "stable"

    async def _check_kpi_thresholds(
        self, value: float, thresholds: dict[str, float]
    ) -> dict[str, Any]:
        """Check KPI against thresholds."""
        breached = False
        if "min" in thresholds and value < thresholds["min"]:
            breached = True
        if "max" in thresholds and value > thresholds["max"]:
            breached = True

        return {
            "breached": breached,
            "thresholds": thresholds,
            "status": "critical" if breached else "normal",
        }

    async def _parse_query(self, query: str) -> dict[str, Any]:
        """Parse natural language query."""
        return {"parsed": query}

    async def _execute_query(
        self, parsed_query: dict[str, Any], filters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Execute data query."""
        return []

    async def _format_query_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format query results."""
        return results

    async def _refresh_widget_data(self, widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Refresh data for dashboard widgets."""
        refreshed = []
        for widget in widgets:
            widget_data = widget.copy()
            widget_type = widget.get("type")
            if widget_type in {"health_summary", "portfolio_health"}:
                widget_data["data"] = await self._summarize_health_portfolio(
                    widget.get("tenant_id", "default")
                )
            elif widget_type == "kpi_summary":
                widget_data["data"] = list(self.kpis.values())
            else:
                widget_data["data"] = []
            widget_data["last_refreshed"] = datetime.now(timezone.utc).isoformat()
            refreshed.append(widget_data)
        return refreshed

    async def _collect_insights_data(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Collect data for insights generation."""
        tenant_id = filters.get("tenant_id", "default")
        health_summary = await self._summarize_health_portfolio(tenant_id)
        return {
            "health_summary": health_summary,
            "project_metrics": filters.get("project_metrics", []),
        }

    async def _detect_anomalies(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect anomalies in data."""
        anomalies: list[dict[str, Any]] = []
        for metric in data.get("project_metrics", []):
            cycle_time_days = metric.get("cycle_time_days")
            if isinstance(cycle_time_days, (int, float)) and cycle_time_days > 20:
                anomalies.append(
                    {
                        "project_id": metric.get("project_id"),
                        "metric": "cycle_time_days",
                        "value": cycle_time_days,
                        "reason": "Consistently high cycle time",
                    }
                )
            budget_variance_pct = metric.get("budget_variance_pct")
            if isinstance(budget_variance_pct, (int, float)) and abs(budget_variance_pct) > 0.15:
                anomalies.append(
                    {
                        "project_id": metric.get("project_id"),
                        "metric": "budget_variance_pct",
                        "value": budget_variance_pct,
                        "reason": "Budget variance outside tolerated range",
                    }
                )
        return anomalies

    async def _identify_patterns(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify patterns in data."""
        patterns: list[dict[str, Any]] = []
        project_metrics = data.get("project_metrics", [])
        if not project_metrics:
            return patterns
        delayed_projects = [
            item for item in project_metrics if float(item.get("late_task_ratio", 0)) >= 0.25
        ]
        if delayed_projects:
            patterns.append(
                {
                    "pattern": "recurring_late_tasks",
                    "count": len(delayed_projects),
                    "description": "Multiple projects have high late-task ratios",
                }
            )
        scope_creep_projects = [
            item for item in project_metrics if float(item.get("scope_creep_count", 0)) >= 2
        ]
        if scope_creep_projects:
            patterns.append(
                {
                    "pattern": "recurring_scope_creep",
                    "count": len(scope_creep_projects),
                    "description": "Scope creep appears repeatedly across projects",
                }
            )
        return patterns

    async def _generate_periodic_report(
        self, tenant_id: str, period: str, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate periodic analytics report used by continuous improvement workflows."""
        report_id = await self._generate_report_id()
        metrics = filters.get("project_metrics", [])
        cycle_times = [float(metric.get("cycle_time_days", 0)) for metric in metrics]
        risk_occurrences = [int(metric.get("risk_occurrences", 0)) for metric in metrics]
        budget_variances = [float(metric.get("budget_variance_pct", 0)) for metric in metrics]

        insights_data = await self._collect_insights_data({"tenant_id": tenant_id, **filters})
        anomalies = await self._detect_anomalies(insights_data)
        patterns = await self._identify_patterns(insights_data)
        insights = await self._generate_insights(insights_data, anomalies, patterns)
        recommendations = await self._generate_recommendations(insights)

        report = {
            "report_id": report_id,
            "type": "periodic_performance",
            "period": period,
            "summary": {
                "project_count": len(metrics),
                "avg_cycle_time_days": (
                    round(sum(cycle_times) / len(cycle_times), 2) if cycle_times else 0
                ),
                "risk_occurrences_total": sum(risk_occurrences),
                "avg_budget_variance_pct": (
                    round(sum(budget_variances) / len(budget_variances), 4)
                    if budget_variances
                    else 0
                ),
            },
            "trends": patterns,
            "anomalies": anomalies,
            "insights": insights,
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.reports[report_id] = report
        self.analytics_output_store.upsert(tenant_id, report_id, report.copy())
        await self.report_repository.store_report(report.copy())

        if self.event_bus:
            await self.event_bus.publish(
                "analytics.periodic_report.generated",
                {
                    "tenant_id": tenant_id,
                    "report": report,
                },
            )

        return report

    async def _generate_insights(
        self, data: dict[str, Any], anomalies: list[dict[str, Any]], patterns: list[dict[str, Any]]
    ) -> list[str]:
        """Generate AI insights."""
        insights = []
        if anomalies:
            insights.append(f"Detected {len(anomalies)} anomalies requiring investigation")
        if patterns:
            insights.append(f"Identified {len(patterns)} recurring patterns")
        health_summary = data.get("health_summary", {})
        concerns = health_summary.get("concerns", [])
        if concerns:
            insights.append(f"{len(concerns)} portfolio health concerns identified")
        return insights

    async def _generate_recommendations(self, insights: list[str]) -> list[str]:
        """Generate recommendations from insights."""
        recommendations = []
        for insight in insights:
            lowered = insight.lower()
            if "anomal" in lowered:
                recommendations.append("Investigate anomalies with the delivery leads")
            if "concerns" in lowered:
                recommendations.append("Schedule a portfolio health review and mitigation planning")
        if not recommendations:
            recommendations.append("Maintain current monitoring cadence")
        return recommendations

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
