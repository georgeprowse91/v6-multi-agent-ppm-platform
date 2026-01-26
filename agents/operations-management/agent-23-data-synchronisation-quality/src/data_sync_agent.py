"""
Agent 23: Data Synchronization & Consistency Agent

Purpose:
Ensures that data flowing through the PPM platform and across integrated systems remains
consistent, up-to-date and accurate through master data management and event-driven synchronization.

Specification: agents/operations-management/agent-23-data-synchronisation-quality/README.md
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from agents.runtime import BaseAgent
from agents.runtime.src.audit import build_audit_event, emit_audit_event
from agents.runtime.src.state_store import TenantStateStore
from observability.tracing import get_trace_id
from security.lineage import mask_lineage_payload


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

    async def initialize(self) -> None:
        """Initialize data sync infrastructure and integrations."""
        await super().initialize()
        self.logger.info("Initializing Data Synchronization & Consistency Agent...")

        # Future work: Initialize Azure Service Bus for event-driven sync
        # Future work: Set up Azure Event Grid for publish/subscribe patterns
        # Future work: Connect to Azure SQL Database or Cosmos DB for master records
        # Future work: Initialize Azure Data Factory for transformation pipelines
        # Future work: Set up Azure Functions for sync orchestration
        # Future work: Connect to external systems (Planview, SAP, Jira, Workday)
        # Future work: Initialize Azure Durable Functions for multi-step transformations
        # Future work: Set up Azure Monitor for sync pipeline monitoring
        # Future work: Connect to all domain agents for data collection
        # Future work: Initialize fuzzy matching algorithms for duplicate detection
        # Future work: Set up Azure Key Vault for external system credentials

        self.logger.info("Data Synchronization & Consistency Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "sync_data",
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

        if action == "sync_data":
            return await self._sync_data(
                tenant_id,
                input_data.get("entity_type"),  # type: ignore
                input_data.get("data"),  # type: ignore
                input_data.get("source_system"),  # type: ignore
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
                input_data.get("master_ids", []), input_data.get("primary_id")  # type: ignore
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

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _sync_data(
        self, tenant_id: str, entity_type: str, data: dict[str, Any], source_system: str
    ) -> dict[str, Any]:
        """
        Synchronize data from source system.

        Returns sync status and master record ID.
        """
        self.logger.info(f"Synchronizing {entity_type} from {source_system}")

        # Validate data
        validation_result = await self._validate_data(entity_type, data)
        if not validation_result.get("valid"):
            return {
                "status": "failed",
                "error": "Data validation failed",
                "validation_errors": validation_result.get("errors"),
            }

        # Transform data using mapping rules
        transformed_data = await self._transform_data(entity_type, data, source_system)

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
            result = await self._create_master_record(tenant_id, entity_type, transformed_data)
            master_id = result.get("master_id")

        # Record sync event
        sync_event_id = await self._record_sync_event(
            tenant_id, entity_type, master_id, source_system, "success"  # type: ignore
        )

        await self._record_sync_lineage(
            tenant_id, entity_type, master_id, source_system, transformed_data
        )

        # Publish sync event
        # Future work: Publish to Event Grid for subscribers

        return {
            "status": "success",
            "master_id": master_id,
            "sync_event_id": sync_event_id,
            "action": "updated" if existing_master else "created",
            "latency_seconds": 0.5,  # Future work: Calculate actual latency
        }

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
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
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

        # Future work: Store in database
        # Future work: Publish master_record.created event

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
        master_record["source_systems"][source_system] = datetime.utcnow().isoformat()
        master_record["version"] += 1
        master_record["updated_at"] = datetime.utcnow().isoformat()
        self.master_record_store.upsert(tenant_id, master_id, master_record.copy())

        await self._emit_audit_event(
            tenant_id,
            action="master_record.updated",
            resource_id=master_id,
            resource_type=master_record.get("entity_type", "unknown"),
            metadata={"version": master_record["version"], "source_system": source_system},
        )

        # Future work: Store in database
        # Future work: Publish master_record.updated event

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
        conflict["resolved_at"] = datetime.utcnow().isoformat()
        conflict["status"] = "resolved"

        # Update master record
        master_id = conflict.get("master_id")
        if master_id and master_id in self.master_records:
            field = conflict.get("field")
            self.master_records[master_id]["data"][field] = resolved_value

        # Future work: Store in database
        # Future work: Publish conflict.resolved event

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

    async def _merge_duplicates(self, master_ids: list[str], primary_id: str) -> dict[str, Any]:
        """
        Merge duplicate records.

        Returns merge result.
        """
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
                duplicate_record["merged_at"] = datetime.utcnow().isoformat()

        # Update primary record
        primary_record["data"] = merged_data
        primary_record["version"] += 1
        primary_record["updated_at"] = datetime.utcnow().isoformat()

        # Future work: Store in database
        # Future work: Publish duplicates.merged event

        return {
            "primary_id": primary_id,
            "merged_count": len(master_ids) - 1,
            "merged_ids": [mid for mid in master_ids if mid != primary_id],
        }

    async def _validate_data(self, entity_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate data quality.

        Returns validation results.
        """
        self.logger.info(f"Validating {entity_type} data")

        errors = []
        warnings = []

        # Get validation rules for entity type
        # Future work: Load from configuration
        validation_rules = await self._get_validation_rules(entity_type)

        # Apply validation rules
        for rule in validation_rules:
            result = await self._apply_validation_rule(data, rule)
            if not result.get("valid"):
                if result.get("severity") == "error":
                    errors.append(result.get("message"))
                else:
                    warnings.append(result.get("message"))

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validated_at": datetime.utcnow().isoformat(),
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
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store mapping rule
        self.mapping_rules[mapping_id] = mapping_rule

        # Future work: Store in database

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

        return {
            "total_sync_events": total_events,
            "successful_syncs": successful_syncs,
            "failed_syncs": failed_syncs,
            "success_rate": (successful_syncs / total_events * 100) if total_events > 0 else 0,
            "pending_conflicts": pending_conflicts,
            "recent_events": recent_events,
            "avg_latency_seconds": 0.8,  # Future work: Calculate actual average
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

    async def _generate_master_id(self, entity_type: str) -> str:
        """Generate unique master ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"MASTER-{entity_type.upper()}-{timestamp}"

    async def _generate_mapping_id(self) -> str:
        """Generate unique mapping ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"MAP-{timestamp}"

    async def _transform_data(
        self, entity_type: str, data: dict[str, Any], source_system: str
    ) -> dict[str, Any]:
        """Transform data using mapping rules."""
        # Future work: Apply actual transformation rules
        return data

    async def _find_existing_master(
        self, entity_type: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Find existing master record."""
        # Future work: Use matching algorithm
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
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.sync_events[event_id] = event_record
        self.sync_event_store.upsert(tenant_id, event_id, event_record)
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
            "timestamp": datetime.utcnow().isoformat(),
        }
        masked_lineage = mask_lineage_payload(lineage_record)
        self.sync_lineage_store.upsert(tenant_id, lineage_id, masked_lineage)

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
            "detected_at": datetime.utcnow().isoformat(),
        }
        return conflict_id

    async def _apply_conflict_resolution(
        self,
        master_record: dict[str, Any],
        new_data: dict[str, Any],
        conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Apply conflict resolution strategy."""
        if self.conflict_resolution_strategy == "last_write_wins":
            return new_data
        elif self.conflict_resolution_strategy == "authoritative_source":
            # Future work: Implement authoritative source logic
            return new_data
        else:
            return new_data

    async def _fuzzy_match_duplicates(self, records: list[tuple]) -> list[list[str]]:
        """Find duplicates using fuzzy matching."""
        # Future work: Implement actual fuzzy matching
        duplicates: list[dict[str, Any]] = []
        return duplicates  # type: ignore

    async def _get_validation_rules(self, entity_type: str) -> list[dict[str, Any]]:
        """Get validation rules for entity type."""
        # Future work: Load from configuration
        return [
            {"field": "id", "required": True, "severity": "error"},
            {"field": "name", "required": True, "severity": "error"},
        ]

    async def _apply_validation_rule(
        self, data: dict[str, Any], rule: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply validation rule."""
        field = rule.get("field")
        required = rule.get("required", False)

        if required and not data.get(field):  # type: ignore
            return {
                "valid": False,
                "severity": rule.get("severity", "error"),
                "message": f"Required field '{field}' is missing",
            }

        return {"valid": True}

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Data Synchronization & Consistency Agent...")
        # Future work: Close database connections
        # Future work: Close event bus connections
        # Future work: Flush pending sync events

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
