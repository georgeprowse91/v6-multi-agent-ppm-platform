from __future__ import annotations

from pathlib import Path

from connectors.jira.src.main import run_sync


def test_fixture_sync_job_maps_records() -> None:
    fixture = Path("connectors/jira/tests/fixtures/projects.json")

    results = run_sync(fixture, "tenant-fixture")

    assert results == [
        {
            "tenant_id": "tenant-fixture",
            "id": "proj-100",
            "name": "Migration Wave 1",
            "status": "active",
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
            "owner": "program-manager",
        }
    ]
