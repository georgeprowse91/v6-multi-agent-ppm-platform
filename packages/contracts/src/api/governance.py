"""Shared API governance contract definitions."""

from __future__ import annotations

from dataclasses import dataclass

API_VERSION = "1.0.0"
API_PREFIX = "/v1"

AUTH_HEADERS = {
    "Authorization": "Bearer <token>",
    "X-Tenant-ID": "Tenant scope for multi-tenant requests",
}

CORRELATION_ID_HEADER = "X-Correlation-ID"
PAGINATION_HEADERS = ("X-Page", "X-Page-Size", "X-Total-Count", "Link")


@dataclass(frozen=True, slots=True)
class ErrorEnvelopeRule:
    root_key: str = "error"
    message_key: str = "message"
    code_key: str = "code"
    details_key: str = "details"
    correlation_id_key: str = "correlation_id"


ERROR_ENVELOPE_RULE = ErrorEnvelopeRule()
