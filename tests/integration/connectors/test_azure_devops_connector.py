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

import json

import httpx

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.modules.pop("connectors", None)

from connectors.azure_devops.src.main import AzureDevOpsConfig, run_sync
from connectors.sdk.src.http_client import HttpClient


def test_azure_devops_live_sync_uses_continuation() -> None:
    calls = {"projects": 0, "wiql": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path.endswith("/_apis/projects"):
            calls["projects"] += 1
            if calls["projects"] == 1:
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
        if request.method == "POST" and path.endswith("/_apis/wit/wiql"):
            calls["wiql"] += 1
            return httpx.Response(200, json={"workItems": []})
        return httpx.Response(404, json={"message": "not found"})

    transport = httpx.MockTransport(handler)
    client = HttpClient(base_url="https://dev.azure.com/org", transport=transport)
    config = AzureDevOpsConfig(
        organization_url="https://dev.azure.com/org",
        pat="pat-token",
        rate_limit_per_minute=120,
    )

    results = run_sync(None, "tenant-demo", live=True, client=client, config=config)

    assert calls == {"projects": 2, "wiql": 2}
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


def test_azure_devops_syncs_work_items_in_batches() -> None:
    calls = {"projects": 0, "wiql": 0, "batch": 0}
    work_item_ids = list(range(1001, 2201))

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path.endswith("/_apis/projects"):
            calls["projects"] += 1
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "id": "proj-123",
                            "name": "Sample Project",
                            "state": "wellFormed",
                            "lastUpdateTime": "2024-02-01T00:00:00Z",
                        }
                    ]
                },
            )
        if request.method == "POST" and path.endswith("/_apis/wit/wiql"):
            calls["wiql"] += 1
            return httpx.Response(
                200,
                json={"workItems": [{"id": item_id} for item_id in work_item_ids]},
            )
        if request.method == "POST" and path.endswith("/_apis/wit/workitemsbatch"):
            calls["batch"] += 1
            payload = json.loads(request.content.decode("utf-8"))
            ids = payload.get("ids", [])
            return httpx.Response(
                200,
                json={
                    "value": [
                        {
                            "id": item_id,
                            "fields": {
                                "System.Id": item_id,
                                "System.Title": f"Work Item {item_id}",
                                "System.WorkItemType": "Task",
                                "System.State": "Active",
                                "System.AssignedTo": {"displayName": "Taylor Swift"},
                                "System.TeamProject": "Sample Project",
                                "System.CreatedDate": "2024-02-01T00:00:00Z",
                                "System.ChangedDate": "2024-02-02T00:00:00Z",
                                "System.AreaPath": "Sample Project",
                                "Microsoft.VSTS.Scheduling.DueDate": "2024-02-10",
                            },
                        }
                        for item_id in ids
                    ]
                },
            )
        return httpx.Response(404, json={"message": "not found"})

    transport = httpx.MockTransport(handler)
    client = HttpClient(base_url="https://dev.azure.com/org", transport=transport)
    config = AzureDevOpsConfig(
        organization_url="https://dev.azure.com/org",
        pat="pat-token",
        rate_limit_per_minute=120,
    )

    results = run_sync(None, "tenant-demo", live=True, client=client, config=config)

    assert calls == {"projects": 1, "wiql": 1, "batch": 6}
    work_items = [item for item in results if item["id"] in {1001, 2200}]
    assert work_items == [
        {
            "tenant_id": "tenant-demo",
            "id": 1001,
            "project_id": "proj-123",
            "title": "Work Item 1001",
            "type": "task",
            "status": "in_progress",
            "assigned_to": "Taylor Swift",
            "due_date": "2024-02-10",
            "classification": "Sample Project",
            "created_at": "2024-02-01T00:00:00Z",
            "updated_at": "2024-02-02T00:00:00Z",
        },
        {
            "tenant_id": "tenant-demo",
            "id": 2200,
            "project_id": "proj-123",
            "title": "Work Item 2200",
            "type": "task",
            "status": "in_progress",
            "assigned_to": "Taylor Swift",
            "due_date": "2024-02-10",
            "classification": "Sample Project",
            "created_at": "2024-02-01T00:00:00Z",
            "updated_at": "2024-02-02T00:00:00Z",
        },
    ]
