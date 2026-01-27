from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from connectors.sdk.src.auth import OAuth2TokenManager
from connectors.sdk.src.http_client import HttpClient, HttpClientError
from connectors.sdk.src.runtime import ConnectorRuntime
from connectors.sdk.src.secrets import resolve_secret

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class PlanviewConfig:
    instance_url: str
    client_id: str
    client_secret: str
    refresh_token: str
    rate_limit_per_minute: int

    @classmethod
    def from_env(cls, rate_limit_per_minute: int) -> "PlanviewConfig":
        instance_url = resolve_secret(os.getenv("PLANVIEW_INSTANCE_URL"))
        client_id = resolve_secret(os.getenv("PLANVIEW_CLIENT_ID"))
        client_secret = resolve_secret(os.getenv("PLANVIEW_CLIENT_SECRET"))
        refresh_token = resolve_secret(os.getenv("PLANVIEW_REFRESH_TOKEN"))
        if not instance_url or not client_id or not client_secret or not refresh_token:
            raise ValueError(
                "PLANVIEW_INSTANCE_URL, PLANVIEW_CLIENT_ID, PLANVIEW_CLIENT_SECRET, and "
                "PLANVIEW_REFRESH_TOKEN are required"
            )
        return cls(
            instance_url=instance_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            rate_limit_per_minute=rate_limit_per_minute,
        )


def _build_token_manager(config: PlanviewConfig, token_url: str, scope: str | None) -> OAuth2TokenManager:
    return OAuth2TokenManager(
        token_url=token_url,
        client_id=config.client_id,
        client_secret=config.client_secret,
        refresh_token=config.refresh_token,
        scope=scope,
    )


def _build_client(
    config: PlanviewConfig,
    token_manager: OAuth2TokenManager,
    transport: Any | None = None,
) -> HttpClient:
    client = HttpClient(
        base_url=config.instance_url,
        headers={"Accept": "application/json"},
        timeout=10.0,
        rate_limit_per_minute=config.rate_limit_per_minute,
        transport=transport,
    )
    client.set_header("Authorization", f"Bearer {token_manager.get_access_token()}")
    return client


def _refresh_if_unauthorized(
    client: HttpClient,
    token_manager: OAuth2TokenManager,
    method: str,
    url: str,
    **kwargs: Any,
) -> Any:
    try:
        return client.request(method, url, **kwargs)
    except HttpClientError as exc:
        if exc.status_code != 401:
            raise
    token_manager.refresh()
    client.set_header("Authorization", f"Bearer {token_manager.get_access_token()}")
    return client.request(method, url, **kwargs)


def _fetch_projects(client: HttpClient, token_manager: OAuth2TokenManager) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    offset = 0
    limit = 50
    while True:
        response = _refresh_if_unauthorized(
            client,
            token_manager,
            "GET",
            "/api/v1/projects",
            params={"offset": offset, "limit": limit},
        )
        data = response.json()
        items = data.get("items", [])
        for item in items:
            projects.append(
                {
                    "source": "project",
                    "id": item.get("id"),
                    "program_id": item.get("programId") or "unassigned",
                    "name": item.get("name"),
                    "status": item.get("status") or "execution",
                    "start_date": item.get("startDate") or "1970-01-01",
                    "end_date": item.get("endDate"),
                    "owner": item.get("owner"),
                    "classification": item.get("classification") or "internal",
                    "created_at": item.get("createdAt") or "1970-01-01T00:00:00Z",
                }
            )
        total = data.get("total", 0)
        offset += limit
        if not items or offset >= total:
            return projects


def run_sync(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    client: HttpClient | None = None,
    config: PlanviewConfig | None = None,
    token_manager: OAuth2TokenManager | None = None,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id)

    rate_limit = runtime.manifest.sync.get("rate_limit_per_minute", 200)
    config = config or PlanviewConfig.from_env(rate_limit)
    auth_config = runtime.manifest.auth
    token_url = auth_config.get("token_url")
    if not token_url:
        raise ValueError("Planview manifest missing token_url for OAuth2")
    scope = None
    scopes = auth_config.get("scopes")
    if isinstance(scopes, list) and scopes:
        scope = " ".join(scopes)
    token_manager = token_manager or _build_token_manager(config, token_url, scope)
    if client is None:
        client = _build_client(config, token_manager)
    else:
        client.set_header("Authorization", f"Bearer {token_manager.get_access_token()}")
    records = _fetch_projects(client, token_manager)
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
