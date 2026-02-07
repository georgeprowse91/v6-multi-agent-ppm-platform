"""Demo script for chaining MCP tool calls across systems.

This script shows how to:
- Discover MCP tool inventories.
- Invoke MCP tools for Jira and Slack.
- Pass results between systems in a simple workflow.

Set the environment variables for MCP endpoints and auth before running.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from integrations.connectors.mcp_client import MCPClient


def _build_client(server_id: str, server_url: str, tool_map: dict[str, str]) -> MCPClient:
    return MCPClient(
        mcp_server_id=server_id,
        mcp_server_url=server_url,
        tool_map=tool_map,
    )


def _build_summary(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No items returned from MCP tool."
    lines = ["MCP sync summary:"]
    for item in items[:5]:
        key = item.get("key") or item.get("id") or "unknown"
        title = item.get("summary") or item.get("name") or "Untitled"
        lines.append(f"- {key}: {title}")
    return "\n".join(lines)


async def main() -> None:
    jira_url = os.getenv("JIRA_MCP_SERVER_URL", "https://mcp.example.com/jira")
    slack_url = os.getenv("SLACK_MCP_SERVER_URL", "https://mcp.example.com/slack")

    jira_client = _build_client(
        server_id="jira",
        server_url=jira_url,
        tool_map={"list_records": "jira.listIssues"},
    )
    slack_client = _build_client(
        server_id="slack",
        server_url=slack_url,
        tool_map={"send_message": "slack.postMessage"},
    )

    tools = await jira_client.list_tools()
    print(f"Jira MCP tools: {[tool.name for tool in tools]}")

    issues = await jira_client.list_records({"project_key": "PPM", "limit": 5})
    summary = _build_summary(issues.get("items", []) if isinstance(issues, dict) else [])

    response = await slack_client.invoke_tool(
        "slack.postMessage",
        {
            "channel": os.getenv("SLACK_CHANNEL", "#ppm-updates"),
            "text": summary,
        },
    )
    print("Slack response:", response)


if __name__ == "__main__":
    asyncio.run(main())
