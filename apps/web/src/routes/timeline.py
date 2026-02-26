"""Timeline milestone routes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from routes._deps import _require_session, logger, timeline_store
from routes._deps import (
    Milestone,
    MilestoneCreate,
    MilestoneUpdate,
    TimelineExportResponse,
    TimelineResponse,
)

router = APIRouter()


@router.get("/api/timeline/{project_id}", response_model=TimelineResponse)
async def list_timeline_milestones(project_id: str, request: Request) -> TimelineResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    milestones = timeline_store.list_milestones(tenant_id, project_id)
    logger.info("timeline.list", extra={"tenant_id": tenant_id, "project_id": project_id})
    return TimelineResponse(tenant_id=tenant_id, project_id=project_id, milestones=milestones)


@router.post("/api/timeline/{project_id}/milestones", response_model=Milestone)
async def create_timeline_milestone(project_id: str, payload: MilestoneCreate, request: Request) -> Milestone:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    milestone = timeline_store.create_milestone(tenant_id, project_id, payload)
    logger.info("timeline.create", extra={"tenant_id": tenant_id, "project_id": project_id, "milestone_id": milestone.milestone_id})
    return milestone


@router.patch("/api/timeline/{project_id}/milestones/{milestone_id}", response_model=Milestone)
async def update_timeline_milestone(project_id: str, milestone_id: str, payload: MilestoneUpdate, request: Request) -> Milestone:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    milestone = timeline_store.update_milestone(tenant_id, project_id, milestone_id, payload)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    logger.info("timeline.update", extra={"tenant_id": tenant_id, "project_id": project_id, "milestone_id": milestone_id})
    return milestone


@router.delete("/api/timeline/{project_id}/milestones/{milestone_id}")
async def delete_timeline_milestone(project_id: str, milestone_id: str, request: Request) -> dict[str, Any]:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    deleted = timeline_store.delete_milestone(tenant_id, project_id, milestone_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Milestone not found")
    logger.info("timeline.delete", extra={"tenant_id": tenant_id, "project_id": project_id, "milestone_id": milestone_id})
    return {"deleted": True, "milestone_id": milestone_id}


@router.get("/api/timeline/{project_id}/export", response_model=TimelineExportResponse)
async def export_timeline(project_id: str, request: Request) -> TimelineExportResponse:
    session = _require_session(request)
    tenant_id = session["tenant_id"]
    milestones = timeline_store.list_milestones(tenant_id, project_id)
    logger.info("timeline.export", extra={"tenant_id": tenant_id, "project_id": project_id})
    return TimelineExportResponse(tenant_id=tenant_id, project_id=project_id, exported_at=datetime.now(timezone.utc), milestones=milestones)
