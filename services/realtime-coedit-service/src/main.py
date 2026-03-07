from __future__ import annotations

import asyncio
import logging
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

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(REPO_ROOT)

from observability.metrics import RequestMetricsMiddleware, configure_metrics  # noqa: E402
from observability.tracing import TraceMiddleware, configure_tracing  # noqa: E402
from security.api_governance import apply_api_governance, version_response_payload  # noqa: E402
from security.auth import AuthTenantMiddleware  # noqa: E402
from storage import (  # noqa: E402
    HistoryRecord,
    ParticipantRecord,
    PubSubBroker,
    SessionRecord,
    build_backend,
    now_iso,
)

from packages.version import API_VERSION  # noqa: E402

logger = logging.getLogger("realtime-coedit-service")
logging.basicConfig(level=logging.INFO)


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


class WebSocketHub:
    def __init__(self, pubsub: PubSubBroker):
        self.pubsub = pubsub
        self.connections: dict[str, set[WebSocket]] = {}
        self.subscriptions: dict[str, Any] = {}
        self.lock = asyncio.Lock()

    async def register(self, session_id: str, websocket: WebSocket) -> None:
        async with self.lock:
            self.connections.setdefault(session_id, set()).add(websocket)
            if session_id not in self.subscriptions:
                self.subscriptions[session_id] = await self.pubsub.subscribe(
                    f"session:{session_id}",
                    lambda payload: self._fanout(session_id, payload),
                )

    async def unregister(self, session_id: str, websocket: WebSocket) -> None:
        async with self.lock:
            bucket = self.connections.get(session_id, set())
            bucket.discard(websocket)
            if not bucket and session_id in self.subscriptions:
                unsubscribe = self.subscriptions.pop(session_id)
                await unsubscribe()

    async def publish(self, session_id: str, payload: dict[str, Any]) -> None:
        await self.pubsub.publish(f"session:{session_id}", payload)

    async def broadcast(
        self,
        session_id: str,
        payload: dict[str, Any],
        *,
        exclude: WebSocket | None = None,
    ) -> None:
        """Send *payload* to every local connection except *exclude*."""
        dead: set[WebSocket] = set()
        for connection in self.connections.get(session_id, set()):
            if connection is exclude:
                continue
            try:
                await connection.send_json(payload)
            except RuntimeError:
                dead.add(connection)
        for connection in dead:
            self.connections.get(session_id, set()).discard(connection)

    async def _fanout(self, session_id: str, payload: dict[str, Any]) -> None:
        dead: set[WebSocket] = set()
        for connection in self.connections.get(session_id, set()):
            try:
                await connection.send_json(payload)
            except RuntimeError:
                dead.add(connection)
        for connection in dead:
            self.connections.get(session_id, set()).discard(connection)


backend = build_backend()


def _serialize_session(session: SessionRecord) -> SessionResponse:
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


def create_app() -> FastAPI:
    app = FastAPI(title="Realtime Coedit Service", version=API_VERSION)
    api_router = APIRouter(prefix="/v1")
    hub = WebSocketHub(backend)

    app.add_middleware(AuthTenantMiddleware, exempt_paths={"/healthz", "/version"})
    configure_tracing("realtime-coedit-service")
    configure_metrics("realtime-coedit-service")
    app.add_middleware(TraceMiddleware, service_name="realtime-coedit-service")
    app.add_middleware(RequestMetricsMiddleware, service_name="realtime-coedit-service")
    apply_api_governance(app, service_name="realtime-coedit-service")

    @app.get("/healthz", response_model=HealthResponse)
    async def healthz() -> HealthResponse:
        storage_ok = await backend.healthy()
        pubsub_ok = await hub.pubsub.healthy()
        dependencies = {
            "session_store": "ok" if storage_ok else "error",
            "history_store": "ok" if storage_ok else "error",
            "pubsub": "ok" if pubsub_ok else "error",
        }
        status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
        return HealthResponse(status=status, dependencies=dependencies)

    @app.get("/version")
    async def version() -> dict[str, str]:
        return version_response_payload("realtime-coedit-service")

    @api_router.post("/sessions", response_model=SessionResponse)
    async def start_session(
        request: SessionCreateRequest, http_request: Request
    ) -> SessionResponse:
        session_id = str(uuid4())
        created_at = now_iso()
        tenant_id = http_request.state.auth.tenant_id
        session = SessionRecord(
            session_id=session_id,
            document_id=request.document_id,
            tenant_id=tenant_id,
            content=request.initial_content,
            version=1,
            created_at=created_at,
            updated_at=created_at,
        )
        await backend.create(session)
        await backend.append(
            request.document_id,
            HistoryRecord(
                version=session.version,
                content=request.initial_content,
                updated_at=now_iso(),
                updated_by=None,
            ),
        )
        return _serialize_session(session)

    @api_router.get("/sessions/{session_id}", response_model=SessionResponse)
    async def get_session(session_id: str, http_request: Request) -> SessionResponse:
        session = await backend.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.tenant_id != http_request.state.auth.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        return _serialize_session(session)

    @api_router.post("/sessions/{session_id}/stop", response_model=SessionStopResponse)
    async def stop_session(session_id: str, http_request: Request) -> SessionStopResponse:
        session = await backend.delete(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.tenant_id != http_request.state.auth.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        return SessionStopResponse(session_id=session_id, status="stopped", stopped_at=now_iso())

    @api_router.post("/sessions/{session_id}/persist", response_model=PersistResponse)
    async def persist_session(
        session_id: str, request: PersistRequest, http_request: Request
    ) -> PersistResponse:
        session = await backend.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.tenant_id != http_request.state.auth.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        await backend.append(
            session.document_id,
            HistoryRecord(
                version=session.version,
                content=session.content,
                updated_at=now_iso(),
                updated_by=None,
            ),
        )
        return PersistResponse(
            session_id=session_id,
            document_id=session.document_id,
            version=session.version,
            persisted_at=now_iso(),
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
        entries = await backend.list(document_id)
        sliced, total = _paginate(entries, offset=offset, limit=limit)
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Limit"] = str(limit)
        response.headers["X-Offset"] = str(offset)
        return [DocumentHistoryEntry(**entry.__dict__) for entry in sliced]

    @api_router.websocket("/ws/documents/{document_id}")
    async def coedit_socket(
        websocket: WebSocket,
        document_id: str,
        session_id: str = Query(..., alias="session_id"),
        user_id: str = Query(..., alias="user_id"),
        user_name: str = Query("Anonymous", alias="user_name"),
    ) -> None:
        session = await backend.get(session_id)
        if not session or session.document_id != document_id:
            await websocket.close(code=1008)
            return

        await websocket.accept()
        await hub.register(session_id, websocket)
        session = await backend.add_participant(
            session_id,
            ParticipantRecord(user_id=user_id, user_name=user_name, joined_at=now_iso()),
        )
        if not session:
            await websocket.close(code=1011)
            return

        await websocket.send_json(
            {
                "type": "session_state",
                "session_id": session.session_id,
                "document_id": session.document_id,
                "content": session.content,
                "version": session.version,
                "participants": [
                    {"user_id": p.user_id, "user_name": p.user_name, "joined_at": p.joined_at}
                    for p in session.participants.values()
                ],
                "cursors": session.cursors,
            }
        )

        await hub.publish(
            session_id,
            {
                "type": "presence_update",
                "participants": [
                    {"user_id": p.user_id, "user_name": p.user_name, "joined_at": p.joined_at}
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
                    session = await backend.update_cursor(session_id, user_id, cursor)
                    if session:
                        await hub.publish(
                            session_id,
                            {"type": "cursor_update", "user_id": user_id, "cursor": cursor},
                        )
                    continue

                if message_type == "content_update":
                    incoming_content = payload.get("content", "")
                    base_version = int(payload.get("base_version", session.version))
                    updated_session, conflict = await backend.update_content(
                        session_id,
                        incoming_content=incoming_content,
                        base_version=base_version,
                        updated_by=user_id,
                    )
                    if updated_session:
                        await backend.append(
                            updated_session.document_id,
                            HistoryRecord(
                                version=updated_session.version,
                                content=updated_session.content,
                                updated_at=now_iso(),
                                updated_by=user_id,
                                conflict=conflict,
                            ),
                        )
                        session = updated_session
                        await hub.broadcast(
                            session_id,
                            {
                                "type": "content_update",
                                "content": session.content,
                                "version": session.version,
                                "sender": user_id,
                                "conflict": conflict,
                            },
                            exclude=websocket,
                        )
                    continue

                # --- Gantt-specific collaborative events ---
                if message_type in (
                    "gantt_task_move",
                    "gantt_task_update",
                    "gantt_task_add",
                    "gantt_task_delete",
                    "gantt_optimization_action",
                    "gantt_dependency_update",
                ):
                    await hub.broadcast(
                        session_id,
                        {**payload, "sender": user_id},
                        exclude=websocket,
                    )
                    continue

                await websocket.send_json({"type": "error", "message": "Unknown message"})
        except WebSocketDisconnect:
            await hub.unregister(session_id, websocket)
            session = await backend.remove_participant(session_id, user_id)
            await backend.clear_cursor(session_id, user_id)
            if session:
                await hub.publish(
                    session_id,
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
    return app


app = create_app()
