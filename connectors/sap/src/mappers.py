from __future__ import annotations
from datetime import date, datetime
from typing import Any, Iterable


STATUS_CODE_MAP = {
    "active": "REL",
    "in_progress": "REL",
    "planned": "PLN",
    "on_hold": "HLD",
    "blocked": "HLD",
    "completed": "CMP",
    "done": "CMP",
    "cancelled": "CNL",
    "canceled": "CNL",
}

REQUIRED_CANONICAL_FIELDS = ("id", "name", "status", "start_date", "end_date")


def map_to_sap(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert canonical PPM records into SAP-compatible payloads.

    Args:
        records: Canonical records produced by the mapping engine.

    Returns:
        A list of dictionaries formatted for the SAP API.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    mapped_records: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        _validate_required_fields(record, index)
        mapped_records.append(
            {
                "ProjectID": str(record["id"]).strip(),
                "Description": str(record["name"]).strip(),
                "LifecycleStatus": _normalize_status(record["status"]),
                "PlannedStartDate": _normalize_date(record["start_date"], field_name="start_date"),
                "PlannedFinishDate": _normalize_date(record["end_date"], field_name="end_date"),
                "ProjectManager": _normalize_optional_text(record.get("owner")),
                "BudgetAmount": _normalize_optional_number(record.get("budget"), field_name="budget"),
                "PercentComplete": _normalize_optional_number(
                    record.get("progress"), field_name="progress", as_int=True
                ),
                "IsActive": _normalize_bool(record.get("is_active"), fallback_from_status=record.get("status")),
            }
        )
    return mapped_records


def _validate_required_fields(record: dict[str, Any], index: int) -> None:
    missing = [
        field
        for field in REQUIRED_CANONICAL_FIELDS
        if field not in record or record[field] is None or str(record[field]).strip() == ""
    ]
    if missing:
        raise ValueError(
            f"SAP outbound record at index {index} missing required fields: {', '.join(missing)}"
        )


def _normalize_status(value: Any) -> str:
    raw = str(value).strip().lower()
    mapped = STATUS_CODE_MAP.get(raw)
    if mapped:
        return mapped
    if not raw:
        raise ValueError("SAP outbound status cannot be empty")
    return raw.upper()


def _normalize_date(value: Any, *, field_name: str) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"SAP outbound {field_name} cannot be empty")
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
        except ValueError as exc:
            raise ValueError(f"SAP outbound {field_name} must be an ISO date/datetime") from exc
    raise ValueError(f"SAP outbound {field_name} must be a date, datetime, or ISO string")


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_optional_number(value: Any, *, field_name: str, as_int: bool = False) -> float | int | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"SAP outbound {field_name} must be numeric") from exc
    return int(number) if as_int else number


def _normalize_bool(value: Any, *, fallback_from_status: Any = None) -> bool:
    if value is None:
        if fallback_from_status is None:
            return True
        return _normalize_status(fallback_from_status) not in {"CMP", "CNL"}
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    raise ValueError("SAP outbound is_active must be boolean-like")


def map_to_mcp_params(operation: str, canonical_payload: dict[str, Any]) -> dict[str, Any]:
    """Map canonical payloads to SAP MCP tool parameters.

    Operations
    ----------
    list
        Required fields:
            - resource_type (str): Expected enum: "projects" | "costs".
        Optional fields:
            - filters (dict[str, Any]): query fields; defaults to {}.
            - limit (int): defaults to 100 if omitted.
            - offset (int): defaults to 0 if omitted.
        Type conversions:
            - limit/offset are coerced to int when provided.
    """
    if operation != "list":
        raise ValueError(f"Unsupported SAP MCP operation: {operation}")

    return {
        "resource_type": canonical_payload.get("resource_type", "projects"),
        "filters": canonical_payload.get("filters") or {},
        "limit": int(canonical_payload.get("limit", 100)),
        "offset": int(canonical_payload.get("offset", 0)),
    }


def map_from_mcp_response(operation: str, tool_response: Any) -> list[dict[str, Any]]:
    """Normalize MCP tool responses into canonical SAP payloads."""
    if operation != "list":
        raise ValueError(f"Unsupported SAP MCP operation: {operation}")
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
