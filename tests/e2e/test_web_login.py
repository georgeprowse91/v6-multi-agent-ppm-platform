from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import jwt
from fastapi.testclient import TestClient


class MockResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("mock error")


class MockAsyncClient:
    def __init__(self, calls: list[dict], *args, **kwargs) -> None:
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, data=None, json=None, headers=None):
        self.calls.append(
            {"method": "post", "url": url, "headers": headers, "data": data, "json": json}
        )
        if url.endswith("/token"):
            return MockResponse({"access_token": "access-token", "id_token": "id-token"})
        if url.endswith("/workflows/start"):
            return MockResponse(
                {
                    "run_id": "run-123",
                    "workflow_id": json["workflow_id"],
                    "tenant_id": json["tenant_id"],
                    "status": "running",
                    "created_at": "now",
                    "updated_at": "now",
                }
            )
        return MockResponse({"ok": True})

    async def get(self, url, headers=None):
        self.calls.append({"method": "get", "url": url, "headers": headers})
        return MockResponse({"status": "healthy"})


def _load_web_app():
    module_path = Path(__file__).resolve().parents[2] / "apps" / "web" / "src" / "main.py"
    spec = spec_from_file_location("web_main", module_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_web_oidc_session_flow(monkeypatch) -> None:
    web = _load_web_app()
    calls: list[dict] = []

    def _mock_client(*args, **kwargs):
        return MockAsyncClient(calls, *args, **kwargs)

    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_AUTH_URL", "https://login.test/authorize")
    monkeypatch.setenv("OIDC_TOKEN_URL", "https://login.test/token")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "https://app.test/callback")
    monkeypatch.setenv("OIDC_INSECURE_SKIP_VERIFY", "true")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    monkeypatch.setenv("API_GATEWAY_URL", "https://api.test")
    monkeypatch.setenv("WORKFLOW_ENGINE_URL", "https://workflow.test")
    monkeypatch.setattr(web, "httpx", type("Httpx", (), {"AsyncClient": _mock_client}))

    token = jwt.encode(
        {
            "sub": "user-123",
            "tenant_id": "tenant-alpha",
            "roles": ["portfolio_admin"],
        },
        "secret",
        algorithm="HS256",
    )

    client = TestClient(web.app)

    login_response = client.get("/login", follow_redirects=False)
    assert login_response.status_code == 307
    location = login_response.headers["location"]
    params = parse_qs(urlparse(location).query)
    state = params["state"][0]

    async def _mock_exchange(code: str):
        return {"access_token": "access-token", "id_token": token}

    monkeypatch.setattr(web, "_exchange_code_for_token", _mock_exchange)

    callback_response = client.get(f"/callback?code=abc&state={state}", follow_redirects=False)
    assert callback_response.status_code == 307

    session_response = client.get("/session")
    assert session_response.json()["tenant_id"] == "tenant-alpha"

    status_response = client.get("/api/status")
    assert status_response.status_code == 200

    workflow_response = client.post("/api/workflows/start", json={"workflow_id": "intake-triage"})
    assert workflow_response.status_code == 200

    auth_calls = [call for call in calls if call["method"] in {"get", "post"}]
    assert any(
        call["headers"] and call["headers"].get("X-Tenant-ID") == "tenant-alpha"
        for call in auth_calls
    )
