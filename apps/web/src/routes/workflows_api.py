"""Workflow definition CRUD + start routes (from legacy_main.py)."""
from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request

from routes._deps import (
    _require_session,
    permission_required,
    workflow_definition_store,
)
from routes._deps import (
    WorkflowDefinitionPayload,
    WorkflowDefinitionRecord,
    WorkflowDefinitionSummary,
)
from routes._models import WorkflowStartRequest, WorkflowStartResponse

router = APIRouter()


def _validate_workflow_payload(payload: WorkflowDefinitionPayload) -> None:
    if not payload.workflow_id:
        raise HTTPException(status_code=422, detail="workflow_id is required")
    if not payload.definition:
        raise HTTPException(status_code=422, detail="definition is required")


async def _sync_workflow_definition(request: Request, workflow_id: str, definition: dict[str, Any]) -> None:
    workflow_url = os.getenv("WORKFLOW_SERVICE_URL")
    if not workflow_url:
        return
    session = _require_session(request)
    headers = {"Authorization": f"Bearer {session['access_token']}", "X-Tenant-ID": session["tenant_id"]}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.put(f"{workflow_url}/v1/workflows/{workflow_id}", headers=headers, json=definition)
    except httpx.RequestError:
        pass


async def _delete_workflow_definition(request: Request, workflow_id: str) -> None:
    workflow_url = os.getenv("WORKFLOW_SERVICE_URL")
    if not workflow_url:
        return
    session = _require_session(request)
    headers = {"Authorization": f"Bearer {session['access_token']}", "X-Tenant-ID": session["tenant_id"]}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.delete(f"{workflow_url}/v1/workflows/{workflow_id}", headers=headers)
    except httpx.RequestError:
        pass


@router.get("/api/workflows", response_model=list[WorkflowDefinitionSummary])
@permission_required("config.manage")
def list_workflow_definitions(request: Request) -> list[WorkflowDefinitionSummary]:
    _require_session(request)
    return workflow_definition_store.list_summaries()


@router.get("/api/workflows/{workflow_id}", response_model=WorkflowDefinitionRecord)
@permission_required("config.manage")
def get_workflow_definition(workflow_id: str, request: Request) -> WorkflowDefinitionRecord:
    _require_session(request)
    record = workflow_definition_store.get(workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    return record


@router.post("/api/workflows", response_model=WorkflowDefinitionRecord)
@permission_required("config.manage")
async def create_workflow_definition(request: Request, payload: WorkflowDefinitionPayload) -> WorkflowDefinitionRecord:
    _validate_workflow_payload(payload)
    record = workflow_definition_store.upsert(payload)
    await _sync_workflow_definition(request, payload.workflow_id, payload.definition)
    return record


@router.put("/api/workflows/{workflow_id}", response_model=WorkflowDefinitionRecord)
@permission_required("config.manage")
async def update_workflow_definition(workflow_id: str, request: Request, payload: WorkflowDefinitionPayload) -> WorkflowDefinitionRecord:
    if payload.workflow_id != workflow_id:
        raise HTTPException(status_code=422, detail="workflow_id mismatch")
    _validate_workflow_payload(payload)
    record = workflow_definition_store.upsert(payload)
    await _sync_workflow_definition(request, workflow_id, payload.definition)
    return record


@router.delete("/api/workflows/{workflow_id}")
@permission_required("config.manage")
async def delete_workflow_definition(workflow_id: str, request: Request) -> dict[str, str]:
    _require_session(request)
    record = workflow_definition_store.get(workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow definition not found")
    workflow_definition_store.delete(workflow_id)
    await _delete_workflow_definition(request, workflow_id)
    return {"status": "deleted"}


@router.post("/api/workflows/start", response_model=WorkflowStartResponse)
async def api_start_workflow(request: Request, payload: WorkflowStartRequest) -> dict[str, Any]:
    session = _require_session(request)
    workflow_url = os.getenv("WORKFLOW_SERVICE_URL", "http://localhost:8082")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{workflow_url}/v1/workflows/start",
            headers={"Authorization": f"Bearer {session['access_token']}", "X-Tenant-ID": session["tenant_id"]},
            json={"workflow_id": payload.workflow_id, "tenant_id": session["tenant_id"], "classification": "internal", "payload": {"request": "run"}, "actor": {"id": session.get("subject") or "ui-user", "type": "user", "roles": session.get("roles") or ["PMO_ADMIN"]}},
        )
        response.raise_for_status()
        return response.json()
