"""
Action handlers for retry queue operations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from data_sync_agent import DataSyncAgent


async def enqueue_retry(
    agent: DataSyncAgent,
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
    agent.retry_queue_store.upsert(tenant_id, retry_id, retry_payload)
    await agent._store_record("sync_retry_queue", retry_id, retry_payload)


async def handle_process_retry_queue(agent: DataSyncAgent, tenant_id: str) -> dict[str, Any]:
    retries = agent.retry_queue_store.list(tenant_id)
    processed = 0
    successes = 0
    failures = 0
    for payload in retries:
        retry_id = payload.get("retry_id")
        if not retry_id:
            continue
        attempts = payload.get("attempts", 0)
        if attempts >= agent.max_retry_attempts:
            continue
        try:
            await agent._sync_data(
                tenant_id,
                payload.get("entity_type"),
                payload.get("data"),
                payload.get("source_system"),
            )
            successes += 1
            agent.retry_queue_store.delete(tenant_id, retry_id)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
            payload["attempts"] = attempts + 1
            payload["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
            agent.retry_queue_store.upsert(tenant_id, retry_id, payload)
            failures += 1
        processed += 1
    return {
        "processed": processed,
        "successes": successes,
        "failures": failures,
        "remaining": len(agent.retry_queue_store.list(tenant_id)),
    }


async def handle_reprocess_retry(
    agent: DataSyncAgent, tenant_id: str, retry_id: str | None
) -> dict[str, Any]:
    if not retry_id:
        raise ValueError("retry_id is required")
    payload = agent.retry_queue_store.get(tenant_id, retry_id)
    if not payload:
        raise ValueError(f"Retry item not found: {retry_id}")
    try:
        await agent._sync_data(
            tenant_id,
            payload.get("entity_type"),
            payload.get("data"),
            payload.get("source_system"),
        )
        agent.retry_queue_store.delete(tenant_id, retry_id)
        return {"retry_id": retry_id, "status": "success"}
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        payload["attempts"] = payload.get("attempts", 0) + 1
        payload["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
        payload["last_error"] = str(exc)
        agent.retry_queue_store.upsert(tenant_id, retry_id, payload)
        return {"retry_id": retry_id, "status": "failed", "error": str(exc)}


async def handle_get_retry_queue(agent: DataSyncAgent, tenant_id: str) -> dict[str, Any]:
    retries = agent.retry_queue_store.list(tenant_id)
    return {
        "tenant_id": tenant_id,
        "retry_count": len(retries),
        "retries": retries,
    }
