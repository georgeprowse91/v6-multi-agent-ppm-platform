from __future__ import annotations

import hashlib
import os
import re
from typing import Any

PII_FIELD_NAMES = {
    "address",
    "birthdate",
    "date_of_birth",
    "dob",
    "email",
    "employee_id",
    "first_name",
    "full_name",
    "last_name",
    "phone",
    "phone_number",
    "ssn",
    "social_security_number",
    "user_id",
    "username",
}

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}", re.IGNORECASE)
SSN_RE = re.compile(r"\\b\\d{3}-\\d{2}-\\d{4}\\b")
PHONE_RE = re.compile(r"\\+?\\d[\\d\\s().-]{7,}\\d")


def _mask_value(value: str, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:16]
    return f"masked_{digest}"


def _contains_pii(value: str) -> bool:
    return bool(EMAIL_RE.search(value) or SSN_RE.search(value) or PHONE_RE.search(value))


def mask_lineage_payload(payload: Any, *, salt: str | None = None) -> Any:
    """Deterministically mask PII in lineage payloads."""
    effective_salt = salt or os.getenv("LINEAGE_MASK_SALT")
    if not effective_salt:
        raise ValueError("LINEAGE_MASK_SALT is required to mask lineage payloads")

    if isinstance(payload, dict):
        masked: dict[str, Any] = {}
        for key, value in payload.items():
            if key.lower() in PII_FIELD_NAMES and value is not None:
                masked[key] = _mask_value(str(value), effective_salt)
            else:
                masked[key] = mask_lineage_payload(value, salt=effective_salt)
        return masked

    if isinstance(payload, list):
        return [mask_lineage_payload(item, salt=effective_salt) for item in payload]

    if isinstance(payload, tuple):
        return tuple(mask_lineage_payload(item, salt=effective_salt) for item in payload)

    if isinstance(payload, str) and _contains_pii(payload):
        return _mask_value(payload, effective_salt)

    return payload
