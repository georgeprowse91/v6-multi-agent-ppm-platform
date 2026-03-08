from __future__ import annotations

from types import SimpleNamespace

import pytest
from api.middleware import security
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.testclient import TestClient


@pytest.mark.anyio
async def test_auth_tenant_middleware_missing_headers_returns_401():
    app = FastAPI()
    middleware = security.AuthTenantMiddleware(app)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/agents",
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
    }

    async def _receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(scope, receive=_receive)

    async def call_next(_request):
        return JSONResponse({"ok": True})

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 401


@pytest.mark.anyio
async def test_auth_tenant_middleware_deny_allow_matrix(monkeypatch):
    app = FastAPI()
    middleware = security.AuthTenantMiddleware(app)

    async def _valid_claims(_token: str):
        return {"sub": "user-1", "tenant_id": "tenant-a", "roles": ["viewer"]}

    async def _allow(*_args, **_kwargs):
        return None

    async def _deny(*_args, **_kwargs):
        raise security.HTTPException(status_code=403, detail="RBAC denied")

    monkeypatch.setattr(security, "_validate_jwt", _valid_claims)
    monkeypatch.setattr(security, "_evaluate_abac", _allow)

    async def _call_next(_request):
        return JSONResponse({"ok": True})

    allow_scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/agents",
        "headers": [
            (b"authorization", b"Bearer token"),
            (b"x-tenant-id", b"tenant-a"),
        ],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
    }
    monkeypatch.setattr(security, "_evaluate_rbac", _allow)

    async def _receive_allow():
        return {"type": "http.request", "body": b"", "more_body": False}

    response = await middleware.dispatch(Request(allow_scope, receive=_receive_allow), _call_next)
    assert response.status_code == 200

    deny_scope = dict(allow_scope)
    monkeypatch.setattr(security, "_evaluate_rbac", _deny)

    async def _receive_deny():
        return {"type": "http.request", "body": b"", "more_body": False}

    denied = await middleware.dispatch(Request(deny_scope, receive=_receive_deny), _call_next)
    assert denied.status_code == 403


def test_field_masking_and_dlp_redaction_applied():
    field_cfg = {
        "fields": {
            "project": {
                "budget": {"allowed_roles": ["finance"]},
                "credentials.token": {"allowed_roles": ["security"]},
            }
        }
    }

    payload = {
        "project": {
            "budget": 50000,
            "credentials": {"token": "secret-token"},
            "name": "Roadmap",
        }
    }

    redacted = security._mask_fields(payload, field_cfg, roles=["viewer"])

    assert redacted["project"]["budget"] == "REDACTED"
    assert redacted["project"]["credentials"]["token"] == "REDACTED"
    assert redacted["project"]["name"] == "Roadmap"


def test_field_masking_middleware_keeps_response_shape(monkeypatch):
    app = FastAPI()
    app.add_middleware(security.FieldMaskingMiddleware)

    @app.get("/payload")
    async def payload_endpoint():
        return {
            "project": {"budget": 42, "credentials": {"token": "abc"}, "name": "demo"},
            "status": "ok",
        }

    monkeypatch.setattr(
        security,
        "_load_rbac",
        lambda: (
            {},
            {
                "fields": {
                    "project": {
                        "budget": {"allowed_roles": ["finance"]},
                        "credentials.token": {"allowed_roles": ["security"]},
                    }
                }
            },
        ),
    )

    with TestClient(app) as client:
        response = client.get("/payload")

    # middleware should bypass when auth context is missing
    assert response.status_code == 200
    assert response.json()["project"]["budget"] == 42


def test_required_permission_mapping_for_agents_and_query_routes():
    request_agents = SimpleNamespace(url=SimpleNamespace(path="/v1/agents"), method="GET")
    request_query = SimpleNamespace(url=SimpleNamespace(path="/v1/query"), method="POST")

    assert security._required_permission(request_agents) == "workflow.read"
    assert security._required_permission(request_query) == "workflow.execute"
