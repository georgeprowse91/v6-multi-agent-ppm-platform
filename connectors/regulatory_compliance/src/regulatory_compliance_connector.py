"""
Regulatory Compliance Connector Implementation.

Integrates with GRC/compliance platforms for HIPAA and FDA CFR 21 Part 11 audit trails.

Supports:
- API key authentication
- Reading audit logs, compliance events, regulations, and findings
- Writing audit logs and findings
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths(_REPO_ROOT)

from base_connector import ConnectorCategory, ConnectorConfig  # noqa: E402
from rest_connector import ApiKeyRestConnector  # noqa: E402


class RegulatoryComplianceConnector(ApiKeyRestConnector):
    """Connector for regulatory compliance APIs (HIPAA, FDA CFR 21 Part 11).

    Integrates with GRC platforms to synchronize audit trails, compliance events,
    regulation definitions, and compliance findings.

    Environment variables required:
    - REGULATORY_COMPLIANCE_ENDPOINT: The compliance API base URL
    - REGULATORY_COMPLIANCE_API_KEY: API key for authentication
    """

    CONNECTOR_ID = "regulatory_compliance"
    CONNECTOR_NAME = "Regulatory Compliance"
    CONNECTOR_VERSION = "1.0.0"
    CONNECTOR_CATEGORY = ConnectorCategory.COMPLIANCE
    SUPPORTS_WRITE = True
    RATE_LIMIT_PER_MINUTE = 100

    API_KEY_ENV = "REGULATORY_COMPLIANCE_API_KEY"
    INSTANCE_URL_ENV = "REGULATORY_COMPLIANCE_ENDPOINT"
    API_KEY_HEADER = "Authorization"
    API_KEY_PREFIX = "Bearer"

    AUTH_TEST_ENDPOINT = "/health"

    IDEMPOTENCY_FIELDS = ("id", "external_id", "event_id")
    CONFLICT_TIMESTAMP_FIELD = "updated_at"

    RESOURCE_PATHS = {
        "audit_logs": {
            "path": "/api/v1/audit-logs",
            "items_path": "items",
            "write_path": "/api/v1/audit-logs",
            "write_method": "POST",
        },
        "compliance_events": {
            "path": "/api/v1/events",
            "items_path": "items",
        },
        "regulations": {
            "path": "/api/v1/regulations",
            "items_path": "items",
        },
        "findings": {
            "path": "/api/v1/findings",
            "items_path": "items",
            "write_path": "/api/v1/findings",
            "write_method": "POST",
        },
    }

    SCHEMA = {
        "audit_logs": {
            "id": "string",
            "event_type": "string",
            "actor": "string",
            "action": "string",
            "resource": "string",
            "timestamp": "datetime",
            "details": "object",
            "regulation": "string",
            "compliance_status": "string",
        },
        "compliance_events": {
            "id": "string",
            "event_type": "string",
            "regulation": "string",
            "severity": "string",
            "description": "string",
            "timestamp": "datetime",
            "status": "string",
        },
        "regulations": {
            "id": "string",
            "name": "string",
            "code": "string",
            "description": "string",
            "category": "string",
            "effective_date": "date",
            "status": "string",
        },
        "findings": {
            "id": "string",
            "title": "string",
            "regulation": "string",
            "severity": "string",
            "status": "string",
            "description": "string",
            "remediation": "string",
            "due_date": "date",
            "assigned_to": "string",
        },
    }

    def __init__(self, config: ConnectorConfig, **kwargs: object) -> None:
        super().__init__(config, **kwargs)


def create_regulatory_compliance_connector(
    endpoint_url: str = "",
    sync_direction: str = "inbound",
    sync_frequency: str = "daily",
    transport: Any | None = None,
) -> RegulatoryComplianceConnector:
    """Factory function to create a RegulatoryComplianceConnector instance.

    Args:
        endpoint_url: Optional compliance API URL (can also use env var).
        sync_direction: 'inbound', 'outbound', or 'bidirectional'.
        sync_frequency: Sync frequency setting.
        transport: Optional HTTP transport for testing.

    Returns:
        Configured RegulatoryComplianceConnector instance.
    """
    from base_connector import SyncDirection, SyncFrequency

    config = ConnectorConfig(
        connector_id="regulatory_compliance",
        name="Regulatory Compliance",
        category=ConnectorCategory.COMPLIANCE,
        enabled=True,
        sync_direction=SyncDirection(sync_direction),
        sync_frequency=SyncFrequency(sync_frequency),
        instance_url=endpoint_url,
    )

    return RegulatoryComplianceConnector(config, transport=transport)
