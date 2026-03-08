"""
Service manager classes for the Analytics & Insights Agent.

Contains Azure-integrated manager classes for Synapse, Data Lake, ML,
Power BI, Data Factory, Event Hub, Stream Analytics, NLG, language query,
and report storage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


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
        if not self.power_bi_client or not hasattr(self.power_bi_client, "generate_embed_token"):
            raise RuntimeError(
                "Power BI client is not configured. Set POWER_BI_* environment "
                "variables to enable report embedding."
            )
        embed_token = self.power_bi_client.generate_embed_token(template["report_id"], user_context)
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
