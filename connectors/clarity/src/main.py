from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from connectors.sdk.src.runtime import ConnectorRuntime
from connectors.sdk.src.secrets import resolve_secret

from .clarity_connector import ClarityConnector, create_clarity_connector

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]


def _ensure_source(records: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    return [{"source": source, **record} for record in records]


def run_sync(
    fixture_path: Path | None,
    tenant_id: str,
    *,
    live: bool = False,
    connector: ClarityConnector | None = None,
    include_schema: bool = False,
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    if fixture_path and not live:
        return runtime.run_sync(fixture_path, tenant_id, include_schema=include_schema)

    if connector is None:
        instance_url = resolve_secret(os.getenv("CLARITY_INSTANCE_URL")) or ""
        connector = create_clarity_connector(instance_url=instance_url)

    records = _ensure_source(connector.read("projects"), "project")
    return runtime.apply_mappings(records, tenant_id, include_schema=include_schema)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Run connector sync against a fixture file")
    parser.add_argument("fixture", nargs="?", type=str, help="Path to fixture JSON")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--live", action="store_true", help="Run against live API using env vars")
    args = parser.parse_args()

    fixture = Path(args.fixture) if args.fixture else None
    output = run_sync(fixture, args.tenant, live=args.live)
    print(json.dumps(output, indent=2))


# New outbound hook placeholder. Later, this should send data to Clarity via real API.
def send_to_external_system(records: list[dict[str, object]], tenant_id: str, *, include_schema: bool) -> None:
    """
    Placeholder outbound handler for Clarity.
    This function currently logs the records to be written and performs no external calls.

    Args:
        records: Mapped records in the canonical schema.
        tenant_id: Tenant identifier.
        include_schema: Whether the mapped records include schema metadata.
    """
    import logging
    logging.getLogger(__name__).info(
        "Outbound payload for Clarity tenant %s (include_schema=%s): %s",
        tenant_id,
        include_schema,
        records,
    )
