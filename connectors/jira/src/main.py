from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from connectors.sdk.src.http_client import HttpClient
from connectors.sdk.src.runtime import ConnectorRuntime
from connectors.sdk.src.secrets import resolve_secret

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class JiraConfig:
    instance_url: str
    email: str
    api_token: str
    rate_limit_per_minute: int

    @classmethod
    def from_env(cls, rate_limit_per_minute: int) -> "JiraConfig":
        instance_url = resolve_secret(os.getenv("JIRA_INSTANCE_URL"))
        email = resolve_secret(os.getenv("JIRA_EMAIL"))
        api_token = resolve_secret(os.getenv("JIRA_API_TOKEN"))
        if not instance_url or not email or not api_token:
            raise ValueError("JIRA_INSTANCE_URL, JIRA_EMAIL, and JIRA_API_TOKEN are required")
        return cls(
            instance_url=instance_url,
            email=email,
            api_token=api_token,
            rate_limit_per_minute=rate_limit_per_minute,
        )


def _build_client(config: JiraConfig, transport: Any | None = None) -> HttpClient:
    token = f"{config.email}:{config.api_token}".encode("utf-8")
    auth_header = base64.b64encode(token).decode("utf-8")
    return HttpClient(
        base_url=config.instance_url,
        headers={"Authorization": f"Basic {auth_header}", "Accept": "application/json"},
        timeout=10.0,
        rate_limit_per_minute=config.rate_limit_per_minute,
        transport=transport,
    )


def _project_status(archived: bool) -> str:
    return "closed" if archived else "execution"


def _issue_status(status_category: str | None) -> str:
    if status_category in {"done", "complete"}:
        return "done"
    if status_category in {"indeterminate", "in_progress"}:
        return "in_progress"
    if status_category in {"blocked"}:
        return "blocked"
    return "todo"


def _issue_type(name: str | None) -> str:
    if not name:
        return "task"
    normalized = name.lower()
    if "milestone" in normalized:
        return "milestone"
    if "deliverable" in normalized:
        return "deliverable"
    return "task"


def _fetch_projects(client: HttpClient) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []

    def is_last(data: dict[str, Any], items: list[dict[str, Any]]) -> bool:
        return bool(data.get("isLast")) or not items

    for page in client.paginate_offset(
        "/rest/api/3/project/search",
        params={},
        items_path="values",
        offset_param="startAt",
        limit_param="maxResults",
        limit=50,
        is_last_page=is_last,
    ):
        for item in page:
            insight = item.get("insight") or {}
            start_date = insight.get("oldestIssueDate") or "1970-01-01"
            created_at = insight.get("lastIssueUpdateTime") or "1970-01-01T00:00:00Z"
            program_id = (item.get("projectCategory") or {}).get("id") or "unassigned"
            projects.append(
                {
                    "source": "project",
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "status": _project_status(bool(item.get("archived"))),
                    "start_date": start_date,
                    "end_date": None,
                    "owner": (item.get("lead") or {}).get("displayName"),
                    "program_id": program_id,
                    "classification": "internal",
                    "created_at": created_at,
                }
            )
    return projects


def _fetch_issues(client: HttpClient) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    def is_last(data: dict[str, Any], items: list[dict[str, Any]]) -> bool:
        total = data.get("total", 0)
        start_at = data.get("startAt", 0)
        max_results = data.get("maxResults", len(items))
        return bool(data.get("isLast")) or start_at + max_results >= total

    for page in client.paginate_offset(
        "/rest/api/3/search",
        params={
            "jql": "order by updated DESC",
            "fields": "summary,status,assignee,created,updated,duedate,project,issuetype",
        },
        items_path="issues",
        offset_param="startAt",
        limit_param="maxResults",
        limit=50,
        is_last_page=is_last,
    ):
        for issue in page:
            fields = issue.get("fields") or {}
            status_category = (fields.get("status") or {}).get("statusCategory", {}).get("key")
            issues.append(
                {
                    "source": "work_item",
                    "id": issue.get("id") or issue.get("key"),
                    "project_id": (fields.get("project") or {}).get("id") or "unknown",
                    "title": fields.get("summary") or issue.get("key"),
                    "type": _issue_type((fields.get("issuetype") or {}).get("name")),
                    "status": _issue_status(status_category),
                    "assigned_to": (fields.get("assignee") or {}).get("displayName") or "unassigned",
                    "due_date": fields.get("duedate"),
                    "classification": "internal",
                    "created_at": fields.get("created") or "1970-01-01T00:00:00Z",
                    "updated_at": fields.get("updated"),
                }
            )
    return issues


def run_sync(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    client: HttpClient | None = None,
    config: JiraConfig | None = None,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id)

    rate_limit = runtime.manifest.sync.get("rate_limit_per_minute", 60)
    config = config or JiraConfig.from_env(rate_limit)
    client = client or _build_client(config)
    records = _fetch_projects(client)
    records.extend(_fetch_issues(client))
    return runtime.apply_mappings(records, tenant_id)


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
