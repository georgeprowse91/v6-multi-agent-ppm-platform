"""
Action handlers for conflict detection and resolution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sync_utils import resolve_by_authority, resolve_by_timestamp, resolve_prefer_existing

if TYPE_CHECKING:
    from data_sync_agent import DataSyncAgent


async def handle_detect_conflicts(agent: DataSyncAgent, master_id: str) -> dict[str, Any]:
    """
    Detect data conflicts for master record.

    Returns detected conflicts.
    """
    agent.logger.info("Detecting conflicts for master record: %s", master_id)

    # Get conflicts for this master record
    record_conflicts = [
        conflict
        for conflict_id, conflict in agent.conflicts.items()
        if conflict.get("master_id") == master_id and conflict.get("status") == "pending"
    ]

    return {
        "master_id": master_id,
        "conflicts": record_conflicts,
        "conflict_count": len(record_conflicts),
    }


async def handle_resolve_conflict(
    agent: DataSyncAgent, conflict_id: str, resolution: dict[str, Any]
) -> dict[str, Any]:
    """
    Resolve data conflict.

    Returns resolution result.
    """
    agent.logger.info("Resolving conflict: %s", conflict_id)

    conflict = agent.conflicts.get(conflict_id)
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
    if master_id and master_id in agent.master_records:
        field = conflict.get("field")
        agent.master_records[master_id]["data"][field] = resolved_value

    await agent._store_record("conflicts", conflict_id, conflict)
    await agent._publish_event(
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


async def detect_update_conflicts(
    agent: DataSyncAgent,
    master_record: dict[str, Any],
    new_data: dict[str, Any],
    source_system: str,
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


async def record_conflicts(
    agent: DataSyncAgent, master_id: str, conflicts: list[dict[str, Any]]
) -> str:
    """Record conflicts."""
    conflict_id = f"CONFLICT-{len(agent.conflicts) + 1}"
    agent.conflicts[conflict_id] = {
        "conflict_id": conflict_id,
        "master_id": master_id,
        "conflicts": conflicts,
        "status": "pending",
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }
    await agent._publish_event(
        "conflict.detected",
        {
            "conflict_id": conflict_id,
            "master_id": master_id,
            "conflicts": conflicts,
            "detected_at": agent.conflicts[conflict_id]["detected_at"],
        },
    )
    return conflict_id


async def apply_conflict_resolution(
    agent: DataSyncAgent,
    master_record: dict[str, Any],
    new_data: dict[str, Any],
    conflicts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply conflict resolution strategy."""
    if agent.conflict_resolution_strategy == "last_write_wins":
        return resolve_by_timestamp(master_record, new_data, conflicts)
    elif agent.conflict_resolution_strategy == "timestamp_based":
        return resolve_by_timestamp(master_record, new_data, conflicts)
    elif agent.conflict_resolution_strategy == "authoritative_source":
        return resolve_by_authority(master_record, new_data, conflicts, agent.authoritative_sources)
    elif agent.conflict_resolution_strategy == "prefer_existing":
        return resolve_prefer_existing(master_record, new_data, conflicts)
    elif agent.conflict_resolution_strategy == "manual":
        agent.logger.info("conflict_manual_review_required", extra={"conflicts": conflicts})
        return master_record.get("data", {}).copy()
    else:
        return new_data
