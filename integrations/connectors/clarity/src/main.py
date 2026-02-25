from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from connector_secrets import resolve_secret
from integrations.connectors.integration import ClarityMcpConnector, IntegrationAuthType, IntegrationConfig
from integrations.connectors.sdk.src.runtime import ConnectorRuntime

from .clarity_connector import ClarityConnector, create_clarity_connector
from .mappers import map_to_clarity

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]


def _ensure_source(records: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    return [{"source": source, **record} for record in records]


def run_sync(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    connector: ClarityConnector | None = None,
    include_schema: bool = False,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id, include_schema=include_schema)

    if live and _should_use_mcp():
        mcp_connector = _build_mcp_connector()
        records = mcp_connector.list_projects()
        return runtime.apply_mappings(records, tenant_id, include_schema=include_schema)

    if connector is None:
        instance_url = resolve_secret(os.getenv("CLARITY_INSTANCE_URL")) or ""
        connector = create_clarity_connector(instance_url=instance_url)

    records = _ensure_source(connector.read("projects"), "project")
    return runtime.apply_mappings(records, tenant_id, include_schema=include_schema)


def _build_mcp_connector() -> ClarityMcpConnector:
    tool_map = {
        "list_projects": "clarity.listProjects",
        "create_work_item": "clarity.createWorkItem",
    }
    config = IntegrationConfig(
        system="clarity",
        base_url=resolve_secret(os.getenv("CLARITY_INSTANCE_URL")) or "",
        auth_type=IntegrationAuthType.NONE,
        mcp_server_url=resolve_secret(os.getenv("CLARITY_MCP_SERVER_URL")),
        mcp_server_id=resolve_secret(os.getenv("CLARITY_MCP_SERVER_ID")) or "clarity",
        mcp_client_id=resolve_secret(os.getenv("CLARITY_MCP_CLIENT_ID")),
        mcp_client_secret=resolve_secret(os.getenv("CLARITY_MCP_CLIENT_SECRET")),
        mcp_scope=resolve_secret(os.getenv("CLARITY_MCP_SCOPE")),
        mcp_api_key=resolve_secret(os.getenv("CLARITY_MCP_API_KEY")),
        mcp_api_key_header=resolve_secret(os.getenv("CLARITY_MCP_API_KEY_HEADER")),
        mcp_oauth_token=resolve_secret(os.getenv("CLARITY_MCP_OAUTH_TOKEN")),
        mcp_tool_map=tool_map,
        prefer_mcp=True,
    )
    return ClarityMcpConnector(config)


def _should_use_mcp() -> bool:
    prefer_mcp = (resolve_secret(os.getenv("CLARITY_PREFER_MCP")) or "").lower() in {"1", "true", "yes"}
    return prefer_mcp and bool(resolve_secret(os.getenv("CLARITY_MCP_SERVER_URL")))


def create_app() -> FastAPI:
    app = FastAPI(title="Clarity Connector")
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


def send_to_external_system(records: list[dict[str, object]], tenant_id: str, *, include_schema: bool) -> None:
    """Outbound handler – routes canonical records to Clarity via MCP or REST API."""
    mapped_payload = map_to_clarity(records)
    logger = logging.getLogger(__name__)

    if not mapped_payload:
        logger.warning(
            "No valid Clarity outbound records produced for tenant %s (include_schema=%s)",
            tenant_id,
            include_schema,
        )
        return

    if _should_use_mcp():
        connector = _build_mcp_connector()
        for payload in mapped_payload:
            connector.create_work_item(payload)
        logger.info(
            "Sent %d record(s) to Clarity via MCP for tenant %s",
            len(mapped_payload),
            tenant_id,
        )
        return

    instance_url = resolve_secret(os.getenv("CLARITY_INSTANCE_URL")) or ""
    if not instance_url:
        logger.error(
            "CLARITY_INSTANCE_URL is not set; cannot send outbound records for tenant %s",
            tenant_id,
        )
        return

    rest_connector = create_clarity_connector(instance_url=instance_url, sync_direction="outbound")

    succeeded = 0
    failed = 0
    for payload in mapped_payload:
        external_id = payload.get("externalId", "")
        try:
            rest_connector._request("POST", "/ppm/rest/v1/projects", json=payload)
            succeeded += 1
            logger.debug(
                "Clarity outbound record accepted: externalId=%s tenant=%s",
                external_id,
                tenant_id,
            )
        except Exception as exc:
            failed += 1
            logger.error(
                "Failed to push Clarity outbound record externalId=%s tenant=%s: %s",
                external_id,
                tenant_id,
                exc,
            )

    logger.info(
        "Clarity outbound sync complete for tenant %s: %d succeeded, %d failed",
        tenant_id,
        succeeded,
        failed,
    )
