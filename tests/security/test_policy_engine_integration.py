from __future__ import annotations

import jwt
from fastapi.testclient import TestClient


class DummyResponse:
    def __init__(self, status_code: int, payload: dict[str, str]):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("bad status")

    def json(self):
        return self._payload


class DummyAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return DummyResponse(200, {"decision": "deny"})


def test_policy_engine_denies(monkeypatch) -> None:
    monkeypatch.setenv("IDENTITY_JWT_SECRET", "test-secret")
    monkeypatch.setenv("POLICY_ENGINE_URL", "http://policy")
    monkeypatch.setenv("POLICY_ENGINE_SERVICE_TOKEN", "service-token")
    monkeypatch.setattr("api.middleware.security.httpx.AsyncClient", DummyAsyncClient)

    token = jwt.encode(
        {
            "sub": "user-123",
            "roles": ["portfolio_admin"],
            "aud": "ppm-platform",
            "iss": "https://issuer.example.com",
            "tenant_id": "tenant-alpha",
        },
        "test-secret",
        algorithm="HS256",
    )

    from api.main import app

    client = TestClient(app)
    response = client.get(
        "/api/v1/status",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-alpha"},
    )
    assert response.status_code == 403
