from __future__ import annotations

import httpx

from connectors.jira.src.main import JiraConfig, run_sync
from connectors.sdk.src.http_client import HttpClient


def test_jira_live_sync_maps_projects() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/api/3/project/search":
            return httpx.Response(
                200,
                json={
                    "values": [
                        {
                            "id": "1000",
                            "name": "Integration Project",
                            "archived": False,
                            "lead": {"displayName": "Ada Lovelace"},
                            "projectCategory": {"id": "program-1"},
                            "insight": {
                                "oldestIssueDate": "2024-01-01",
                                "lastIssueUpdateTime": "2024-01-02T12:00:00Z",
                            },
                        }
                    ],
                    "isLast": True,
                },
            )
        if request.url.path == "/rest/api/3/search":
            return httpx.Response(
                200,
                json={
                    "issues": [
                        {
                            "id": "2000",
                            "key": "PROJ-1",
                            "fields": {
                                "summary": "Create API integration",
                                "status": {"statusCategory": {"key": "indeterminate"}},
                                "assignee": {"displayName": "Grace Hopper"},
                                "created": "2024-01-03T10:00:00Z",
                                "updated": "2024-01-04T11:00:00Z",
                                "duedate": "2024-02-01",
                                "project": {"id": "1000"},
                                "issuetype": {"name": "Task"},
                            },
                        }
                    ],
                    "startAt": 0,
                    "maxResults": 50,
                    "total": 1,
                    "isLast": True,
                },
            )
        raise AssertionError(f"Unexpected path: {request.url.path}")

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
            "program_id": "program-1",
            "name": "Integration Project",
            "status": "execution",
            "start_date": "2024-01-01",
            "end_date": None,
            "owner": "Ada Lovelace",
            "classification": "internal",
            "created_at": "2024-01-02T12:00:00Z",
        },
        {
            "tenant_id": "tenant-demo",
            "id": "2000",
            "project_id": "1000",
            "title": "Create API integration",
            "type": "task",
            "status": "in_progress",
            "assigned_to": "Grace Hopper",
            "due_date": "2024-02-01",
            "classification": "internal",
            "created_at": "2024-01-03T10:00:00Z",
            "updated_at": "2024-01-04T11:00:00Z",
        },
    ]
