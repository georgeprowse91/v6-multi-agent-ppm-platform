from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

PLANVIEW_TARGET_SCHEMA = "work_item"
PLANVIEW_REQUIRED_FIELDS = ("id", "name", "status", "start_date")

_STATUS_MAP: dict[str, str] = {
    "new": "proposed",
    "draft": "proposed",
    "planned": "proposed",
    "initiated": "proposed",
    "open": "active",
    "active": "active",
    "execution": "active",
    "in_progress": "active",
    "on_track": "active",
    "hold": "on_hold",
    "on_hold": "on_hold",
    "blocked": "on_hold",
    "paused": "on_hold",
    "done": "completed",
    "complete": "completed",
    "completed": "completed",
    "closed": "completed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}

_CLASSIFICATION_MAP: dict[str, str] = {
    "strategic": "STRATEGIC",
    "internal": "INTERNAL",
    "external": "EXTERNAL",
    "customer": "CUSTOMER",
    "regulatory": "REGULATORY",
}


class PlanviewMappingError(ValueError):
    """Structured validation error for outbound Planview mapping."""

    def __init__(
        self,
        message: str,
        *,
        index: int | None = None,
        field: str | None = None,
        record_id: str | None = None,
    ) -> None:
        self.index = index
        self.field = field
        self.record_id = record_id
        super().__init__(message)

    def as_dict(self) -> dict[str, Any]:
        return {
            "error": "planview_mapping_error",
            "message": str(self),
            "index": self.index,
            "field": self.field,
            "record_id": self.record_id,
        }


def map_to_planview(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert canonical PPM records into Planview work-item payloads."""
    mapped: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        try:
            mapped.append(_map_record(record))
        except PlanviewMappingError as exc:
            if exc.index is None:
                exc.index = index
            if exc.record_id is None and isinstance(record, dict):
                rid = record.get("id")
                exc.record_id = str(rid) if rid is not None else None
            raise
        except Exception as exc:  # pragma: no cover - defensive conversion
            raise PlanviewMappingError(
                f"Unexpected mapping error: {exc}",
                index=index,
                record_id=str(record.get("id")) if isinstance(record, dict) and record.get("id") else None,
            ) from exc
    return mapped


def _map_record(record: dict[str, Any]) -> dict[str, Any]:
    record_id = _require_string(record, "id")
    name = _require_string(record, "name")

    payload = {
        "externalId": record_id,
        "name": name,
        "lifecycleState": _to_planview_status(record.get("status")),
        "startDate": _format_date(record.get("start_date"), field="start_date", required=True),
        "finishDate": _format_date(record.get("end_date"), field="end_date", required=False),
        "parentProgramExternalId": _optional_string(record.get("program_id")),
        "owner": {"principalName": _optional_string(record.get("owner"))},
        "financials": {
            "classification": _to_planview_classification(record.get("classification")),
            "plannedCost": _coerce_number(record.get("planned_cost"), field="planned_cost"),
            "actualCost": _coerce_number(record.get("actual_cost"), field="actual_cost"),
            "currency": _optional_string(record.get("currency")) or "USD",
        },
        "metadata": {
            "sourceCreatedAt": _format_datetime(record.get("created_at"), field="created_at"),
            "sourceUpdatedAt": _format_datetime(record.get("updated_at"), field="updated_at"),
            "sourceTenantId": _optional_string(record.get("tenant_id")),
        },
    }
    return _drop_none(payload)


def _require_string(record: dict[str, Any], field: str) -> str:
    value = record.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise PlanviewMappingError(f"Missing required field: {field}", field=field)
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        raise PlanviewMappingError(f"Missing required field: {field}", field=field)
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    text = str(value).strip()
    return text or None


def _to_planview_status(value: Any) -> str:
    if value is None:
        raise PlanviewMappingError("Missing required field: status", field="status")
    normalized = str(value).strip().lower().replace(" ", "_")
    mapped = _STATUS_MAP.get(normalized)
    if not mapped:
        raise PlanviewMappingError(
            f"Unsupported status value for Planview: {value}",
            field="status",
        )
    return mapped


def _to_planview_classification(value: Any) -> str | None:
    normalized = _optional_string(value)
    if not normalized:
        return None
    mapped = _CLASSIFICATION_MAP.get(normalized.lower())
    if mapped:
        return mapped
    return normalized.upper().replace(" ", "_")


def _format_date(value: Any, *, field: str, required: bool) -> str | None:
    if value in (None, ""):
        if required:
            raise PlanviewMappingError(f"Missing required field: {field}", field=field)
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        if required:
            raise PlanviewMappingError(f"Missing required field: {field}", field=field)
        return None
    try:
        if "T" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise PlanviewMappingError(
            f"Invalid date format for {field}: {value}",
            field=field,
        ) from exc


def _format_datetime(value: Any, *, field: str) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).isoformat() + "Z"
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except ValueError as exc:
        raise PlanviewMappingError(
            f"Invalid datetime format for {field}: {value}",
            field=field,
        ) from exc


def _coerce_number(value: Any, *, field: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise PlanviewMappingError(
            f"Invalid numeric value for {field}: {value}",
            field=field,
        ) from exc


def _drop_none(payload: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            nested = _drop_none(value)
            if nested:
                compact[key] = nested
        elif value is not None:
            compact[key] = value
    return compact


def map_to_mcp_params(operation: str, canonical_payload: dict[str, Any]) -> dict[str, Any]:
    """Map canonical payloads to Planview MCP tool parameters.

    Operations
    ----------
    list
        Required fields:
            - resource_type (str): Expected enum: "projects".
        Optional fields:
            - filters (dict[str, Any]): query fields; defaults to {}.
            - limit (int): defaults to 100 if omitted.
            - offset (int): defaults to 0 if omitted.
        Type conversions:
            - limit/offset are coerced to int when provided.
    """
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
