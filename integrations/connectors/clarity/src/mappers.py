from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# Clarity outbound work-item contract used by createWorkItem MCP tool.
#
# Required fields
# ---------------
# - externalId (str): Stable source-system identifier for idempotency.
# - name (str): Work item title/name.
# - status (str): Enum; one of DRAFT | APPROVED | IN_PROGRESS | ON_HOLD | COMPLETED | CANCELLED.
# - startDate (str): Date in YYYY-MM-DD format.
# - finishDate (str): Date in YYYY-MM-DD format.
# - ownerId (str): Owning user identifier.
# - sourceSystem (str): Integration source marker.
#
# Optional fields
# ---------------
# - programId (str): Parent program/portfolio identifier.
# - classification (str): Enum; one of strategic | internal | regulatory | customer.
# - createdDate (str): UTC timestamp in ISO-8601 format (YYYY-MM-DDTHH:MM:SSZ).
# - metadata (dict[str, Any]): Additional metadata for traceability.
CLARITY_STATUS_MAP = {
    "new": "DRAFT",
    "draft": "DRAFT",
    "planned": "DRAFT",
    "proposed": "DRAFT",
    "approved": "APPROVED",
    "execution": "IN_PROGRESS",
    "in_progress": "IN_PROGRESS",
    "in-progress": "IN_PROGRESS",
    "on_hold": "ON_HOLD",
    "on-hold": "ON_HOLD",
    "blocked": "ON_HOLD",
    "completed": "COMPLETED",
    "done": "COMPLETED",
    "cancelled": "CANCELLED",
    "canceled": "CANCELLED",
}

CLARITY_ALLOWED_CLASSIFICATIONS = {"strategic", "internal", "regulatory", "customer"}


class MappingValidationError(ValueError):
    """Raised when a canonical record cannot be mapped to valid Clarity payload."""


def map_to_clarity(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map canonical records into validated Clarity outbound payloads.

    Malformed records are skipped with structured warning logs.
    """
    mapped_payloads: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        try:
            payload = _map_record_to_clarity(record)
            _validate_clarity_payload(payload)
        except MappingValidationError as exc:
            logger.warning(
                "Skipping malformed Clarity outbound record",
                extra={
                    "record_index": index,
                    "record_id": record.get("id") if isinstance(record, dict) else None,
                    "reason": str(exc),
                },
            )
            continue
        mapped_payloads.append(payload)
    return mapped_payloads


def _map_record_to_clarity(record: dict[str, Any]) -> dict[str, Any]:
    external_id = _normalize_required_string(record.get("id"), "id")
    name = _normalize_optional_string(record.get("name") or record.get("title"), default=external_id)
    owner_id = _normalize_required_string(record.get("owner") or record.get("owner_id"), "owner")

    status = _normalize_status(record.get("status"))
    start_date = _format_date(record.get("start_date"), field_name="start_date")
    finish_date = _format_date(record.get("end_date"), field_name="end_date")

    classification = _normalize_classification(record.get("classification"))
    created_date = _format_datetime(record.get("created_at"), field_name="created_at")

    metadata = {
        "tenantId": record.get("tenant_id"),
        "schema": record.get("schema"),
        "source": record.get("source"),
    }
    metadata = {key: value for key, value in metadata.items() if value is not None}

    payload: dict[str, Any] = {
        "externalId": external_id,
        "name": name,
        "status": status,
        "startDate": start_date,
        "finishDate": finish_date,
        "ownerId": owner_id,
        "sourceSystem": "canonical-ppm",
    }

    if record.get("program_id") is not None:
        payload["programId"] = _normalize_optional_string(record.get("program_id"))
    if classification is not None:
        payload["classification"] = classification
    if created_date is not None:
        payload["createdDate"] = created_date
    if metadata:
        payload["metadata"] = metadata

    return payload


def _normalize_status(value: Any) -> str:
    normalized = _normalize_required_string(value, "status").lower().replace(" ", "_")
    mapped = CLARITY_STATUS_MAP.get(normalized)
    if mapped is None:
        raise MappingValidationError(f"Unsupported status value: {value}")
    return mapped


def _normalize_classification(value: Any) -> str | None:
    if value is None:
        return None
    normalized = _normalize_optional_string(value).lower()
    if normalized not in CLARITY_ALLOWED_CLASSIFICATIONS:
        raise MappingValidationError(f"Unsupported classification value: {value}")
    return normalized


def _normalize_required_string(value: Any, field_name: str) -> str:
    if value is None:
        raise MappingValidationError(f"Missing required field: {field_name}")
    return _normalize_optional_string(value)


def _normalize_optional_string(value: Any, default: str | None = None) -> str:
    if value is None:
        if default is None:
            raise MappingValidationError("Expected non-null string value")
        return default
    text = str(value).strip()
    if not text:
        if default is None:
            raise MappingValidationError("Expected non-empty string value")
        return default
    return text


def _format_date(value: Any, *, field_name: str) -> str:
    if value is None:
        raise MappingValidationError(f"Missing required field: {field_name}")
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = _normalize_optional_string(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError as exc:
        raise MappingValidationError(f"Invalid date value for {field_name}: {value}") from exc


def _format_datetime(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = _normalize_optional_string(value)
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise MappingValidationError(f"Invalid datetime value for {field_name}: {value}") from exc
    if dt.tzinfo is None:
        return dt.replace(microsecond=0).isoformat() + "Z"
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_clarity_payload(payload: dict[str, Any]) -> None:
    required_fields = ("externalId", "name", "status", "startDate", "finishDate", "ownerId", "sourceSystem")
    for field in required_fields:
        if not payload.get(field):
            raise MappingValidationError(f"Missing required mapped field: {field}")

    if payload["status"] not in set(CLARITY_STATUS_MAP.values()):
        raise MappingValidationError(f"Mapped status is invalid: {payload['status']}")

    start = datetime.fromisoformat(payload["startDate"]).date()
    finish = datetime.fromisoformat(payload["finishDate"]).date()
    if start > finish:
        raise MappingValidationError("startDate cannot be after finishDate")



def map_to_mcp_params(operation: str, canonical_payload: dict[str, Any]) -> dict[str, Any]:
    """Map canonical payloads to Clarity MCP tool parameters.

    Operations
    ----------
    list
        Required fields:
            - resource_type (str): Expected enum: "projects".
        Optional fields:
            - filters (dict[str, Any]): filter clauses; defaults to {}.
            - limit (int): defaults to 100 if omitted.
            - offset (int): defaults to 0 if omitted.
        Type conversions:
            - limit/offset are coerced to int when provided.
    """
    if operation != "list":
        raise ValueError(f"Unsupported Clarity MCP operation: {operation}")

    return {
        "resource_type": canonical_payload.get("resource_type", "projects"),
        "filters": canonical_payload.get("filters") or {},
        "limit": int(canonical_payload.get("limit", 100)),
        "offset": int(canonical_payload.get("offset", 0)),
    }


def map_from_mcp_response(operation: str, tool_response: Any) -> list[dict[str, Any]]:
    """Normalize MCP tool responses into canonical Clarity payloads."""
    if operation != "list":
        raise ValueError(f"Unsupported Clarity MCP operation: {operation}")
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
