from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from integrations.connectors.sdk.src.auth import OAuth2TokenManager
from integrations.connectors.sdk.src.http_client import HttpClient, HttpClientError
from integrations.connectors.sdk.src.runtime import ConnectorRuntime
from integrations.connectors.sdk.src.secrets import fetch_keyvault_secret, resolve_secret

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class WorkdayConfig:
    api_url: str
    client_id: str
    client_secret: str
    refresh_token: str
    token_url: str
    rate_limit_per_minute: int

    @classmethod
    def from_env(cls, rate_limit_per_minute: int) -> "WorkdayConfig":
        api_url = resolve_secret(os.getenv("WORKDAY_API_URL"))
        keyvault_url = resolve_secret(os.getenv("WORKDAY_KEYVAULT_URL"))
        client_id = resolve_secret(os.getenv("WORKDAY_CLIENT_ID"))
        client_secret = resolve_secret(os.getenv("WORKDAY_CLIENT_SECRET"))
        refresh_token = resolve_secret(os.getenv("WORKDAY_REFRESH_TOKEN"))
        client_id_secret = resolve_secret(os.getenv("WORKDAY_CLIENT_ID_SECRET"))
        client_secret_secret = resolve_secret(os.getenv("WORKDAY_CLIENT_SECRET_SECRET"))
        refresh_token_secret = resolve_secret(os.getenv("WORKDAY_REFRESH_TOKEN_SECRET"))
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
        token_url = resolve_secret(os.getenv("WORKDAY_TOKEN_URL")) or ""
        if not token_url and api_url:
            token_url = f"{api_url.rstrip('/')}/ccx/oauth2/token"
        if not api_url or not client_id or not client_secret or not refresh_token or not token_url:
            raise ValueError(
                "WORKDAY_API_URL, WORKDAY_CLIENT_ID, WORKDAY_CLIENT_SECRET, "
                "WORKDAY_REFRESH_TOKEN, and WORKDAY_TOKEN_URL are required"
            )
        return cls(
            api_url=api_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            token_url=token_url,
            rate_limit_per_minute=rate_limit_per_minute,
        )


def _build_token_manager(config: WorkdayConfig) -> OAuth2TokenManager:
    keyvault_url = resolve_secret(os.getenv("WORKDAY_KEYVAULT_URL"))
    refresh_secret = resolve_secret(os.getenv("WORKDAY_REFRESH_TOKEN_SECRET"))
    client_secret_secret = resolve_secret(os.getenv("WORKDAY_CLIENT_SECRET_SECRET"))
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
    config: WorkdayConfig,
    token_manager: OAuth2TokenManager,
    transport: Any | None = None,
) -> HttpClient:
    client = HttpClient(
        base_url=config.api_url,
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


def _fetch_projects(client: HttpClient, token_manager: OAuth2TokenManager) -> list[dict[str, Any]]:
    endpoint = resolve_secret(os.getenv("WORKDAY_PROJECTS_ENDPOINT")) or "/projects"
    response = _request_with_refresh(client, token_manager, "GET", endpoint)
    data = response.json()
    items = data.get("items") if isinstance(data, dict) else data
    if items is None and isinstance(data, dict):
        items = data.get("projects")
    if not isinstance(items, list):
        return []
    projects: list[dict[str, Any]] = []
    for item in items:
        projects.append(
            {
                "source": "project",
                "id": item.get("id") or item.get("project_id"),
                "name": item.get("name") or item.get("title"),
                "status": item.get("status"),
                "start_date": item.get("start_date") or item.get("planned_start"),
                "end_date": item.get("end_date") or item.get("planned_end"),
                "owner": item.get("owner") or item.get("manager"),
            }
        )
    return projects


def _normalize_status(raw_status: str | None) -> str:
    if not raw_status:
        return "active"
    normalized = raw_status.lower()
    if normalized in {"terminated", "inactive", "separated"}:
        return "inactive"
    if normalized in {"leave", "on_leave"}:
        return "on_leave"
    return "active"


def _iso_from_date(value: str | None) -> str:
    if not value:
        return "1970-01-01T00:00:00Z"
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return "1970-01-01T00:00:00Z"


def _extract_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "items", "workers"):
            items = data.get(key)
            if isinstance(items, list):
                return items
    return []


def _fetch_workers(client: HttpClient, token_manager: OAuth2TokenManager) -> list[dict[str, Any]]:
    endpoint = resolve_secret(os.getenv("WORKDAY_WORKERS_ENDPOINT")) or "/ccx/api/v1/workers"
    response = _request_with_refresh(client, token_manager, "GET", endpoint, params={"limit": 200})
    data = response.json()
    workers = _extract_items(data)
    records: list[dict[str, Any]] = []
    for worker in workers:
        name = (
            worker.get("name")
            or worker.get("display_name")
            or worker.get("full_name")
            or worker.get("worker_name")
        )
        records.append(
            {
                "source": "resource",
                "id": worker.get("id") or worker.get("worker_id") or worker.get("employee_id"),
                "name": name,
                "role": worker.get("job_title") or worker.get("position") or "employee",
                "location": worker.get("location") or worker.get("work_location"),
                "status": _normalize_status(worker.get("status") or worker.get("worker_status")),
                "created_at": _iso_from_date(worker.get("hire_date") or worker.get("created_at")),
                "metadata": {
                    "email": worker.get("email"),
                    "department": worker.get("department"),
                },
            }
        )
    return records


def run_sync(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    client: HttpClient | None = None,
    config: WorkdayConfig | None = None,
    token_manager: OAuth2TokenManager | None = None,
    include_schema: bool = False,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id, include_schema=include_schema)
    if not live:
        raise ValueError("Fixture path is required when live mode is disabled")
    rate_limit = runtime.manifest.sync.get("rate_limit_per_minute", 120)
    config = config or WorkdayConfig.from_env(rate_limit)
    token_manager = token_manager or _build_token_manager(config)
    client = client or _build_client(config, token_manager)
    records = _fetch_projects(client, token_manager)
    records.extend(_fetch_workers(client, token_manager))
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
