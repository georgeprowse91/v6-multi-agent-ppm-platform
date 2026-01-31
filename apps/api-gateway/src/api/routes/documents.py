from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()


@dataclass
class DocumentSession:
    session_id: str
    document_id: str
    tenant_id: str
    status: str
    started_by: str
    started_at: str
    updated_at: str
    collaborators: list[str] = field(default_factory=list)
    content: str = ""
    version: int = 1


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


_SESSION_STORE: dict[str, DocumentSession] = {}
_DOCUMENT_VERSIONS: dict[str, list[dict[str, Any]]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_payload(session: DocumentSession) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        document_id=session.document_id,
        tenant_id=session.tenant_id,
        status=session.status,
        started_by=session.started_by,
        started_at=session.started_at,
        updated_at=session.updated_at,
        collaborators=session.collaborators,
        version=session.version,
        content=session.content,
    )


def _record_version(document_id: str, payload: dict[str, Any]) -> None:
    history = _DOCUMENT_VERSIONS.setdefault(document_id, [])
    history.append(payload)


@router.post("/documents/sessions", response_model=SessionResponse)
async def start_session(request: SessionStartRequest, http_request: Request) -> SessionResponse:
    session_id = str(uuid4())
    tenant_id = http_request.state.auth.tenant_id
    started_at = _now()
    session = DocumentSession(
        session_id=session_id,
        document_id=request.document_id,
        tenant_id=tenant_id,
        status="active",
        started_by=request.started_by,
        started_at=started_at,
        updated_at=started_at,
        collaborators=request.collaborators,
        content=request.initial_content,
        version=1,
    )
    _SESSION_STORE[session_id] = session
    _record_version(
        request.document_id,
        {
            "version": session.version,
            "content": request.initial_content,
            "persisted_at": started_at,
            "persisted_by": request.started_by,
        },
    )
    return _session_payload(session)


@router.get("/documents/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, http_request: Request) -> SessionResponse:
    session = _SESSION_STORE.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return _session_payload(session)


@router.post("/documents/sessions/{session_id}/stop", response_model=SessionStopResponse)
async def stop_session(
    session_id: str, request: SessionStopRequest, http_request: Request
) -> SessionStopResponse:
    session = _SESSION_STORE.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    session.status = "stopped"
    session.updated_at = _now()
    return SessionStopResponse(
        session_id=session.session_id,
        status=session.status,
        ended_by=request.ended_by,
        stopped_at=session.updated_at,
        reason=request.reason,
    )


@router.post("/documents/sessions/{session_id}/persist", response_model=PersistSessionResponse)
async def persist_session(
    session_id: str, request: PersistSessionRequest, http_request: Request
) -> PersistSessionResponse:
    session = _SESSION_STORE.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    session.content = request.content
    session.version = request.version
    session.updated_at = _now()
    _record_version(
        session.document_id,
        {
            "version": session.version,
            "content": session.content,
            "persisted_at": session.updated_at,
            "persisted_by": request.persisted_by,
            "summary": request.summary,
            "metadata": request.metadata,
        },
    )
    return PersistSessionResponse(
        document_id=session.document_id,
        session_id=session.session_id,
        version=session.version,
        persisted_at=session.updated_at,
        persisted_by=request.persisted_by,
        summary=request.summary,
        metadata=request.metadata,
    )
