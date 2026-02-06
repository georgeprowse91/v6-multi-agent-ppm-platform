"""Jira MCP mapping helpers.

Canonical payloads exchanged with the connector are intentionally stable and
converted to the MCP tool schema here. These helpers document the Jira MCP
contract for tool parameters and responses.

Operations
----------
list
    Required fields:
        - resource_type (str): Expected enum: "issues".
    Optional fields:
        - filters (dict[str, Any]): Jira query fields; defaults to {}.
        - limit (int): defaults to 100 if omitted.
        - offset (int): defaults to 0 if omitted.
    Type conversions:
        - limit/offset are coerced to int when provided.

create
    Required fields:
        - resource_type (str): "issues".
        - record (dict[str, Any]): canonical issue payload.
    Optional fields:
        - status (str): desired status transition.

update
    Required fields:
        - resource_type (str): "issues".
        - record (dict[str, Any]): canonical issue payload.
    Optional fields:
        - id (str): issue id or key. If missing, will be inferred from record.
        - status (str): desired status transition.

delete
    Required fields:
        - resource_type (str): "issues".
        - id (str): issue id or key.
"""

from __future__ import annotations

from typing import Any


def map_to_mcp_params(operation: str, canonical_payload: dict[str, Any]) -> dict[str, Any]:
    """Map canonical payloads to Jira MCP tool parameters."""
    resource_type = canonical_payload.get("resource_type", "issues")
    payload: dict[str, Any] = {"resource_type": resource_type}

    if operation == "list":
        filters = canonical_payload.get("filters") or {}
        payload["filters"] = filters
        payload["limit"] = int(canonical_payload.get("limit", 100))
        payload["offset"] = int(canonical_payload.get("offset", 0))
        return payload

    if operation == "create":
        payload["record"] = canonical_payload.get("record", {})
        if canonical_payload.get("status") is not None:
            payload["status"] = canonical_payload["status"]
        return payload

    if operation == "update":
        payload["record"] = canonical_payload.get("record", {})
        record = canonical_payload.get("record") or {}
        payload["id"] = canonical_payload.get("id") or record.get("id") or record.get("key")
        if canonical_payload.get("status") is not None:
            payload["status"] = canonical_payload["status"]
        return payload

    if operation == "delete":
        payload["id"] = canonical_payload.get("id")
        return payload

    raise ValueError(f"Unsupported Jira MCP operation: {operation}")


def map_from_mcp_response(operation: str, tool_response: Any) -> Any:
    """Normalize MCP tool responses into canonical Jira payloads."""
    if operation == "list":
        return _extract_records(tool_response)
    return _extract_record(tool_response)


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("records", "items", "values", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _extract_record(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        if "record" in payload and isinstance(payload["record"], dict):
            return payload["record"]
        return payload
    return {}
