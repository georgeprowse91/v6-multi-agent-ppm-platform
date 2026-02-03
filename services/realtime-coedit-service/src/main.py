from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import (
    APIRouter,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_ROOT = REPO_ROOT / "packages" / "security" / "src"
OBSERVABILITY_ROOT = REPO_ROOT / "packages" / "observability" / "src"
for root in (REPO_ROOT, SECURITY_ROOT, OBSERVABILITY_ROOT):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from packages.version import API_VERSION  # noqa: E402
from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402
from security.errors import register_error_handlers  # noqa: E402
from security.headers import SecurityHeadersMiddleware  # noqa: E402

logger = logging.getLogger("realtime-coedit-service")
logging.basicConfig(level=logging.INFO)

MAX_HISTORY = int(os.getenv("COEDIT_MAX_HISTORY", "25"))


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "realtime-coedit-service"
    dependencies: dict[str, str] = Field(default_factory=dict)


class SessionCreateRequest(BaseModel):
    document_id: str
    initial_content: str = ""
    classification: str = "internal"


class SessionResponse(BaseModel):
    session_id: str
    document_id: str
    tenant_id: str
    version: int
    content: str
    participants: list[dict[str, Any]]
    cursors: dict[str, Any]
    conflicts: list[dict[str, Any]]
    created_at: str
    updated_at: str


class SessionStopResponse(BaseModel):
    session_id: str
    status: str
    stopped_at: str


class PersistRequest(BaseModel):
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersistResponse(BaseModel):
    session_id: str
    document_id: str
    version: int
    persisted_at: str
    summary: str | None
    metadata: dict[str, Any]


class DocumentHistoryEntry(BaseModel):
    version: int
    content: str
    updated_at: str
    updated_by: str | None
    conflict: dict[str, Any] | None = None


@dataclass
class Participant:
    user_id: str
    user_name: str
    joined_at: str


@dataclass
class CoeditSession:
    session_id: str
    document_id: str
    tenant_id: str
    content: str
    version: int
    created_at: str
    updated_at: str
    participants: dict[str, Participant] = field(default_factory=dict)
    cursors: dict[str, Any] = field(default_factory=dict)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    connections: set[WebSocket] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


app = FastAPI(title="Realtime Coedit Service", version=API_VERSION, openapi_prefix="/v1")
api_router = APIRouter(prefix="/v1")
app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz", "/version"})
app.add_middleware(SecurityHeadersMiddleware)
configure_tracing("realtime-coedit-service")
configure_metrics("realtime-coedit-service")
app.add_middleware(TraceMiddleware, service_name="realtime-coedit-service")
app.add_middleware(RequestMetricsMiddleware, service_name="realtime-coedit-service")
register_error_handlers(app)

_sessions: dict[str, CoeditSession] = {}
_document_history: dict[str, list[DocumentHistoryEntry]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_history(
    document_id: str,
    version: int,
    content: str,
    updated_by: str | None,
    conflict: dict[str, Any] | None = None,
) -> None:
    history = _document_history.setdefault(document_id, [])
    history.append(
        DocumentHistoryEntry(
            version=version,
            content=content,
            updated_at=_now(),
            updated_by=updated_by,
            conflict=conflict,
        )
    )
    if len(history) > MAX_HISTORY:
        del history[:-MAX_HISTORY]


def _resolve_conflict(current: str, incoming: str) -> str:
    if incoming == current:
        return current
    if current and current in incoming:
        return incoming
    if incoming and incoming in current:
        return current
    separator = "\n\n"
    return f"{current}{separator}{incoming}" if current else incoming


def _serialize_session(session: CoeditSession) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        document_id=session.document_id,
        tenant_id=session.tenant_id,
        version=session.version,
        content=session.content,
        participants=[
            {"user_id": p.user_id, "user_name": p.user_name, "joined_at": p.joined_at}
            for p in session.participants.values()
        ],
        cursors=session.cursors,
        conflicts=session.conflicts,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _paginate(items: list[Any], *, offset: int, limit: int) -> tuple[list[Any], int]:
    total = len(items)
    return items[offset : offset + limit], total


async def _broadcast(session: CoeditSession, payload: dict[str, Any]) -> None:
    dead: set[WebSocket] = set()
    for connection in session.connections:
        try:
            await connection.send_json(payload)
        except RuntimeError:
            dead.add(connection)
    for connection in dead:
        session.connections.discard(connection)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    dependencies = {"session_store": "ok", "history_buffer": "ok"}
    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    return HealthResponse(status=status, dependencies=dependencies)


@app.get("/version")
async def version() -> dict[str, str]:
    return {
        "service": "realtime-coedit-service",
        "api_version": API_VERSION,
        "build_sha": os.getenv("BUILD_SHA", "unknown"),
    }


@api_router.post("/sessions", response_model=SessionResponse)
async def start_session(request: SessionCreateRequest, http_request: Request) -> SessionResponse:
    session_id = str(uuid4())
    created_at = _now()
    tenant_id = http_request.state.auth.tenant_id
    session = CoeditSession(
        session_id=session_id,
        document_id=request.document_id,
        tenant_id=tenant_id,
        content=request.initial_content,
        version=1,
        created_at=created_at,
        updated_at=created_at,
    )
    _sessions[session_id] = session
    _record_history(request.document_id, session.version, request.initial_content, None)
    logger.info(
        "coedit_session_started",
        extra={
            "session_id": session_id,
            "document_id": request.document_id,
            "tenant_id": tenant_id,
        },
    )
    return _serialize_session(session)


@api_router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, http_request: Request) -> SessionResponse:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return _serialize_session(session)


@api_router.post("/sessions/{session_id}/stop", response_model=SessionStopResponse)
async def stop_session(session_id: str, http_request: Request) -> SessionStopResponse:
    session = _sessions.pop(session_id, None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    logger.info(
        "coedit_session_stopped",
        extra={"session_id": session_id, "document_id": session.document_id},
    )
    return SessionStopResponse(
        session_id=session_id, status="stopped", stopped_at=_now()
    )


@api_router.post("/sessions/{session_id}/persist", response_model=PersistResponse)
async def persist_session(
    session_id: str, request: PersistRequest, http_request: Request
) -> PersistResponse:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.tenant_id != http_request.state.auth.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    _record_history(session.document_id, session.version, session.content, None)
    return PersistResponse(
        session_id=session_id,
        document_id=session.document_id,
        version=session.version,
        persisted_at=_now(),
        summary=request.summary,
        metadata=request.metadata,
    )


@api_router.get("/documents/{document_id}/history", response_model=list[DocumentHistoryEntry])
async def document_history(
    document_id: str,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[DocumentHistoryEntry]:
    entries = _document_history.get(document_id, [])
    sliced, total = _paginate(entries, offset=offset, limit=limit)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return sliced


@api_router.websocket("/ws/documents/{document_id}")
async def coedit_socket(
    websocket: WebSocket,
    document_id: str,
    session_id: str = Query(..., alias="session_id"),
    user_id: str = Query(..., alias="user_id"),
    user_name: str = Query("Anonymous", alias="user_name"),
) -> None:
    session = _sessions.get(session_id)
    if not session or session.document_id != document_id:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    session.connections.add(websocket)
    session.participants[user_id] = Participant(
        user_id=user_id, user_name=user_name, joined_at=_now()
    )

    await websocket.send_json(
        {
            "type": "session_state",
            "session_id": session.session_id,
            "document_id": session.document_id,
            "content": session.content,
            "version": session.version,
            "participants": [
                {
                    "user_id": p.user_id,
                    "user_name": p.user_name,
                    "joined_at": p.joined_at,
                }
                for p in session.participants.values()
            ],
            "cursors": session.cursors,
        }
    )

    await _broadcast(
        session,
        {
            "type": "presence_update",
            "participants": [
                {
                    "user_id": p.user_id,
                    "user_name": p.user_name,
                    "joined_at": p.joined_at,
                }
                for p in session.participants.values()
            ],
        },
    )

    try:
        while True:
            payload = await websocket.receive_json()
            message_type = payload.get("type")

            if message_type == "cursor_update":
                cursor = payload.get("cursor") or {}
                session.cursors[user_id] = cursor
                await _broadcast(
                    session,
                    {
                        "type": "cursor_update",
                        "user_id": user_id,
                        "cursor": cursor,
                    },
                )
                continue

            if message_type == "content_update":
                incoming_content = payload.get("content", "")
                base_version = int(payload.get("base_version", session.version))
                conflict: dict[str, Any] | None = None
                async with session.lock:
                    if base_version != session.version:
                        conflict = {
                            "conflict_id": str(uuid4()),
                            "base_version": base_version,
                            "current_version": session.version,
                            "received_at": _now(),
                        }
                        session.conflicts.append(conflict)
                    resolved = _resolve_conflict(session.content, incoming_content)
                    if resolved != session.content or base_version == session.version:
                        session.content = resolved
                        session.version += 1
                        session.updated_at = _now()
                        _record_history(
                            session.document_id,
                            session.version,
                            session.content,
                            user_id,
                            conflict,
                        )

                await _broadcast(
                    session,
                    {
                        "type": "content_update",
                        "content": session.content,
                        "version": session.version,
                        "sender": user_id,
                        "conflict": conflict,
                    },
                )
                continue

            await websocket.send_json({"type": "error", "message": "Unknown message"})
    except WebSocketDisconnect:
        session.connections.discard(websocket)
        session.participants.pop(user_id, None)
        session.cursors.pop(user_id, None)
        await _broadcast(
            session,
            {
                "type": "presence_update",
                "participants": [
                    {
                        "user_id": p.user_id,
                        "user_name": p.user_name,
                        "joined_at": p.joined_at,
                    }
                    for p in session.participants.values()
                ],
            },
        )


app.include_router(api_router)
