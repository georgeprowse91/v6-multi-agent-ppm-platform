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
