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


def run_sync(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    client: HttpClient | None = None,
    config: AzureDevOpsConfig | None = None,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id)

    rate_limit = runtime.manifest.sync.get("rate_limit_per_minute", 60)
    config = config or AzureDevOpsConfig.from_env(rate_limit)
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
