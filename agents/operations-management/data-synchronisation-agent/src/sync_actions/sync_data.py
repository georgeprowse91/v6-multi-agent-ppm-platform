"""
Action handlers for sync_data and run_sync operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sync_utils import is_duplicate_record

if TYPE_CHECKING:
    from data_sync_agent import DataSyncAgent


async def handle_sync_data(
    agent: DataSyncAgent,
    tenant_id: str,
    entity_type: str,
    data: dict[str, Any],
    source_system: str,
) -> dict[str, Any]:
    """
    Synchronize data from source system.

    Returns sync status and master record ID.
    """
    sync_started_at = datetime.now(timezone.utc)
    agent.logger.info("Synchronizing %s from %s", entity_type, source_system)
    await agent._record_sync_log(
        tenant_id=tenant_id,
        entity_type=entity_type,
        source_system=source_system,
        status="started",
        mode="single",
        started_at=sync_started_at,
    )
    await agent._publish_event(
        "sync.start",
        {
            "tenant_id": tenant_id,
            "entity_type": entity_type,
            "source_system": source_system,
            "started_at": sync_started_at.isoformat(),
        },
    )

    if is_duplicate_record(agent.seen_record_hashes, tenant_id, entity_type, data):
        await agent._record_sync_log(
            tenant_id=tenant_id,
            entity_type=entity_type,
            source_system=source_system,
            status="duplicate",
            mode="single",
            started_at=sync_started_at,
            finished_at=datetime.now(timezone.utc),
            details={"reason": "Duplicate record discarded"},
        )
        await agent._publish_event(
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

    mapped_data = await agent._map_to_canonical(entity_type, data, source_system)
    # Validate data
    validation_result = await agent._validate_data(entity_type, mapped_data)
    await agent._record_quality_metrics(
        tenant_id=tenant_id,
        entity_type=entity_type,
        source_system=source_system,
        validation_result=validation_result,
    )
    if not validation_result.get("valid"):
        await agent._record_sync_log(
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
        await agent._enqueue_retry(
            tenant_id,
            entity_type,
            mapped_data,
            source_system,
            reason="validation_failed",
        )
        await agent._publish_event(
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
        transformed_data = await agent._transform_data(entity_type, mapped_data, source_system)
        await agent._run_etl_workflows(tenant_id, entity_type, transformed_data, source_system)

        # Check for existing master record
        existing_master = await agent._find_existing_master(entity_type, transformed_data)

        if existing_master:
            # Update existing record
            result = await agent._update_master_record(
                tenant_id,
                existing_master.get("master_id"),  # type: ignore
                transformed_data,
                source_system,
            )
            master_id = existing_master.get("master_id")
        else:
            # Create new master record
            result = await agent._create_master_record(tenant_id, entity_type, transformed_data)
            master_id = result.get("master_id")

        # Record sync event
        sync_event_id = await agent._record_sync_event(
            tenant_id, entity_type, master_id, source_system, "success"  # type: ignore
        )

        await agent._record_sync_lineage(
            tenant_id, entity_type, master_id, source_system, transformed_data
        )

        # Publish sync event
        await agent._publish_sync_event(
            tenant_id, entity_type, master_id, source_system, transformed_data
        )

        sync_finished_at = datetime.now(timezone.utc)
        latency_seconds = (sync_finished_at - sync_started_at).total_seconds()
        await agent._record_sync_metrics(
            tenant_id,
            entity_type,
            source_system,
            latency_seconds,
            sync_started_at,
            sync_finished_at,
        )
        await agent._record_sync_log(
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
        await agent._publish_event(
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
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        await agent._enqueue_retry(
            tenant_id,
            entity_type,
            mapped_data,
            source_system,
            reason=str(exc),
        )
        await agent._record_sync_log(
            tenant_id=tenant_id,
            entity_type=entity_type,
            source_system=source_system,
            status="failed",
            mode="single",
            started_at=sync_started_at,
            finished_at=datetime.now(timezone.utc),
            details={"error": str(exc)},
        )
        await agent._publish_event(
            "data_sync.failure",
            {
                "tenant_id": tenant_id,
                "entity_type": entity_type,
                "source_system": source_system,
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        await agent._publish_event(
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


async def handle_run_sync(
    agent: DataSyncAgent,
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
    sync_state = agent.sync_state_store.get(tenant_id, state_key) or {}
    last_synced_at = sync_state.get("last_synced_at")
    cursor = sync_state.get("cursor")

    if sync_mode not in {"incremental", "full"}:
        raise ValueError(f"Unsupported sync mode: {mode}")

    await agent._publish_event(
        "sync.batch.start",
        {
            "tenant_id": tenant_id,
            "entity_type": entity_type,
            "source_system": source_system,
            "mode": sync_mode,
            "started_at": sync_started_at.isoformat(),
        },
    )
    await agent._record_sync_log(
        tenant_id=tenant_id,
        entity_type=entity_type,
        source_system=source_system,
        status="started",
        mode=sync_mode,
        started_at=sync_started_at,
        details={"filters": filters},
    )

    if sync_mode == "incremental":
        records, new_cursor = await _fetch_incremental_records(
            agent, source_system, entity_type, last_synced_at, cursor, filters
        )
    else:
        records, new_cursor = await _fetch_full_records(
            agent, source_system, entity_type, filters
        )

    results = []
    for record in records:
        try:
            result = await agent._sync_data(tenant_id, entity_type, record, source_system)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
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
    agent.sync_state_store.upsert(tenant_id, state_key, new_state)
    await agent._store_record("sync_state", state_key, new_state)

    await agent._publish_event(
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
    await agent._record_sync_log(
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
    agent._record_connector_sync_metrics(
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


async def _fetch_incremental_records(
    agent: DataSyncAgent,
    source_system: str,
    entity_type: str,
    last_synced_at: str | None,
    cursor: str | None,
    filters: dict[str, Any],
) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch records using change data capture or timestamp-based queries."""
    connector = agent.connectors.get(source_system)
    if connector is None:
        return [], None

    if hasattr(connector, "read_changes"):
        try:
            records = connector.read_changes(entity_type, cursor=cursor, filters=filters)
            new_cursor = getattr(connector, "last_cursor", None)
            return records, new_cursor
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            agent.logger.warning("cdc_fetch_failed", extra={"error": str(exc)})

    query_filters = dict(filters)
    if last_synced_at:
        query_filters.setdefault("updated_since", last_synced_at)
        query_filters.setdefault("since", last_synced_at)
    records = _fetch_connector_records(agent, connector, entity_type, query_filters)
    return records, None


async def _fetch_full_records(
    agent: DataSyncAgent,
    source_system: str,
    entity_type: str,
    filters: dict[str, Any],
) -> tuple[list[dict[str, Any]], str | None]:
    connector = agent.connectors.get(source_system)
    if connector is None:
        return [], None
    records = _fetch_connector_records(agent, connector, entity_type, filters)
    return records, None


def _fetch_connector_records(
    agent: DataSyncAgent, connector: Any, entity_type: str, filters: dict[str, Any]
) -> list[dict[str, Any]]:
    if hasattr(connector, "read"):
        try:
            return connector.read(entity_type, filters=filters)
        except TypeError:
            return connector.read(entity_type)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            agent.logger.warning(
                "connector_read_failed",
                extra={"entity_type": entity_type, "error": str(exc)},
            )
    return []
