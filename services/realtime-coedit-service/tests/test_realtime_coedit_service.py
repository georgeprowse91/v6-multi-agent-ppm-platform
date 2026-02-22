from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SERVICE_ROOT / "src" / "main.py"

import types


def _install_dependency_stubs() -> None:
    class _PassthroughMiddleware:
        def __init__(self, app, **kwargs):
            self.app = app

        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)

    metrics = types.ModuleType("observability.metrics")
    metrics.RequestMetricsMiddleware = _PassthroughMiddleware
    metrics.configure_metrics = lambda *args, **kwargs: None

    tracing = types.ModuleType("observability.tracing")
    tracing.TraceMiddleware = _PassthroughMiddleware
    tracing.configure_tracing = lambda *args, **kwargs: None

    api_gov = types.ModuleType("security.api_governance")
    api_gov.apply_api_governance = lambda app, service_name=None: None
    api_gov.version_response_payload = lambda service: {"service": service, "version": "test"}

    auth = types.ModuleType("security.auth")

    class _AuthTenantMiddleware:
        def __init__(self, app, exempt_paths=None):
            self.app = app

        async def __call__(self, scope, receive, send):
            state = scope.setdefault("state", {})
            headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
            tenant_id = headers.get("x-tenant-id", "tenant-a")
            state["auth"] = types.SimpleNamespace(tenant_id=tenant_id)
            await self.app(scope, receive, send)

    auth.AuthTenantMiddleware = _AuthTenantMiddleware

    sys.modules["observability.metrics"] = metrics
    sys.modules["observability.tracing"] = tracing
    sys.modules["security.api_governance"] = api_gov
    sys.modules["security.auth"] = auth


def _load_module(name: str):
    _install_dependency_stubs()
    spec = spec_from_file_location(name, MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.path.insert(0, str(SERVICE_ROOT / "src"))
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _build_token(secret: str, tenant_id: str) -> str:
    return jwt.encode(
        {"sub": "user-1", "tenant_id": tenant_id, "roles": ["editor"]},
        secret,
        algorithm="HS256",
    )


def _headers(secret: str, tenant_id: str) -> dict[str, str]:
    token = _build_token(secret, tenant_id)
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}


def test_session_create_and_history(monkeypatch) -> None:
    secret = "test-secret"
    monkeypatch.setenv("IDENTITY_JWT_SECRET", secret)
    monkeypatch.setenv("COEDIT_STORAGE_BACKEND", "inmemory")
    monkeypatch.setenv("COEDIT_STORAGE_NAMESPACE", f"ns-{uuid4()}")

    module = _load_module(f"realtime_coedit_main_{uuid4().hex}")
    with TestClient(module.app) as client:
        response = client.post(
            "/v1/v1/sessions",
            json={"document_id": "doc-1", "initial_content": "hello", "classification": "internal"},
            headers=_headers(secret, "tenant-a"),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["document_id"] == "doc-1"

        history = client.get(
            "/v1/v1/documents/doc-1/history?limit=10&offset=0", headers=_headers(secret, "tenant-a")
        )
        assert history.status_code == 200
        assert history.headers["X-Total-Count"] == "1"
        entries = history.json()
        assert entries[0]["content"] == "hello"


def test_multi_instance_session_continuity(monkeypatch) -> None:
    secret = "test-secret"
    namespace = f"shared-{uuid4()}"
    monkeypatch.setenv("IDENTITY_JWT_SECRET", secret)
    monkeypatch.setenv("COEDIT_STORAGE_BACKEND", "inmemory")
    monkeypatch.setenv("COEDIT_STORAGE_NAMESPACE", namespace)

    module_a = _load_module(f"realtime_coedit_main_a_{uuid4().hex}")
    module_b = _load_module(f"realtime_coedit_main_b_{uuid4().hex}")

    with TestClient(module_a.app) as client_a, TestClient(module_b.app) as client_b:
        created = client_a.post(
            "/v1/v1/sessions",
            json={
                "document_id": "doc-shared",
                "initial_content": "seed",
                "classification": "internal",
            },
            headers=_headers(secret, "tenant-a"),
        )
        assert created.status_code == 200
        session_id = created.json()["session_id"]

        fetched = client_b.get(
            f"/v1/v1/sessions/{session_id}", headers=_headers(secret, "tenant-a")
        )
        assert fetched.status_code == 200
        assert fetched.json()["content"] == "seed"


def test_cross_node_pubsub_broadcast(monkeypatch) -> None:
    secret = "test-secret"
    namespace = f"pubsub-{uuid4()}"
    monkeypatch.setenv("IDENTITY_JWT_SECRET", secret)
    monkeypatch.setenv("COEDIT_STORAGE_BACKEND", "inmemory")
    monkeypatch.setenv("COEDIT_STORAGE_NAMESPACE", namespace)

    module_a = _load_module(f"realtime_coedit_main_c_{uuid4().hex}")
    module_b = _load_module(f"realtime_coedit_main_d_{uuid4().hex}")

    with TestClient(module_a.app) as client_a, TestClient(module_b.app) as client_b:
        created = client_a.post(
            "/v1/v1/sessions",
            json={
                "document_id": "doc-ws",
                "initial_content": "initial",
                "classification": "internal",
            },
            headers=_headers(secret, "tenant-a"),
        )
        assert created.status_code == 200
        session_id = created.json()["session_id"]

        ws_a_url = (
            f"/v1/v1/ws/documents/doc-ws?session_id={session_id}&user_id=user-a&user_name=Alice"
        )
        ws_b_url = (
            f"/v1/v1/ws/documents/doc-ws?session_id={session_id}&user_id=user-b&user_name=Bob"
        )

        with (
            client_a.websocket_connect(ws_a_url) as ws_a,
            client_b.websocket_connect(ws_b_url) as ws_b,
        ):
            ws_a.receive_json()  # session_state
            ws_b.receive_json()  # session_state

            ws_a.send_json(
                {"type": "content_update", "content": "changed by node-a", "base_version": 1}
            )

            # drain until content update seen by node-b replica
            seen = False
            for _ in range(5):
                message = ws_b.receive_json()
                if message.get("type") == "content_update":
                    assert "changed by node-a" in message["content"]
                    seen = True
                    break
            assert seen


def test_healthz_checks_store_and_pubsub(monkeypatch) -> None:
    secret = "test-secret"
    monkeypatch.setenv("IDENTITY_JWT_SECRET", secret)
    monkeypatch.setenv("COEDIT_STORAGE_BACKEND", "inmemory")
    monkeypatch.setenv("COEDIT_STORAGE_NAMESPACE", f"health-{uuid4()}")

    module = _load_module(f"realtime_coedit_main_health_{uuid4().hex}")
    with TestClient(module.app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        body = response.json()
        assert body["dependencies"]["session_store"] == "ok"
        assert body["dependencies"]["pubsub"] == "ok"
