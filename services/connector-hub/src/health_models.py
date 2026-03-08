"""Models for connector health monitoring."""

from __future__ import annotations

from pydantic import BaseModel


class ConnectorHealthRecord(BaseModel):
    connector_id: str
    name: str
    category: str
    status: str  # healthy, degraded, down
    circuit_state: str  # closed, half_open, open
    last_sync: str | None = None
    error_rate_1h: float = 0.0
    sync_direction: str = "bidirectional"  # inbound, outbound, bidirectional


class DataFreshnessRecord(BaseModel):
    connector_id: str
    connector_name: str
    entity_type: str
    last_synced_at: str | None = None
    record_count: int = 0
    freshness_status: str = "fresh"  # fresh, stale, critical


class ConflictRecord(BaseModel):
    conflict_id: str
    connector_id: str
    connector_name: str
    entity_type: str
    entity_id: str
    source_value: str
    canonical_value: str
    detected_at: str
    status: str = "unresolved"  # unresolved, resolved
    resolution: str | None = None


class ConflictResolution(BaseModel):
    strategy: str  # accept_source, keep_canonical, manual
    manual_value: str | None = None
