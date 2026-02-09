from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
import sys

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = Path(__file__).resolve().parents[1]
sys.path = [path for path in sys.path if Path(path).resolve() != TESTS_ROOT]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integrations.connectors.mcp_client import client as mcp_client_module
from integrations.connectors.mcp_client.client import MCPClient


class DummyAsyncClient:
    def __init__(self, responses: list[dict[str, Any]], requests: list[dict[str, Any]]) -> None:
        self._responses = responses
        self._requests = requests

    async def __aenter__(self) -> "DummyAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def post(self, url: str, json: dict[str, Any], headers: dict[str, Any]) -> httpx.Response:
        self._requests.append({"url": url, "json": json, "headers": headers})
        response = self._responses.pop(0)
        return httpx.Response(200, json=response)


def test_mcp_client_invokes_tool_map(monkeypatch) -> None:
    requests: list[dict[str, Any]] = []
    responses = [
        {
            "jsonrpc": "2.0",
            "id": "1",
            "result": {"protocolVersion": "2025-06-18", "capabilities": {}},
        },
        {
            "jsonrpc": "2.0",
            "id": "2",
            "result": {"records": [{"id": "p-1"}]},
        }
    ]

    def fake_async_client(*_args, **_kwargs) -> DummyAsyncClient:
        return DummyAsyncClient(responses, requests)

    monkeypatch.setattr(mcp_client_module.httpx, "AsyncClient", fake_async_client)

    client = MCPClient(
        mcp_server_id="slack",
        mcp_server_url="https://mcp.example.com",
        tool_map={"list_records": "tools.listRecords"},
    )

    result = asyncio.run(client.list_records({"limit": 1}))

    assert result["records"][0]["id"] == "p-1"
    assert requests[0]["json"]["method"] == "initialize"
    assert requests[1]["json"]["method"] == "tools/call"
    assert requests[1]["json"]["params"]["name"] == "tools.listRecords"


def test_mcp_client_lists_tools(monkeypatch) -> None:
    requests: list[dict[str, Any]] = []
    responses = [
        {
            "jsonrpc": "2.0",
            "id": "1",
            "result": {"protocolVersion": "2025-06-18", "capabilities": {}},
        },
        {
            "jsonrpc": "2.0",
            "id": "2",
            "result": {
                "tools": [
                    {
                        "name": "tools.listRecords",
                        "description": "List records",
                        "inputSchema": {"type": "object"},
                    }
                ]
            },
        }
    ]

    def fake_async_client(*_args, **_kwargs) -> DummyAsyncClient:
        return DummyAsyncClient(responses, requests)

    monkeypatch.setattr(mcp_client_module.httpx, "AsyncClient", fake_async_client)

    client = MCPClient(mcp_server_id="slack", mcp_server_url="https://mcp.example.com")
    tools = asyncio.run(client.list_tools())

    assert tools[0].name == "tools.listRecords"
    assert requests[1]["json"]["method"] == "tools/list"
