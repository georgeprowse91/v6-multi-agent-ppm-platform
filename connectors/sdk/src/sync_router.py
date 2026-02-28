from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from connectors.sdk.src.runtime import ConnectorRuntime


class InboundSyncRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    live: bool = Field(default=False, description="Run against live API using env credentials")
    records: list[dict[str, Any]] | None = Field(
        default=None, description="Optional raw source records to map"
    )
    include_schema: bool = Field(default=False, description="Include schema metadata in response")


class OutboundSyncRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    live: bool = Field(default=False, description="Run outbound sync against live API")
    records: list[dict[str, Any]] = Field(..., description="Canonical records to sync outbound")
    include_schema: bool = Field(default=False, description="Include schema metadata in response")


def normalize_records(
    records: list[dict[str, Any]],
    source: str,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for record in records:
        if "source" in record:
            normalized.append(record)
        else:
            normalized.append({"source": source, **record})
    return normalized


def map_records(
    connector_root: Path,
    records: list[dict[str, Any]],
    tenant_id: str,
    *,
    include_schema: bool = False,
    default_source: str = "project",
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(connector_root)
    normalized = normalize_records(records, default_source)
    return runtime.apply_mappings(normalized, tenant_id, include_schema=include_schema)
