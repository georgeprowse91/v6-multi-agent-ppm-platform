from __future__ import annotations

from typing import Any


SENSITIVE_FIELDS = {"ssn", "social_security", "credit_card", "iban", "passport"}
CONFIDENTIAL_FIELDS = {"salary", "compensation", "bonus", "health"}


def infer_classification(record: dict[str, Any], mapped: dict[str, Any]) -> str:
    explicit = record.get("classification") or mapped.get("classification")
    if explicit:
        return str(explicit)
    fields = set(record.keys()) | set(mapped.keys())
    if fields.intersection(SENSITIVE_FIELDS):
        return "restricted"
    if fields.intersection(CONFIDENTIAL_FIELDS):
        return "confidential"
    return "internal"
