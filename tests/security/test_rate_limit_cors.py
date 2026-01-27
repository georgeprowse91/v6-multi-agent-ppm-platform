from __future__ import annotations

import sys

import pytest
from fastapi.testclient import TestClient


def _fresh_app(monkeypatch, env: dict[str, str]):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    sys.modules.pop("api.main", None)
    sys.modules.pop("api.limiter", None)
    from api.main import app

    return app


def test_rate_limit_exceeded_returns_429(monkeypatch, auth_headers) -> None:
    app = _fresh_app(
        monkeypatch,
        {
            "ENVIRONMENT": "development",
            "RATE_LIMIT_DEFAULT": "1/minute",
            "RATE_LIMIT_STORAGE": "memory://",
        },
    )
    client = TestClient(app)
    response_ok = client.get("/api/v1/status", headers=auth_headers)
    response_limited = client.get("/api/v1/status", headers=auth_headers)
    assert response_ok.status_code == 200
    assert response_limited.status_code == 429


def test_wildcard_cors_blocked_in_production(monkeypatch) -> None:
    with pytest.raises(RuntimeError):
        _fresh_app(
            monkeypatch,
            {
                "ENVIRONMENT": "production",
                "ALLOWED_ORIGINS": "*",
            },
        )
