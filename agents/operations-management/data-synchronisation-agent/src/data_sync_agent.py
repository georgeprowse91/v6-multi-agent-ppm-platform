"""
Data Synchronization & Consistency Agent

Purpose:
Ensures that data flowing through the PPM platform and across integrated systems remains
consistent, up-to-date and accurate through master data management and event-driven synchronization.

Specification: agents/operations-management/data-synchronisation-agent/README.md
"""

import os
from pathlib import Path
from typing import Any

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths()

import sync_infrastructure as infra  # noqa: E402
from feature_flags import is_feature_enabled  # noqa: E402
from observability.metrics import build_business_workflow_metrics  # noqa: E402
from sync_actions import (  # noqa: E402
    apply_conflict_resolution,
    detect_update_conflicts,
    enqueue_retry,
    governed_connector_write,
    handle_create_master_record,
    handle_define_mapping,
    handle_detect_conflicts,
    handle_detect_duplicates,
    handle_get_dashboard,
    handle_get_master_record,
    handle_get_metrics,
    handle_get_quality_report,
    handle_get_retry_queue,
    handle_get_schema,
    handle_get_sync_status,
    handle_merge_duplicates,
    handle_process_retry_queue,
    handle_register_schema,
    handle_reprocess_retry,
    handle_resolve_conflict,
    handle_run_sync,
    handle_sync_data,
    handle_update_master_record,
    handle_validate_data,
    record_conflicts,
    record_quality_metrics,
)
from sync_models import InMemorySecretContext, SecretContext  # noqa: E402

from agents.common.connector_integration import (  # noqa: E402
    ConnectorWriteGate,
    DatabaseStorageService,
)
from agents.runtime import BaseAgent  # noqa: E402
from agents.runtime.src.event_bus import EventBus  # noqa: E402
from agents.runtime.src.state_store import TenantStateStore  # noqa: E402

# Re-export Azure SDK classes so monkeypatching in tests works against this module
try:
    from azure.identity import DefaultAzureCredential  # noqa: E402, F811
    from azure.keyvault.secrets import SecretClient  # noqa: E402, F811
except ImportError:  # pragma: no cover - optional dependencies
    DefaultAzureCredential = None  # type: ignore[assignment,misc]
    SecretClient = None  # type: ignore[assignment,misc]


class DataSyncAgent(BaseAgent):
    """
    Data Synchronization & Consistency Agent - Manages data synchronization across systems.

    Key Capabilities:
    - Master data management (MDM)
    - Data mapping and transformation
    - Event-driven synchronization
    - Conflict detection and resolution
    - Duplicate detection and merging
    - Data quality and validation
    - Audit and lineage tracking
    - Synchronization monitoring
    """

    def __init__(self, agent_id: str = "data-synchronisation-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        self.secret_context: SecretContext = (
            config.get("secret_context")
            if config and config.get("secret_context")
            else InMemorySecretContext(config.get("secrets") if config else None)
        )

        # Configuration parameters
        self.sync_latency_sla_seconds = config.get("sync_latency_sla_seconds", 60) if config else 60
        self.duplicate_confidence_threshold = (
            config.get("duplicate_confidence_threshold", 0.85) if config else 0.85
        )
        self.conflict_resolution_strategy = (
            config.get("conflict_resolution_strategy", "last_write_wins") if config else "last_write_wins"
        )
        self.authoritative_sources = config.get("authoritative_sources", {}) if config else {}
        self.sync_event_webhook_url = config.get("sync_event_webhook_url") if config else None
        self.sync_event_webhook_timeout = config.get("sync_event_webhook_timeout", 5.0) if config else 5.0
        self.transformation_rules = config.get("transformation_rules", []) if config else []
        self.transformation_schema = {
            "type": "object",
            "properties": {
                "entity_type": {"type": "string"}, "source_system": {"type": "string"},
                "field_mappings": {"type": "object", "additionalProperties": {"type": "string"}},
                "defaults": {"type": "object"},
                "transformations": {"type": "array", "items": {"type": "object", "properties": {"field": {"type": "string"}, "operation": {"type": "string"}, "value": {}}, "required": ["field", "operation"]}},
            },
            "required": ["entity_type", "field_mappings"],
        }

        master_store_path = Path(config.get("master_record_store_path", "data/master_records.json")) if config else Path("data/master_records.json")
        sync_event_store_path = Path(config.get("sync_event_store_path", "data/sync_events.json")) if config else Path("data/sync_events.json")
        lineage_store_path = Path(config.get("sync_lineage_store_path", "data/lineage/sync_lineage.json")) if config else Path("data/lineage/sync_lineage.json")

        environment = os.getenv("ENVIRONMENT", "dev")
        duplicate_resolution_flag = is_feature_enabled("duplicate_resolution", environment=environment, default=False)
        self.duplicate_resolution_enabled = config.get("duplicate_resolution_enabled", duplicate_resolution_flag) if config else duplicate_resolution_flag
        audit_store_path = Path(config.get("sync_audit_store_path", "data/sync_audit_events.json")) if config else Path("data/sync_audit_events.json")

        self.master_record_store = TenantStateStore(master_store_path)
        self.sync_event_store = TenantStateStore(sync_event_store_path)
        self.sync_lineage_store = TenantStateStore(lineage_store_path)
        self.sync_audit_store = TenantStateStore(audit_store_path)

        self.master_records = {}  # type: ignore
        self.mapping_rules = {}  # type: ignore
        self.sync_events = {}  # type: ignore
        self.conflicts = {}  # type: ignore
        self.duplicates = {}  # type: ignore
        self.audit_records = {}  # type: ignore
        self.db_service: DatabaseStorageService | None = None
        self.write_gate = ConnectorWriteGate(config or {})
        self.event_bus: EventBus | None = None
        self.service_bus_client: Any | None = None
        self.service_bus_queue_sender: Any | None = None
        self.service_bus_topic_sender: Any | None = None
        self.service_bus_topic_name = os.getenv("AZURE_SERVICE_BUS_TOPIC_NAME", "ppm-events")
        self.service_bus_queue_name = os.getenv("AZURE_SERVICE_BUS_QUEUE_NAME", "ppm-sync-queue")
        self.event_grid_client: Any | None = None
        self.sql_engine: Any | None = None
        self.cosmos_client: Any | None = None
        self.data_factory_client: Any | None = None
        self.data_factory_pipelines: list[str] = []
        self.function_app: Any | None = None
        self.function_names: list[str] = []
        self.data_factory_resource_group = os.getenv("AZURE_RESOURCE_GROUP")
        self.data_factory_name = os.getenv("AZURE_DATA_FACTORY_NAME")
        self.function_base_url = os.getenv("AZURE_FUNCTION_BASE_URL")
        self.function_key = os.getenv("AZURE_FUNCTION_KEY")
        self.validation_rules: dict[str, list[dict[str, Any]]] = {}
        self.quality_thresholds: dict[str, float] = {}
        self.schema_registry: dict[str, dict[str, Any]] = {}
        self.schema_versions: dict[str, list[dict[str, Any]]] = {}
        self.schema_registry_store = TenantStateStore(Path(config.get("schema_registry_store_path", "data/schema_registry.json") if config else "data/schema_registry.json"))
        self.seen_record_hashes: dict[str, set[str]] = {}
        self.latency_records: list[dict[str, Any]] = []
        self.quality_records: list[dict[str, Any]] = []
        self.sync_logs: list[dict[str, Any]] = []
        self.sync_state_store = TenantStateStore(Path(config.get("sync_state_store_path", "data/sync_state.json") if config else "data/sync_state.json"))
        self.retry_queue_store = TenantStateStore(Path(config.get("retry_queue_store_path", "data/sync_retry_queue.json") if config else "data/sync_retry_queue.json"))
        self.max_retry_attempts = config.get("max_retry_attempts", 3) if config else 3
        self.log_analytics_client: Any | None = None
        self.connectors: dict[str, Any] = {}
        self._sync_business_metrics = build_business_workflow_metrics("data-sync-agent", "connector_sync")

    def _record_sync_business_start(self, tenant_id: str, trace_id: str) -> None:
        """Record connector sync execution start via standard business metrics."""
        self._sync_business_metrics.executions_total.add(1, {"tenant.id": tenant_id, "trace.id": trace_id})

    def _record_sync_business_duration(self, tenant_id: str, trace_id: str, duration: float) -> None:
        """Record connector sync duration via standard business metrics."""
        self._sync_business_metrics.execution_duration_seconds.record(duration, {"tenant.id": tenant_id, "trace.id": trace_id})

    def _get_setting(self, key: str, default: str | None = None) -> str | None:
        secret_value = self.secret_context.get(key)
        if secret_value is not None:
            return secret_value
        return os.getenv(key, default)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize data sync infrastructure and integrations."""
        await super().initialize()
        self.logger.info("Initializing Data Synchronization & Consistency Agent...")
        self.validation_rules = infra.load_validation_rules(self)
        self.quality_thresholds = infra.load_quality_thresholds(self)
        self.schema_registry, self.schema_versions = infra.load_schema_registry(self)
        self.transformation_rules = infra.load_mapping_rules(self)
        self.data_factory_pipelines, self.function_names = infra.load_pipeline_config(self)
        await infra.initialize_key_vault_secrets(self)
        await infra.initialize_connectors(self)
        await infra.initialize_service_bus(self)
        await infra.initialize_event_grid(self)
        await infra.initialize_datastores(self)
        await infra.initialize_data_factory(self)
        await infra.initialize_functions(self)
        await infra.initialize_monitoring(self)
        db_config = self.config.get("database_storage", {}) if self.config else {}
        self.db_service = DatabaseStorageService(db_config)
        self.logger.info("Database Storage Service initialized")
        self.logger.info("Data Synchronization & Consistency Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")
        if not action:
            self.logger.warning("No action specified")
            return False
        valid_actions = [
            "sync_data", "run_sync", "create_master_record", "update_master_record",
            "detect_conflicts", "resolve_conflict", "detect_duplicates", "merge_duplicates",
            "validate_data", "define_mapping", "get_sync_status", "get_master_record",
            "metrics", "get_schema", "register_schema", "get_quality_report",
            "process_retries", "reprocess_retry", "get_retry_queue", "get_dashboard",
        ]
        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False
        if action == "sync_data":
            if "entity_type" not in input_data or "data" not in input_data:
                self.logger.warning("Missing entity_type or data for sync")
                return False
        return True

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Data Synchronization & Consistency Agent...")
        if self.event_bus and hasattr(self.event_bus, "stop"):
            await self.event_bus.stop()
        if self.service_bus_queue_sender and hasattr(self.service_bus_queue_sender, "close"):
            await self.service_bus_queue_sender.close()
        if self.service_bus_topic_sender and hasattr(self.service_bus_topic_sender, "close"):
            await self.service_bus_topic_sender.close()
        if self.service_bus_client and hasattr(self.service_bus_client, "close"):
            await self.service_bus_client.close()
        if self.sql_engine and hasattr(self.sql_engine, "dispose"):
            self.sql_engine.dispose()
        if self.cosmos_client and hasattr(self.cosmos_client, "close"):
            self.cosmos_client.close()
        if self.log_analytics_client and hasattr(self.log_analytics_client, "close"):
            await self.log_analytics_client.close()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "master_data_management", "event_driven_sync", "data_mapping",
            "data_transformation", "conflict_detection", "conflict_resolution",
            "duplicate_detection", "duplicate_merging", "data_validation",
            "data_quality", "sync_monitoring", "audit_logging", "fuzzy_matching",
        ]

    # ------------------------------------------------------------------
    # Process routing
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process data synchronization requests."""
        action = input_data.get("action", "get_sync_status")
        tenant_id = input_data.get("tenant_id") or input_data.get("context", {}).get("tenant_id") or "default"
        correlation_id = input_data.get("context", {}).get("correlation_id") or input_data.get("correlation_id")

        if action == "sync_data":
            return await self._sync_data(tenant_id, input_data.get("entity_type"), input_data.get("data"), input_data.get("source_system"))
        if action == "run_sync":
            return await self._run_sync(tenant_id=tenant_id, entity_type=input_data.get("entity_type"), source_system=input_data.get("source_system"), mode=input_data.get("mode", "incremental"), filters=input_data.get("filters", {}))
        elif action == "create_master_record":
            return await self._create_master_record(tenant_id, input_data.get("entity_type"), input_data.get("data"))
        elif action == "update_master_record":
            return await self._update_master_record(tenant_id, input_data.get("master_id"), input_data.get("data"), input_data.get("source_system"))
        elif action == "detect_conflicts":
            return await self._detect_conflicts(input_data.get("master_id"))
        elif action == "resolve_conflict":
            return await self._resolve_conflict(input_data.get("conflict_id"), input_data.get("resolution"))
        elif action == "detect_duplicates":
            return await self._detect_duplicates(input_data.get("entity_type"))
        elif action == "merge_duplicates":
            return await self._merge_duplicates(input_data.get("master_ids", []), input_data.get("primary_id"), decision=input_data.get("decision"), reviewer_id=input_data.get("reviewer_id"), comments=input_data.get("comments"), tenant_id=tenant_id, correlation_id=correlation_id)
        elif action == "validate_data":
            return await self._validate_data(input_data.get("entity_type"), input_data.get("data"))
        elif action == "define_mapping":
            return await self._define_mapping(input_data.get("mapping", {}))
        elif action == "get_sync_status":
            return await self._get_sync_status(input_data.get("filters", {}))
        elif action == "get_master_record":
            return await self._get_master_record(tenant_id, input_data.get("master_id"))
        elif action == "metrics":
            return await self._get_metrics(tenant_id)
        elif action == "get_schema":
            return await self._get_schema(input_data.get("entity_type"))
        elif action == "register_schema":
            return await self._register_schema(tenant_id=tenant_id, entity_type=input_data.get("entity_type"), schema=input_data.get("schema", {}), version=input_data.get("version"))
        elif action == "get_quality_report":
            return await self._get_quality_report(tenant_id, input_data.get("entity_type"))
        elif action == "process_retries":
            return await self._process_retry_queue(tenant_id)
        elif action == "reprocess_retry":
            return await self._reprocess_retry(tenant_id, input_data.get("retry_id"))
        elif action == "get_retry_queue":
            return await self._get_retry_queue(tenant_id)
        elif action == "get_dashboard":
            return await self._get_dashboard(tenant_id)
        else:
            raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Delegate methods (preserve original signatures on the class)
    # ------------------------------------------------------------------

    async def _sync_data(self, tenant_id, entity_type, data, source_system):
        return await handle_sync_data(self, tenant_id, entity_type, data, source_system)

    async def _run_sync(self, tenant_id, entity_type, source_system, mode="incremental", filters=None):
        return await handle_run_sync(self, tenant_id, entity_type, source_system, mode, filters)

    async def _create_master_record(self, tenant_id, entity_type, data):
        return await handle_create_master_record(self, tenant_id, entity_type, data)

    async def _update_master_record(self, tenant_id, master_id, data, source_system):
        return await handle_update_master_record(self, tenant_id, master_id, data, source_system)

    async def _detect_conflicts(self, master_id):
        return await handle_detect_conflicts(self, master_id)

    async def _resolve_conflict(self, conflict_id, resolution):
        return await handle_resolve_conflict(self, conflict_id, resolution)

    async def _detect_duplicates(self, entity_type):
        return await handle_detect_duplicates(self, entity_type)

    async def _merge_duplicates(self, master_ids, primary_id, *, decision=None, reviewer_id=None, comments=None, tenant_id=None, correlation_id=None):
        return await handle_merge_duplicates(self, master_ids, primary_id, decision=decision, reviewer_id=reviewer_id, comments=comments, tenant_id=tenant_id, correlation_id=correlation_id)

    async def _validate_data(self, entity_type, data):
        return await handle_validate_data(self, entity_type, data)

    async def _define_mapping(self, mapping_config):
        return await handle_define_mapping(self, mapping_config)

    async def _get_sync_status(self, filters):
        return await handle_get_sync_status(self, filters)

    async def _get_metrics(self, tenant_id):
        return await handle_get_metrics(self, tenant_id)

    async def _get_master_record(self, tenant_id, master_id):
        return await handle_get_master_record(self, tenant_id, master_id)

    async def _get_schema(self, entity_type):
        return await handle_get_schema(self, entity_type)

    async def _register_schema(self, tenant_id, entity_type, schema, version=None):
        return await handle_register_schema(self, tenant_id, entity_type, schema, version)

    async def _get_quality_report(self, tenant_id, entity_type):
        return await handle_get_quality_report(self, tenant_id, entity_type)

    async def _process_retry_queue(self, tenant_id):
        return await handle_process_retry_queue(self, tenant_id)

    async def _reprocess_retry(self, tenant_id, retry_id):
        return await handle_reprocess_retry(self, tenant_id, retry_id)

    async def _get_retry_queue(self, tenant_id):
        return await handle_get_retry_queue(self, tenant_id)

    async def _get_dashboard(self, tenant_id):
        return await handle_get_dashboard(self, tenant_id)

    async def _detect_update_conflicts(self, master_record, new_data, source_system):
        return await detect_update_conflicts(self, master_record, new_data, source_system)

    async def _record_conflicts(self, master_id, conflicts):
        return await record_conflicts(self, master_id, conflicts)

    async def _apply_conflict_resolution(self, master_record, new_data, conflicts):
        return await apply_conflict_resolution(self, master_record, new_data, conflicts)

    async def _enqueue_retry(self, tenant_id, entity_type, data, source_system, reason):
        return await enqueue_retry(self, tenant_id, entity_type, data, source_system, reason)

    async def _record_quality_metrics(self, tenant_id, entity_type, source_system, validation_result):
        return await record_quality_metrics(self, tenant_id, entity_type, source_system, validation_result)

    async def governed_connector_write(self, connector_id, resource_type, payloads, *, approval_required=False, approval_status=None, dry_run=False, tenant_id=""):
        return await governed_connector_write(self, connector_id, resource_type, payloads, approval_required=approval_required, approval_status=approval_status, dry_run=dry_run, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Infrastructure delegates
    # ------------------------------------------------------------------

    def _record_connector_sync_metrics(self, **kwargs):
        return infra.record_connector_sync_metrics(self, **kwargs)

    async def _map_to_canonical(self, entity_type, data, source_system):
        return await infra.map_to_canonical(self, entity_type, data, source_system)

    async def _transform_data(self, entity_type, data, source_system):
        return await infra.transform_data(self, entity_type, data, source_system)

    async def _find_existing_master(self, entity_type, data):
        return await infra.find_existing_master(self, entity_type, data)

    async def _generate_master_id(self, entity_type):
        return await infra.generate_master_id(entity_type)

    async def _generate_mapping_id(self):
        return await infra.generate_mapping_id()

    async def _record_sync_event(self, tenant_id, entity_type, master_id, source_system, status):
        return await infra.record_sync_event(self, tenant_id, entity_type, master_id, source_system, status)

    async def _record_sync_lineage(self, tenant_id, entity_type, master_id, source_system, payload):
        return await infra.record_sync_lineage(self, tenant_id, entity_type, master_id, source_system, payload)

    async def _record_sync_metrics(self, tenant_id, entity_type, source_system, latency_seconds, started_at, finished_at):
        return await infra.record_sync_metrics(self, tenant_id, entity_type, source_system, latency_seconds, started_at, finished_at)

    async def _record_sync_log(self, tenant_id, entity_type, source_system, status, mode, started_at, finished_at=None, master_id=None, details=None):
        return await infra.record_sync_log(self, tenant_id, entity_type, source_system, status, mode, started_at, finished_at, master_id, details)

    async def _emit_audit_event(self, tenant_id, action, resource_id, resource_type, metadata):
        return await infra.emit_audit_event_helper(self, tenant_id, action, resource_id, resource_type, metadata)

    async def _store_record(self, table, record_id, payload):
        return await infra.store_record(self, table, record_id, payload)

    async def _publish_event(self, topic, payload):
        return await infra.publish_event(self, topic, payload)

    async def _publish_sync_event(self, tenant_id, entity_type, master_id, source_system, payload):
        return await infra.publish_sync_event(self, tenant_id, entity_type, master_id, source_system, payload)

    async def _run_etl_workflows(self, tenant_id, entity_type, payload, source_system):
        return await infra.run_etl_workflows(self, tenant_id, entity_type, payload, source_system)

    async def _ingest_latency_metric(self, record):
        return await infra.ingest_latency_metric(self, record)

    async def _ingest_quality_metric(self, record):
        return await infra.ingest_quality_metric(self, record)

    # Config loaders (delegates to infra, exposed for tests)
    def _load_validation_rules(self):
        return infra.load_validation_rules(self)

    def _load_quality_thresholds(self):
        return infra.load_quality_thresholds(self)

    def _load_schema_registry(self):
        return infra.load_schema_registry(self)

    def _load_mapping_rules(self):
        return infra.load_mapping_rules(self)

    def _load_pipeline_config(self):
        return infra.load_pipeline_config(self)

    # Azure initialization (delegates to infra, exposed for tests)
    async def _initialize_key_vault_secrets(self):
        return await infra.initialize_key_vault_secrets(
            self,
            credential_cls=DefaultAzureCredential,
            secret_client_cls=SecretClient,
        )

    async def _initialize_connectors(self):
        return await infra.initialize_connectors(self)

    async def _initialize_service_bus(self):
        return await infra.initialize_service_bus(self)

    async def _initialize_event_grid(self):
        return await infra.initialize_event_grid(self)

    async def _initialize_datastores(self):
        return await infra.initialize_datastores(self)

    async def _initialize_data_factory(self):
        return await infra.initialize_data_factory(self)

    async def _initialize_functions(self):
        return await infra.initialize_functions(self)

    async def _initialize_monitoring(self):
        return await infra.initialize_monitoring(self)
