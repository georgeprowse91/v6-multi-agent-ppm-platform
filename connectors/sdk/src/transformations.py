from __future__ import annotations

from datetime import datetime
from typing import Any


class TransformationError(ValueError):
    pass


def _apply_lookup(value: Any, mapping: dict[str, Any], default: Any = None) -> Any:
    if value is None:
        return default
    return mapping.get(str(value), default if default is not None else value)


def _apply_date(value: Any, fmt: str | None = None) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    raw = str(value)
    if fmt:
        parsed = datetime.strptime(raw, fmt)
        return parsed.date().isoformat()
    try:
        return datetime.fromisoformat(raw).date().isoformat()
    except ValueError as exc:
        raise TransformationError(f"Invalid date value: {value}") from exc


def _apply_datetime(value: Any, fmt: str | None = None) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    raw = str(value)
    if fmt:
        parsed = datetime.strptime(raw, fmt)
        return parsed.isoformat()
    try:
        return datetime.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise TransformationError(f"Invalid datetime value: {value}") from exc


def apply_transformation(value: Any, transform: dict[str, Any] | None) -> Any:
    if not transform:
        return value
    transform_type = transform.get("type")
    if transform_type in {"lookup", "enum"}:
        return _apply_lookup(value, transform.get("mapping", {}), transform.get("default"))
    if transform_type == "date":
        return _apply_date(value, transform.get("format"))
    if transform_type == "datetime":
        return _apply_datetime(value, transform.get("format"))
    if transform_type == "upper":
        return str(value).upper() if value is not None else None
    if transform_type == "lower":
        return str(value).lower() if value is not None else None
    if transform_type == "trim":
        return str(value).strip() if value is not None else None
    return value
