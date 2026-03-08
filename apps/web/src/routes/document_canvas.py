"""Document canvas + audit evidence routes."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from routes._deps import (
    _document_client,
    _raise_upstream_error,
    _require_session,
    build_forward_headers,
    logger,
    permission_required,
)
from routes._models import DocumentCanvasRequest

router = APIRouter()


@router.post("/api/document-canvas/documents")
async def create_document_canvas_document(
    payload: DocumentCanvasRequest, request: Request
) -> dict[str, Any]:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _document_client()
    response = await client.create_document(payload.model_dump(), headers=headers)
    if response.status_code == 403:
        logger.info(
            "document_canvas.create",
            extra={
                "tenant_id": session.get("tenant_id"),
                "project_id": request.query_params.get("project_id"),
            },
        )
        return JSONResponse(status_code=403, content=response.json())
    if response.status_code >= 400:
        _raise_upstream_error(response)
    body = response.json()
    logger.info(
        "document_canvas.create",
        extra={
            "tenant_id": session.get("tenant_id"),
            "project_id": request.query_params.get("project_id"),
            "document_id": body.get("document_id"),
        },
    )
    return body


@router.get("/api/document-canvas/documents")
async def list_document_canvas_documents(request: Request) -> list[dict[str, Any]]:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _document_client()
    response = await client.list_documents(headers=headers)
    if response.status_code >= 400:
        _raise_upstream_error(response)
    body = response.json()
    logger.info(
        "document_canvas.list",
        extra={
            "tenant_id": session.get("tenant_id"),
            "project_id": request.query_params.get("project_id"),
        },
    )
    return body


@router.get("/api/document-canvas/documents/{document_id}")
async def get_document_canvas_document(document_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    headers = build_forward_headers(request, session)
    client = _document_client()
    response = await client.get_document(document_id, headers=headers)
    if response.status_code >= 400:
        _raise_upstream_error(response)
    body = response.json()
    logger.info(
        "document_canvas.get",
        extra={
            "tenant_id": session.get("tenant_id"),
            "project_id": request.query_params.get("project_id"),
            "document_id": document_id,
        },
    )
    return body


@router.get("/api/audit/evidence/export")
@permission_required("audit.view")
async def export_audit_evidence(request: Request) -> Response:
    session = _require_session(request)
    audit_url = os.getenv("AUDIT_LOG_SERVICE_URL")
    if not audit_url:
        raise HTTPException(status_code=503, detail="Audit log service unavailable")
    headers = {}
    auth_header = request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    headers["X-Tenant-ID"] = session.get("tenant_id") or "unknown"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{audit_url}/audit/evidence/export", headers=headers)
    if response.status_code >= 400:
        _raise_upstream_error(response)
    filename = f"audit-evidence-{session.get('tenant_id', 'tenant')}.zip"
    return Response(
        content=response.content,
        media_type=response.headers.get("content-type", "application/zip"),
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
