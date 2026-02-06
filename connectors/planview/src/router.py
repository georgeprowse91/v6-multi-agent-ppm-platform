from __future__ import annotations

from fastapi import APIRouter, HTTPException

from connectors.sdk.src.sync_router import InboundSyncRequest, OutboundSyncRequest, map_records

from .main import CONNECTOR_ROOT, run_sync

router = APIRouter(prefix="/connectors/planview", tags=["connectors"])


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
    if request.live:
        # Temporary implementation: acknowledge but do not write back to Planview.
        # TODO: Implement full outbound create/update support in a future update.
        run_sync(
            mapped,
            request.tenant_id,
            live=True,
            include_schema=request.include_schema,
        )
        return {
            "status": "dry_run",
            "message": "Outbound sync is not yet fully implemented; data not written",
        }
    return {"status": "dry_run", "records": mapped}
