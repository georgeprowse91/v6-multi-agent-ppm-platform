"""
Integration tests for Clarity connector runtime mapping.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integrations.connectors.clarity.src.main import run_sync


def test_clarity_runtime_mapping_projects() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "projects.json"
    results = run_sync(fixture_path, tenant_id="tenant-123")

    assert results == [
        {
            "tenant_id": "tenant-123",
            "id": "clarity-100",
            "program_id": "portfolio-01",
            "name": "Core Platform Upgrade",
            "status": "approved",
            "start_date": "2024-03-01",
            "end_date": "2024-12-31",
            "owner": "delivery-lead",
            "classification": "strategic",
            "created_at": "2024-01-20T00:00:00Z",
        }
    ]
