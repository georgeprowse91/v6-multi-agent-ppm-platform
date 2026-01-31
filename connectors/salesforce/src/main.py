from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from connectors.sdk.src.auth import OAuth2TokenManager
from connectors.sdk.src.http_client import HttpClient, HttpClientError
from connectors.sdk.src.runtime import ConnectorRuntime
from connectors.sdk.src.secrets import fetch_keyvault_secret, resolve_secret

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class SalesforceConfig:
    instance_url: str
    client_id: str
    client_secret: str
    refresh_token: str
    token_url: str
    rate_limit_per_minute: int

    @classmethod
    def from_env(cls, token_url: str, rate_limit_per_minute: int) -> "SalesforceConfig":
        instance_url = resolve_secret(os.getenv("SALESFORCE_INSTANCE_URL"))
        keyvault_url = resolve_secret(os.getenv("SALESFORCE_KEYVAULT_URL"))
        client_id = resolve_secret(os.getenv("SALESFORCE_CLIENT_ID"))
        client_secret = resolve_secret(os.getenv("SALESFORCE_CLIENT_SECRET"))
        refresh_token = resolve_secret(os.getenv("SALESFORCE_REFRESH_TOKEN"))
        client_id_secret = resolve_secret(os.getenv("SALESFORCE_CLIENT_ID_SECRET"))
        client_secret_secret = resolve_secret(os.getenv("SALESFORCE_CLIENT_SECRET_SECRET"))
        refresh_token_secret = resolve_secret(os.getenv("SALESFORCE_REFRESH_TOKEN_SECRET"))
        client_id = (
            fetch_keyvault_secret(keyvault_url, client_id_secret) if client_id_secret else client_id
        ) or client_id
        client_secret = (
            fetch_keyvault_secret(keyvault_url, client_secret_secret)
            if client_secret_secret
            else client_secret
        ) or client_secret
        refresh_token = (
            fetch_keyvault_secret(keyvault_url, refresh_token_secret)
            if refresh_token_secret
            else refresh_token
        ) or refresh_token
        if not instance_url or not client_id or not client_secret or not refresh_token:
            raise ValueError(
                "SALESFORCE_INSTANCE_URL, SALESFORCE_CLIENT_ID, SALESFORCE_CLIENT_SECRET, "
                "and SALESFORCE_REFRESH_TOKEN are required"
            )
        return cls(
            instance_url=instance_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            token_url=token_url,
            rate_limit_per_minute=rate_limit_per_minute,
        )


def _build_token_manager(config: SalesforceConfig) -> OAuth2TokenManager:
    keyvault_url = resolve_secret(os.getenv("SALESFORCE_KEYVAULT_URL"))
    refresh_secret = resolve_secret(os.getenv("SALESFORCE_REFRESH_TOKEN_SECRET"))
    client_secret_secret = resolve_secret(os.getenv("SALESFORCE_CLIENT_SECRET_SECRET"))
    return OAuth2TokenManager(
        token_url=config.token_url,
        client_id=config.client_id,
        client_secret=config.client_secret,
        refresh_token=config.refresh_token,
        keyvault_url=keyvault_url,
        refresh_token_secret_name=refresh_secret,
        client_secret_secret_name=client_secret_secret,
    )


def _build_client(
    config: SalesforceConfig,
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


def _request_with_refresh(
    client: HttpClient,
    token_manager: OAuth2TokenManager,
    method: str,
    url: str,
    **kwargs: Any,
) -> Any:
    client.set_header("Authorization", f"Bearer {token_manager.get_access_token()}")
    try:
        return client.request(method, url, **kwargs)
    except HttpClientError as exc:
        if exc.status_code != 401:
            raise
    token_manager.refresh()
    client.set_header("Authorization", f"Bearer {token_manager.get_access_token()}")
    return client.request(method, url, **kwargs)


def _fetch_projects(
    client: HttpClient, token_manager: OAuth2TokenManager
) -> list[dict[str, Any]]:
    endpoint = resolve_secret(os.getenv("SALESFORCE_PROJECTS_ENDPOINT")) or (
        "/services/data/v57.0/sobjects/Project__c"
    )
    response = _request_with_refresh(client, token_manager, "GET", endpoint)
    data = response.json()
    records = data.get("records") if isinstance(data, dict) else data
    if records is None and isinstance(data, dict):
        records = data.get("items")
    if not isinstance(records, list):
        return []
    projects: list[dict[str, Any]] = []
    for item in records:
        projects.append(
            {
                "source": "project",
                "id": item.get("Id") or item.get("id"),
                "name": item.get("Name") or item.get("name"),
                "status": item.get("Status__c") or item.get("status"),
                "start_date": item.get("Start_Date__c") or item.get("start_date"),
                "end_date": item.get("End_Date__c") or item.get("end_date"),
                "owner": (item.get("Owner") or {}).get("Name")
                if isinstance(item.get("Owner"), dict)
                else None,
            }
        )
    return projects

def run_sync(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    client: HttpClient | None = None,
    config: SalesforceConfig | None = None,
    token_manager: OAuth2TokenManager | None = None,
    include_schema: bool = False,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id, include_schema=include_schema)
    if not live:
        raise ValueError("Fixture path is required when live mode is disabled")
    token_url = runtime.manifest.auth.get("token_url") or ""
    rate_limit = runtime.manifest.sync.get("rate_limit_per_minute", 300)
    config = config or SalesforceConfig.from_env(token_url, rate_limit)
    token_manager = token_manager or _build_token_manager(config)
    client = client or _build_client(config, token_manager)
    records = _fetch_projects(client, token_manager)
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
