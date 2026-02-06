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
class SapConfig:
    instance_url: str
    username: str
    password: str
    client: str | None
    rate_limit_per_minute: int

    @classmethod
    def from_env(cls, rate_limit_per_minute: int) -> "SapConfig":
        instance_url = resolve_secret(os.getenv("SAP_URL"))
        username = resolve_secret(os.getenv("SAP_USERNAME"))
        password = resolve_secret(os.getenv("SAP_PASSWORD"))
        client = resolve_secret(os.getenv("SAP_CLIENT"))
        if not instance_url or not username or not password:
            raise ValueError("SAP_URL, SAP_USERNAME, and SAP_PASSWORD are required")
        return cls(
            instance_url=instance_url,
            username=username,
            password=password,
            client=client,
            rate_limit_per_minute=rate_limit_per_minute,
        )


def _build_client(config: SapConfig, transport: Any | None = None) -> HttpClient:
    token = f"{config.username}:{config.password}".encode("utf-8")
    auth_header = base64.b64encode(token).decode("utf-8")
    return HttpClient(
        base_url=config.instance_url,
        headers={"Authorization": f"Basic {auth_header}", "Accept": "application/json"},
        timeout=10.0,
        rate_limit_per_minute=config.rate_limit_per_minute,
        transport=transport,
    )


def _fetch_projects(client: HttpClient, client_id: str | None) -> list[dict[str, Any]]:
    endpoint = resolve_secret(os.getenv("SAP_PROJECTS_ENDPOINT")) or "/api/projects"
    params = {"client": client_id} if client_id else None
    response = client.get(endpoint, params=params)
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
                "name": item.get("name") or item.get("description"),
                "status": item.get("status") or item.get("lifecycle_status"),
                "start_date": item.get("start_date") or item.get("planned_start"),
                "end_date": item.get("end_date") or item.get("planned_finish"),
                "owner": item.get("owner") or item.get("manager"),
            }
        )
    return projects


def run_sync(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    client: HttpClient | None = None,
    config: SapConfig | None = None,
    include_schema: bool = False,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id, include_schema=include_schema)
    if not live:
        raise ValueError("Fixture path is required when live mode is disabled")
    rate_limit = runtime.manifest.sync.get("rate_limit_per_minute", 120)
    config = config or SapConfig.from_env(rate_limit)
    client = client or _build_client(config)
    records = _fetch_projects(client, config.client)
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


# New outbound hook placeholder. Later, this should send data to SAP via real API.
def send_to_external_system(records: list[dict[str, object]], tenant_id: str, *, include_schema: bool) -> None:
    """
    Placeholder outbound handler for SAP.
    This function currently logs the records to be written and performs no external calls.

    Args:
        records: Mapped records in the canonical schema.
        tenant_id: Tenant identifier.
        include_schema: Whether the mapped records include schema metadata.
    """
    # TODO: Implement SAP API calls here (e.g. using pyrfc or REST client).
    # For now, simply log the outbound payload for debugging.
    import logging
    logging.getLogger(__name__).info(
        "Outbound payload for SAP tenant %s (include_schema=%s): %s",
        tenant_id,
        include_schema,
        records,
    )
