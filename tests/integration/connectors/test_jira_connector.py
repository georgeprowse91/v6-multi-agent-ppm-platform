from __future__ import annotations

import httpx

from connectors.jira.src.main import JiraConfig, run_sync
from connectors.sdk.src.http_client import HttpClient


def test_jira_live_sync_maps_projects() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/api/3/project/search"
        return httpx.Response(
            200,
            json={
                "values": [
                    {
                        "id": "1000",
                        "name": "Integration Project",
                        "archived": False,
                        "lead": {"displayName": "Ada Lovelace"},
                    }
                ],
                "isLast": True,
            },
        )

    transport = httpx.MockTransport(handler)
    client = HttpClient(base_url="https://jira.example", transport=transport)
    config = JiraConfig(
        instance_url="https://jira.example",
        email="user@example.com",
        api_token="token",
        rate_limit_per_minute=120,
    )

    results = run_sync(None, "tenant-demo", live=True, client=client, config=config)

    assert results == [
        {
            "tenant_id": "tenant-demo",
            "id": "1000",
            "name": "Integration Project",
            "status": "active",
            "start_date": None,
            "end_date": None,
            "owner": "Ada Lovelace",
        }
    ]
