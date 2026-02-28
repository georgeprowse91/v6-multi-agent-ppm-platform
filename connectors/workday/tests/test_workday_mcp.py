"""MCP behavior tests for the Workday connector."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CONNECTOR_SDK_PATH = REPO_ROOT / "connectors" / "sdk" / "src"
WORKDAY_CONNECTOR_PATH = REPO_ROOT / "connectors" / "workday" / "src"
for path in (REPO_ROOT, CONNECTOR_SDK_PATH, WORKDAY_CONNECTOR_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
from mcp_client import MCPClientError
from rest_connector import OAuth2RestConnector
from workday_connector import WorkdayConnector


class FakeMCPClient:
    def __init__(self, payloads: dict[str, Any], error: Exception | None = None) -> None:
        self.payloads = payloads
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def invoke_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        self.calls.append((tool_name, params))
        if self.error:
            raise self.error
        return self.payloads.get(tool_name, {})


@pytest.fixture
def workday_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_id="workday",
        name="Workday",
        category=ConnectorCategory.HRIS,
        enabled=True,
        sync_direction=SyncDirection.INBOUND,
        sync_frequency=SyncFrequency.DAILY,
        instance_url="https://workday.example.com",
        prefer_mcp=True,
        mcp_server_url="https://mcp.example.com",
    )


def test_workday_mcp_routing_and_rest_fallback(workday_config: ConnectorConfig) -> None:
    payloads = {
        "workday.listWorkers": {"records": [{"id": "W1", "name": "Ada"}]}
    }
    fake_client = FakeMCPClient(payloads)
    connector = WorkdayConnector(workday_config)
    connector._mcp_tool_map = {"list_workers": "workday.listWorkers"}
    rest_records = [{"id": "REST"}]

    with patch.object(connector, "_build_mcp_client", return_value=fake_client), patch.object(
        OAuth2RestConnector, "read", return_value=rest_records
    ):
        workers = connector.read("workers", limit=2, offset=0)
        positions = connector.read("positions", limit=1, offset=1)

    assert fake_client.calls == [
        (
            "workday.listWorkers",
            {"resource_type": "workers", "filters": {}, "limit": 2, "offset": 0},
        )
    ]
    assert workers == [{"id": "W1", "name": "Ada"}]
    assert positions == rest_records


def test_workday_mcp_error_falls_back(workday_config: ConnectorConfig) -> None:
    fake_client = FakeMCPClient(payloads={}, error=MCPClientError("boom"))
    connector = WorkdayConnector(workday_config)
    rest_records = [{"id": "REST-2"}]

    with patch.object(connector, "_build_mcp_client", return_value=fake_client), patch.object(
        OAuth2RestConnector, "read", return_value=rest_records
    ):
        result = connector.read("workers")

    assert result == rest_records
