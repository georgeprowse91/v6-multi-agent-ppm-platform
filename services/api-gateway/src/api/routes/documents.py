from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.dependencies import get_document_session_store
from api.document_session_store import DocumentSessionStore

router = APIRouter()


class SessionStartRequest(BaseModel):
    document_id: str
    started_by: str
    collaborators: list[str] = Field(default_factory=list)
    initial_content: str = ""


class SessionResponse(BaseModel):
    session_id: str
    document_id: str
    tenant_id: str
    status: str
    started_by: str
    started_at: str
    updated_at: str
    collaborators: list[str]
    version: int
    content: str


class SessionStopRequest(BaseModel):
    ended_by: str
    reason: str | None = None


class SessionStopResponse(BaseModel):
    session_id: str
    status: str
    ended_by: str
    stopped_at: str
    reason: str | None = None


class PersistSessionRequest(BaseModel):
    content: str
    version: int
    persisted_by: str
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersistSessionResponse(BaseModel):
    document_id: str
    session_id: str
    version: int
    persisted_at: str
    persisted_by: str
    summary: str | None
    metadata: dict[str, Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_payload(session: dict[str, Any]) -> SessionResponse:
    return SessionResponse(**session)


@router.post("/documents/sessions", response_model=SessionResponse)
async def start_session(
    request: SessionStartRequest,
    http_request: Request,
    session_store: DocumentSessionStore = Depends(get_document_session_store),
) -> SessionResponse:
    session_id = str(uuid4())
    tenant_id = http_request.state.auth.tenant_id
    started_at = _now()
    session = {
        "session_id": session_id,
        "document_id": request.document_id,
        "tenant_id": tenant_id,
        "status": "active",
        "started_by": request.started_by,
        "started_at": started_at,
        "updated_at": started_at,
        "collaborators": request.collaborators,
        "content": request.initial_content,
        "version": 1,
    }
    session_store.create_session(session)
    session_store.record_version(
        request.document_id,
        1,
        request.initial_content,
        started_at,
        request.started_by,
    )
    return _session_payload(session)


@router.get("/documents/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    http_request: Request,
    session_store: DocumentSessionStore = Depends(get_document_session_store),
) -> SessionResponse:
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["tenant_id"] != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return _session_payload(session)


@router.post("/documents/sessions/{session_id}/stop", response_model=SessionStopResponse)
async def stop_session(
    session_id: str,
    request: SessionStopRequest,
    http_request: Request,
    session_store: DocumentSessionStore = Depends(get_document_session_store),
) -> SessionStopResponse:
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["tenant_id"] != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    updated_at = _now()
    session = session_store.update_session(session_id, status="stopped", updated_at=updated_at)
    assert session is not None
    return SessionStopResponse(
        session_id=session["session_id"],
        status=session["status"],
        ended_by=request.ended_by,
        stopped_at=session["updated_at"],
        reason=request.reason,
    )


@router.post("/documents/sessions/{session_id}/persist", response_model=PersistSessionResponse)
async def persist_session(
    session_id: str,
    request: PersistSessionRequest,
    http_request: Request,
    session_store: DocumentSessionStore = Depends(get_document_session_store),
) -> PersistSessionResponse:
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["tenant_id"] != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    updated_at = _now()
    session = session_store.update_session(
        session_id,
        content=request.content,
        version=request.version,
        updated_at=updated_at,
    )
    assert session is not None
    session_store.record_version(
        session["document_id"],
        session["version"],
        session["content"],
        session["updated_at"],
        request.persisted_by,
        summary=request.summary,
        metadata=request.metadata,
    )
    return PersistSessionResponse(
        document_id=session["document_id"],
        session_id=session["session_id"],
        version=session["version"],
        persisted_at=session["updated_at"],
        persisted_by=request.persisted_by,
        summary=request.summary,
        metadata=request.metadata,
    )
