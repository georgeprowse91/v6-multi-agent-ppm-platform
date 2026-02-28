"""
Integration tests for Planview connector runtime mapping.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integrations.connectors.planview.src.main import run_sync


def test_planview_runtime_mapping_projects() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "projects.json"
    results = run_sync(fixture_path, tenant_id="tenant-123")

    assert results == [
        {
            "tenant_id": "tenant-123",
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
