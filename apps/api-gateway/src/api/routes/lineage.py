"""
Lineage API Routes

Proxy endpoints for lineage queries.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

LINEAGE_SERVICE_URL = os.getenv("DATA_LINEAGE_SERVICE_URL", "http://data-lineage-service:8080")


def _forward_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key in ("authorization", "x-tenant-id", "x-dev-user"):
        value = request.headers.get(key)
        if value:
            headers[key] = value
    return headers


async def _proxy_request(
    request: Request, method: str, path: str, *, params: dict[str, Any] | None = None
) -> Any:
    url = f"{LINEAGE_SERVICE_URL.rstrip('/')}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.request(
            method, url, headers=_forward_headers(request), params=params
        )
    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = {"detail": response.text}
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


@router.get("/lineage")
async def list_lineage(
    request: Request,
    work_item_id: str | None = None,
    connector_id: str | None = None,
) -> Any:
    if not work_item_id and not connector_id:
        raise HTTPException(
            status_code=400, detail="work_item_id or connector_id query parameter is required"
        )
    params: dict[str, Any] = {}
    if work_item_id:
        params["work_item_id"] = work_item_id
    if connector_id:
        params["connector_id"] = connector_id
    return await _proxy_request(request, "GET", "/lineage/events", params=params)
