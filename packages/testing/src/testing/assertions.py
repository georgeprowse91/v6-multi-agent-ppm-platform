"""Reusable assertion helpers for PPM platform tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def assert_valid_uuid(value: str, *, msg: str | None = None) -> None:
    """Assert that *value* is a valid UUID string.

    Args:
        value: The string to validate.
        msg: Optional custom assertion message.
    """
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise AssertionError(msg or f"Not a valid UUID: {value!r}") from exc


def assert_datetime_recent(
    dt: datetime | str,
    *,
    max_age_seconds: float = 60,
    msg: str | None = None,
) -> None:
    """Assert that a datetime is within *max_age_seconds* of now (UTC).

    Args:
        dt: A :class:`datetime` or ISO-format string.
        max_age_seconds: Maximum allowed age in seconds.
        msg: Optional custom assertion message.
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = abs((now - dt).total_seconds())
    if delta > max_age_seconds:
        raise AssertionError(
            msg or f"Datetime {dt.isoformat()} is {delta:.1f}s old (max {max_age_seconds}s)"
        )


def assert_error_response(
    response: Any,
    *,
    status_code: int,
    detail_contains: str | None = None,
) -> None:
    """Assert that an HTTP response has the expected error status and optional detail text.

    Works with ``httpx.Response`` and ``starlette.testclient`` responses.

    Args:
        response: An HTTP response object with ``.status_code`` and ``.json()`` attributes.
        status_code: Expected HTTP status code.
        detail_contains: Optional substring expected in the ``detail`` field of the JSON body.
    """
    assert (
        response.status_code == status_code
    ), f"Expected status {status_code}, got {response.status_code}: {response.text}"
    if detail_contains is not None:
        body = response.json()
        detail = body.get("detail", "")
        assert (
            detail_contains in detail
        ), f"Expected detail to contain {detail_contains!r}, got {detail!r}"


def assert_json_schema(
    data: dict[str, Any],
    *,
    required_keys: list[str] | None = None,
    type_checks: dict[str, type] | None = None,
) -> None:
    """Lightweight schema assertion for JSON-like dictionaries.

    Args:
        data: The dictionary to validate.
        required_keys: Keys that must be present.
        type_checks: Mapping of key names to expected types.

    Raises:
        AssertionError: When validation fails.
    """
    if required_keys:
        missing = [k for k in required_keys if k not in data]
        if missing:
            raise AssertionError(f"Missing required keys: {missing}")
    if type_checks:
        for key, expected_type in type_checks.items():
            if key in data:
                actual = type(data[key])
                if not isinstance(data[key], expected_type):
                    raise AssertionError(
                        f"Key {key!r}: expected {expected_type.__name__}, got {actual.__name__}"
                    )
