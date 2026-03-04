"""
Infrastructure helpers for the Data Synchronization Agent.

Contains config loading, Azure service initialization, event publishing,
ETL workflow triggering, and metrics ingestion -- all extracted from the
main agent class to keep it focused on routing and lifecycle.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import yaml
from observability.metrics import build_business_workflow_metrics
from observability.tracing import get_trace_id
from security.lineage import mask_lineage_payload

from agents.common.connector_integration import _ensure_connector_paths
from agents.runtime.src.audit import build_audit_event, emit_audit_event
from agents.runtime.src.event_bus import ServiceBusEventBus

from sync_utils import apply_transformations, get_transformation_rules, validate_transformation_rule

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.cosmos import CosmosClient
    from azure.eventgrid import EventGridPublisherClient
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    from azure.mgmt.datafactory import DataFactoryManagementClient
    from azure.monitor.ingestion import LogsIngestionClient
    from azure.servicebus import ServiceBusMessage
    from azure.servicebus.aio import ServiceBusClient
except ImportError:  # pragma: no cover - optional dependencies
    AzureKeyCredential = None
    CosmosClient = None
    EventGridPublisherClient = None
    DefaultAzureCredential = None
    SecretClient = None
    DataFactoryManagementClient = None
    LogsIngestionClient = None
    ServiceBusMessage = None
    ServiceBusClient = None

try:
    import azure.functions as azure_functions
except ImportError:  # pragma: no cover - optional dependencies
    azure_functions = None

try:
    from sqlalchemy import create_engine
except ImportError:  # pragma: no cover - optional dependencies
    create_engine = None

if TYPE_CHECKING:
    from data_sync_agent import DataSyncAgent


# ---------------------------------------------------------------------------
# Config loaders
# ---------------------------------------------------------------------------


def load_validation_rules(agent: DataSyncAgent) -> dict[str, list[dict[str, Any]]]:
    rules_path = (
        Path(agent.config.get("validation_rules_path", "ops/config/agents/data-synchronisation-agent/validation_rules.yaml"))
        if agent.config else Path("ops/config/agents/data-synchronisation-agent/validation_rules.yaml")
    )
    if not rules_path.exists():
        return {}
    try:
        with rules_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        agent.logger.warning("validation_rules_load_failed", extra={"error": str(exc)})
        return {}
    return {key: value if isinstance(value, list) else [] for key, value in payload.items()}


def load_quality_thresholds(agent: DataSyncAgent) -> dict[str, float | dict[str, float]]:
    thresholds_path = (
        Path(agent.config.get("quality_thresholds_path", "ops/config/agents/data-synchronisation-agent/quality_thresholds.yaml"))
        if agent.config else Path("ops/config/agents/data-synchronisation-agent/quality_thresholds.yaml")
    )
    if not thresholds_path.exists():
        return {}
    try:
        with thresholds_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        agent.logger.warning("quality_thresholds_load_failed", extra={"error": str(exc)})
        return {}
    thresholds: dict[str, float | dict[str, float]] = {}
    for key, value in payload.items():
        if isinstance(value, (int, float)):
            thresholds[key] = float(value)
        elif isinstance(value, dict):
            thresholds[key] = {metric: float(metric_value) for metric, metric_value in value.items() if isinstance(metric_value, (int, float))}
    return thresholds


def load_schema_registry(agent: DataSyncAgent) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    registry_path = (
        Path(agent.config.get("schema_registry_path", "ops/config/agents/data-synchronisation-agent/schema_registry.yaml"))
        if agent.config else Path("ops/config/agents/data-synchronisation-agent/schema_registry.yaml")
    )
    if not registry_path.exists():
        return {}, {}
    try:
        with registry_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        agent.logger.warning("schema_registry_load_failed", extra={"error": str(exc)})
        return {}, {}
    registry: dict[str, dict[str, Any]] = {}
    versions: dict[str, list[dict[str, Any]]] = {}
    for entry in payload.get("entities", []):
        if not isinstance(entry, dict):
            continue
        entity_type = entry.get("name")
        schema = entry.get("schema")
        version = entry.get("version", "1.0")
        if entity_type and isinstance(schema, dict):
            registry[entity_type] = schema
            versions.setdefault(entity_type, []).append({"version": version, "schema": schema})
    return registry, versions


def load_mapping_rules(agent: DataSyncAgent) -> list[dict[str, Any]]:
    mapping_path = (
        Path(agent.config.get("mapping_rules_path", "ops/config/agents/data-synchronisation-agent/mapping_rules.yaml"))
        if agent.config else Path("ops/config/agents/data-synchronisation-agent/mapping_rules.yaml")
    )
    if not mapping_path.exists():
        return []
    try:
        with mapping_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        agent.logger.warning("mapping_rules_load_failed", extra={"error": str(exc)})
        return []
    mappings = payload.get("mappings", [])
    if not isinstance(mappings, list):
        return []
    return [entry for entry in mappings if isinstance(entry, dict)]


def load_pipeline_config(agent: DataSyncAgent) -> tuple[list[str], list[str]]:
    config_path = (
        Path(agent.config.get("pipeline_config_path", "ops/config/agents/data-synchronisation-agent/pipelines.yaml"))
        if agent.config else Path("ops/config/agents/data-synchronisation-agent/pipelines.yaml")
    )
    if not config_path.exists():
        return [], []
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        agent.logger.warning("pipeline_config_load_failed", extra={"error": str(exc)})
        return [], []
    pipelines = [entry.get("name") for entry in payload.get("pipelines", []) if isinstance(entry, dict) and entry.get("name")]
    functions = [entry.get("name") for entry in payload.get("functions", []) if isinstance(entry, dict) and entry.get("name")]
    return pipelines, functions


# ---------------------------------------------------------------------------
# Azure initialization
# ---------------------------------------------------------------------------


async def initialize_key_vault_secrets(
    agent: DataSyncAgent,
    credential_cls: Any | None = None,
    secret_client_cls: Any | None = None,
) -> None:
    credential_cls = credential_cls or DefaultAzureCredential
    secret_client_cls = secret_client_cls or SecretClient
    key_vault_url = agent._get_setting("AZURE_KEY_VAULT_URL")
    if not key_vault_url or not credential_cls or not secret_client_cls:
        return
    credential = credential_cls()
    client = secret_client_cls(vault_url=key_vault_url, credential=credential)
    secret_names = [
        "PLANVIEW_CLIENT_ID", "PLANVIEW_CLIENT_SECRET", "PLANVIEW_REFRESH_TOKEN", "PLANVIEW_INSTANCE_URL",
        "SAP_USERNAME", "SAP_PASSWORD", "SAP_URL",
        "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_INSTANCE_URL",
        "WORKDAY_CLIENT_ID", "WORKDAY_CLIENT_SECRET", "WORKDAY_REFRESH_TOKEN", "WORKDAY_API_URL",
    ]
    loaded_secrets: dict[str, str] = {}
    for secret_name in secret_names:
        if agent._get_setting(secret_name):
            continue
        try:
            secret = client.get_secret(secret_name)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
            agent.logger.warning("keyvault_secret_unavailable", extra={"secret": secret_name, "error": str(exc)})
            continue
        if secret and secret.value:
            loaded_secrets[secret_name] = secret.value
    if loaded_secrets:
        agent.secret_context.set_many(loaded_secrets)


async def initialize_connectors(agent: DataSyncAgent) -> None:
    _ensure_connector_paths()
    try:
        from azure_devops_connector import AzureDevOpsConnector
        from base_connector import ConnectorCategory, ConnectorConfig
        from jira_connector import JiraConnector
        from planview_connector import PlanviewConnector
        from sap_connector import SapConnector
        from smartsheet_connector import SmartsheetConnector
        from workday_connector import WorkdayConnector
    except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
        agent.logger.warning("connector_import_failed", extra={"error": str(exc)})
        return

    agent.connectors = {}
    agent._sync_business_metrics = build_business_workflow_metrics("data-sync-agent", "connector_sync")
    for connector_spec in [
        ("planview", "Planview", "PPM", "PLANVIEW_INSTANCE_URL", PlanviewConnector),
        ("sap", "SAP", "ERP", "SAP_URL", SapConnector),
        ("jira", "Jira", "PM", "JIRA_INSTANCE_URL", JiraConnector),
        ("workday", "Workday", "HRIS", "WORKDAY_API_URL", WorkdayConnector),
        ("smartsheet", "Smartsheet", "PM", "SMARTSHEET_API_URL", SmartsheetConnector),
        ("azure_devops", "Azure DevOps", "PM", "AZURE_DEVOPS_ORG_URL", AzureDevOpsConnector),
    ]:
        cid, cname, cat_name, url_key, cls = connector_spec
        try:
            cat = getattr(ConnectorCategory, cat_name)
            cfg = ConnectorConfig(connector_id=cid, name=cname, category=cat, instance_url=agent._get_setting(url_key, "") or "")
            agent.connectors[cid] = cls(cfg)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
            agent.logger.warning("%s_connector_failed", cid, extra={"error": str(exc)})


async def initialize_service_bus(agent: DataSyncAgent) -> None:
    if agent.config and agent.config.get("event_bus"):
        agent.event_bus = agent.config["event_bus"]
    connection_string = agent._get_setting("AZURE_SERVICE_BUS_CONNECTION_STRING")
    if not connection_string:
        return
    agent.event_bus = ServiceBusEventBus(connection_string=connection_string, topic_name=agent.service_bus_topic_name)
    if ServiceBusClient is None:
        return
    agent.service_bus_client = ServiceBusClient.from_connection_string(connection_string)
    try:
        agent.service_bus_queue_sender = agent.service_bus_client.get_queue_sender(queue_name=agent.service_bus_queue_name)
        agent.service_bus_topic_sender = agent.service_bus_client.get_topic_sender(topic_name=agent.service_bus_topic_name)
    except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
        agent.logger.warning("service_bus_sender_unavailable", extra={"error": str(exc)})


async def initialize_event_grid(agent: DataSyncAgent) -> None:
    endpoint = agent._get_setting("EVENT_GRID_ENDPOINT")
    key = agent._get_setting("EVENT_GRID_KEY")
    if not endpoint or not key or not EventGridPublisherClient or not AzureKeyCredential:
        return
    agent.event_grid_client = EventGridPublisherClient(endpoint, AzureKeyCredential(key))


async def initialize_datastores(agent: DataSyncAgent) -> None:
    sql_connection_string = agent._get_setting("SQL_CONNECTION_STRING")
    if sql_connection_string and create_engine:
        agent.sql_engine = create_engine(sql_connection_string)
    cosmos_endpoint = agent._get_setting("COSMOS_ENDPOINT")
    cosmos_key = agent._get_setting("COSMOS_KEY")
    if cosmos_endpoint and cosmos_key and CosmosClient:
        agent.cosmos_client = CosmosClient(cosmos_endpoint, credential=cosmos_key)


async def initialize_data_factory(agent: DataSyncAgent) -> None:
    if not DataFactoryManagementClient or not DefaultAzureCredential:
        return
    subscription_id = agent._get_setting("AZURE_SUBSCRIPTION_ID")
    if not subscription_id:
        return
    credential = DefaultAzureCredential()
    agent.data_factory_client = DataFactoryManagementClient(credential, subscription_id)
    resource_group = agent.data_factory_resource_group
    factory_name = agent.data_factory_name
    if resource_group and factory_name and agent.data_factory_pipelines:
        for pipeline_name in agent.data_factory_pipelines:
            try:  # pragma: no cover - network dependent
                agent.data_factory_client.pipelines.get(resource_group_name=resource_group, factory_name=factory_name, pipeline_name=pipeline_name)
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
                agent.logger.warning("data_factory_pipeline_unavailable", extra={"pipeline": pipeline_name, "error": str(exc)})


async def initialize_functions(agent: DataSyncAgent) -> None:
    if not azure_functions:
        return
    agent.function_app = azure_functions.FunctionApp()
    if not agent.function_names:
        return
    if not agent.function_base_url:
        agent.logger.info("function_base_url_missing", extra={"configured_functions": agent.function_names})


async def initialize_monitoring(agent: DataSyncAgent) -> None:
    endpoint = agent._get_setting("LOG_ANALYTICS_ENDPOINT")
    if not endpoint or not LogsIngestionClient or not DefaultAzureCredential:
        return
    credential = DefaultAzureCredential()
    agent.log_analytics_client = LogsIngestionClient(endpoint=endpoint, credential=credential)


# ---------------------------------------------------------------------------
# Event publishing
# ---------------------------------------------------------------------------


async def publish_event(agent: DataSyncAgent, topic: str, payload: dict[str, Any]) -> None:
    if agent.event_bus:
        await agent.event_bus.publish(topic, payload)
    await publish_service_bus_message(agent, topic, payload)
    await publish_event_grid_event(agent, topic, payload)


async def publish_service_bus_message(agent: DataSyncAgent, topic: str, payload: dict[str, Any]) -> None:
    if not agent.service_bus_client or not ServiceBusMessage:
        return
    message = ServiceBusMessage(json.dumps({"topic": topic, "payload": payload, "published_at": datetime.now(timezone.utc).isoformat()}, default=str))
    if agent.service_bus_topic_sender:
        try:  # pragma: no cover - network dependent
            async with agent.service_bus_topic_sender:
                await agent.service_bus_topic_sender.send_messages(message)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
            agent.logger.warning("service_bus_topic_publish_failed", extra={"error": str(exc)})
    if agent.service_bus_queue_sender:
        try:  # pragma: no cover - network dependent
            async with agent.service_bus_queue_sender:
                await agent.service_bus_queue_sender.send_messages(message)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
            agent.logger.warning("service_bus_queue_publish_failed", extra={"error": str(exc)})


async def publish_event_grid_event(agent: DataSyncAgent, topic: str, payload: dict[str, Any]) -> None:
    if not agent.event_grid_client:
        return
    event = {
        "id": str(uuid.uuid4()), "subject": f"data-sync/{topic}", "eventType": topic,
        "eventTime": datetime.now(timezone.utc).isoformat() + "Z", "dataVersion": "1.0", "data": payload,
    }
    try:  # pragma: no cover - network dependent
        await agent.event_grid_client.send([event])
    except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
        agent.logger.warning("event_grid_publish_failed", extra={"error": str(exc)})


async def publish_sync_event(agent: DataSyncAgent, tenant_id: str, entity_type: str, master_id: str, source_system: str, payload: dict[str, Any]) -> None:
    agent.logger.info("sync_event_published", extra={"tenant_id": tenant_id, "entity_type": entity_type, "master_id": master_id, "source_system": source_system})
    if not agent.sync_event_webhook_url:
        return
    webhook_payload = {"tenant_id": tenant_id, "entity_type": entity_type, "master_id": master_id, "source_system": source_system, "payload": payload, "timestamp": datetime.now(timezone.utc).isoformat()}
    try:
        async with httpx.AsyncClient(timeout=agent.sync_event_webhook_timeout) as client:
            await client.post(agent.sync_event_webhook_url, json=webhook_payload)
    except httpx.RequestError:
        agent.logger.warning("sync_event_webhook_unavailable", extra={"url": agent.sync_event_webhook_url})


async def emit_lineage_event(agent: DataSyncAgent, tenant_id: str, entity_type: str, master_id: str, source_system: str, payload: dict[str, Any]) -> None:
    base_url = agent._get_setting("DATA_LINEAGE_SERVICE_URL")
    if not base_url:
        return
    token = agent._get_setting("DATA_LINEAGE_SERVICE_TOKEN")
    headers = {"X-Tenant-ID": tenant_id}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    lineage_payload = {
        "tenant_id": tenant_id, "connector": "data-sync-agent",
        "source": {"system": source_system, "object": entity_type, "record_id": payload.get("id")},
        "target": {"schema": entity_type, "record_id": master_id},
        "transformations": [f"{source_system}.{entity_type} -> {entity_type}"],
        "entity_type": entity_type, "entity_payload": payload, "classification": "internal",
    }
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
            await client.post("/lineage/events", json=lineage_payload, headers=headers)
    except httpx.RequestError:
        agent.logger.warning("lineage_service_unavailable", extra={"base_url": base_url})


# ---------------------------------------------------------------------------
# ETL workflows
# ---------------------------------------------------------------------------


async def run_etl_workflows(agent: DataSyncAgent, tenant_id: str, entity_type: str, payload: dict[str, Any], source_system: str) -> None:
    await trigger_data_factory_pipelines(agent, tenant_id=tenant_id, entity_type=entity_type, payload=payload, source_system=source_system)
    await invoke_transformation_functions(agent, tenant_id=tenant_id, entity_type=entity_type, payload=payload, source_system=source_system)


async def trigger_data_factory_pipelines(agent: DataSyncAgent, tenant_id: str, entity_type: str, payload: dict[str, Any], source_system: str) -> None:
    if not agent.data_factory_client:
        return
    if not agent.data_factory_resource_group or not agent.data_factory_name:
        return
    for pipeline_name in agent.data_factory_pipelines:
        try:  # pragma: no cover - network dependent
            agent.data_factory_client.pipelines.create_run(
                resource_group_name=agent.data_factory_resource_group, factory_name=agent.data_factory_name,
                pipeline_name=pipeline_name,
                parameters={"tenant_id": tenant_id, "entity_type": entity_type, "source_system": source_system, "payload": payload},
            )
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
            agent.logger.warning("data_factory_pipeline_trigger_failed", extra={"pipeline": pipeline_name, "error": str(exc)})


async def invoke_transformation_functions(agent: DataSyncAgent, tenant_id: str, entity_type: str, payload: dict[str, Any], source_system: str) -> None:
    if not agent.function_names or not agent.function_base_url:
        return
    headers = {"Content-Type": "application/json"}
    if agent.function_key:
        headers["x-functions-key"] = agent.function_key
    for function_name in agent.function_names:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{agent.function_base_url.rstrip('/')}/api/{function_name}",
                    json={"tenant_id": tenant_id, "entity_type": entity_type, "source_system": source_system, "payload": payload},
                    headers=headers,
                )
        except httpx.RequestError:
            agent.logger.warning("function_invocation_failed", extra={"function": function_name})


# ---------------------------------------------------------------------------
# Metrics ingestion
# ---------------------------------------------------------------------------


async def ingest_latency_metric(agent: DataSyncAgent, record: dict[str, Any]) -> None:
    if not agent.log_analytics_client:
        return
    rule_id = agent._get_setting("LOG_ANALYTICS_RULE_ID")
    stream_name = agent._get_setting("LOG_ANALYTICS_STREAM_NAME", "DataSyncLatency") or "DataSyncLatency"
    if not rule_id:
        return
    try:
        await agent.log_analytics_client.upload(rule_id=rule_id, stream_name=stream_name, logs=[record])
    except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
        agent.logger.warning("log_analytics_upload_failed", extra={"error": str(exc)})


async def ingest_quality_metric(agent: DataSyncAgent, record: dict[str, Any]) -> None:
    if not agent.log_analytics_client:
        return
    rule_id = agent._get_setting("LOG_ANALYTICS_RULE_ID")
    stream_name = agent._get_setting("LOG_ANALYTICS_QUALITY_STREAM_NAME", "DataQualityMetrics") or "DataQualityMetrics"
    if not rule_id:
        return
    try:
        await agent.log_analytics_client.upload(rule_id=rule_id, stream_name=stream_name, logs=[record])
    except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
        agent.logger.warning("log_analytics_quality_upload_failed", extra={"error": str(exc)})


# ---------------------------------------------------------------------------
# Data transformation (kept close to infrastructure as it touches agent state)
# ---------------------------------------------------------------------------


async def map_to_canonical(agent: DataSyncAgent, entity_type: str, data: dict[str, Any], source_system: str) -> dict[str, Any]:
    rules = [
        rule for rule in agent.transformation_rules
        if rule.get("entity_type") == entity_type and rule.get("source_system") == source_system
    ]
    if not rules:
        return data
    mapped = data.copy()
    for rule in rules:
        if not validate_transformation_rule(rule, agent.transformation_schema, agent.logger):
            continue
        field_mappings = rule.get("field_mappings", {})
        mapped_payload: dict[str, Any] = {}
        for source_field, target_field in field_mappings.items():
            if source_field in mapped:
                mapped_payload[target_field] = mapped.get(source_field)
        defaults = rule.get("defaults", {})
        for key, value in defaults.items():
            mapped_payload.setdefault(key, value)
        mapped = mapped_payload
    return mapped


async def transform_data(agent: DataSyncAgent, entity_type: str, data: dict[str, Any], source_system: str) -> dict[str, Any]:
    applicable_rules = get_transformation_rules(agent.transformation_rules, entity_type, source_system)
    if not applicable_rules:
        return data
    transformed = data.copy()
    for rule in applicable_rules:
        if not validate_transformation_rule(rule, agent.transformation_schema, agent.logger):
            continue
        field_mappings = rule.get("field_mappings", {})
        mapped_payload: dict[str, Any] = {}
        has_mapping = False
        for source_field, target_field in field_mappings.items():
            if source_field in transformed:
                mapped_payload[target_field] = transformed.get(source_field)
                has_mapping = True
        defaults = rule.get("defaults", {})
        for key, value in defaults.items():
            mapped_payload.setdefault(key, value)
        if has_mapping:
            transformed = mapped_payload
        transformations = rule.get("transformations", [])
        transformed = apply_transformations(transformed, transformations)
    return transformed


# ---------------------------------------------------------------------------
# Record helpers
# ---------------------------------------------------------------------------


async def find_existing_master(agent: DataSyncAgent, entity_type: str, data: dict[str, Any]) -> dict[str, Any] | None:
    for master_id, record in agent.master_records.items():
        if record.get("entity_type") == entity_type and record.get("data", {}).get("id") == data.get("id"):
            return record  # type: ignore
    return None


async def generate_master_id(entity_type: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"MASTER-{entity_type.upper()}-{timestamp}"


async def generate_mapping_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"MAP-{timestamp}"


async def record_sync_event(agent: DataSyncAgent, tenant_id: str, entity_type: str, master_id: str, source_system: str, status: str) -> str:
    event_id = f"EVENT-{len(agent.sync_events) + 1}"
    event_record = {
        "event_id": event_id, "entity_type": entity_type, "master_id": master_id,
        "source_system": source_system, "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    agent.sync_events[event_id] = event_record
    agent.sync_event_store.upsert(tenant_id, event_id, event_record)
    await store_record(agent, "sync_events", event_id, event_record)
    return event_id


async def record_sync_lineage(agent: DataSyncAgent, tenant_id: str, entity_type: str, master_id: str, source_system: str, payload: dict[str, Any]) -> None:
    lineage_id = f"LINEAGE-{len(agent.sync_events) + 1}"
    lineage_record = {
        "lineage_id": lineage_id, "entity_type": entity_type, "master_id": master_id,
        "source_system": source_system, "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    masked_lineage = mask_lineage_payload(lineage_record)
    agent.sync_lineage_store.upsert(tenant_id, lineage_id, masked_lineage)
    await emit_lineage_event(agent, tenant_id, entity_type, master_id, source_system, payload)


async def record_sync_metrics(agent: DataSyncAgent, tenant_id: str, entity_type: str, source_system: str, latency_seconds: float, started_at: datetime, finished_at: datetime) -> None:
    record = {
        "tenant_id": tenant_id, "entity_type": entity_type, "source_system": source_system,
        "latency_seconds": latency_seconds,
        "started_at": started_at.isoformat(), "finished_at": finished_at.isoformat(),
    }
    agent.latency_records.append(record)
    await ingest_latency_metric(agent, record)


async def record_sync_log(agent: DataSyncAgent, tenant_id: str, entity_type: str, source_system: str, status: str, mode: str, started_at: datetime, finished_at: datetime | None = None, master_id: str | None = None, details: dict[str, Any] | None = None) -> None:
    log_record = {
        "log_id": f"SYNCLOG-{len(agent.sync_logs) + 1}",
        "tenant_id": tenant_id, "entity_type": entity_type,
        "source_system": source_system, "status": status, "mode": mode,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat() if finished_at else None,
        "master_id": master_id, "details": details or {},
    }
    agent.sync_logs.append(log_record)
    await store_record(agent, "sync_logs", log_record["log_id"], log_record)


async def emit_audit_event_helper(agent: DataSyncAgent, tenant_id: str, action: str, resource_id: str, resource_type: str, metadata: dict[str, Any]) -> None:
    audit_event = build_audit_event(
        tenant_id=tenant_id, action=action, outcome="success",
        actor_id=agent.agent_id, actor_type="service", actor_roles=[],
        resource_id=resource_id, resource_type=resource_type,
        metadata=metadata, trace_id=get_trace_id(),
    )
    agent.audit_records[audit_event["id"]] = audit_event
    agent.sync_audit_store.upsert(tenant_id, audit_event["id"], audit_event)
    emit_audit_event(audit_event)


async def store_record(agent: DataSyncAgent, table: str, record_id: str, payload: dict[str, Any]) -> None:
    if not agent.db_service:
        return
    await agent.db_service.store(table, record_id, payload)


def record_connector_sync_metrics(agent: DataSyncAgent, *, tenant_id: str, source_system: str, sync_mode: str, outcome: str, started: datetime) -> None:
    attributes = {
        "service.name": "data-sync-agent",
        "tenant.id": tenant_id,
        "trace.id": get_trace_id() or "unavailable",
        "workflow": "connector_sync",
        "connector": source_system,
        "mode": sync_mode,
        "outcome": outcome,
    }
    agent._sync_business_metrics.executions_total.add(1, attributes)
    agent._sync_business_metrics.execution_duration_seconds.record(
        max((datetime.now(timezone.utc) - started).total_seconds(), 0.0),
        attributes,
    )
