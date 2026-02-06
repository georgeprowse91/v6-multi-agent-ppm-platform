"""Planview MCP mapping helpers.

Canonical payloads exchanged with the connector are converted into MCP tool
parameters here. These helpers document the Planview MCP contract.

Operations
----------
list
    Required fields:
        - resource_type (str): Expected enum: "projects".
    Optional fields:
        - filters (dict[str, Any]): Currently unused by REST; defaults to {}.
        - limit (int): defaults to 100 if omitted.
        - offset (int): defaults to 0 if omitted.
    Type conversions:
        - limit/offset are coerced to int when provided.

create/update/delete
    Not supported by Planview connector (read-only). Mapping will raise.
"""

from __future__ import annotations

from typing import Any


def map_to_mcp_params(operation: str, canonical_payload: dict[str, Any]) -> dict[str, Any]:
    """Map canonical payloads to Planview MCP tool parameters."""
    if operation != "list":
        raise ValueError(f"Unsupported Planview MCP operation: {operation}")

    return {
        "resource_type": canonical_payload.get("resource_type", "projects"),
        "filters": canonical_payload.get("filters") or {},
        "limit": int(canonical_payload.get("limit", 100)),
        "offset": int(canonical_payload.get("offset", 0)),
    }


def map_from_mcp_response(operation: str, tool_response: Any) -> list[dict[str, Any]]:
    """Normalize MCP tool responses into canonical Planview payloads."""
    if operation != "list":
        raise ValueError(f"Unsupported Planview MCP operation: {operation}")
    return _extract_records(tool_response)


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("records", "items", "values", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []
