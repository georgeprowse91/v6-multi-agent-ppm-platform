from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

if not os.getenv("ENABLE_CONNECTOR_INTEGRATION_TESTS"):
    pytest.skip(
        "Connector integration tests require ENABLE_CONNECTOR_INTEGRATION_TESTS=1",
        allow_module_level=True,
    )

pytest.importorskip("opentelemetry")

import httpx

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.modules.pop("connectors", None)

from connectors.planview.src.main import PlanviewConfig, run_sync
from connectors.sdk.src.auth import OAuth2TokenManager
from connectors.sdk.src.http_client import HttpClient


def test_planview_live_sync_refreshes_token() -> None:
    calls = {"token": 0, "projects": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/token":
            calls["token"] += 1
            return httpx.Response(
                200,
                json={"access_token": f"token-{calls['token']}", "expires_in": 3600},
            )
        if request.url.path == "/api/v1/projects":
            calls["projects"] += 1
            if calls["projects"] == 1:
                return httpx.Response(401, json={"error": "unauthorized"})
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "pv-100",
                            "programId": "program-01",
                            "name": "Planview Build",
                            "status": "execution",
                            "startDate": "2024-01-05",
                            "endDate": "2024-06-30",
                            "owner": "pm-owner",
                            "classification": "internal",
                            "createdAt": "2024-01-01T08:00:00Z",
                        }
                    ],
                    "total": 1,
                    "offset": 0,
                    "limit": 50,
                },
            )
        raise AssertionError(f"Unexpected path: {request.url.path}")

    transport = httpx.MockTransport(handler)
    token_client = HttpClient(base_url="https://planview.example", transport=transport)
    token_manager = OAuth2TokenManager(
        token_url="https://planview.example/oauth/token",
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-token",
        scope="read",
        http_client=token_client,
    )
    client = HttpClient(base_url="https://planview.example", transport=transport)
    config = PlanviewConfig(
        instance_url="https://planview.example",
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-token",
        rate_limit_per_minute=120,
    )

    results = run_sync(
        None,
        "tenant-planview",
        live=True,
        client=client,
        config=config,
        token_manager=token_manager,
    )

    assert calls["token"] >= 2
    assert results == [
        {
            "tenant_id": "tenant-planview",
            "id": "pv-100",
            "program_id": "program-01",
            "name": "Planview Build",
            "status": "execution",
            "start_date": "2024-01-05",
            "end_date": "2024-06-30",
            "owner": "pm-owner",
            "classification": "internal",
            "created_at": "2024-01-01T08:00:00Z",
        }
    ]
