from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_SRC = REPO_ROOT / "services" / "workflow-service" / "src"
COMMON_SRC = REPO_ROOT / "packages" / "common" / "src"
for path in (WORKFLOW_SRC, COMMON_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from workflow_storage import resolve_workflow_storage


def test_resolve_workflow_storage_dev_allows_default_sqlite() -> None:
    selection = resolve_workflow_storage(environment="development", configured_db_path=None)

    assert str(selection.db_path).endswith("services/workflow-service/storage/workflows.db")
    assert selection.source == "default"
    assert selection.durability_mode == "file-backed"


def test_resolve_workflow_storage_production_rejects_default_sqlite() -> None:
    with pytest.raises(ValueError, match="WORKFLOW_DB_PATH"):
        resolve_workflow_storage(environment="production", configured_db_path=None)
