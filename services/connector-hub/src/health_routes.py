"""Connector health dashboard API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query
from health_aggregator import ConnectorHealthAggregator
from health_models import (
    ConflictRecord,
    ConflictResolution,
    ConnectorHealthRecord,
    DataFreshnessRecord,
)

router = APIRouter(prefix="/v1/connectors/health", tags=["connector-health"])
_aggregator = ConnectorHealthAggregator()


@router.get("/summary")
async def health_summary(
    tenant_id: str = Query(default="default"),
) -> list[ConnectorHealthRecord]:
    return _aggregator.get_all_status(tenant_id)


@router.get("/freshness")
async def data_freshness(
    tenant_id: str = Query(default="default"),
) -> list[DataFreshnessRecord]:
    return _aggregator.get_data_freshness(tenant_id)


@router.get("/conflicts")
async def conflict_queue(
    tenant_id: str = Query(default="default"),
) -> list[ConflictRecord]:
    return _aggregator.get_conflict_queue(tenant_id)


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    resolution: ConflictResolution,
    tenant_id: str = Query(default="default"),
) -> ConflictRecord:
    return _aggregator.resolve_conflict(
        tenant_id, conflict_id, resolution.strategy, resolution.manual_value
    )
