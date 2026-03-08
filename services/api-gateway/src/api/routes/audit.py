"""
Audit log API routes.
"""

from typing import Any

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel
from security.audit_log import get_audit_log_store

router = APIRouter()


class AuditEventResponse(BaseModel):
    event_id: str
    timestamp: str
    tenant_id: str
    actor: dict[str, Any]
    action: str
    resource: dict[str, Any]
    outcome: str
    metadata: dict[str, Any] | None = None


@router.get("/audit/events", response_model=list[AuditEventResponse])
async def list_audit_events(
    request: Request,
    response: Response,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[AuditEventResponse]:
    store = get_audit_log_store()
    events = store.list_events(
        tenant_id=request.state.auth.tenant_id,
        limit=limit,
        offset=offset,
    )
    response.headers["X-Total-Count"] = str(len(events))
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return [AuditEventResponse(**event) for event in events]
