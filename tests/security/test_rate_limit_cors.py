from __future__ import annotations

import importlib.util

import pytest
from api.cors import ALLOWED_CORS_HEADERS, ALLOWED_CORS_METHODS, get_allowed_origins
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient


def test_wildcard_cors_blocked_when_credentials_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")

    with pytest.raises(Exception, match="Wildcard CORS origins are not permitted"):
        get_allowed_origins("development")


def _cors_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS_TEST", "http://localhost:3000")
    app = FastAPI()

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins("test"),
        allow_credentials=True,
        allow_methods=ALLOWED_CORS_METHODS,
        allow_headers=ALLOWED_CORS_HEADERS,
    )
    return TestClient(app)


def test_cors_preflight_blocks_disallowed_origin(monkeypatch) -> None:
    client = _cors_client(monkeypatch)
    response = client.options(
        "/healthz",
        headers={
            "Origin": "https://malicious.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400
    assert response.text == "Disallowed CORS origin"


def test_cors_preflight_blocks_disallowed_method(monkeypatch) -> None:
    client = _cors_client(monkeypatch)
    response = client.options(
        "/healthz",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "TRACE",
        },
    )
    assert response.status_code == 400
    assert response.text == "Disallowed CORS method"


def test_cors_preflight_blocks_disallowed_header(monkeypatch) -> None:
    client = _cors_client(monkeypatch)
    response = client.options(
        "/healthz",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-untrusted-header",
        },
    )
    assert response.status_code == 400
    assert response.text == "Disallowed CORS headers"


def test_rate_limit_exceeded_returns_429(monkeypatch, auth_headers) -> None:
    if (
        importlib.util.find_spec("slowapi") is None
        or importlib.util.find_spec("cryptography") is None
    ):
        pytest.skip("slowapi/cryptography dependencies are unavailable in this environment")

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("RATE_LIMIT_DEFAULT", "1/minute")
    monkeypatch.setenv("RATE_LIMIT_STORAGE", "memory://")

    import sys

    sys.modules.pop("api.main", None)
    sys.modules.pop("api.limiter", None)

    from api.main import app

    client = TestClient(app)
    response_ok = client.get("/v1/status", headers=auth_headers)
    response_limited = client.get("/v1/status", headers=auth_headers)
    assert response_ok.status_code == 200
    assert response_limited.status_code == 429
