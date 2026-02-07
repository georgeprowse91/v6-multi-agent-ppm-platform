from __future__ import annotations

from fastapi import APIRouter, HTTPException

from integrations.connectors.sdk.src.sync_router import InboundSyncRequest, OutboundSyncRequest, map_records

from .main import CONNECTOR_ROOT, run_sync

router = APIRouter(prefix="/connectors/sap", tags=["connectors"])


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
    return run_sync(
        None,
        request.tenant_id,
        live=True,
        include_schema=request.include_schema,
    )


@router.post("/sync/outbound")
def sync_outbound(request: OutboundSyncRequest) -> dict[str, object]:
    mapped = map_records(
        CONNECTOR_ROOT,
        request.records,
        request.tenant_id,
        include_schema=request.include_schema,
    )
    # If live, call the outbound hook. Otherwise return the mapped records for dry-run.
    if request.live:
        # First, run any existing sync logic (e.g. local handlers) if defined.
        run_sync(
            mapped,
            request.tenant_id,
            live=True,
            include_schema=request.include_schema,
        )
        # Call the outbound hook which can later be replaced with real SAP API calls.
        from .main import send_to_external_system
        send_to_external_system(mapped, request.tenant_id, include_schema=request.include_schema)
        return {
            "status": "accepted",
            "records": mapped,
        }
    return {"status": "dry_run", "records": mapped}
