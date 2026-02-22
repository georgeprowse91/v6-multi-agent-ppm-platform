from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from api.document_session_store import DocumentSessionStore
from api.routes.documents import router
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


def _build_app(tmp_path) -> FastAPI:
    app = FastAPI()
    app.state.document_session_store = DocumentSessionStore(tmp_path / "sessions.db")

    @app.middleware("http")
    async def inject_auth(request: Request, call_next):
        request.state.auth = SimpleNamespace(tenant_id="tenant-a")
        return await call_next(request)

    app.include_router(router)
    return app


def test_parallel_persist_requests_are_consistent(tmp_path) -> None:
    app = _build_app(tmp_path)
    with TestClient(app) as client:
        start = client.post(
            "/documents/sessions",
            json={
                "document_id": "doc-1",
                "started_by": "user-1",
                "collaborators": ["user-2"],
                "initial_content": "v0",
            },
        )
        assert start.status_code == 200
        session_id = start.json()["session_id"]

        def persist(version: int) -> int:
            response = client.post(
                f"/documents/sessions/{session_id}/persist",
                json={
                    "content": f"content-{version}",
                    "version": version,
                    "persisted_by": "user-1",
                    "summary": f"summary-{version}",
                },
            )
            assert response.status_code == 200
            return response.json()["version"]

        with ThreadPoolExecutor(max_workers=8) as pool:
            versions = list(pool.map(persist, range(2, 18)))

        session = client.get(f"/documents/sessions/{session_id}")
        assert session.status_code == 200
        payload = session.json()
        assert payload["version"] in set(versions)
        assert payload["content"].startswith("content-")

    app.state.document_session_store.close()
