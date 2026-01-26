from __future__ import annotations

import httpx

from connectors.azure_devops.src.main import AzureDevOpsConfig, run_sync
from connectors.sdk.src.http_client import HttpClient


def test_azure_devops_live_sync_uses_continuation() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "id": "proj-1",
                            "name": "AzDO Project One",
                            "state": "wellFormed",
                            "lastUpdateTime": "2024-01-15T00:00:00Z",
                        }
                    ]
                },
                headers={"x-ms-continuationtoken": "next"},
            )
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "id": "proj-2",
                        "name": "AzDO Project Two",
                        "state": "wellFormed",
                        "lastUpdateTime": "2024-01-20T00:00:00Z",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = HttpClient(base_url="https://dev.azure.com/org", transport=transport)
    config = AzureDevOpsConfig(
        organization_url="https://dev.azure.com/org",
        pat="pat-token",
        rate_limit_per_minute=120,
    )

    results = run_sync(None, "tenant-demo", live=True, client=client, config=config)

    assert calls["count"] == 2
    assert results == [
        {
            "tenant_id": "tenant-demo",
            "id": "proj-1",
            "name": "AzDO Project One",
            "status": "wellFormed",
            "start_date": "2024-01-15T00:00:00Z",
            "end_date": None,
            "owner": None,
        },
        {
            "tenant_id": "tenant-demo",
            "id": "proj-2",
            "name": "AzDO Project Two",
            "status": "wellFormed",
            "start_date": "2024-01-20T00:00:00Z",
            "end_date": None,
            "owner": None,
        },
    ]
