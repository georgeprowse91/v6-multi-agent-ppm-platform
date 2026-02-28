from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from connectors.sdk.src.http_client import HttpClient
from connectors.sdk.src.runtime import ConnectorRuntime
from connector_secrets import resolve_secret

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class AzureDevOpsConfig:
    organization_url: str
    pat: str
    rate_limit_per_minute: int

    @classmethod
    def from_env(cls, rate_limit_per_minute: int) -> "AzureDevOpsConfig":
        organization_url = resolve_secret(os.getenv("AZURE_DEVOPS_ORG_URL"))
        pat = resolve_secret(os.getenv("AZURE_DEVOPS_PAT"))
        if not organization_url or not pat:
            raise ValueError("AZURE_DEVOPS_ORG_URL and AZURE_DEVOPS_PAT are required")
        return cls(
            organization_url=organization_url,
            pat=pat,
            rate_limit_per_minute=rate_limit_per_minute,
        )


def _build_client(config: AzureDevOpsConfig, transport: Any | None = None) -> HttpClient:
    token = f":{config.pat}".encode("utf-8")
    auth_header = base64.b64encode(token).decode("utf-8")
    return HttpClient(
        base_url=config.organization_url,
        headers={"Authorization": f"Basic {auth_header}", "Accept": "application/json"},
        timeout=10.0,
        rate_limit_per_minute=config.rate_limit_per_minute,
        transport=transport,
    )


def _fetch_projects(client: HttpClient) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    params = {"api-version": "7.0", "$top": 100}
    for page in client.paginate_continuation(
        "/_apis/projects",
        params=params,
        items_path="value",
        continuation_header="x-ms-continuationtoken",
        continuation_param="continuationToken",
    ):
        for item in page:
            projects.append(
                {
                    "source": "project",
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "status": item.get("state"),
                    "start_date": item.get("lastUpdateTime"),
                    "end_date": None,
                    "owner": None,
                }
            )
    return projects


def _work_item_status(state: str | None) -> str:
    if not state:
        return "todo"
    normalized = state.lower()
    if any(token in normalized for token in ["done", "closed", "resolved", "completed"]):
        return "done"
    if any(token in normalized for token in ["active", "in progress", "implementing", "committed"]):
        return "in_progress"
    if any(token in normalized for token in ["blocked", "removed"]):
        return "blocked"
    return "todo"


def _work_item_type(name: str | None) -> str:
    if not name:
        return "task"
    normalized = name.lower()
    if "milestone" in normalized:
        return "milestone"
    if "epic" in normalized or "feature" in normalized:
        return "deliverable"
    return "task"


def _chunked(values: list[int], size: int) -> list[list[int]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def _fetch_work_items(client: HttpClient, projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    work_items: list[dict[str, Any]] = []
    project_lookup = {
        project["name"]: project["id"] for project in projects if project.get("source") == "project"
    }
    wiql_query = (
        "SELECT [System.Id] FROM WorkItems "
        "WHERE [System.TeamProject] = @project "
        "ORDER BY [System.ChangedDate] DESC"
    )
    batch_fields = [
        "System.Id",
        "System.Title",
        "System.WorkItemType",
        "System.State",
        "System.AssignedTo",
        "System.TeamProject",
        "System.CreatedDate",
        "System.ChangedDate",
        "System.AreaPath",
        "Microsoft.VSTS.Scheduling.DueDate",
    ]

    for project in projects:
        if project.get("source") != "project":
            continue
        project_name = project.get("name")
        if not project_name:
            continue
        response = client.post(
            f"/{project_name}/_apis/wit/wiql",
            params={"api-version": "7.0"},
            json={"query": wiql_query},
        )
        data = response.json()
        work_item_refs = data.get("workItems") or []
        ids = [item.get("id") for item in work_item_refs if item.get("id") is not None]
        for chunk in _chunked(ids, 200):
            batch_response = client.post(
                "/_apis/wit/workitemsbatch",
                params={"api-version": "7.0"},
                json={"ids": chunk, "fields": batch_fields, "errorPolicy": "Omit"},
            )
            batch_data = batch_response.json()
            for item in batch_data.get("value", []):
                fields = item.get("fields") or {}
                assigned_to = fields.get("System.AssignedTo")
                if isinstance(assigned_to, dict):
                    assigned_to = assigned_to.get("displayName") or assigned_to.get("uniqueName")
                team_project = fields.get("System.TeamProject") or project_name
                work_items.append(
                    {
                        "source": "work_item",
                        "id": item.get("id"),
                        "project_id": project_lookup.get(team_project, team_project),
                        "title": fields.get("System.Title") or f"Work Item {item.get('id')}",
                        "type": _work_item_type(fields.get("System.WorkItemType")),
                        "status": _work_item_status(fields.get("System.State")),
                        "assigned_to": assigned_to or "unassigned",
                        "due_date": fields.get("Microsoft.VSTS.Scheduling.DueDate"),
                        "classification": fields.get("System.AreaPath") or "internal",
                        "created_at": fields.get("System.CreatedDate") or "1970-01-01T00:00:00Z",
                        "updated_at": fields.get("System.ChangedDate"),
                    }
                )
    return work_items


def run_sync(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    client: HttpClient | None = None,
    config: AzureDevOpsConfig | None = None,
    include_schema: bool = False,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id, include_schema=include_schema)

    rate_limit = runtime.manifest.sync.get("rate_limit_per_minute", 60)
    config = config or AzureDevOpsConfig.from_env(rate_limit)
    client = client or _build_client(config)
    records = _fetch_projects(client)
    records.extend(_fetch_work_items(client, records))
    return runtime.apply_mappings(records, tenant_id, include_schema=include_schema)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Run connector sync against a fixture file")
    parser.add_argument("fixture", nargs="?", type=str, help="Path to fixture JSON")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--live", action="store_true", help="Run against live API using env vars")
    args = parser.parse_args()

    fixture = Path(args.fixture) if args.fixture else None
    output = run_sync(fixture, args.tenant, live=args.live)
    print(json.dumps(output, indent=2))
