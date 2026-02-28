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
sys.modules.pop("integrations", None)

from connectors.servicenow.src.main import ServiceNowConfig, run_sync


def test_servicenow_live_sync_refreshes_token() -> None:
    calls = {"token": 0, "api": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth_token.do"):
            calls["token"] += 1
            return httpx.Response(
                200,
                json={
                    "access_token": "sn-access-token",
                    "refresh_token": "sn-refresh",
                    "expires_in": 3600,
                },
            )
        calls["api"] += 1
        return httpx.Response(
            200,
            json={
                "result": [
                    {
                        "sys_id": "proj-1",
                        "short_description": "ServiceNow Project",
                        "state": "active",
                        "start_date": "2024-02-01",
                        "end_date": "2024-12-31",
                        "manager": {"display_value": "Grace Hopper"},
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    config = ServiceNowConfig(
        instance_url="https://servicenow.example",
        token_url="https://servicenow.example/oauth_token.do",
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-token",
        scope="project.read",
        rate_limit_per_minute=120,
    )

    results = run_sync(
        None,
        "tenant-demo",
        live=True,
        config=config,
        transport=transport,
    )

    assert calls["token"] == 1
    assert calls["api"] == 1
    assert results == [
        {
            "tenant_id": "tenant-demo",
            "id": "proj-1",
            "name": "ServiceNow Project",
            "status": "active",
            "start_date": "2024-02-01",
            "end_date": "2024-12-31",
            "owner": "Grace Hopper",
        }
    ]
