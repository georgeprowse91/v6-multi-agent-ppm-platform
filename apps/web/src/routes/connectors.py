"""Connector gallery routes — consolidated from connectors.py + connectors_api.py.

Serves both the v1 stub paths (``/v1/api/connector-gallery/…``) and the
legacy paths (``/api/connector-gallery/…``).  All operations delegate to
:class:`web_services.connectors.ConnectorService` so that business logic
lives in a single place.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from dependencies import get_connector_hub_client
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from web_services.connectors import ConnectorService

from routes._models import ConnectorInstanceCreate, ConnectorInstanceUpdate

logger = logging.getLogger("web-ui")

router = APIRouter(prefix="/v1/api/connector-gallery", tags=["connectors"])

# Legacy router — no prefix; endpoints specify full paths for backwards
# compatibility with the old ``/api/connector-gallery/*`` URLs.
legacy_router = APIRouter(tags=["connectors"])


def get_connector_service() -> ConnectorService:
    return ConnectorService(get_connector_hub_client())


def _get_service_with_headers(request: Request) -> ConnectorService:
    from routes._deps import _connector_hub_client, _require_session, build_forward_headers

    session = _require_session(request)
    headers = build_forward_headers(request, session)
    return ConnectorService(_connector_hub_client(), headers=headers)


def _passthrough(response: httpx.Response) -> Response:
    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("content-type"),
    )


def _tenant_id(request: Request) -> str | None:
    from routes._deps import _require_session, _tenant_id_from_request

    session = _require_session(request)
    return _tenant_id_from_request(request, session)


# -----------------------------------------------------------------------
# v1 stub endpoints  (prefix: /v1/api/connector-gallery)
# -----------------------------------------------------------------------


@router.get("/instances")
async def list_instances(service: ConnectorService = Depends(get_connector_service)) -> list[dict]:
    return await service.list_instances()


# -----------------------------------------------------------------------
# Legacy endpoints  (full paths for backwards compatibility)
# -----------------------------------------------------------------------


@legacy_router.get("/api/connector-gallery/types")
async def list_connector_types(request: Request) -> list[dict[str, Any]]:
    tenant = _tenant_id(request)
    svc = _get_service_with_headers(request)
    types = svc.list_types()
    logger.info("connector_gallery.types.list", extra={"tenant_id": tenant})
    return types


@legacy_router.get("/api/connector-gallery/instances")
async def list_connector_instances(request: Request) -> Response:
    tenant = _tenant_id(request)
    svc = _get_service_with_headers(request)
    try:
        response = await svc.list_instances_raw()
    except httpx.RequestError:
        raise HTTPException(status_code=504, detail="Connector hub unavailable")
    logger.info("connector_gallery.instances.list", extra={"tenant_id": tenant})
    if response.status_code >= 400:
        return _passthrough(response)
    return JSONResponse(status_code=response.status_code, content=response.json())


@legacy_router.post("/api/connector-gallery/instances")
async def create_connector_instance(payload: ConnectorInstanceCreate, request: Request) -> Response:
    tenant = _tenant_id(request)
    svc = _get_service_with_headers(request)
    metadata = {"connector_type_id": payload.connector_type_id}
    metadata.update(payload.metadata or {})
    connector_request = {
        "name": payload.connector_type_id,
        "version": payload.version,
        "enabled": payload.enabled,
        "metadata": metadata,
    }
    try:
        response = await svc.create_instance(connector_request)
    except httpx.RequestError:
        raise HTTPException(status_code=504, detail="Connector hub unavailable")
    if response.status_code >= 400:
        return _passthrough(response)
    body = response.json()
    logger.info(
        "connector_gallery.instances.create",
        extra={
            "tenant_id": tenant,
            "connector_id": body.get("connector_id"),
            "connector_type_id": payload.connector_type_id,
        },
    )
    return JSONResponse(status_code=response.status_code, content=body)


@legacy_router.patch("/api/connector-gallery/instances/{connector_id}")
async def update_connector_instance(
    connector_id: str, payload: ConnectorInstanceUpdate, request: Request
) -> Response:
    tenant = _tenant_id(request)
    svc = _get_service_with_headers(request)
    update_payload = payload.model_dump(exclude_none=True)
    try:
        response = await svc.update_instance(connector_id, update_payload)
    except httpx.RequestError:
        raise HTTPException(status_code=504, detail="Connector hub unavailable")
    if response.status_code >= 400:
        return _passthrough(response)
    body = response.json()
    logger.info(
        "connector_gallery.instances.update",
        extra={
            "tenant_id": tenant,
            "connector_id": connector_id,
            "connector_type_id": body.get("metadata", {}).get("connector_type_id"),
        },
    )
    return JSONResponse(status_code=response.status_code, content=body)


@legacy_router.get("/api/connector-gallery/instances/{connector_id}/health")
async def get_connector_health(connector_id: str, request: Request) -> Response:
    tenant = _tenant_id(request)
    svc = _get_service_with_headers(request)
    try:
        response = await svc.get_health(connector_id)
    except httpx.RequestError:
        raise HTTPException(status_code=504, detail="Connector hub unavailable")
    if response.status_code >= 400:
        return _passthrough(response)
    body = response.json()
    logger.info(
        "connector_gallery.instances.health",
        extra={
            "tenant_id": tenant,
            "connector_id": connector_id,
            "connector_type_id": body.get("metadata", {}).get("connector_type_id"),
        },
    )
    return JSONResponse(status_code=response.status_code, content=body)
