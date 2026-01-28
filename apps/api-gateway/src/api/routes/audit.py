"""
Audit log API routes.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from security.audit_log import get_audit_log_store

router = APIRouter()


class AuditEventResponse(BaseModel):
    event_id: str
    timestamp: str
    tenant_id: str
    actor: dict
    action: str
    resource: dict
    outcome: str
    metadata: dict | None = None


@router.get("/audit/events", response_model=list[AuditEventResponse])
async def list_audit_events(
    request: Request, limit: int = 200, offset: int = 0
) -> list[AuditEventResponse]:
    store = get_audit_log_store()
    events = store.list_events(
        tenant_id=request.state.auth.tenant_id,
        limit=min(limit, 500),
        offset=offset,
    )
    return [AuditEventResponse(**event) for event in events]
