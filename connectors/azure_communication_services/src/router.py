from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from connectors.sdk.src.base_connector import (
    ConnectorCategory,
    ConnectorConfig,
    SyncDirection,
    SyncFrequency,
)
from connectors.sdk.src.runtime import ConnectorRuntime
from connectors.sdk.src.sync_router import InboundSyncRequest, OutboundSyncRequest, map_records

from .azure_communication_services_connector import AzureCommunicationServicesConnector

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]

router = APIRouter(prefix="/connectors/azure_communication_services", tags=["connectors"])


def _build_connector() -> AzureCommunicationServicesConnector:
    config = ConnectorConfig(
        connector_id="azure_communication_services",
        name="Azure Communication Services",
        category=ConnectorCategory.COLLABORATION,
        enabled=True,
        sync_direction=SyncDirection.OUTBOUND,
        sync_frequency=SyncFrequency.MANUAL,
        instance_url="",
        project_key="",
    )
    return AzureCommunicationServicesConnector(config)


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
    messages = connector.read("sms")
    records = [
        {
            "source": "project",
            "id": message.get("messageId"),
            "name": message.get("to"),
            "status": "sent",
            "owner": message.get("from"),
        }
        for message in messages
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
        response = connector.write("sms", request.records)
        return {"status": "sent", "records": response}
    return {"status": "dry_run", "records": mapped}
