#!/usr/bin/env python3
"""Validate MCP-enabled connector manifests have required MCP configuration fields."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONNECTORS_DIR = REPO_ROOT / "connectors"

MCP_REQUIRED_FIELDS = {"mcp_server_url", "mcp_tools"}


def main() -> int:
    if not CONNECTORS_DIR.exists():
        print(f"Connectors directory not found: {CONNECTORS_DIR.relative_to(REPO_ROOT)}")
        return 1

    failures: list[str] = []
    checked = 0
    for manifest in sorted(CONNECTORS_DIR.rglob("manifest.yaml")):
        relative = manifest.relative_to(REPO_ROOT)
        try:
            with manifest.open(encoding="utf-8") as fh:
                doc = yaml.safe_load(fh)
        except yaml.YAMLError:
            continue  # YAML errors are caught by validate-manifests.py

        if not isinstance(doc, dict):
            continue

        # Only validate connectors that declare MCP support
        if not doc.get("mcp_enabled") and not doc.get("protocol") == "mcp":
            continue

        checked += 1
        missing = MCP_REQUIRED_FIELDS - doc.keys()
        if missing:
            failures.append(f"{relative}: MCP-enabled but missing: {', '.join(sorted(missing))}")

    if failures:
        print("MCP manifest validation failures:")
        for f in failures:
            print(f"  {f}")
        return 1

    print(f"MCP manifest validation passed ({checked} MCP manifests checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
