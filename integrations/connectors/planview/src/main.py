from __future__ import annotations

import os
from dataclasses import dataclass
from fastapi import FastAPI
from pathlib import Path
from typing import Any

from integrations.connectors.sdk.src.auth import OAuth2TokenManager
from integrations.connectors.sdk.src.http_client import HttpClient, HttpClientError
from integrations.connectors.sdk.src.runtime import ConnectorRuntime
from integrations.connectors.sdk.src.secrets import fetch_keyvault_secret, resolve_secret

from integrations.connectors.integration import IntegrationAuthType, IntegrationConfig, PlanviewMcpConnector

from .mappers import map_to_planview

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
        keyvault_url = resolve_secret(os.getenv("PLANVIEW_KEYVAULT_URL"))
        client_id = resolve_secret(os.getenv("PLANVIEW_CLIENT_ID"))
        client_secret = resolve_secret(os.getenv("PLANVIEW_CLIENT_SECRET"))
        refresh_token = resolve_secret(os.getenv("PLANVIEW_REFRESH_TOKEN"))
        client_id_secret = resolve_secret(os.getenv("PLANVIEW_CLIENT_ID_SECRET"))
        client_secret_secret = resolve_secret(os.getenv("PLANVIEW_CLIENT_SECRET_SECRET"))
        refresh_token_secret = resolve_secret(os.getenv("PLANVIEW_REFRESH_TOKEN_SECRET"))
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
    keyvault_url = resolve_secret(os.getenv("PLANVIEW_KEYVAULT_URL"))
    refresh_secret = resolve_secret(os.getenv("PLANVIEW_REFRESH_TOKEN_SECRET"))
    client_secret_secret = resolve_secret(os.getenv("PLANVIEW_CLIENT_SECRET_SECRET"))
    return OAuth2TokenManager(
        token_url=token_url,
        client_id=config.client_id,
        client_secret=config.client_secret,
        refresh_token=config.refresh_token,
        scope=scope,
        keyvault_url=keyvault_url,
        refresh_token_secret_name=refresh_secret,
        client_secret_secret_name=client_secret_secret,
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
    include_schema: bool = False,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id, include_schema=include_schema)

    use_mcp = _should_use_mcp()
    if live and use_mcp:
        mcp_connector = _build_mcp_connector()
        records = mcp_connector.list_projects()
        return runtime.apply_mappings(records, tenant_id, include_schema=include_schema)

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
    return runtime.apply_mappings(records, tenant_id, include_schema=include_schema)


def _build_mcp_connector() -> PlanviewMcpConnector:
    tool_map = {
        "list_projects": "planview.listProjects",
        "create_work_item": "planview.createWorkItem",
    }
    config = IntegrationConfig(
        system="planview",
        base_url=resolve_secret(os.getenv("PLANVIEW_INSTANCE_URL")) or "",
        auth_type=IntegrationAuthType.NONE,
        mcp_server_url=resolve_secret(os.getenv("PLANVIEW_MCP_SERVER_URL")),
        mcp_server_id=resolve_secret(os.getenv("PLANVIEW_MCP_SERVER_ID")) or "planview",
        mcp_client_id=resolve_secret(os.getenv("PLANVIEW_MCP_CLIENT_ID")),
        mcp_client_secret=resolve_secret(os.getenv("PLANVIEW_MCP_CLIENT_SECRET")),
        mcp_scope=resolve_secret(os.getenv("PLANVIEW_MCP_SCOPE")),
        mcp_api_key=resolve_secret(os.getenv("PLANVIEW_MCP_API_KEY")),
        mcp_api_key_header=resolve_secret(os.getenv("PLANVIEW_MCP_API_KEY_HEADER")),
        mcp_oauth_token=resolve_secret(os.getenv("PLANVIEW_MCP_OAUTH_TOKEN")),
        mcp_tool_map=tool_map,
        prefer_mcp=True,
    )
    return PlanviewMcpConnector(config)


def _should_use_mcp() -> bool:
    prefer = (resolve_secret(os.getenv("PLANVIEW_PREFER_MCP")) or "").lower() in {
        "1",
        "true",
        "yes",
    }
    return bool(prefer and resolve_secret(os.getenv("PLANVIEW_MCP_SERVER_URL")))


def create_app() -> FastAPI:
    app = FastAPI(title="Planview Connector")
    from .router import router

    app.include_router(router)
    return app


app = create_app()


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


# New outbound hook placeholder. Later, this should send data to Planview via real API.
def send_to_external_system(records: list[dict[str, object]], tenant_id: str, *, include_schema: bool) -> None:
    """
    Placeholder outbound handler for Planview.
    This function currently logs the records to be written and performs no external calls.

    Args:
        records: Mapped records in the canonical schema.
        tenant_id: Tenant identifier.
        include_schema: Whether the mapped records include schema metadata.
    """
    import logging

    mapped_payload = map_to_planview(records)
    if _should_use_mcp():
        connector = _build_mcp_connector()
        for payload in mapped_payload:
            connector.create_work_item(payload)
        return
    logging.getLogger(__name__).info(
        "Outbound payload for Planview tenant %s (include_schema=%s): %s",
        tenant_id,
        include_schema,
        mapped_payload,
    )
