from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from connectors.sdk.src.base_connector import (
    ConnectorCategory,
    ConnectorConfig,
    SyncDirection,
    SyncFrequency,
)
from connectors.sdk.src.runtime import ConnectorRuntime
from connectors.sdk.src.sync_router import InboundSyncRequest, OutboundSyncRequest, map_records

from .slack_connector import SlackConnector

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]

router = APIRouter(prefix="/connectors/slack", tags=["connectors"])


def _build_connector() -> SlackConnector:
    prefer_mcp = os.getenv("SLACK_PREFER_MCP", "").lower() in {"1", "true", "yes"}
    config = ConnectorConfig(
        connector_id="slack",
        name="Slack",
        category=ConnectorCategory.COLLABORATION,
        enabled=True,
        sync_direction=SyncDirection.OUTBOUND,
        sync_frequency=SyncFrequency.MANUAL,
        instance_url="",
        project_key="",
        mcp_server_url=os.getenv("SLACK_MCP_SERVER_URL", ""),
        mcp_server_id=os.getenv("SLACK_MCP_SERVER_ID") or "slack",
        mcp_client_id=os.getenv("SLACK_MCP_CLIENT_ID", ""),
        mcp_client_secret=os.getenv("SLACK_MCP_CLIENT_SECRET", ""),
        mcp_scope=os.getenv("SLACK_MCP_SCOPE", ""),
        mcp_api_key=os.getenv("SLACK_MCP_API_KEY", ""),
        mcp_api_key_header=os.getenv("SLACK_MCP_API_KEY_HEADER", ""),
        mcp_oauth_token=os.getenv("SLACK_MCP_OAUTH_TOKEN", ""),
        prefer_mcp=bool(prefer_mcp and os.getenv("SLACK_MCP_SERVER_URL")),
    )
    return SlackConnector(config)


@router.post("/sync/inbound")
def sync_inbound(request: InboundSyncRequest) -> list[dict[str, object]]:
    if request.records:
        return map_records(
            CONNECTOR_ROOT,
            request.records,
            request.tenant_id,
            include_schema=request.include_schema,
        )
    if not request.live:
        raise HTTPException(status_code=400, detail="Either records or live=true is required")
    connector = _build_connector()
    channels = connector.read("channels")
    records = [
        {
            "source": "project",
            "id": channel.get("id"),
            "name": channel.get("name"),
            "status": "active",
            "owner": channel.get("creator"),
        }
        for channel in channels
    ]
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    return runtime.apply_mappings(records, request.tenant_id, include_schema=request.include_schema)


@router.post("/sync/outbound")
def sync_outbound(request: OutboundSyncRequest) -> dict[str, object]:
    mapped = map_records(
        CONNECTOR_ROOT,
        request.records,
        request.tenant_id,
        include_schema=request.include_schema,
    )
    if request.live:
        connector = _build_connector()
        payloads = [
            {
                "channel": record.get("channel") or record.get("id"),
                "text": record.get("text") or record.get("message") or record.get("name"),
            }
            for record in request.records
        ]
        response = connector.write("messages", payloads)
        return {"status": "sent", "records": response}
    return {"status": "dry_run", "records": mapped}
