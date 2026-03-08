"""
Action handlers for schema registry operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from data_sync_agent import DataSyncAgent


async def handle_get_schema(agent: DataSyncAgent, entity_type: str | None) -> dict[str, Any]:
    if not entity_type:
        return {"schemas": agent.schema_registry}
    schema = agent.schema_registry.get(entity_type)
    if not schema:
        raise ValueError(f"Schema not found for {entity_type}")
    return {"entity_type": entity_type, "schema": schema}


async def handle_register_schema(
    agent: DataSyncAgent,
    tenant_id: str,
    entity_type: str | None,
    schema: dict[str, Any],
    version: str | None = None,
) -> dict[str, Any]:
    if not entity_type:
        raise ValueError("entity_type is required for schema registration")
    version = version or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    agent.schema_registry[entity_type] = schema
    agent.schema_versions.setdefault(entity_type, []).append({"version": version, "schema": schema})
    agent.schema_registry_store.upsert(
        tenant_id,
        f"{entity_type}:{version}",
        {"entity_type": entity_type, "version": version, "schema": schema},
    )
    await agent._store_record("schema_registry", f"{entity_type}:{version}", schema)
    return {"entity_type": entity_type, "version": version}
