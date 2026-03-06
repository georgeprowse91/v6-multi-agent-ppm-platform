from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from connectors.sdk.src.http_client import HttpClient
from connectors.sdk.src.runtime import ConnectorRuntime
from connector_secrets import resolve_secret
from connectors.regulatory_compliance.src.regulatory_compliance_connector import (
    RegulatoryComplianceConnector,
)
from connectors.sdk.src.base_connector import (
    ConnectorCategory,
    ConnectorConfig,
    SyncDirection,
    SyncFrequency,
)

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class ComplianceConfig:
    endpoint_url: str
    api_key: str
    rate_limit_per_minute: int

    @classmethod
    def from_env(cls, rate_limit_per_minute: int) -> "ComplianceConfig":
        endpoint_url = resolve_secret(os.getenv("REGULATORY_COMPLIANCE_ENDPOINT"))
        api_key = resolve_secret(os.getenv("REGULATORY_COMPLIANCE_API_KEY"))
        if not endpoint_url or not api_key:
            raise ValueError(
                "REGULATORY_COMPLIANCE_ENDPOINT and REGULATORY_COMPLIANCE_API_KEY are required"
            )
        return cls(
            endpoint_url=endpoint_url,
            api_key=api_key,
            rate_limit_per_minute=rate_limit_per_minute,
        )


def _build_client(
    config: ComplianceConfig, transport: Any | None = None
) -> HttpClient:
    return HttpClient(
        base_url=config.endpoint_url,
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Accept": "application/json",
        },
        timeout=30.0,
        rate_limit_per_minute=config.rate_limit_per_minute,
        transport=transport,
    )


def _compliance_status(status: str | None) -> str:
    if not status:
        return "unknown"
    normalized = status.strip().lower()
    if normalized in {"compliant", "passed", "pass"}:
        return "compliant"
    if normalized in {"non_compliant", "failed", "fail", "violation"}:
        return "non_compliant"
    if normalized in {"in_review", "pending", "under_review"}:
        return "in_review"
    return normalized


def _severity_level(severity: str | None) -> str:
    if not severity:
        return "medium"
    normalized = severity.strip().lower()
    if normalized in {"critical", "high", "medium", "low", "info"}:
        return normalized
    return "medium"


def _fetch_audit_logs(client: HttpClient) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    response = client.get("/api/v1/audit-logs", params={"limit": 100, "offset": 0})
    data = response.json()
    items = data.get("items", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return records
    for item in items:
        records.append(
            {
                "source": "audit_trail",
                "id": item.get("id"),
                "event_type": item.get("event_type"),
                "actor": item.get("actor"),
                "action": item.get("action"),
                "resource": item.get("resource"),
                "timestamp": item.get("timestamp"),
                "regulation": item.get("regulation"),
                "compliance_status": _compliance_status(item.get("compliance_status")),
                "details": item.get("details"),
            }
        )
    return records


def _fetch_compliance_events(client: HttpClient) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    response = client.get("/api/v1/events", params={"limit": 100, "offset": 0})
    data = response.json()
    items = data.get("items", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return records
    for item in items:
        records.append(
            {
                "source": "compliance_event",
                "id": item.get("id"),
                "event_type": item.get("event_type"),
                "regulation": item.get("regulation"),
                "severity": _severity_level(item.get("severity")),
                "description": item.get("description"),
                "timestamp": item.get("timestamp"),
                "status": _compliance_status(item.get("status")),
            }
        )
    return records


def _fetch_findings(client: HttpClient) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    response = client.get("/api/v1/findings", params={"limit": 100, "offset": 0})
    data = response.json()
    items = data.get("items", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return records
    for item in items:
        records.append(
            {
                "source": "finding",
                "id": item.get("id"),
                "title": item.get("title"),
                "regulation": item.get("regulation"),
                "severity": _severity_level(item.get("severity")),
                "status": _compliance_status(item.get("status")),
                "description": item.get("description"),
                "remediation": item.get("remediation"),
                "due_date": item.get("due_date"),
                "assigned_to": item.get("assigned_to"),
            }
        )
    return records


def run_sync(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    client: HttpClient | None = None,
    config: ComplianceConfig | None = None,
    include_schema: bool = False,
) -> list[dict[str, Any]]:
    """Run sync against a fixture file or live compliance API."""
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id, include_schema=include_schema)

    rate_limit = runtime.manifest.sync.get("rate_limit_per_minute", 100)
    config = config or ComplianceConfig.from_env(rate_limit)
    client = client or _build_client(config)
    records = _fetch_audit_logs(client)
    records.extend(_fetch_compliance_events(client))
    records.extend(_fetch_findings(client))
    return runtime.apply_mappings(records, tenant_id, include_schema=include_schema)


def run_write(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    client: HttpClient | None = None,
    config: ComplianceConfig | None = None,
    data: list[dict[str, Any]] | None = None,
    resource_type: str = "audit_logs",
) -> list[dict[str, Any]]:
    """Write records to the compliance API."""
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path:
        raw = json.loads(fixture_path.read_text())
        if not isinstance(raw, list):
            raise ValueError("Fixture must be a list of records")
        payload = raw
    elif data is not None:
        payload = data
    else:
        raise ValueError("No records provided for write operation")

    rate_limit = runtime.manifest.sync.get("rate_limit_per_minute", 100)
    config = config or ComplianceConfig.from_env(rate_limit)
    client = client or _build_client(config)

    connector_config = ConnectorConfig(
        connector_id="regulatory_compliance",
        name="Regulatory Compliance",
        category=ConnectorCategory.COMPLIANCE,
        enabled=True,
        sync_direction=SyncDirection.BIDIRECTIONAL,
        sync_frequency=SyncFrequency.MANUAL,
        instance_url=config.endpoint_url if config else "",
    )
    connector = RegulatoryComplianceConnector(connector_config, client=client)
    connector.authenticate()
    return connector.write(resource_type, payload)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run regulatory compliance connector sync against a fixture file"
    )
    parser.add_argument("fixture", nargs="?", type=str, help="Path to fixture JSON")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument(
        "--live", action="store_true", help="Run against live API using env vars"
    )
    parser.add_argument(
        "--write", action="store_true", help="Write records instead of sync"
    )
    parser.add_argument(
        "--resource-type",
        default="audit_logs",
        help="Resource type for write operations (default: audit_logs)",
    )
    args = parser.parse_args()

    fixture = Path(args.fixture) if args.fixture else None
    if args.write:
        output = run_write(
            fixture, args.tenant, live=args.live, resource_type=args.resource_type
        )
    else:
        output = run_sync(fixture, args.tenant, live=args.live)
    print(json.dumps(output, indent=2))
