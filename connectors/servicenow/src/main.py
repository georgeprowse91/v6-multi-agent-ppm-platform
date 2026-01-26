from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from connectors.sdk.src.auth import OAuth2TokenManager
from connectors.sdk.src.http_client import HttpClient
from connectors.sdk.src.runtime import ConnectorRuntime
from connectors.sdk.src.secrets import resolve_secret

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class ServiceNowConfig:
    instance_url: str
    token_url: str
    client_id: str
    client_secret: str
    refresh_token: str
    scope: str | None
    rate_limit_per_minute: int

    @classmethod
    def from_env(cls, manifest: dict[str, Any], rate_limit_per_minute: int) -> "ServiceNowConfig":
        instance_url = resolve_secret(os.getenv("SERVICENOW_INSTANCE_URL"))
        client_id = resolve_secret(os.getenv("SERVICENOW_CLIENT_ID"))
        client_secret = resolve_secret(os.getenv("SERVICENOW_CLIENT_SECRET"))
        refresh_token = resolve_secret(os.getenv("SERVICENOW_REFRESH_TOKEN"))
        token_url = resolve_secret(os.getenv("SERVICENOW_TOKEN_URL")) or manifest.get(
            "token_url"
        )
        scope = os.getenv("SERVICENOW_SCOPE")
        if not instance_url or not client_id or not client_secret or not refresh_token or not token_url:
            raise ValueError(
                "SERVICENOW_INSTANCE_URL, SERVICENOW_CLIENT_ID, SERVICENOW_CLIENT_SECRET, "
                "SERVICENOW_REFRESH_TOKEN, and SERVICENOW_TOKEN_URL are required"
            )
        return cls(
            instance_url=instance_url,
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            scope=scope,
            rate_limit_per_minute=rate_limit_per_minute,
        )


def _build_token_manager(
    config: ServiceNowConfig, token_client: HttpClient | None = None
) -> OAuth2TokenManager:
    return OAuth2TokenManager(
        token_url=config.token_url,
        client_id=config.client_id,
        client_secret=config.client_secret,
        refresh_token=config.refresh_token,
        scope=config.scope,
        http_client=token_client,
    )


def _build_api_client(
    config: ServiceNowConfig, access_token: str, transport: Any | None = None
) -> HttpClient:
    return HttpClient(
        base_url=config.instance_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        timeout=10.0,
        rate_limit_per_minute=config.rate_limit_per_minute,
        transport=transport,
    )


def _fetch_projects(client: HttpClient) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    params = {
        "sysparm_limit": 100,
        "sysparm_offset": 0,
        "sysparm_fields": "sys_id,short_description,state,start_date,end_date,manager",
    }
    for page in client.paginate_offset(
        "/api/now/table/pm_project",
        params=params,
        items_path="result",
        offset_param="sysparm_offset",
        limit_param="sysparm_limit",
        limit=100,
    ):
        for item in page:
            projects.append(
                {
                    "source": "project",
                    "id": item.get("sys_id"),
                    "name": item.get("short_description"),
                    "status": item.get("state"),
                    "start_date": item.get("start_date"),
                    "end_date": item.get("end_date"),
                    "owner": (item.get("manager") or {}).get("display_value")
                    if isinstance(item.get("manager"), dict)
                    else item.get("manager"),
                }
            )
    return projects


def run_sync(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    client: HttpClient | None = None,
    token_client: HttpClient | None = None,
    transport: Any | None = None,
    config: ServiceNowConfig | None = None,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id)

    rate_limit = runtime.manifest.sync.get("rate_limit_per_minute", 60)
    config = config or ServiceNowConfig.from_env(runtime.manifest.auth, rate_limit)
    token_client = token_client or HttpClient(
        base_url=config.instance_url,
        headers={"Accept": "application/json"},
        timeout=10.0,
        rate_limit_per_minute=config.rate_limit_per_minute,
        transport=transport,
    )
    token_manager = _build_token_manager(config, token_client=token_client)
    access_token = token_manager.get_access_token()
    api_client = client or _build_api_client(config, access_token, transport=transport)
    records = _fetch_projects(api_client)
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
