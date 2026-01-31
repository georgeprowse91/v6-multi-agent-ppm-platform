from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

if not os.getenv("ENABLE_CONNECTOR_INTEGRATION_TESTS"):
    pytest.skip(
        "Connector integration tests require ENABLE_CONNECTOR_INTEGRATION_TESTS=1",
        allow_module_level=True,
    )

pytest.importorskip("opentelemetry")

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.modules.pop("connectors", None)

from connectors.jira.src.main import run_sync


def test_fixture_sync_job_maps_records() -> None:
    fixture = Path("connectors/jira/tests/fixtures/projects.json")

    results = run_sync(fixture, "tenant-fixture")

    assert results == [
        {
            "tenant_id": "tenant-fixture",
            "id": "proj-100",
            "program_id": "program-01",
            "name": "Migration Wave 1",
            "status": "execution",
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
            "owner": "program-manager",
            "classification": "internal",
            "created_at": "2024-01-01T00:00:00Z",
        }
    ]
