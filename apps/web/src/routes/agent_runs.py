"""Agent run listing and detail routes."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from routes._deps import _require_session, get_audit_log_store

router = APIRouter()


@router.get("/agent-runs")
async def list_agent_runs(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[dict[str, Any]]:
    session = _require_session(request)
    data_service_url = os.getenv("DATA_SERVICE_URL")
    if not data_service_url:
        raise HTTPException(status_code=503, detail="DATA_SERVICE_URL not configured")
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "X-Tenant-ID": session["tenant_id"],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{data_service_url}/v1/agent-runs",
            headers=headers,
            params={"tenant_id": session["tenant_id"], "skip": skip, "limit": limit},
        )
        response.raise_for_status()
        return response.json()


@router.get("/agent-runs/{agent_run_id}")
async def get_agent_run(agent_run_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    data_service_url = os.getenv("DATA_SERVICE_URL")
    if not data_service_url:
        raise HTTPException(status_code=503, detail="DATA_SERVICE_URL not configured")
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "X-Tenant-ID": session["tenant_id"],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{data_service_url}/v1/agent-runs/{agent_run_id}", headers=headers
        )
        response.raise_for_status()
        return response.json()


@router.get("/audit/events")
async def list_audit_events(
    request: Request,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    session = _require_session(request)
    return get_audit_log_store().list_events(
        tenant_id=session["tenant_id"], limit=limit, offset=offset
    )


@router.get("/audit/events/{event_id}")
async def get_audit_event(event_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    audit_url = os.getenv("AUDIT_LOG_SERVICE_URL")
    if audit_url:
        headers = {
            "Authorization": f"Bearer {session['access_token']}",
            "X-Tenant-ID": session["tenant_id"],
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{audit_url}/audit/events/{event_id}", headers=headers)
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Audit event not found")
            response.raise_for_status()
            return response.json()
    record = get_audit_log_store().get_event(event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audit event not found")
    if record.get("tenant_id") != session["tenant_id"]:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return record
