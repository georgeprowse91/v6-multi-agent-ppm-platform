"""
Agent 23: Data Synchronization & Consistency Agent

Purpose:
Ensures that data flowing through the PPM platform and across integrated systems remains
consistent, up-to-date and accurate through master data management and event-driven synchronization.

Specification: agents/operations-management/agent-23-data-synchronisation-quality/README.md
"""

import hashlib
import json
import os
import sys
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import httpx
import yaml
from observability.metrics import build_business_workflow_metrics
from observability.tracing import get_trace_id
from security.lineage import mask_lineage_payload

from agents.common.connector_integration import DatabaseStorageService, _ensure_connector_paths
from agents.runtime import BaseAgent
from agents.runtime.src.audit import build_audit_event, emit_audit_event
from agents.runtime.src.event_bus import EventBus, ServiceBusEventBus
from agents.runtime.src.state_store import TenantStateStore
from jsonschema import ValidationError, validate

FEATURE_FLAGS_ROOT = Path(__file__).resolve().parents[4] / "packages" / "feature-flags" / "src"
if str(FEATURE_FLAGS_ROOT) not in sys.path:
    sys.path.insert(0, str(FEATURE_FLAGS_ROOT))

from feature_flags import is_feature_enabled  # noqa: E402

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - optional dependency
    fuzz = None

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


class SecretContext(Protocol):
    def get(self, name: str) -> str | None: ...

    def set_many(self, values: Mapping[str, str]) -> None: ...

    def snapshot(self) -> dict[str, str]: ...


class InMemorySecretContext:
    def __init__(self, initial: Mapping[str, str] | None = None) -> None:
        self._values = dict(initial or {})

    def get(self, name: str) -> str | None:
        return self._values.get(name)

    def set_many(self, values: Mapping[str, str]) -> None:
        self._values.update(values)

    def snapshot(self) -> dict[str, str]:
        return dict(self._values)




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

    def __init__(self, agent_id: str = "agent_023", config: dict[str, Any] | None = None):
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
            config.get("conflict_resolution_strategy", "last_write_wins")
            if config
            else "last_write_wins"
        )
        self.authoritative_sources = (
            config.get("authoritative_sources", {}) if config else {}
        )
        self.sync_event_webhook_url = (
            config.get("sync_event_webhook_url") if config else None
        )
        self.sync_event_webhook_timeout = (
            config.get("sync_event_webhook_timeout", 5.0) if config else 5.0
        )
        self.transformation_rules = config.get("transformation_rules", []) if config else []
        self.transformation_schema = {
            "type": "object",
            "properties": {
                "entity_type": {"type": "string"},
                "source_system": {"type": "string"},
                "field_mappings": {"type": "object", "additionalProperties": {"type": "string"}},
                "defaults": {"type": "object"},
                "transformations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field": {"type": "string"},
                            "operation": {"type": "string"},
                            "value": {},
                        },
                        "required": ["field", "operation"],
                    },
                },
            },
            "required": ["entity_type", "field_mappings"],
        }

        master_store_path = (
            Path(config.get("master_record_store_path", "data/master_records.json"))
            if config
            else Path("data/master_records.json")
        )
        sync_event_store_path = (
            Path(config.get("sync_event_store_path", "data/sync_events.json"))
            if config
            else Path("data/sync_events.json")
        )
        lineage_store_path = (
            Path(config.get("sync_lineage_store_path", "data/lineage/sync_lineage.json"))
            if config
            else Path("data/lineage/sync_lineage.json")
        )

        environment = os.getenv("ENVIRONMENT", "dev")
        duplicate_resolution_flag = is_feature_enabled(
            "duplicate_resolution", environment=environment, default=False
        )
        self.duplicate_resolution_enabled = (
            config.get("duplicate_resolution_enabled", duplicate_resolution_flag)
            if config
            else duplicate_resolution_flag
        )
        audit_store_path = (
            Path(config.get("sync_audit_store_path", "data/sync_audit_events.json"))
            if config
            else Path("data/sync_audit_events.json")
        )
        self.master_record_store = TenantStateStore(master_store_path)
        self.sync_event_store = TenantStateStore(sync_event_store_path)
        self.sync_lineage_store = TenantStateStore(lineage_store_path)
        self.sync_audit_store = TenantStateStore(audit_store_path)

        # Data stores (will be replaced with database)
        self.master_records = {}  # type: ignore
        self.mapping_rules = {}  # type: ignore
        self.sync_events = {}  # type: ignore
        self.conflicts = {}  # type: ignore
        self.duplicates = {}  # type: ignore
        self.audit_records = {}  # type: ignore
        self.db_service: DatabaseStorageService | None = None
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
        self.schema_registry_store = TenantStateStore(
            Path(
                config.get("schema_registry_store_path", "data/schema_registry.json")
                if config
                else "data/schema_registry.json"
            )
        )
        self.seen_record_hashes: dict[str, set[str]] = {}
        self.latency_records: list[dict[str, Any]] = []
        self.quality_records: list[dict[str, Any]] = []
        self.sync_logs: list[dict[str, Any]] = []
        self.sync_state_store = TenantStateStore(
            Path(config.get("sync_state_store_path", "data/sync_state.json") if config else "data/sync_state.json")
        )
        self.retry_queue_store = TenantStateStore(
            Path(config.get("retry_queue_store_path", "data/sync_retry_queue.json") if config else "data/sync_retry_queue.json")
        )
        self.max_retry_attempts = config.get("max_retry_attempts", 3) if config else 3
        self.log_analytics_client: Any | None = None
        self.connectors: dict[str, Any] = {}
        self._sync_business_metrics = build_business_workflow_metrics(
            "data-sync-agent", "connector_sync"
        )

    def _get_setting(self, key: str, default: str | None = None) -> str | None:
        secret_value = self.secret_context.get(key)
        if secret_value is not None:
            return secret_value
        return os.getenv(key, default)

    async def initialize(self) -> None:
        """Initialize data sync infrastructure and integrations."""
        await super().initialize()
        self.logger.info("Initializing Data Synchronization & Consistency Agent...")

        self.validation_rules = self._load_validation_rules()
        self.quality_thresholds = self._load_quality_thresholds()
        self.schema_registry, self.schema_versions = self._load_schema_registry()
        self.transformation_rules = self._load_mapping_rules()
        self.data_factory_pipelines, self.function_names = self._load_pipeline_config()

        await self._initialize_key_vault_secrets()
        await self._initialize_connectors()
        await self._initialize_service_bus()
        await self._initialize_event_grid()
        await self._initialize_datastores()
        await self._initialize_data_factory()
        await self._initialize_functions()
        await self._initialize_monitoring()

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
            "sync_data",
            "run_sync",
            "create_master_record",
            "update_master_record",
            "detect_conflicts",
            "resolve_conflict",
            "detect_duplicates",
            "merge_duplicates",
            "validate_data",
            "define_mapping",
            "get_sync_status",
            "get_master_record",
            "metrics",
            "get_schema",
            "register_schema",
            "get_quality_report",
            "process_retries",
            "reprocess_retry",
            "get_retry_queue",
            "get_dashboard",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "sync_data":
            if "entity_type" not in input_data or "data" not in input_data:
                self.logger.warning("Missing entity_type or data for sync")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process data synchronization requests.

        Args:
            input_data: {
                "action": "sync_data" | "create_master_record" | "update_master_record" |
                          "detect_conflicts" | "resolve_conflict" | "detect_duplicates" |
                          "merge_duplicates" | "validate_data" | "define_mapping" |
                          "get_sync_status" | "get_master_record",
                "entity_type": Type of entity (project, resource, vendor, etc.),
                "data": Entity data,
                "source_system": Source system identifier,
                "master_id": Master record ID,
                "conflict_id": Conflict identifier,
                "mapping": Mapping rule definition,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - sync_data: Sync status and master record ID
            - create_master_record: Master record ID
            - update_master_record: Update confirmation
            - detect_conflicts: Detected conflicts
            - resolve_conflict: Resolution result
            - detect_duplicates: Duplicate candidates
            - merge_duplicates: Merge result
            - validate_data: Validation results
            - define_mapping: Mapping rule ID
            - get_sync_status: Synchronization status
            - get_master_record: Master record data
        """
        action = input_data.get("action", "get_sync_status")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )
        correlation_id = input_data.get("context", {}).get("correlation_id") or input_data.get(
            "correlation_id"
        )

        if action == "sync_data":
            return await self._sync_data(
                tenant_id,
                input_data.get("entity_type"),  # type: ignore
                input_data.get("data"),  # type: ignore
                input_data.get("source_system"),  # type: ignore
            )
        if action == "run_sync":
            return await self._run_sync(
                tenant_id=tenant_id,
                entity_type=input_data.get("entity_type"),  # type: ignore
                source_system=input_data.get("source_system"),  # type: ignore
                mode=input_data.get("mode", "incremental"),
                filters=input_data.get("filters", {}),
            )

        elif action == "create_master_record":
            return await self._create_master_record(
                tenant_id, input_data.get("entity_type"), input_data.get("data")  # type: ignore
            )

        elif action == "update_master_record":
            return await self._update_master_record(
                tenant_id,
                input_data.get("master_id"),
                input_data.get("data"),
                input_data.get("source_system"),  # type: ignore
            )

        elif action == "detect_conflicts":
            return await self._detect_conflicts(input_data.get("master_id"))  # type: ignore

        elif action == "resolve_conflict":
            return await self._resolve_conflict(
                input_data.get("conflict_id"), input_data.get("resolution")  # type: ignore
            )

        elif action == "detect_duplicates":
            return await self._detect_duplicates(input_data.get("entity_type"))  # type: ignore

        elif action == "merge_duplicates":
            return await self._merge_duplicates(
                input_data.get("master_ids", []),
                input_data.get("primary_id"),  # type: ignore
                decision=input_data.get("decision"),
                reviewer_id=input_data.get("reviewer_id"),
                comments=input_data.get("comments"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "validate_data":
            return await self._validate_data(input_data.get("entity_type"), input_data.get("data"))  # type: ignore

        elif action == "define_mapping":
            return await self._define_mapping(input_data.get("mapping", {}))

        elif action == "get_sync_status":
            return await self._get_sync_status(input_data.get("filters", {}))

        elif action == "get_master_record":
            return await self._get_master_record(
                tenant_id, input_data.get("master_id")  # type: ignore
            )

        elif action == "metrics":
            return await self._get_metrics(tenant_id)

        elif action == "get_schema":
            return await self._get_schema(input_data.get("entity_type"))  # type: ignore

        elif action == "register_schema":
            return await self._register_schema(
                tenant_id=tenant_id,
                entity_type=input_data.get("entity_type"),
                schema=input_data.get("schema", {}),
                version=input_data.get("version"),
            )

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

    async def _sync_data(
        self, tenant_id: str, entity_type: str, data: dict[str, Any], source_system: str
    ) -> dict[str, Any]:
        """
        Synchronize data from source system.

        Returns sync status and master record ID.
        """
        sync_started_at = datetime.now(timezone.utc)
        self.logger.info(f"Synchronizing {entity_type} from {source_system}")
        await self._record_sync_log(
            tenant_id=tenant_id,
            entity_type=entity_type,
            source_system=source_system,
            status="started",
            mode="single",
            started_at=sync_started_at,
        )
        await self._publish_event(
            "sync.start",
            {
                "tenant_id": tenant_id,
                "entity_type": entity_type,
                "source_system": source_system,
                "started_at": sync_started_at.isoformat(),
            },
        )

        if self._is_duplicate_record(tenant_id, entity_type, data):
            await self._record_sync_log(
                tenant_id=tenant_id,
                entity_type=entity_type,
                source_system=source_system,
                status="duplicate",
                mode="single",
                started_at=sync_started_at,
                finished_at=datetime.now(timezone.utc),
                details={"reason": "Duplicate record discarded"},
            )
            await self._publish_event(
                "sync.complete",
                {
                    "tenant_id": tenant_id,
                    "entity_type": entity_type,
                    "source_system": source_system,
                    "started_at": sync_started_at.isoformat(),
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "status": "duplicate",
                },
            )
            return {
                "status": "duplicate",
                "reason": "Duplicate record discarded",
                "entity_type": entity_type,
                "source_system": source_system,
                "latency_seconds": 0.0,
            }

        mapped_data = await self._map_to_canonical(entity_type, data, source_system)
        # Validate data
        validation_result = await self._validate_data(entity_type, mapped_data)
        await self._record_quality_metrics(
            tenant_id=tenant_id,
            entity_type=entity_type,
            source_system=source_system,
            validation_result=validation_result,
        )
        if not validation_result.get("valid"):
            await self._record_sync_log(
                tenant_id=tenant_id,
                entity_type=entity_type,
                source_system=source_system,
                status="failed",
                mode="single",
                started_at=sync_started_at,
                finished_at=datetime.now(timezone.utc),
                details={
                    "error": "validation_failed",
                    "errors": validation_result.get("errors"),
                },
            )
            await self._enqueue_retry(
                tenant_id,
                entity_type,
                mapped_data,
                source_system,
                reason="validation_failed",
            )
            await self._publish_event(
                "sync.complete",
                {
                    "tenant_id": tenant_id,
                    "entity_type": entity_type,
                    "source_system": source_system,
                    "error": "validation_failed",
                    "errors": validation_result.get("errors"),
                    "started_at": sync_started_at.isoformat(),
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "status": "failed",
                },
            )
            return {
                "status": "failed",
                "error": "Data validation failed",
                "validation_errors": validation_result.get("errors"),
            }

        try:
            # Transform data using mapping rules
            transformed_data = await self._transform_data(
                entity_type, mapped_data, source_system
            )
            await self._run_etl_workflows(tenant_id, entity_type, transformed_data, source_system)

            # Check for existing master record
            existing_master = await self._find_existing_master(entity_type, transformed_data)

            if existing_master:
                # Update existing record
                result = await self._update_master_record(
                    tenant_id,
                    existing_master.get("master_id"),  # type: ignore
                    transformed_data,
                    source_system,
                )
                master_id = existing_master.get("master_id")
            else:
                # Create new master record
                result = await self._create_master_record(
                    tenant_id, entity_type, transformed_data
                )
                master_id = result.get("master_id")

            # Record sync event
            sync_event_id = await self._record_sync_event(
                tenant_id, entity_type, master_id, source_system, "success"  # type: ignore
            )

            await self._record_sync_lineage(
                tenant_id, entity_type, master_id, source_system, transformed_data
            )

            # Publish sync event
            await self._publish_sync_event(
                tenant_id, entity_type, master_id, source_system, transformed_data
            )

            sync_finished_at = datetime.now(timezone.utc)
            latency_seconds = (sync_finished_at - sync_started_at).total_seconds()
            await self._record_sync_metrics(
                tenant_id,
                entity_type,
                source_system,
                latency_seconds,
                sync_started_at,
                sync_finished_at,
            )
            await self._record_sync_log(
                tenant_id=tenant_id,
                entity_type=entity_type,
                source_system=source_system,
                status="success",
                mode="single",
                master_id=master_id,
                started_at=sync_started_at,
                finished_at=sync_finished_at,
                details={"action": "updated" if existing_master else "created"},
            )
            await self._publish_event(
                "sync.complete",
                {
                    "tenant_id": tenant_id,
                    "entity_type": entity_type,
                    "source_system": source_system,
                    "master_id": master_id,
                    "started_at": sync_started_at.isoformat(),
                    "finished_at": sync_finished_at.isoformat(),
                    "latency_seconds": latency_seconds,
                    "status": "success",
                },
            )

            return {
                "status": "success",
                "master_id": master_id,
                "sync_event_id": sync_event_id,
                "action": "updated" if existing_master else "created",
                "latency_seconds": latency_seconds,
            }
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
            await self._enqueue_retry(
                tenant_id,
                entity_type,
                mapped_data,
                source_system,
                reason=str(exc),
            )
            await self._record_sync_log(
                tenant_id=tenant_id,
                entity_type=entity_type,
                source_system=source_system,
                status="failed",
                mode="single",
                started_at=sync_started_at,
                finished_at=datetime.now(timezone.utc),
                details={"error": str(exc)},
            )
            await self._publish_event(
                "data_sync.failure",
                {
                    "tenant_id": tenant_id,
                    "entity_type": entity_type,
                    "source_system": source_system,
                    "error": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            await self._publish_event(
                "sync.complete",
                {
                    "tenant_id": tenant_id,
                    "entity_type": entity_type,
                    "source_system": source_system,
                    "error": str(exc),
                    "started_at": sync_started_at.isoformat(),
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "status": "failed",
                },
            )
            raise

    async def _run_sync(
        self,
        tenant_id: str,
        entity_type: str,
        source_system: str,
        mode: str = "incremental",
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run full or incremental synchronization for a connector."""
        filters = filters or {}
        sync_mode = mode.lower()
        sync_started_at = datetime.now(timezone.utc)
        state_key = f"{source_system}:{entity_type}"
        sync_state = self.sync_state_store.get(tenant_id, state_key) or {}
        last_synced_at = sync_state.get("last_synced_at")
        cursor = sync_state.get("cursor")

        if sync_mode not in {"incremental", "full"}:
            raise ValueError(f"Unsupported sync mode: {mode}")

        await self._publish_event(
            "sync.batch.start",
            {
                "tenant_id": tenant_id,
                "entity_type": entity_type,
                "source_system": source_system,
                "mode": sync_mode,
                "started_at": sync_started_at.isoformat(),
            },
        )
        await self._record_sync_log(
            tenant_id=tenant_id,
            entity_type=entity_type,
            source_system=source_system,
            status="started",
            mode=sync_mode,
            started_at=sync_started_at,
            details={"filters": filters},
        )

        if sync_mode == "incremental":
            records, new_cursor = await self._fetch_incremental_records(
                source_system, entity_type, last_synced_at, cursor, filters
            )
        else:
            records, new_cursor = await self._fetch_full_records(
                source_system, entity_type, filters
            )

        results = []
        for record in records:
            try:
                result = await self._sync_data(tenant_id, entity_type, record, source_system)
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
                result = {"status": "failed", "error": str(exc)}
            results.append(result)

        sync_finished_at = datetime.now(timezone.utc)
        new_state = {
            "source_system": source_system,
            "entity_type": entity_type,
            "last_synced_at": sync_finished_at.isoformat(),
            "cursor": new_cursor or cursor,
            "mode": sync_mode,
            "record_count": len(records),
            "updated_at": sync_finished_at.isoformat(),
        }
        self.sync_state_store.upsert(tenant_id, state_key, new_state)
        await self._store_record("sync_state", state_key, new_state)

        await self._publish_event(
            "sync.batch.complete",
            {
                "tenant_id": tenant_id,
                "entity_type": entity_type,
                "source_system": source_system,
                "mode": sync_mode,
                "record_count": len(records),
                "started_at": sync_started_at.isoformat(),
                "finished_at": sync_finished_at.isoformat(),
            },
        )
        await self._record_sync_log(
            tenant_id=tenant_id,
            entity_type=entity_type,
            source_system=source_system,
            status="completed",
            mode=sync_mode,
            started_at=sync_started_at,
            finished_at=sync_finished_at,
            details={"record_count": len(records)},
        )
        failed_records = sum(1 for item in results if item.get("status") == "failed")
        self._record_connector_sync_metrics(
            tenant_id=tenant_id,
            source_system=source_system,
            sync_mode=sync_mode,
            outcome="failed" if failed_records else "completed",
            started=sync_started_at,
        )

        return {
            "status": "completed",
            "mode": sync_mode,
            "records_processed": len(records),
            "results": results,
            "started_at": sync_started_at.isoformat(),
            "finished_at": sync_finished_at.isoformat(),
        }

    def _record_connector_sync_metrics(
        self,
        *,
        tenant_id: str,
        source_system: str,
        sync_mode: str,
        outcome: str,
        started: datetime,
    ) -> None:
        attributes = {
            "service.name": "data-sync-agent",
            "tenant.id": tenant_id,
            "trace.id": get_trace_id() or "unavailable",
            "workflow": "connector_sync",
            "connector": source_system,
            "mode": sync_mode,
            "outcome": outcome,
        }
        self._sync_business_metrics.executions_total.add(1, attributes)
        self._sync_business_metrics.execution_duration_seconds.record(
            max((datetime.now(timezone.utc) - started).total_seconds(), 0.0),
            attributes,
        )

    async def _fetch_incremental_records(
        self,
        source_system: str,
        entity_type: str,
        last_synced_at: str | None,
        cursor: str | None,
        filters: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Fetch records using change data capture or timestamp-based queries."""
        connector = self.connectors.get(source_system)
        if connector is None:
            return [], None

        if hasattr(connector, "read_changes"):
            try:
                records = connector.read_changes(entity_type, cursor=cursor, filters=filters)
                new_cursor = getattr(connector, "last_cursor", None)
                return records, new_cursor
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
                self.logger.warning("cdc_fetch_failed", extra={"error": str(exc)})

        query_filters = dict(filters)
        if last_synced_at:
            query_filters.setdefault("updated_since", last_synced_at)
            query_filters.setdefault("since", last_synced_at)
        records = self._fetch_connector_records(connector, entity_type, query_filters)
        return records, None

    async def _fetch_full_records(
        self,
        source_system: str,
        entity_type: str,
        filters: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str | None]:
        connector = self.connectors.get(source_system)
        if connector is None:
            return [], None
        records = self._fetch_connector_records(connector, entity_type, filters)
        return records, None

    def _fetch_connector_records(
        self, connector: Any, entity_type: str, filters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        if hasattr(connector, "read"):
            try:
                return connector.read(entity_type, filters=filters)
            except TypeError:
                return connector.read(entity_type)
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
                self.logger.warning(
                    "connector_read_failed",
                    extra={"entity_type": entity_type, "error": str(exc)},
                )
        return []

    async def _create_master_record(
        self, tenant_id: str, entity_type: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create new master record.

        Returns master record ID.
        """
        self.logger.info(f"Creating master record for {entity_type}")

        # Generate master ID
        master_id = await self._generate_master_id(entity_type)

        # Create master record
        master_record = {
            "master_id": master_id,
            "entity_type": entity_type,
            "data": data,
            "source_systems": {},
            "version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store master record
        self.master_records[master_id] = master_record
        self.master_record_store.upsert(tenant_id, master_id, master_record.copy())

        await self._emit_audit_event(
            tenant_id,
            action="master_record.created",
            resource_id=master_id,
            resource_type=entity_type,
            metadata={"version": 1},
        )

        await self._store_record("master_records", master_id, master_record)

        return {"master_id": master_id, "entity_type": entity_type, "version": 1}

    async def _update_master_record(
        self, tenant_id: str, master_id: str, data: dict[str, Any], source_system: str
    ) -> dict[str, Any]:
        """
        Update existing master record.

        Returns update confirmation.
        """
        self.logger.info(f"Updating master record: {master_id}")

        master_record = self.master_records.get(master_id)
        if not master_record:
            raise ValueError(f"Master record not found: {master_id}")

        # Detect conflicts
        conflicts = await self._detect_update_conflicts(master_record, data, source_system)

        if conflicts:
            # Record conflicts
            await self._record_conflicts(master_id, conflicts)

            # Apply conflict resolution strategy
            resolved_data = await self._apply_conflict_resolution(master_record, data, conflicts)
        else:
            resolved_data = data

        # Update master record
        master_record["data"].update(resolved_data)
        master_record["source_systems"][source_system] = datetime.now(timezone.utc).isoformat()
        master_record["version"] += 1
        master_record["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.master_record_store.upsert(tenant_id, master_id, master_record.copy())

        await self._emit_audit_event(
            tenant_id,
            action="master_record.updated",
            resource_id=master_id,
            resource_type=master_record.get("entity_type", "unknown"),
            metadata={"version": master_record["version"], "source_system": source_system},
        )

        await self._store_record("master_records", master_id, master_record)

        return {
            "master_id": master_id,
            "version": master_record["version"],
            "conflicts_detected": len(conflicts) if conflicts else 0,
            "updated_at": master_record["updated_at"],
        }

    async def _detect_conflicts(self, master_id: str) -> dict[str, Any]:
        """
        Detect data conflicts for master record.

        Returns detected conflicts.
        """
        self.logger.info(f"Detecting conflicts for master record: {master_id}")

        # Get conflicts for this master record
        record_conflicts = [
            conflict
            for conflict_id, conflict in self.conflicts.items()
            if conflict.get("master_id") == master_id and conflict.get("status") == "pending"
        ]

        return {
            "master_id": master_id,
            "conflicts": record_conflicts,
            "conflict_count": len(record_conflicts),
        }

    async def _resolve_conflict(
        self, conflict_id: str, resolution: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Resolve data conflict.

        Returns resolution result.
        """
        self.logger.info(f"Resolving conflict: {conflict_id}")

        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            raise ValueError(f"Conflict not found: {conflict_id}")

        # Apply resolution
        resolved_value = resolution.get("value")
        conflict["resolved_value"] = resolved_value
        conflict["resolved_by"] = resolution.get("resolved_by", "system")
        conflict["resolved_at"] = datetime.now(timezone.utc).isoformat()
        conflict["status"] = "resolved"

        # Update master record
        master_id = conflict.get("master_id")
        if master_id and master_id in self.master_records:
            field = conflict.get("field")
            self.master_records[master_id]["data"][field] = resolved_value

        await self._store_record("conflicts", conflict_id, conflict)
        await self._publish_event(
            "conflict.resolved",
            {
                "conflict_id": conflict_id,
                "master_id": master_id,
                "resolved_value": resolved_value,
                "resolved_by": conflict.get("resolved_by"),
                "resolved_at": conflict.get("resolved_at"),
            },
        )

        return {
            "conflict_id": conflict_id,
            "resolution": "success",
            "resolved_value": resolved_value,
        }

    async def _detect_duplicates(self, entity_type: str) -> dict[str, Any]:
        """
        Detect duplicate master records.

        Returns duplicate candidates.
        """
        self.logger.info(f"Detecting duplicates for entity type: {entity_type}")

        # Get all master records of this type
        type_records = [
            (master_id, record)
            for master_id, record in self.master_records.items()
            if record.get("entity_type") == entity_type
        ]

        # Find duplicates using fuzzy matching
        duplicates = await self._fuzzy_match_duplicates(type_records)

        return {
            "entity_type": entity_type,
            "duplicate_sets": duplicates,
            "duplicate_count": len(duplicates),
        }

    async def _merge_duplicates(
        self,
        master_ids: list[str],
        primary_id: str,
        *,
        decision: str | None = None,
        reviewer_id: str | None = None,
        comments: str | None = None,
        tenant_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Merge duplicate records.

        Returns merge result.
        """
        if not primary_id:
            raise ValueError("Primary ID must be provided")
        decision_value = (decision or "approved").lower()
        if decision_value not in {"approved", "rejected"}:
            raise ValueError("Decision must be 'approved' or 'rejected'")

        if decision_value == "rejected":
            self.logger.info(f"Merge decision rejected for {primary_id}")
            if self.duplicate_resolution_enabled:
                self._emit_merge_decision_audit(
                    decision=decision_value,
                    tenant_id=tenant_id or "default",
                    primary_id=primary_id,
                    master_ids=master_ids,
                    reviewer_id=reviewer_id,
                    comments=comments,
                    correlation_id=correlation_id,
                )
            return {
                "primary_id": primary_id,
                "merged_count": 0,
                "merged_ids": [],
                "decision": "rejected",
            }

        self.logger.info(f"Merging {len(master_ids)} duplicates into {primary_id}")

        if primary_id not in master_ids:
            raise ValueError("Primary ID must be in the list of master IDs")

        primary_record = self.master_records.get(primary_id)
        if not primary_record:
            raise ValueError(f"Primary record not found: {primary_id}")

        # Merge data from all records
        merged_data = primary_record["data"].copy()

        for master_id in master_ids:
            if master_id == primary_id:
                continue

            duplicate_record = self.master_records.get(master_id)
            if duplicate_record:
                # Merge data (prefer non-null values)
                for key, value in duplicate_record["data"].items():
                    if value and not merged_data.get(key):
                        merged_data[key] = value

                # Mark as merged
                duplicate_record["merged_into"] = primary_id
                duplicate_record["merged_at"] = datetime.now(timezone.utc).isoformat()

        # Update primary record
        primary_record["data"] = merged_data
        primary_record["version"] += 1
        primary_record["updated_at"] = datetime.now(timezone.utc).isoformat()

        await self._store_record("master_records", primary_id, primary_record)
        for master_id in master_ids:
            duplicate_record = self.master_records.get(master_id)
            if duplicate_record:
                await self._store_record("master_records", master_id, duplicate_record)

        if self.duplicate_resolution_enabled:
            self._emit_merge_decision_audit(
                decision=decision_value,
                tenant_id=tenant_id or "default",
                primary_id=primary_id,
                master_ids=master_ids,
                reviewer_id=reviewer_id,
                comments=comments,
                correlation_id=correlation_id,
            )

        return {
            "primary_id": primary_id,
            "merged_count": len(master_ids) - 1,
            "merged_ids": [mid for mid in master_ids if mid != primary_id],
            "decision": "approved",
        }

    def _emit_merge_decision_audit(
        self,
        *,
        decision: str,
        tenant_id: str,
        primary_id: str,
        master_ids: list[str],
        reviewer_id: str | None,
        comments: str | None,
        correlation_id: str | None,
    ) -> None:
        event = build_audit_event(
            tenant_id=tenant_id,
            action="duplicate_resolution.merge_decision",
            outcome="success" if decision == "approved" else "denied",
            actor_id=reviewer_id or "system",
            actor_type="user" if reviewer_id else "service",
            actor_roles=[],
            resource_id=primary_id,
            resource_type="master_record",
            metadata={
                "decision": decision,
                "primary_id": primary_id,
                "master_ids": master_ids,
                "comments": comments,
            },
            trace_id=get_trace_id() or "unknown",
            correlation_id=correlation_id,
        )
        emit_audit_event(event)

    async def _validate_data(self, entity_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate data quality.

        Returns validation results.
        """
        self.logger.info(f"Validating {entity_type} data")

        errors = []
        warnings = []

        # Get validation rules for entity type
        validation_rules = await self._get_validation_rules(entity_type)

        # Apply validation rules
        for rule in validation_rules:
            result = await self._apply_validation_rule(data, rule)
            if not result.get("valid"):
                if result.get("severity") == "error":
                    errors.append(result.get("message"))
                else:
                    warnings.append(result.get("message"))

        schema = self.schema_registry.get(entity_type)
        if schema:
            schema_errors = self._validate_against_schema(schema, data)
            errors.extend(schema_errors)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

    async def _define_mapping(self, mapping_config: dict[str, Any]) -> dict[str, Any]:
        """
        Define data mapping rule.

        Returns mapping rule ID.
        """
        self.logger.info(f"Defining mapping: {mapping_config.get('name')}")

        # Generate mapping ID
        mapping_id = await self._generate_mapping_id()

        # Create mapping rule
        mapping_rule = {
            "mapping_id": mapping_id,
            "name": mapping_config.get("name"),
            "source_system": mapping_config.get("source_system"),
            "target_entity": mapping_config.get("target_entity"),
            "field_mappings": mapping_config.get("field_mappings", {}),
            "transformations": mapping_config.get("transformations", []),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store mapping rule
        self.mapping_rules[mapping_id] = mapping_rule
        self.transformation_rules.append(
            {
                "entity_type": mapping_rule.get("target_entity"),
                "source_system": mapping_rule.get("source_system"),
                "field_mappings": mapping_rule.get("field_mappings"),
                "transformations": mapping_rule.get("transformations", []),
            }
        )

        await self._store_record("mapping_rules", mapping_id, mapping_rule)

        return {
            "mapping_id": mapping_id,
            "name": mapping_rule["name"],
            "field_count": len(mapping_rule["field_mappings"]),
        }

    async def _get_sync_status(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Get synchronization status.

        Returns sync statistics.
        """
        self.logger.info("Retrieving sync status")

        # Calculate sync statistics
        total_events = len(self.sync_events)
        successful_syncs = sum(
            1 for event in self.sync_events.values() if event.get("status") == "success"
        )
        failed_syncs = total_events - successful_syncs

        # Get recent events
        recent_events = sorted(
            self.sync_events.values(), key=lambda x: x.get("timestamp", ""), reverse=True
        )[:10]

        # Get conflict and duplicate counts
        pending_conflicts = sum(
            1 for conflict in self.conflicts.values() if conflict.get("status") == "pending"
        )
        avg_latency = (
            sum(record["latency_seconds"] for record in self.latency_records)
            / len(self.latency_records)
            if self.latency_records
            else 0.0
        )

        return {
            "total_sync_events": total_events,
            "successful_syncs": successful_syncs,
            "failed_syncs": failed_syncs,
            "success_rate": (successful_syncs / total_events * 100) if total_events > 0 else 0,
            "failure_rate": (failed_syncs / total_events * 100) if total_events > 0 else 0,
            "pending_conflicts": pending_conflicts,
            "recent_events": recent_events,
            "avg_latency_seconds": avg_latency,
        }

    async def _get_metrics(self, tenant_id: str) -> dict[str, Any]:
        """Expose latency metrics and event bus statistics."""
        records = [record for record in self.latency_records if record["tenant_id"] == tenant_id]
        avg_latency = (
            sum(record["latency_seconds"] for record in records) / len(records)
            if records
            else 0.0
        )
        return {
            "tenant_id": tenant_id,
            "latency_records": records[-25:],
            "average_latency_seconds": avg_latency,
            "event_bus_metrics": self.event_bus.get_metrics() if self.event_bus else {},
        }

    async def _get_master_record(self, tenant_id: str, master_id: str) -> dict[str, Any]:
        """
        Get master record with lineage.

        Returns master record data.
        """
        self.logger.info(f"Retrieving master record: {master_id}")

        master_record = self.master_records.get(master_id)
        if not master_record:
            master_record = self.master_record_store.get(tenant_id, master_id)
            if master_record:
                self.master_records[master_id] = master_record
        if not master_record:
            raise ValueError(f"Master record not found: {master_id}")

        return {
            "master_id": master_id,
            "entity_type": master_record.get("entity_type"),
            "data": master_record.get("data"),
            "version": master_record.get("version"),
            "source_systems": master_record.get("source_systems"),
            "created_at": master_record.get("created_at"),
            "updated_at": master_record.get("updated_at"),
        }

    # Helper methods

    def _load_validation_rules(self) -> dict[str, list[dict[str, Any]]]:
        rules_path = Path(self.config.get("validation_rules_path", "config/agent-23/validation_rules.yaml")) if self.config else Path("config/agent-23/validation_rules.yaml")
        if not rules_path.exists():
            return {}
        try:
            with rules_path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
        except (OSError, yaml.YAMLError) as exc:
            self.logger.warning("validation_rules_load_failed", extra={"error": str(exc)})
            return {}
        return {
            key: value if isinstance(value, list) else []
            for key, value in payload.items()
        }

    def _load_quality_thresholds(self) -> dict[str, float | dict[str, float]]:
        thresholds_path = (
            Path(self.config.get("quality_thresholds_path", "config/agent-23/quality_thresholds.yaml"))
            if self.config
            else Path("config/agent-23/quality_thresholds.yaml")
        )
        if not thresholds_path.exists():
            return {}
        try:
            with thresholds_path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
        except (OSError, yaml.YAMLError) as exc:
            self.logger.warning("quality_thresholds_load_failed", extra={"error": str(exc)})
            return {}
        thresholds: dict[str, float | dict[str, float]] = {}
        for key, value in payload.items():
            if isinstance(value, (int, float)):
                thresholds[key] = float(value)
            elif isinstance(value, dict):
                thresholds[key] = {
                    metric: float(metric_value)
                    for metric, metric_value in value.items()
                    if isinstance(metric_value, (int, float))
                }
        return thresholds

    def _load_schema_registry(self) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
        registry_path = (
            Path(self.config.get("schema_registry_path", "config/agent-23/schema_registry.yaml"))
            if self.config
            else Path("config/agent-23/schema_registry.yaml")
        )
        if not registry_path.exists():
            return {}, {}
        try:
            with registry_path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
        except (OSError, yaml.YAMLError) as exc:
            self.logger.warning("schema_registry_load_failed", extra={"error": str(exc)})
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
                versions.setdefault(entity_type, []).append(
                    {"version": version, "schema": schema}
                )
        return registry, versions

    def _load_mapping_rules(self) -> list[dict[str, Any]]:
        mapping_path = (
            Path(self.config.get("mapping_rules_path", "config/agent-23/mapping_rules.yaml"))
            if self.config
            else Path("config/agent-23/mapping_rules.yaml")
        )
        if not mapping_path.exists():
            return []
        try:
            with mapping_path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
        except (OSError, yaml.YAMLError) as exc:
            self.logger.warning("mapping_rules_load_failed", extra={"error": str(exc)})
            return []
        mappings = payload.get("mappings", [])
        if not isinstance(mappings, list):
            return []
        return [entry for entry in mappings if isinstance(entry, dict)]

    async def _get_schema(self, entity_type: str | None) -> dict[str, Any]:
        if not entity_type:
            return {"schemas": self.schema_registry}
        schema = self.schema_registry.get(entity_type)
        if not schema:
            raise ValueError(f"Schema not found for {entity_type}")
        return {"entity_type": entity_type, "schema": schema}

    async def _register_schema(
        self,
        tenant_id: str,
        entity_type: str | None,
        schema: dict[str, Any],
        version: str | None = None,
    ) -> dict[str, Any]:
        if not entity_type:
            raise ValueError("entity_type is required for schema registration")
        version = version or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        self.schema_registry[entity_type] = schema
        self.schema_versions.setdefault(entity_type, []).append(
            {"version": version, "schema": schema}
        )
        self.schema_registry_store.upsert(
            tenant_id,
            f"{entity_type}:{version}",
            {"entity_type": entity_type, "version": version, "schema": schema},
        )
        await self._store_record("schema_registry", f"{entity_type}:{version}", schema)
        return {"entity_type": entity_type, "version": version}

    async def _map_to_canonical(
        self, entity_type: str, data: dict[str, Any], source_system: str
    ) -> dict[str, Any]:
        rules = [
            rule
            for rule in self.transformation_rules
            if rule.get("entity_type") == entity_type
            and rule.get("source_system") == source_system
        ]
        if not rules:
            return data
        mapped = data.copy()
        for rule in rules:
            if not self._validate_transformation_rule(rule):
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

    def _validate_against_schema(self, schema: dict[str, Any], data: dict[str, Any]) -> list[str]:
        try:
            validate(instance=data, schema=schema)
        except ValidationError as exc:
            return [str(exc)]
        return []

    async def _record_quality_metrics(
        self,
        tenant_id: str,
        entity_type: str,
        source_system: str,
        validation_result: dict[str, Any],
    ) -> None:
        completeness_score, consistency_score, timeliness_score, age_seconds = (
            self._compute_quality_dimensions(entity_type, validation_result)
        )
        quality_score = (
            completeness_score + consistency_score + timeliness_score
        ) / 3
        record = {
            "tenant_id": tenant_id,
            "entity_type": entity_type,
            "source_system": source_system,
            "valid": validation_result.get("valid", False),
            "error_count": len(validation_result.get("errors", [])),
            "warning_count": len(validation_result.get("warnings", [])),
            "validated_at": validation_result.get("validated_at"),
            "completeness_score": completeness_score,
            "consistency_score": consistency_score,
            "timeliness_score": timeliness_score,
            "quality_score": quality_score,
            "age_seconds": age_seconds,
        }
        self.quality_records.append(record)
        await self._store_record("data_quality_metrics", self._quality_record_key(record), record)
        await self._ingest_quality_metric(record)
        await self._store_quality_report(tenant_id, entity_type)
        await self._evaluate_quality_thresholds(tenant_id, entity_type)

    async def _get_quality_report(
        self, tenant_id: str, entity_type: str | None
    ) -> dict[str, Any]:
        records = [
            record
            for record in self.quality_records
            if record["tenant_id"] == tenant_id
            and (entity_type is None or record["entity_type"] == entity_type)
        ]
        total = len(records)
        valid_count = sum(1 for record in records if record.get("valid"))
        error_rate = (total - valid_count) / total if total else 0.0
        avg_completeness = (
            sum(record.get("completeness_score", 0.0) for record in records) / total
            if total
            else 0.0
        )
        avg_consistency = (
            sum(record.get("consistency_score", 0.0) for record in records) / total
            if total
            else 0.0
        )
        avg_timeliness = (
            sum(record.get("timeliness_score", 0.0) for record in records) / total
            if total
            else 0.0
        )
        quality_score = (
            (avg_completeness + avg_consistency + avg_timeliness) / 3
            if total
            else 0.0
        )
        return {
            "tenant_id": tenant_id,
            "entity_type": entity_type,
            "total_records": total,
            "valid_records": valid_count,
            "error_rate": error_rate,
            "avg_completeness_score": avg_completeness,
            "avg_consistency_score": avg_consistency,
            "avg_timeliness_score": avg_timeliness,
            "quality_score": quality_score,
            "records": records[-25:],
        }

    async def _evaluate_quality_thresholds(self, tenant_id: str, entity_type: str) -> None:
        threshold_config = self.quality_thresholds.get(
            entity_type, self.quality_thresholds.get("default", 0.9)
        )
        report = await self._get_quality_report(tenant_id, entity_type)
        if report["total_records"] == 0:
            return
        breaches = []
        if isinstance(threshold_config, dict):
            overall_threshold = threshold_config.get("overall")
            if overall_threshold is not None and report["quality_score"] < overall_threshold:
                breaches.append("overall")
            for metric in ("completeness", "consistency", "timeliness"):
                metric_threshold = threshold_config.get(metric)
                metric_key = f"avg_{metric}_score"
                if metric_threshold is not None and report.get(metric_key, 1.0) < metric_threshold:
                    breaches.append(metric)
        else:
            overall_threshold = float(threshold_config)
            if report["quality_score"] < overall_threshold:
                breaches.append("overall")
        if breaches:
            await self._publish_event(
                "data_quality.alert",
                {
                    "tenant_id": tenant_id,
                    "entity_type": entity_type,
                    "quality_score": report["quality_score"],
                    "thresholds": threshold_config,
                    "breaches": breaches,
                    "completeness_score": report.get("avg_completeness_score"),
                    "consistency_score": report.get("avg_consistency_score"),
                    "timeliness_score": report.get("avg_timeliness_score"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

    def _quality_record_key(self, record: dict[str, Any]) -> str:
        return f"{record['tenant_id']}:{record['entity_type']}:{record['validated_at']}"

    async def _enqueue_retry(
        self,
        tenant_id: str,
        entity_type: str,
        data: dict[str, Any],
        source_system: str,
        reason: str,
    ) -> None:
        retry_id = f"RETRY-{uuid.uuid4()}"
        retry_payload = {
            "retry_id": retry_id,
            "tenant_id": tenant_id,
            "entity_type": entity_type,
            "source_system": source_system,
            "data": data,
            "reason": reason,
            "attempts": 0,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        }
        self.retry_queue_store.upsert(tenant_id, retry_id, retry_payload)
        await self._store_record("sync_retry_queue", retry_id, retry_payload)

    async def _process_retry_queue(self, tenant_id: str) -> dict[str, Any]:
        retries = self.retry_queue_store.list(tenant_id)
        processed = 0
        successes = 0
        failures = 0
        for payload in retries:
            retry_id = payload.get("retry_id")
            if not retry_id:
                continue
            attempts = payload.get("attempts", 0)
            if attempts >= self.max_retry_attempts:
                continue
            try:
                await self._sync_data(
                    tenant_id,
                    payload.get("entity_type"),
                    payload.get("data"),
                    payload.get("source_system"),
                )
                successes += 1
                self.retry_queue_store.delete(tenant_id, retry_id)
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError):
                payload["attempts"] = attempts + 1
                payload["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
                self.retry_queue_store.upsert(tenant_id, retry_id, payload)
                failures += 1
            processed += 1
        return {
            "processed": processed,
            "successes": successes,
            "failures": failures,
            "remaining": len(self.retry_queue_store.list(tenant_id)),
        }

    async def _reprocess_retry(self, tenant_id: str, retry_id: str | None) -> dict[str, Any]:
        if not retry_id:
            raise ValueError("retry_id is required")
        payload = self.retry_queue_store.get(tenant_id, retry_id)
        if not payload:
            raise ValueError(f"Retry item not found: {retry_id}")
        try:
            await self._sync_data(
                tenant_id,
                payload.get("entity_type"),
                payload.get("data"),
                payload.get("source_system"),
            )
            self.retry_queue_store.delete(tenant_id, retry_id)
            return {"retry_id": retry_id, "status": "success"}
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
            payload["attempts"] = payload.get("attempts", 0) + 1
            payload["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
            payload["last_error"] = str(exc)
            self.retry_queue_store.upsert(tenant_id, retry_id, payload)
            return {"retry_id": retry_id, "status": "failed", "error": str(exc)}

    async def _get_retry_queue(self, tenant_id: str) -> dict[str, Any]:
        retries = self.retry_queue_store.list(tenant_id)
        return {
            "tenant_id": tenant_id,
            "retry_count": len(retries),
            "retries": retries,
        }

    async def _get_dashboard(self, tenant_id: str) -> dict[str, Any]:
        sync_status = await self._get_sync_status({})
        quality_report = await self._get_quality_report(tenant_id, None)
        state_records = self.sync_state_store.list(tenant_id)
        lag_seconds = []
        for payload in state_records:
            last_synced = payload.get("last_synced_at")
            if last_synced:
                try:
                    last_synced_dt = datetime.fromisoformat(last_synced)
                    lag_seconds.append((datetime.now(timezone.utc) - last_synced_dt).total_seconds())
                except ValueError:
                    continue
        average_lag = sum(lag_seconds) / len(lag_seconds) if lag_seconds else 0.0
        return {
            "sync_status": sync_status,
            "quality_report": quality_report,
            "average_sync_lag_seconds": average_lag,
            "sync_state": state_records,
            "sync_logs": self.sync_logs[-25:],
        }

    def _load_pipeline_config(self) -> tuple[list[str], list[str]]:
        config_path = Path(self.config.get("pipeline_config_path", "config/agent-23/pipelines.yaml")) if self.config else Path("config/agent-23/pipelines.yaml")
        if not config_path.exists():
            return [], []
        try:
            with config_path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
        except (OSError, yaml.YAMLError) as exc:
            self.logger.warning("pipeline_config_load_failed", extra={"error": str(exc)})
            return [], []
        pipelines = [
            entry.get("name")
            for entry in payload.get("pipelines", [])
            if isinstance(entry, dict) and entry.get("name")
        ]
        functions = [
            entry.get("name")
            for entry in payload.get("functions", [])
            if isinstance(entry, dict) and entry.get("name")
        ]
        return pipelines, functions

    async def _initialize_key_vault_secrets(self) -> None:
        key_vault_url = self._get_setting("AZURE_KEY_VAULT_URL")
        if not key_vault_url or not DefaultAzureCredential or not SecretClient:
            return
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=key_vault_url, credential=credential)
        secret_names = [
            "PLANVIEW_CLIENT_ID",
            "PLANVIEW_CLIENT_SECRET",
            "PLANVIEW_REFRESH_TOKEN",
            "PLANVIEW_INSTANCE_URL",
            "SAP_USERNAME",
            "SAP_PASSWORD",
            "SAP_URL",
            "JIRA_EMAIL",
            "JIRA_API_TOKEN",
            "JIRA_INSTANCE_URL",
            "WORKDAY_CLIENT_ID",
            "WORKDAY_CLIENT_SECRET",
            "WORKDAY_REFRESH_TOKEN",
            "WORKDAY_API_URL",
        ]
        loaded_secrets: dict[str, str] = {}
        for secret_name in secret_names:
            if self._get_setting(secret_name):
                continue
            try:
                secret = client.get_secret(secret_name)
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
                self.logger.warning(
                    "keyvault_secret_unavailable",
                    extra={"secret": secret_name, "error": str(exc)},
                )
                continue
            if secret and secret.value:
                loaded_secrets[secret_name] = secret.value

        if loaded_secrets:
            self.secret_context.set_many(loaded_secrets)

    async def _initialize_connectors(self) -> None:
        _ensure_connector_paths()
        try:
            from base_connector import ConnectorCategory, ConnectorConfig
            from azure_devops_connector import AzureDevOpsConnector
            from jira_connector import JiraConnector
            from planview_connector import PlanviewConnector
            from sap_connector import SapConnector
            from smartsheet_connector import SmartsheetConnector
            from workday_connector import WorkdayConnector
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
            self.logger.warning("connector_import_failed", extra={"error": str(exc)})
            return

        self.connectors: dict[str, Any] = {}
        self._sync_business_metrics = build_business_workflow_metrics(
            "data-sync-agent", "connector_sync"
        )
        try:
            planview_config = ConnectorConfig(
                connector_id="planview",
                name="Planview",
                category=ConnectorCategory.PPM,
                instance_url=self._get_setting("PLANVIEW_INSTANCE_URL", "") or "",
            )
            self.connectors["planview"] = PlanviewConnector(planview_config)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
            self.logger.warning("planview_connector_failed", extra={"error": str(exc)})
        try:
            sap_config = ConnectorConfig(
                connector_id="sap",
                name="SAP",
                category=ConnectorCategory.ERP,
                instance_url=self._get_setting("SAP_URL", "") or "",
            )
            self.connectors["sap"] = SapConnector(sap_config)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
            self.logger.warning("sap_connector_failed", extra={"error": str(exc)})
        try:
            jira_config = ConnectorConfig(
                connector_id="jira",
                name="Jira",
                category=ConnectorCategory.PM,
                instance_url=self._get_setting("JIRA_INSTANCE_URL", "") or "",
            )
            self.connectors["jira"] = JiraConnector(jira_config)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
            self.logger.warning("jira_connector_failed", extra={"error": str(exc)})
        try:
            workday_config = ConnectorConfig(
                connector_id="workday",
                name="Workday",
                category=ConnectorCategory.HRIS,
                instance_url=self._get_setting("WORKDAY_API_URL", "") or "",
            )
            self.connectors["workday"] = WorkdayConnector(workday_config)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
            self.logger.warning("workday_connector_failed", extra={"error": str(exc)})
        try:
            smartsheet_config = ConnectorConfig(
                connector_id="smartsheet",
                name="Smartsheet",
                category=ConnectorCategory.PM,
                instance_url=self._get_setting("SMARTSHEET_API_URL", "") or "",
            )
            self.connectors["smartsheet"] = SmartsheetConnector(smartsheet_config)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
            self.logger.warning("smartsheet_connector_failed", extra={"error": str(exc)})
        try:
            ado_config = ConnectorConfig(
                connector_id="azure_devops",
                name="Azure DevOps",
                category=ConnectorCategory.PM,
                instance_url=self._get_setting("AZURE_DEVOPS_ORG_URL", "") or "",
            )
            self.connectors["azure_devops"] = AzureDevOpsConnector(ado_config)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
            self.logger.warning("azure_devops_connector_failed", extra={"error": str(exc)})

    async def _initialize_service_bus(self) -> None:
        if self.config and self.config.get("event_bus"):
            self.event_bus = self.config["event_bus"]
        connection_string = self._get_setting("AZURE_SERVICE_BUS_CONNECTION_STRING")
        if not connection_string:
            return
        self.event_bus = ServiceBusEventBus(
            connection_string=connection_string,
            topic_name=self.service_bus_topic_name,
        )
        if ServiceBusClient is None:
            return
        self.service_bus_client = ServiceBusClient.from_connection_string(connection_string)
        try:
            self.service_bus_queue_sender = self.service_bus_client.get_queue_sender(
                queue_name=self.service_bus_queue_name
            )
            self.service_bus_topic_sender = self.service_bus_client.get_topic_sender(
                topic_name=self.service_bus_topic_name
            )
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
            self.logger.warning("service_bus_sender_unavailable", extra={"error": str(exc)})

    async def _initialize_event_grid(self) -> None:
        endpoint = self._get_setting("EVENT_GRID_ENDPOINT")
        key = self._get_setting("EVENT_GRID_KEY")
        if not endpoint or not key or not EventGridPublisherClient or not AzureKeyCredential:
            return
        self.event_grid_client = EventGridPublisherClient(endpoint, AzureKeyCredential(key))

    async def _initialize_datastores(self) -> None:
        sql_connection_string = self._get_setting("SQL_CONNECTION_STRING")
        if sql_connection_string and create_engine:
            self.sql_engine = create_engine(sql_connection_string)
        cosmos_endpoint = self._get_setting("COSMOS_ENDPOINT")
        cosmos_key = self._get_setting("COSMOS_KEY")
        if cosmos_endpoint and cosmos_key and CosmosClient:
            self.cosmos_client = CosmosClient(cosmos_endpoint, credential=cosmos_key)

    async def _initialize_data_factory(self) -> None:
        if not DataFactoryManagementClient or not DefaultAzureCredential:
            return
        subscription_id = self._get_setting("AZURE_SUBSCRIPTION_ID")
        if not subscription_id:
            return
        credential = DefaultAzureCredential()
        self.data_factory_client = DataFactoryManagementClient(credential, subscription_id)
        resource_group = self.data_factory_resource_group
        factory_name = self.data_factory_name
        if resource_group and factory_name and self.data_factory_pipelines:
            for pipeline_name in self.data_factory_pipelines:
                try:  # pragma: no cover - network dependent
                    self.data_factory_client.pipelines.get(
                        resource_group_name=resource_group,
                        factory_name=factory_name,
                        pipeline_name=pipeline_name,
                    )
                except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
                    self.logger.warning(
                        "data_factory_pipeline_unavailable",
                        extra={"pipeline": pipeline_name, "error": str(exc)},
                    )

    async def _initialize_functions(self) -> None:
        if not azure_functions:
            return
        self.function_app = azure_functions.FunctionApp()
        if not self.function_names:
            return
        if not self.function_base_url:
            self.logger.info(
                "function_base_url_missing",
                extra={"configured_functions": self.function_names},
            )

    async def _initialize_monitoring(self) -> None:
        endpoint = self._get_setting("LOG_ANALYTICS_ENDPOINT")
        if not endpoint or not LogsIngestionClient or not DefaultAzureCredential:
            return
        credential = DefaultAzureCredential()
        self.log_analytics_client = LogsIngestionClient(endpoint=endpoint, credential=credential)

    async def _publish_event(self, topic: str, payload: dict[str, Any]) -> None:
        if self.event_bus:
            await self.event_bus.publish(topic, payload)
        await self._publish_service_bus_message(topic, payload)
        await self._publish_event_grid_event(topic, payload)

    async def _publish_service_bus_message(self, topic: str, payload: dict[str, Any]) -> None:
        if not self.service_bus_client or not ServiceBusMessage:
            return
        message = ServiceBusMessage(
            json.dumps(
                {"topic": topic, "payload": payload, "published_at": datetime.now(timezone.utc).isoformat()},
                default=str,
            )
        )
        if self.service_bus_topic_sender:
            try:  # pragma: no cover - network dependent
                async with self.service_bus_topic_sender:
                    await self.service_bus_topic_sender.send_messages(message)
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
                self.logger.warning("service_bus_topic_publish_failed", extra={"error": str(exc)})
        if self.service_bus_queue_sender:
            try:  # pragma: no cover - network dependent
                async with self.service_bus_queue_sender:
                    await self.service_bus_queue_sender.send_messages(message)
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
                self.logger.warning("service_bus_queue_publish_failed", extra={"error": str(exc)})

    async def _publish_event_grid_event(self, topic: str, payload: dict[str, Any]) -> None:
        if not self.event_grid_client:
            return
        event = {
            "id": str(uuid.uuid4()),
            "subject": f"data-sync/{topic}",
            "eventType": topic,
            "eventTime": datetime.now(timezone.utc).isoformat() + "Z",
            "dataVersion": "1.0",
            "data": payload,
        }
        try:  # pragma: no cover - network dependent
            await self.event_grid_client.send([event])
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
            self.logger.warning("event_grid_publish_failed", extra={"error": str(exc)})

    def _is_duplicate_record(self, tenant_id: str, entity_type: str, data: dict[str, Any]) -> bool:
        normalized_payload = json.dumps(
            {"entity_type": entity_type, "data": data},
            sort_keys=True,
            default=str,
        )
        record_hash = hashlib.sha256(normalized_payload.encode("utf-8")).hexdigest()
        seen_hashes = self.seen_record_hashes.setdefault(tenant_id, set())
        if record_hash in seen_hashes:
            return True
        seen_hashes.add(record_hash)
        return False

    async def _record_sync_metrics(
        self,
        tenant_id: str,
        entity_type: str,
        source_system: str,
        latency_seconds: float,
        started_at: datetime,
        finished_at: datetime,
    ) -> None:
        record = {
            "tenant_id": tenant_id,
            "entity_type": entity_type,
            "source_system": source_system,
            "latency_seconds": latency_seconds,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
        }
        self.latency_records.append(record)
        await self._ingest_latency_metric(record)

    async def _run_etl_workflows(
        self,
        tenant_id: str,
        entity_type: str,
        payload: dict[str, Any],
        source_system: str,
    ) -> None:
        await self._trigger_data_factory_pipelines(
            tenant_id=tenant_id,
            entity_type=entity_type,
            payload=payload,
            source_system=source_system,
        )
        await self._invoke_transformation_functions(
            tenant_id=tenant_id,
            entity_type=entity_type,
            payload=payload,
            source_system=source_system,
        )

    async def _trigger_data_factory_pipelines(
        self,
        tenant_id: str,
        entity_type: str,
        payload: dict[str, Any],
        source_system: str,
    ) -> None:
        if not self.data_factory_client:
            return
        if not self.data_factory_resource_group or not self.data_factory_name:
            return
        for pipeline_name in self.data_factory_pipelines:
            try:  # pragma: no cover - network dependent
                self.data_factory_client.pipelines.create_run(
                    resource_group_name=self.data_factory_resource_group,
                    factory_name=self.data_factory_name,
                    pipeline_name=pipeline_name,
                    parameters={
                        "tenant_id": tenant_id,
                        "entity_type": entity_type,
                        "source_system": source_system,
                        "payload": payload,
                    },
                )
            except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
                self.logger.warning(
                    "data_factory_pipeline_trigger_failed",
                    extra={"pipeline": pipeline_name, "error": str(exc)},
                )

    async def _invoke_transformation_functions(
        self,
        tenant_id: str,
        entity_type: str,
        payload: dict[str, Any],
        source_system: str,
    ) -> None:
        if not self.function_names or not self.function_base_url:
            return
        headers = {"Content-Type": "application/json"}
        if self.function_key:
            headers["x-functions-key"] = self.function_key
        for function_name in self.function_names:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        f"{self.function_base_url.rstrip('/')}/api/{function_name}",
                        json={
                            "tenant_id": tenant_id,
                            "entity_type": entity_type,
                            "source_system": source_system,
                            "payload": payload,
                        },
                        headers=headers,
                    )
            except httpx.RequestError:
                self.logger.warning(
                    "function_invocation_failed",
                    extra={"function": function_name},
                )

    async def _ingest_latency_metric(self, record: dict[str, Any]) -> None:
        if not self.log_analytics_client:
            return
        rule_id = self._get_setting("LOG_ANALYTICS_RULE_ID")
        stream_name = self._get_setting("LOG_ANALYTICS_STREAM_NAME", "DataSyncLatency") or "DataSyncLatency"
        if not rule_id:
            return
        try:
            await self.log_analytics_client.upload(
                rule_id=rule_id,
                stream_name=stream_name,
                logs=[record],
            )
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
            self.logger.warning("log_analytics_upload_failed", extra={"error": str(exc)})

    async def _ingest_quality_metric(self, record: dict[str, Any]) -> None:
        if not self.log_analytics_client:
            return
        rule_id = self._get_setting("LOG_ANALYTICS_RULE_ID")
        stream_name = self._get_setting("LOG_ANALYTICS_QUALITY_STREAM_NAME", "DataQualityMetrics") or "DataQualityMetrics"
        if not rule_id:
            return
        try:
            await self.log_analytics_client.upload(
                rule_id=rule_id,
                stream_name=stream_name,
                logs=[record],
            )
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:  # pragma: no cover - network dependent
            self.logger.warning("log_analytics_quality_upload_failed", extra={"error": str(exc)})

    async def _generate_master_id(self, entity_type: str) -> str:
        """Generate unique master ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"MASTER-{entity_type.upper()}-{timestamp}"

    async def _generate_mapping_id(self) -> str:
        """Generate unique mapping ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"MAP-{timestamp}"

    async def _transform_data(
        self, entity_type: str, data: dict[str, Any], source_system: str
    ) -> dict[str, Any]:
        """Transform data using mapping rules."""
        applicable_rules = self._get_transformation_rules(entity_type, source_system)
        if not applicable_rules:
            return data

        transformed = data.copy()
        for rule in applicable_rules:
            if not self._validate_transformation_rule(rule):
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
            transformed = self._apply_transformations(transformed, transformations)

        return transformed

    async def _find_existing_master(
        self, entity_type: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Find existing master record."""
        for master_id, record in self.master_records.items():
            if record.get("entity_type") == entity_type and record.get("data", {}).get(
                "id"
            ) == data.get("id"):
                return record  # type: ignore
        return None

    async def _record_sync_event(
        self,
        tenant_id: str,
        entity_type: str,
        master_id: str,
        source_system: str,
        status: str,
    ) -> str:
        """Record sync event."""
        event_id = f"EVENT-{len(self.sync_events) + 1}"
        event_record = {
            "event_id": event_id,
            "entity_type": entity_type,
            "master_id": master_id,
            "source_system": source_system,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.sync_events[event_id] = event_record
        self.sync_event_store.upsert(tenant_id, event_id, event_record)
        await self._store_record("sync_events", event_id, event_record)
        return event_id

    async def _record_sync_lineage(
        self,
        tenant_id: str,
        entity_type: str,
        master_id: str,
        source_system: str,
        payload: dict[str, Any],
    ) -> None:
        """Record sync lineage with masking."""
        lineage_id = f"LINEAGE-{len(self.sync_events) + 1}"
        lineage_record = {
            "lineage_id": lineage_id,
            "entity_type": entity_type,
            "master_id": master_id,
            "source_system": source_system,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        masked_lineage = mask_lineage_payload(lineage_record)
        self.sync_lineage_store.upsert(tenant_id, lineage_id, masked_lineage)
        await self._emit_lineage_event(tenant_id, entity_type, master_id, source_system, payload)

    async def _emit_audit_event(
        self,
        tenant_id: str,
        action: str,
        resource_id: str,
        resource_type: str,
        metadata: dict[str, Any],
    ) -> None:
        audit_event = build_audit_event(
            tenant_id=tenant_id,
            action=action,
            outcome="success",
            actor_id=self.agent_id,
            actor_type="service",
            actor_roles=[],
            resource_id=resource_id,
            resource_type=resource_type,
            metadata=metadata,
            trace_id=get_trace_id(),
        )
        self.audit_records[audit_event["id"]] = audit_event
        self.sync_audit_store.upsert(tenant_id, audit_event["id"], audit_event)
        emit_audit_event(audit_event)

    async def _emit_lineage_event(
        self,
        tenant_id: str,
        entity_type: str,
        master_id: str,
        source_system: str,
        payload: dict[str, Any],
    ) -> None:
        base_url = self._get_setting("DATA_LINEAGE_SERVICE_URL")
        if not base_url:
            return
        token = self._get_setting("DATA_LINEAGE_SERVICE_TOKEN")
        headers = {"X-Tenant-ID": tenant_id}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        lineage_payload = {
            "tenant_id": tenant_id,
            "connector": "data-sync-agent",
            "source": {
                "system": source_system,
                "object": entity_type,
                "record_id": payload.get("id"),
            },
            "target": {
                "schema": entity_type,
                "record_id": master_id,
            },
            "transformations": [f"{source_system}.{entity_type} -> {entity_type}"],
            "entity_type": entity_type,
            "entity_payload": payload,
            "classification": "internal",
        }
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
                await client.post("/lineage/events", json=lineage_payload, headers=headers)
        except httpx.RequestError:
            self.logger.warning("lineage_service_unavailable", extra={"base_url": base_url})

    async def _detect_update_conflicts(
        self, master_record: dict[str, Any], new_data: dict[str, Any], source_system: str
    ) -> list[dict[str, Any]]:
        """Detect conflicts in update."""
        conflicts = []

        current_data = master_record.get("data", {})
        for key, new_value in new_data.items():
            current_value = current_data.get(key)
            if current_value and current_value != new_value:
                conflicts.append(
                    {
                        "field": key,
                        "current_value": current_value,
                        "new_value": new_value,
                        "source_system": source_system,
                    }
                )

        return conflicts

    async def _record_conflicts(self, master_id: str, conflicts: list[dict[str, Any]]) -> str:
        """Record conflicts."""
        conflict_id = f"CONFLICT-{len(self.conflicts) + 1}"
        self.conflicts[conflict_id] = {
            "conflict_id": conflict_id,
            "master_id": master_id,
            "conflicts": conflicts,
            "status": "pending",
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._publish_event(
            "conflict.detected",
            {
                "conflict_id": conflict_id,
                "master_id": master_id,
                "conflicts": conflicts,
                "detected_at": self.conflicts[conflict_id]["detected_at"],
            },
        )
        return conflict_id

    async def _apply_conflict_resolution(
        self,
        master_record: dict[str, Any],
        new_data: dict[str, Any],
        conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Apply conflict resolution strategy."""
        if self.conflict_resolution_strategy == "last_write_wins":
            return self._resolve_by_timestamp(master_record, new_data, conflicts)
        elif self.conflict_resolution_strategy == "timestamp_based":
            return self._resolve_by_timestamp(master_record, new_data, conflicts)
        elif self.conflict_resolution_strategy == "authoritative_source":
            return self._resolve_by_authority(master_record, new_data, conflicts)
        elif self.conflict_resolution_strategy == "prefer_existing":
            return self._resolve_prefer_existing(master_record, new_data, conflicts)
        elif self.conflict_resolution_strategy == "manual":
            self.logger.info("conflict_manual_review_required", extra={"conflicts": conflicts})
            return master_record.get("data", {}).copy()
        else:
            return new_data

    async def _fuzzy_match_duplicates(self, records: list[tuple]) -> list[list[str]]:
        """Find duplicates using fuzzy matching."""
        return self._find_potential_duplicates(records)

    async def _get_validation_rules(self, entity_type: str) -> list[dict[str, Any]]:
        """Get validation rules for entity type."""
        if entity_type in self.validation_rules:
            return self.validation_rules[entity_type]
        return self.validation_rules.get(
            "default",
            [
                {"field": "id", "required": True, "severity": "error"},
                {"field": "name", "required": True, "severity": "error"},
            ],
        )

    async def _apply_validation_rule(
        self, data: dict[str, Any], rule: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply validation rule."""
        field = rule.get("field")
        required = rule.get("required", False)
        minimum = rule.get("min")
        maximum = rule.get("max")
        reference = rule.get("reference")

        if required and not data.get(field):  # type: ignore
            return {
                "valid": False,
                "severity": rule.get("severity", "error"),
                "message": f"Required field '{field}' is missing",
            }

        if field and field in data and isinstance(data.get(field), (int, float)):
            value = data.get(field)
            if minimum is not None and value < minimum:
                return {
                    "valid": False,
                    "severity": rule.get("severity", "error"),
                    "message": f"Field '{field}' is below minimum {minimum}",
                }
            if maximum is not None and value > maximum:
                return {
                    "valid": False,
                    "severity": rule.get("severity", "error"),
                    "message": f"Field '{field}' exceeds maximum {maximum}",
                }

        if reference and field:
            referenced_id = data.get(field)
            if referenced_id and not self.master_records.get(referenced_id):
                return {
                    "valid": False,
                    "severity": rule.get("severity", "warning"),
                    "message": f"Referential integrity check failed for '{field}'",
                }

        return {"valid": True}

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

    async def _store_record(self, table: str, record_id: str, payload: dict[str, Any]) -> None:
        if not self.db_service:
            return
        await self.db_service.store(table, record_id, payload)

    async def _publish_sync_event(
        self,
        tenant_id: str,
        entity_type: str,
        master_id: str,
        source_system: str,
        payload: dict[str, Any],
    ) -> None:
        self.logger.info(
            "sync_event_published",
            extra={
                "tenant_id": tenant_id,
                "entity_type": entity_type,
                "master_id": master_id,
                "source_system": source_system,
            },
        )
        if not self.sync_event_webhook_url:
            return
        webhook_payload = {
            "tenant_id": tenant_id,
            "entity_type": entity_type,
            "master_id": master_id,
            "source_system": source_system,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            async with httpx.AsyncClient(timeout=self.sync_event_webhook_timeout) as client:
                await client.post(self.sync_event_webhook_url, json=webhook_payload)
        except httpx.RequestError:
            self.logger.warning(
                "sync_event_webhook_unavailable",
                extra={"url": self.sync_event_webhook_url},
            )

    def _get_transformation_rules(self, entity_type: str, source_system: str) -> list[dict[str, Any]]:
        rules = []
        for rule in self.transformation_rules:
            if rule.get("entity_type") != entity_type:
                continue
            if rule.get("source_system") and rule.get("source_system") != source_system:
                continue
            rules.append(rule)
        return rules

    def _validate_transformation_rule(self, rule: dict[str, Any]) -> bool:
        try:
            validate(instance=rule, schema=self.transformation_schema)
        except ValidationError as exc:
            self.logger.warning(
                "invalid_transformation_rule",
                extra={"error": str(exc), "rule": rule},
            )
            return False
        return True

    def _apply_transformations(
        self, payload: dict[str, Any], transformations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        updated = payload.copy()
        for transformation in transformations:
            field = transformation.get("field")
            operation = transformation.get("operation")
            value = transformation.get("value")
            if field is None or operation is None:
                continue
            current = updated.get(field)
            if operation == "uppercase" and isinstance(current, str):
                updated[field] = current.upper()
            elif operation == "lowercase" and isinstance(current, str):
                updated[field] = current.lower()
            elif operation == "strip" and isinstance(current, str):
                updated[field] = current.strip()
            elif operation == "prefix" and isinstance(current, str) and isinstance(value, str):
                updated[field] = f"{value}{current}"
            elif operation == "suffix" and isinstance(current, str) and isinstance(value, str):
                updated[field] = f"{current}{value}"
            elif operation == "concat" and isinstance(value, list):
                parts = [str(updated.get(part, "")) for part in value]
                updated[field] = "".join(parts)
            elif operation == "cast_int":
                try:
                    updated[field] = int(current)
                except (TypeError, ValueError):
                    continue
            elif operation == "cast_float":
                try:
                    updated[field] = float(current)
                except (TypeError, ValueError):
                    continue
        return updated

    def _resolve_by_timestamp(
        self,
        master_record: dict[str, Any],
        new_data: dict[str, Any],
        conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        resolved = new_data.copy()
        new_timestamp = self._extract_timestamp(new_data) or self._extract_timestamp(
            master_record
        )
        current_timestamp = self._extract_timestamp(master_record)
        if new_timestamp and current_timestamp and new_timestamp < current_timestamp:
            for conflict in conflicts:
                field = conflict.get("field")
                if field in master_record.get("data", {}):
                    resolved[field] = master_record["data"][field]
        return resolved

    def _resolve_by_authority(
        self,
        master_record: dict[str, Any],
        new_data: dict[str, Any],
        conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        resolved = master_record.get("data", {}).copy()
        resolved.update(new_data)
        for conflict in conflicts:
            field = conflict.get("field")
            source_system = conflict.get("source_system")
            authoritative_source = self.authoritative_sources.get(field)
            if authoritative_source and source_system != authoritative_source:
                resolved[field] = master_record.get("data", {}).get(field)
        return resolved

    def _resolve_prefer_existing(
        self,
        master_record: dict[str, Any],
        new_data: dict[str, Any],
        conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        resolved = master_record.get("data", {}).copy()
        for key, value in new_data.items():
            if key not in resolved or resolved[key] in (None, ""):
                resolved[key] = value
        for conflict in conflicts:
            field = conflict.get("field")
            if field in master_record.get("data", {}):
                resolved[field] = master_record["data"][field]
        return resolved

    def _extract_timestamp(self, payload: dict[str, Any]) -> datetime | None:
        for key in ("updated_at", "timestamp", "created_at"):
            raw = payload.get(key)
            if isinstance(raw, str):
                try:
                    return datetime.fromisoformat(raw)
                except ValueError:
                    continue
        return None

    def _compute_quality_dimensions(
        self, entity_type: str, validation_result: dict[str, Any]
    ) -> tuple[float, float, float, float | None]:
        data = validation_result.get("data") or {}
        required_fields = self._get_required_fields(entity_type)
        completeness_score = 1.0
        if required_fields:
            present = sum(
                1
                for field in required_fields
                if data.get(field) not in (None, "", [])
            )
            completeness_score = present / len(required_fields)

        error_count = len(validation_result.get("errors", []))
        if error_count == 0:
            consistency_score = 1.0
        else:
            divisor = max(len(required_fields), 1)
            consistency_score = max(0.0, 1 - (error_count / divisor))

        timestamp = self._extract_timestamp(data) if isinstance(data, dict) else None
        age_seconds = None
        if timestamp:
            age_seconds = max((datetime.now(timezone.utc) - timestamp).total_seconds(), 0.0)
            if self.sync_latency_sla_seconds <= 0:
                timeliness_score = 1.0
            elif age_seconds <= self.sync_latency_sla_seconds:
                timeliness_score = 1.0
            else:
                timeliness_score = max(
                    0.0,
                    1 - (age_seconds / (self.sync_latency_sla_seconds * 2)),
                )
        else:
            timeliness_score = 1.0

        return completeness_score, consistency_score, timeliness_score, age_seconds

    def _get_required_fields(self, entity_type: str) -> list[str]:
        required_fields: list[str] = []
        schema = self.schema_registry.get(entity_type)
        if schema:
            schema_required = schema.get("required")
            if isinstance(schema_required, list):
                required_fields.extend(str(field) for field in schema_required)
        for rule in self.validation_rules.get(entity_type, []):
            if rule.get("required") and rule.get("field"):
                required_fields.append(rule["field"])
        return list(dict.fromkeys(required_fields))

    async def _store_quality_report(self, tenant_id: str, entity_type: str) -> None:
        report = await self._get_quality_report(tenant_id, entity_type)
        report_id = f"{tenant_id}:{entity_type}:{datetime.now(timezone.utc).isoformat()}"
        await self._store_record("data_quality_reports", report_id, report)

    async def _record_sync_log(
        self,
        tenant_id: str,
        entity_type: str,
        source_system: str,
        status: str,
        mode: str,
        started_at: datetime,
        finished_at: datetime | None = None,
        master_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        log_record = {
            "log_id": f"SYNCLOG-{len(self.sync_logs) + 1}",
            "tenant_id": tenant_id,
            "entity_type": entity_type,
            "source_system": source_system,
            "status": status,
            "mode": mode,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat() if finished_at else None,
            "master_id": master_id,
            "details": details or {},
        }
        self.sync_logs.append(log_record)
        await self._store_record("sync_logs", log_record["log_id"], log_record)

    def _find_potential_duplicates(self, records: list[tuple]) -> list[list[str]]:
        duplicates: list[set[str]] = []
        for index, (left_id, left_record) in enumerate(records):
            left_text = self._build_similarity_text(left_record)
            for right_id, right_record in records[index + 1 :]:
                right_text = self._build_similarity_text(right_record)
                similarity = self._calculate_similarity(left_text, right_text)
                if similarity >= self.duplicate_confidence_threshold:
                    self._add_duplicate_pair(duplicates, left_id, right_id)
        return [sorted(group) for group in duplicates]

    def _build_similarity_text(self, record: dict[str, Any]) -> str:
        data = record.get("data", {})
        fields = [
            str(data.get("name", "")),
            str(data.get("title", "")),
            str(data.get("email", "")),
            str(data.get("id", "")),
        ]
        return " ".join(part for part in fields if part).lower().strip()

    def _calculate_similarity(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        fuzz_ratio = fuzz.token_set_ratio(left, right) / 100.0 if fuzz else 0.0
        token_similarity = self._token_similarity(left, right)
        levenshtein_similarity = self._levenshtein_similarity(left, right)
        return max(fuzz_ratio, token_similarity, levenshtein_similarity)

    def _token_similarity(self, left: str, right: str) -> float:
        left_tokens = set(left.split())
        right_tokens = set(right.split())
        if not left_tokens or not right_tokens:
            return 0.0
        intersection = left_tokens.intersection(right_tokens)
        union = left_tokens.union(right_tokens)
        return len(intersection) / len(union)

    def _levenshtein_similarity(self, left: str, right: str) -> float:
        distance = self._levenshtein_distance(left, right)
        max_len = max(len(left), len(right))
        if max_len == 0:
            return 1.0
        return 1 - (distance / max_len)

    def _levenshtein_distance(self, left: str, right: str) -> int:
        if left == right:
            return 0
        if not left:
            return len(right)
        if not right:
            return len(left)
        previous_row = list(range(len(right) + 1))
        for i, left_char in enumerate(left, start=1):
            current_row = [i]
            for j, right_char in enumerate(right, start=1):
                insertions = previous_row[j] + 1
                deletions = current_row[j - 1] + 1
                substitutions = previous_row[j - 1] + (left_char != right_char)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def _add_duplicate_pair(
        self, groups: list[set[str]], left_id: str, right_id: str
    ) -> None:
        left_group = None
        right_group = None
        for group in groups:
            if left_id in group:
                left_group = group
            if right_id in group:
                right_group = group
        if left_group and right_group and left_group is not right_group:
            left_group.update(right_group)
            groups.remove(right_group)
        elif left_group:
            left_group.add(right_id)
        elif right_group:
            right_group.add(left_id)
        else:
            groups.append({left_id, right_id})

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "master_data_management",
            "event_driven_sync",
            "data_mapping",
            "data_transformation",
            "conflict_detection",
            "conflict_resolution",
            "duplicate_detection",
            "duplicate_merging",
            "data_validation",
            "data_quality",
            "sync_monitoring",
            "audit_logging",
            "fuzzy_matching",
        ]
