"""Slack MCP mapping helpers.

Operations
----------
list
    Required fields:
        - resource_type (str): Expected enum: "channels" | "users".
    Optional fields:
        - filters (dict[str, Any]): filter clauses such as team_id; defaults to {}.
        - limit (int): defaults to 100 if omitted.
        - offset (int): defaults to 0 if omitted.
    Type conversions:
        - limit/offset are coerced to int when provided.

write
    Required fields:
        - resource_type (str): Expected enum: "messages".
        - records (list[dict[str, Any]] | dict[str, Any]): message payload(s).
    Optional fields:
        - channel (str): override channel id for MCP tools that accept it.
    Type conversions:
        - single record payloads are wrapped into a list.
"""

from __future__ import annotations

from typing import Any


def map_to_mcp_params(operation: str, canonical_payload: dict[str, Any]) -> dict[str, Any]:
    """Map canonical payloads to Slack MCP tool parameters."""
    resource_type = canonical_payload.get("resource_type")

    if operation == "list":
        return {
            "resource_type": resource_type or "channels",
            "filters": canonical_payload.get("filters") or {},
            "limit": int(canonical_payload.get("limit", 100)),
            "offset": int(canonical_payload.get("offset", 0)),
        }

    if operation == "write":
        records = canonical_payload.get("records") or canonical_payload.get("record") or []
        if isinstance(records, dict):
            records = [records]
        payload: dict[str, Any] = {
            "resource_type": resource_type or "messages",
            "records": records,
        }
        if canonical_payload.get("channel") is not None:
            payload["channel"] = canonical_payload["channel"]
        return payload

    raise ValueError(f"Unsupported Slack MCP operation: {operation}")


def map_from_mcp_response(operation: str, tool_response: Any) -> list[dict[str, Any]]:
    """Normalize MCP tool responses into canonical Slack payloads."""
    if operation == "write":
        return _normalize_write_records(tool_response)
    return _extract_records(tool_response)


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("channels", "members", "records", "items", "values", "data", "value"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return [payload]
    return []


def _normalize_write_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    return []
