"""
Action handlers for duplicate detection and merging.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from agents.runtime.src.audit import build_audit_event, emit_audit_event
from observability.tracing import get_trace_id
from sync_utils import find_potential_duplicates

if TYPE_CHECKING:
    from data_sync_agent import DataSyncAgent


async def handle_detect_duplicates(
    agent: DataSyncAgent, entity_type: str
) -> dict[str, Any]:
    """
    Detect duplicate master records.

    Returns duplicate candidates.
    """
    agent.logger.info("Detecting duplicates for entity type: %s", entity_type)

    # Get all master records of this type
    type_records = [
        (master_id, record)
        for master_id, record in agent.master_records.items()
        if record.get("entity_type") == entity_type
    ]

    # Find duplicates using fuzzy matching
    duplicates = find_potential_duplicates(type_records, agent.duplicate_confidence_threshold)

    return {
        "entity_type": entity_type,
        "duplicate_sets": duplicates,
        "duplicate_count": len(duplicates),
    }


async def handle_merge_duplicates(
    agent: DataSyncAgent,
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
        agent.logger.info("Merge decision rejected for %s", primary_id)
        if agent.duplicate_resolution_enabled:
            _emit_merge_decision_audit(
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

    agent.logger.info("Merging %s duplicates into %s", len(master_ids), primary_id)

    if primary_id not in master_ids:
        raise ValueError("Primary ID must be in the list of master IDs")

    primary_record = agent.master_records.get(primary_id)
    if not primary_record:
        raise ValueError(f"Primary record not found: {primary_id}")

    # Merge data from all records
    merged_data = primary_record["data"].copy()

    for master_id in master_ids:
        if master_id == primary_id:
            continue

        duplicate_record = agent.master_records.get(master_id)
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

    await agent._store_record("master_records", primary_id, primary_record)
    for master_id in master_ids:
        duplicate_record = agent.master_records.get(master_id)
        if duplicate_record:
            await agent._store_record("master_records", master_id, duplicate_record)

    if agent.duplicate_resolution_enabled:
        _emit_merge_decision_audit(
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
