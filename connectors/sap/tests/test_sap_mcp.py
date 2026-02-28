"""MCP behavior tests for the SAP connector."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
CONNECTOR_SDK_PATH = REPO_ROOT / "integrations" / "connectors" / "sdk" / "src"
SAP_CONNECTOR_PATH = REPO_ROOT / "integrations" / "connectors" / "sap" / "src"
for path in (REPO_ROOT, CONNECTOR_SDK_PATH, SAP_CONNECTOR_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
from mcp_client import MCPClientError
from rest_connector import BasicAuthRestConnector
from sap_connector import SapConnector


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
def sap_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_id="sap",
        name="SAP",
        category=ConnectorCategory.ERP,
        enabled=True,
        sync_direction=SyncDirection.INBOUND,
        sync_frequency=SyncFrequency.DAILY,
        instance_url="https://sap.example.com",
        prefer_mcp=True,
        mcp_server_url="https://mcp.example.com",
    )


def test_sap_mcp_routing_and_rest_fallback(sap_config: ConnectorConfig) -> None:
    payloads = {
        "sap.listProjects": {"records": [{"ProjectID": "MCP-1", "Description": "MCP"}]}
    }
    fake_client = FakeMCPClient(payloads)
    connector = SapConnector(sap_config)
    connector._mcp_tool_map = {"list_projects": "sap.listProjects"}
    rest_records = [{"ProjectID": "REST-1", "Description": "REST"}]

    with patch.object(connector, "_build_mcp_client", return_value=fake_client), patch.object(
        BasicAuthRestConnector, "read", return_value=rest_records
    ):
        projects = connector.read("projects", limit=5, offset=0)
        costs = connector.read("costs", limit=3, offset=1)

    assert fake_client.calls == [
        (
            "sap.listProjects",
            {"resource_type": "projects", "filters": {}, "limit": 5, "offset": 0},
        )
    ]
    assert projects == [{"ProjectID": "MCP-1", "Description": "MCP"}]
    assert costs == rest_records


def test_sap_mcp_error_falls_back(sap_config: ConnectorConfig) -> None:
    fake_client = FakeMCPClient(payloads={}, error=MCPClientError("boom"))
    connector = SapConnector(sap_config)
    rest_records = [{"ProjectID": "REST-2"}]

    with patch.object(connector, "_build_mcp_client", return_value=fake_client), patch.object(
        BasicAuthRestConnector, "read", return_value=rest_records
    ):
        result = connector.read("projects")

    assert result == rest_records
