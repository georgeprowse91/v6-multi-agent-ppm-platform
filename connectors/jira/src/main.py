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
            projects.append(
                {
                    "source": "project",
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "status": "archived" if item.get("archived") else "active",
                    "start_date": None,
                    "end_date": None,
                    "owner": (item.get("lead") or {}).get("displayName"),
                }
            )
    return projects


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
