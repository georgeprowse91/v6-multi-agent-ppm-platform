"""
Action handlers for master record CRUD operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from data_sync_agent import DataSyncAgent


async def handle_create_master_record(
    agent: DataSyncAgent, tenant_id: str, entity_type: str, data: dict[str, Any]
) -> dict[str, Any]:
    """
    Create new master record.

    Returns master record ID.
    """
    agent.logger.info("Creating master record for %s", entity_type)

    # Generate master ID
    master_id = await agent._generate_master_id(entity_type)

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
    agent.master_records[master_id] = master_record
    agent.master_record_store.upsert(tenant_id, master_id, master_record.copy())

    await agent._emit_audit_event(
        tenant_id,
        action="master_record.created",
        resource_id=master_id,
        resource_type=entity_type,
        metadata={"version": 1},
    )

    await agent._store_record("master_records", master_id, master_record)

    return {"master_id": master_id, "entity_type": entity_type, "version": 1}


async def handle_update_master_record(
    agent: DataSyncAgent,
    tenant_id: str,
    master_id: str,
    data: dict[str, Any],
    source_system: str,
) -> dict[str, Any]:
    """
    Update existing master record.

    Returns update confirmation.
    """
    agent.logger.info("Updating master record: %s", master_id)

    master_record = agent.master_records.get(master_id)
    if not master_record:
        raise ValueError(f"Master record not found: {master_id}")

    # Detect conflicts
    conflicts = await agent._detect_update_conflicts(master_record, data, source_system)

    if conflicts:
        # Record conflicts
        await agent._record_conflicts(master_id, conflicts)

        # Apply conflict resolution strategy
        resolved_data = await agent._apply_conflict_resolution(master_record, data, conflicts)
    else:
        resolved_data = data

    # Update master record
    master_record["data"].update(resolved_data)
    master_record["source_systems"][source_system] = datetime.now(timezone.utc).isoformat()
    master_record["version"] += 1
    master_record["updated_at"] = datetime.now(timezone.utc).isoformat()
    agent.master_record_store.upsert(tenant_id, master_id, master_record.copy())

    await agent._emit_audit_event(
        tenant_id,
        action="master_record.updated",
        resource_id=master_id,
        resource_type=master_record.get("entity_type", "unknown"),
        metadata={"version": master_record["version"], "source_system": source_system},
    )

    await agent._store_record("master_records", master_id, master_record)

    return {
        "master_id": master_id,
        "version": master_record["version"],
        "conflicts_detected": len(conflicts) if conflicts else 0,
        "updated_at": master_record["updated_at"],
    }


async def handle_get_master_record(
    agent: DataSyncAgent, tenant_id: str, master_id: str
) -> dict[str, Any]:
    """
    Get master record with lineage.

    Returns master record data.
    """
    agent.logger.info("Retrieving master record: %s", master_id)

    master_record = agent.master_records.get(master_id)
    if not master_record:
        master_record = agent.master_record_store.get(tenant_id, master_id)
        if master_record:
            agent.master_records[master_id] = master_record
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
