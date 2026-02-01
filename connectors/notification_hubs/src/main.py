from __future__ import annotations

from pathlib import Path
from typing import Any

from connectors.sdk.src.runtime import ConnectorRuntime

CONNECTOR_ROOT = Path(__file__).resolve().parents[1]


def run_sync(
    fixture_path: Path, tenant_id: str, *, include_schema: bool = False
) -> list[dict[str, Any]]:
    runtime = ConnectorRuntime(CONNECTOR_ROOT)
    return runtime.run_sync(fixture_path, tenant_id, include_schema=include_schema)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Run connector sync against a fixture file")
    parser.add_argument("fixture", type=str, help="Path to fixture JSON")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    args = parser.parse_args()

    output = run_sync(Path(args.fixture), args.tenant)
    print(json.dumps(output, indent=2))
