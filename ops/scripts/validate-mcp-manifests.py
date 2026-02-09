#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONNECTORS_DIR = REPO_ROOT / "integrations" / "connectors"


def _load_manifest(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    return data if isinstance(data, dict) else {}


def _describe(path: Path, message: str) -> str:
    return f"{path}: {message}"


def main() -> int:
    failures: list[str] = []
    manifests = sorted(CONNECTORS_DIR.glob("*_mcp/manifest.yaml"))

    if not manifests:
        print("No MCP manifests found.")
        return 0

    for manifest_path in manifests:
        data = _load_manifest(manifest_path)
        mcp_section = data.get("mcp")
        if mcp_section is None:
            failures.append(_describe(manifest_path, "missing mcp section"))
            continue
        if not isinstance(mcp_section, dict):
            failures.append(_describe(manifest_path, "mcp section must be a mapping"))
            continue

        mcp_server_url = mcp_section.get("server_url")
        mcp_server_id = mcp_section.get("server_id")
        top_server_url = data.get("mcp_server_url")
        top_server_id = data.get("mcp_server_id")

        if not (mcp_server_url or top_server_url):
            failures.append(_describe(manifest_path, "missing MCP server_url"))
        if not (mcp_server_id or top_server_id):
            failures.append(_describe(manifest_path, "missing MCP server_id"))

        if mcp_server_url and top_server_url and mcp_server_url != top_server_url:
            failures.append(_describe(manifest_path, "mcp.server_url differs from mcp_server_url"))
        if mcp_server_id and top_server_id and mcp_server_id != top_server_id:
            failures.append(_describe(manifest_path, "mcp.server_id differs from mcp_server_id"))

        tool_map = mcp_section.get("tool_map")
        top_tool_map = data.get("tool_map") or data.get("mcp_tool_map")
        if tool_map is None and top_tool_map is None:
            failures.append(_describe(manifest_path, "missing mcp tool map"))
        if tool_map is not None and not isinstance(tool_map, dict):
            failures.append(_describe(manifest_path, "mcp.tool_map must be a mapping"))
        if top_tool_map is not None and not isinstance(top_tool_map, dict):
            failures.append(_describe(manifest_path, "tool_map must be a mapping"))
        if (
            isinstance(tool_map, dict)
            and isinstance(top_tool_map, dict)
            and tool_map != top_tool_map
        ):
            failures.append(_describe(manifest_path, "mcp.tool_map differs from tool_map"))

    if failures:
        for failure in failures:
            print(f"Manifest validation failed: {failure}")
        return 1

    print("MCP manifest validation succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
