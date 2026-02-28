from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException

from connectors.sdk.src.sync_router import InboundSyncRequest, OutboundSyncRequest, map_records

from connectors.sdk.src.http_client import HttpClientError

from .main import (
    CONNECTOR_ROOT,
    SalesforceConfig,
    _build_client,
    _build_token_manager,
    _request_with_refresh,
    run_sync,
)

router = APIRouter(prefix="/connectors/salesforce", tags=["connectors"])


def _build_outbound_summary(
    *,
    status: str,
    records: list[dict[str, Any]],
    sent_count: int,
    failed_count: int,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "status": status,
        "records": records,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "errors": errors,
    }


def _http_error(detail: str, exc: HttpClientError) -> HTTPException:
    status_code = exc.status_code
    if status_code in {401, 403}:
        return HTTPException(status_code=502, detail=f"{detail}: authentication failed")
    if status_code == 429:
        return HTTPException(status_code=503, detail=f"{detail}: provider rate limit reached")
    if status_code is not None and status_code >= 500:
        return HTTPException(status_code=502, detail=f"{detail}: provider unavailable")
    return HTTPException(status_code=502, detail=f"{detail}: provider request failed")


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
    if not request.live:
        return _build_outbound_summary(
            status="dry_run",
            records=mapped,
            sent_count=0,
            failed_count=0,
            errors=[],
        )

    try:
        config = SalesforceConfig.from_env("", 300)
        token_manager = _build_token_manager(config)
        client = _build_client(config, token_manager)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HttpClientError as exc:
        raise _http_error("Failed to initialize Salesforce outbound sync", exc) from exc

    endpoint = os.getenv("SALESFORCE_OUTBOUND_ENDPOINT") or "/services/data/v57.0/sobjects/Project__c"
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    sent_count = 0

    for record in mapped:
        payload = {
            "Id": record.get("id"),
            "Name": record.get("name"),
            "Status__c": record.get("status"),
            "Start_Date__c": record.get("start_date"),
            "End_Date__c": record.get("end_date"),
            "Owner_Name__c": record.get("owner"),
        }
        try:
            response = _request_with_refresh(client, token_manager, "POST", endpoint, json=payload)
            response_body: Any
            try:
                response_body = response.json()
            except ValueError:
                response_body = {"status_code": response.status_code}
            results.append({"id": record.get("id"), "success": True, "response": response_body})
            sent_count += 1
        except HttpClientError as exc:
            failure = {
                "id": record.get("id"),
                "message": str(exc),
                "status_code": exc.status_code,
            }
            results.append({"id": record.get("id"), "success": False, "error": failure})
            errors.append(failure)

    failed_count = len(mapped) - sent_count
    if sent_count == 0 and failed_count > 0:
        status = "failed"
    elif failed_count > 0:
        status = "partial_failure"
    else:
        status = "sent"
    return _build_outbound_summary(
        status=status,
        records=results,
        sent_count=sent_count,
        failed_count=failed_count,
        errors=errors,
    )
