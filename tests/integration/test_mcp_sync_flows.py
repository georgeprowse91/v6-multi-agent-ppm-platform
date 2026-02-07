from __future__ import annotations

from pathlib import Path

from integrations.connectors.mcp_client.client import MCPClient as AsyncMcpClient
from integrations.connectors.sdk.src.base_connector import (
    ConnectorCategory,
    ConnectorConfig,
    ConnectorConfigStore,
    SyncDirection,
    SyncFrequency,
)
from integrations.connectors.sdk.src.operation_router import OperationRouter


def _load_config(tmp_path: Path, **overrides) -> ConnectorConfig:
    config = ConnectorConfig(
        connector_id="mock",
        name="Mock Connector",
        category=ConnectorCategory.PM,
        enabled=True,
        sync_direction=SyncDirection.INBOUND,
        sync_frequency=SyncFrequency.DAILY,
        instance_url="https://example.test",
        mcp_server_url="https://mcp.test",
        mcp_server_id="mock",
        mcp_tool_map={"list_records": "tools.listRecords"},
        prefer_mcp=True,
        mcp_enabled=True,
    )
    for key, value in overrides.items():
        setattr(config, key, value)
    store = ConnectorConfigStore(storage_path=tmp_path / "config.json")
    store.save(config)
    loaded = store.get("mock")
    assert loaded is not None
    return loaded


def test_mcp_enabled_sync_flow_lists_tools_and_records(
    mock_mcp_server, tmp_path: Path
) -> None:
    mock_mcp_server.register_tool(
        "tools.listRecords",
        result={"records": [{"id": "rec-1", "name": "Alpha"}]},
        schema={"type": "object", "properties": {"id": {"type": "string"}}},
    )

    config = _load_config(tmp_path)
    assert config.mcp_server_url == "https://mcp.test"

    mcp_client = AsyncMcpClient(
        mcp_server_id=config.mcp_server_id or config.connector_id,
        mcp_server_url=config.mcp_server_url,
        config=config,
    )
    tools = OperationRouter(config, mcp_client=mcp_client).run_mcp(mcp_client.list_tools())

    assert tools[0].name == "tools.listRecords"
    router = OperationRouter(config, mcp_client=mcp_client)

    result = router.run(
        "list_records",
        mcp_call=lambda: router.run_mcp(mcp_client.list_records({"limit": 1})),
        rest_call=lambda: [{"id": "fallback"}],
    )

    assert result["records"][0]["id"] == "rec-1"
    assert any(request.get("method") == "invokeTool" for request in mock_mcp_server.requests)


def test_mcp_disabled_sync_flow_uses_rest(mock_mcp_server, tmp_path: Path) -> None:
    config = _load_config(tmp_path, prefer_mcp=False)
    router = OperationRouter(config)

    result = router.run(
        "list_records",
        mcp_call=lambda: {"records": [{"id": "mcp"}]},
        rest_call=lambda: [{"id": "rest-only"}],
    )

    assert result == [{"id": "rest-only"}]
    assert mock_mcp_server.requests == []


def test_mcp_fallback_sync_flow_uses_rest_on_error(
    mock_mcp_server, tmp_path: Path
) -> None:
    mock_mcp_server.register_tool(
        "tools.listRecords",
        error={"code": -32001, "message": "MCP tool failure"},
    )

    config = _load_config(tmp_path)
    mcp_client = AsyncMcpClient(
        mcp_server_id=config.mcp_server_id or config.connector_id,
        mcp_server_url=config.mcp_server_url,
        config=config,
    )
    router = OperationRouter(config, mcp_client=mcp_client)

    result = router.run(
        "list_records",
        mcp_call=lambda: router.run_mcp(mcp_client.list_records({"limit": 5})),
        rest_call=lambda: [{"id": "rest-fallback"}],
    )

    assert result == [{"id": "rest-fallback"}]
    assert any(request.get("method") == "invokeTool" for request in mock_mcp_server.requests)
