from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from integrations.connectors.sdk.src.base_connector import (
    ConnectorCategory,
    ConnectorConfig,
    SyncDirection,
    SyncFrequency,
)
from integrations.connectors.sdk.src.runtime import ConnectorRuntime
from integrations.connectors.sdk.src.sync_router import InboundSyncRequest, OutboundSyncRequest, map_records

from .smartsheet_connector import SmartsheetConnector

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]

router = APIRouter(prefix="/connectors/smartsheet", tags=["connectors"])


def _build_connector() -> SmartsheetConnector:
    config = ConnectorConfig(
        connector_id="smartsheet",
        name="Smartsheet",
        category=ConnectorCategory.PM,
        enabled=True,
        sync_direction=SyncDirection.BIDIRECTIONAL,
        sync_frequency=SyncFrequency.MANUAL,
        instance_url="",
        project_key="",
    )
    return SmartsheetConnector(config)


@router.post("/sync/inbound")
def sync_inbound(request: InboundSyncRequest) -> list[dict[str, object]]:
    if request.records:
        return map_records(
            CONNECTOR_ROOT,
            request.records,
            request.tenant_id,
            include_schema=request.include_schema,
        )
    if not request.live:
        raise HTTPException(status_code=400, detail="Either records or live=true is required")
    connector = _build_connector()
    sheets = connector.read("sheets")
    records = [
        {
            "source": "project",
            "id": sheet.get("id"),
            "name": sheet.get("name"),
            "status": "active",
            "owner": sheet.get("owner"),
        }
        for sheet in sheets
    ]
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    return runtime.apply_mappings(records, request.tenant_id, include_schema=request.include_schema)


@router.post("/sync/outbound")
def sync_outbound(request: OutboundSyncRequest) -> dict[str, object]:
    mapped = map_records(
        CONNECTOR_ROOT,
        request.records,
        request.tenant_id,
        include_schema=request.include_schema,
    )
    if request.live:
        connector = _build_connector()
        response = connector.write("sheets", request.records)
        return {"status": "sent", "records": response}
    return {"status": "dry_run", "records": mapped}
