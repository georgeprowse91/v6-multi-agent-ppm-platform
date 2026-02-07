"""MCP behavior tests for the Clarity connector."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CONNECTOR_SDK_PATH = REPO_ROOT / "connectors" / "sdk" / "src"
CLARITY_CONNECTOR_PATH = REPO_ROOT / "connectors" / "clarity" / "src"
for path in (REPO_ROOT, CONNECTOR_SDK_PATH, CLARITY_CONNECTOR_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from base_connector import ConnectorCategory, ConnectorConfig, SyncDirection, SyncFrequency
from clarity_connector import ClarityConnector
from mcp_client import MCPClientError


class FakeMCPClient:
    def __init__(self, payload: Any, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def invoke_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        self.calls.append((tool_name, params))
        if self.error:
            raise self.error
        return self.payload


@pytest.fixture
def clarity_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_id="clarity",
        name="Clarity PPM",
        category=ConnectorCategory.PPM,
        enabled=True,
        sync_direction=SyncDirection.INBOUND,
        sync_frequency=SyncFrequency.DAILY,
        instance_url="https://clarity.example.com",
        prefer_mcp=True,
        mcp_server_url="https://mcp.example.com",
    )


def test_clarity_mcp_invocation_and_mapping(clarity_config: ConnectorConfig) -> None:
    payload = {
        "records": [
            {
                "id": "123",
                "name": "Alpha",
                "programId": "PRG1",
                "status": "completed",
                "startDate": "2024-01-01",
                "finishDate": "2024-02-01",
                "manager": "Ada",
            }
        ]
    }
    fake_client = FakeMCPClient(payload)
    connector = ClarityConnector(clarity_config)
    connector._authenticated = True

    with patch.object(connector, "_build_mcp_client", return_value=fake_client), patch.object(
        connector, "_read_projects", return_value=[]
    ):
        result = connector.read("projects", limit=5, offset=10)

    assert fake_client.calls == [
        (
            "clarity.listProjects",
            {"resource_type": "projects", "filters": {}, "limit": 5, "offset": 10},
        )
    ]
    assert result == [
        {
            "id": "123",
            "program_id": "PRG1",
            "name": "Alpha",
            "status": "completed",
            "start_date": "2024-01-01",
            "end_date": "2024-02-01",
            "owner": "Ada",
            "classification": "internal",
            "created_at": None,
        }
    ]


def test_clarity_mcp_tool_missing_falls_back(clarity_config: ConnectorConfig) -> None:
    connector = ClarityConnector(clarity_config)
    connector._authenticated = True
    connector._mcp_tool_map = {}
    rest_records = [{"id": "rest-project"}]

    with patch.object(connector, "_read_projects", return_value=rest_records):
        result = connector.read("projects")

    assert result == rest_records


def test_clarity_mcp_error_falls_back(clarity_config: ConnectorConfig) -> None:
    connector = ClarityConnector(clarity_config)
    connector._authenticated = True
    rest_records = [{"id": "rest-project"}]

    fake_client = FakeMCPClient(payload={}, error=MCPClientError("boom"))

    with patch.object(connector, "_build_mcp_client", return_value=fake_client), patch.object(
        connector, "_read_projects", return_value=rest_records
    ):
        result = connector.read("projects")

    assert result == rest_records
