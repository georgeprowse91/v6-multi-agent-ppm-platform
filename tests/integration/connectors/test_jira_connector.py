from __future__ import annotations

import httpx

from connectors.jira.src.main import JiraConfig, run_sync, run_write
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


def test_jira_live_write_creates_issue() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/rest/api/3/myself":
            return httpx.Response(200, json={"displayName": "Tester"})
        if request.url.path == "/rest/api/3/issue" and request.method == "POST":
            return httpx.Response(201, json={"id": "3000", "key": "PROJ-9"})
        raise AssertionError(f"Unexpected path: {request.method} {request.url.path}")

    transport = httpx.MockTransport(handler)
    client = HttpClient(base_url="https://jira.example", transport=transport)
    config = JiraConfig(
        instance_url="https://jira.example",
        email="user@example.com",
        api_token="token",
        rate_limit_per_minute=120,
    )

    payload = [
        {
            "summary": "New connector issue",
            "project_key": "PROJ",
            "issue_type": "Task",
            "description": "Create from PPM",
        }
    ]

    results = run_write(
        None,
        "tenant-demo",
        live=True,
        client=client,
        config=config,
        data=payload,
    )

    assert results == [{"id": "3000", "key": "PROJ-9", "status": None}]
    assert any(request.url.path == "/rest/api/3/myself" for request in requests)


def test_jira_live_write_updates_issue_status_and_detects_conflict() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/rest/api/3/myself":
            return httpx.Response(200, json={"displayName": "Tester"})
        if request.url.path == "/rest/api/3/issue/PROJ-1":
            return httpx.Response(
                200,
                json={
                    "id": "1001",
                    "key": "PROJ-1",
                    "fields": {"updated": "2024-01-01T00:00:00Z", "status": {"name": "To Do"}},
                },
            )
        if request.url.path == "/rest/api/3/issue/PROJ-2":
            return httpx.Response(
                200,
                json={
                    "id": "1002",
                    "key": "PROJ-2",
                    "fields": {"updated": "2024-01-02T00:00:00Z", "status": {"name": "To Do"}},
                },
            )
        if request.url.path.endswith("/transitions") and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "transitions": [
                        {"id": "31", "to": {"name": "Done"}},
                    ]
                },
            )
        if request.url.path.endswith("/transitions") and request.method == "POST":
            return httpx.Response(204)
        raise AssertionError(f"Unexpected path: {request.method} {request.url.path}")

    transport = httpx.MockTransport(handler)
    client = HttpClient(base_url="https://jira.example", transport=transport)
    config = JiraConfig(
        instance_url="https://jira.example",
        email="user@example.com",
        api_token="token",
        rate_limit_per_minute=120,
    )

    payload = [
        {"key": "PROJ-1", "status": "done", "updated_at": "2024-01-01T00:00:00Z"},
        {"key": "PROJ-2", "status": "done", "updated_at": "2024-01-01T00:00:00Z"},
    ]

    results = run_write(
        None,
        "tenant-demo",
        live=True,
        client=client,
        config=config,
        data=payload,
    )

    assert results[0] == {"id": "1001", "key": "PROJ-1", "status": "done"}
    assert results[1]["conflict"] is True
    assert results[1]["server_updated"] == "2024-01-02T00:00:00Z"
    assert any(
        request.url.path.endswith("/transitions") and request.method == "POST"
        for request in requests
    )
