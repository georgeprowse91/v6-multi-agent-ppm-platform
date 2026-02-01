from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[3]
SRC_DIR = TESTS_DIR.parent / "src"
OBSERVABILITY_SRC = REPO_ROOT / "packages" / "observability" / "src"
SECURITY_SRC = REPO_ROOT / "packages" / "security" / "src"

sys.path.extend([str(REPO_ROOT), str(SRC_DIR), str(OBSERVABILITY_SRC), str(SECURITY_SRC)])

from data_sync_agent import DataSyncAgent


class FakeConnector:
    def __init__(self, records: list[dict[str, object]]) -> None:
        self.records = records

    def read(self, _entity_type: str, filters: dict[str, object] | None = None) -> list[dict[str, object]]:
        return self.records


@pytest.mark.anyio
async def test_mapping_and_schema_validation() -> None:
    agent = DataSyncAgent(
        config={
            "mapping_rules_path": "config/agent-23/mapping_rules.yaml",
            "schema_registry_path": "config/agent-23/schema_registry.yaml",
        }
    )
    agent.validation_rules = agent._load_validation_rules()
    agent.transformation_rules = agent._load_mapping_rules()
    agent.schema_registry, agent.schema_versions = agent._load_schema_registry()

    mapped = await agent._map_to_canonical(
        "tasks",
        {"key": "TASK-1", "summary": " Test task ", "status": "Open", "project_id": "P-1"},
        "jira",
    )

    assert mapped["id"] == "TASK-1"
    assert mapped["name"].strip() == "Test task"

    valid_payload = {
        "id": "TASK-1",
        "name": "Test task",
        "status": "Open",
        "project_id": "P-1",
    }
    validation = await agent._validate_data("tasks", valid_payload)
    assert validation["valid"] is True

    invalid_payload = {"id": "TASK-1", "name": "Test task", "status": "Open"}
    invalid = await agent._validate_data("tasks", invalid_payload)
    assert invalid["valid"] is False
    assert invalid["errors"]


@pytest.mark.anyio
async def test_conflict_resolution_last_write_wins() -> None:
    agent = DataSyncAgent()
    master_record = {
        "data": {"status": "Open", "updated_at": "2024-02-01T10:00:00"},
        "updated_at": "2024-02-01T10:00:00",
    }
    new_data = {"status": "Closed", "updated_at": "2024-01-01T10:00:00"}
    conflicts = await agent._detect_update_conflicts(master_record, new_data, "jira")
    resolved = await agent._apply_conflict_resolution(master_record, new_data, conflicts)

    assert resolved["status"] == "Open"


@pytest.mark.anyio
async def test_full_sync_updates_state() -> None:
    agent = DataSyncAgent(
        config={
            "schema_registry_path": "config/agent-23/schema_registry.yaml",
        }
    )
    agent.schema_registry, agent.schema_versions = agent._load_schema_registry()
    agent.transformation_rules = []
    agent.connectors = {
        "planview": FakeConnector(
            [{"id": "P-100", "name": "Apollo", "status": "Active"}]
        )
    }

    result = await agent._run_sync(
        tenant_id="tenant-a",
        entity_type="projects",
        source_system="planview",
        mode="full",
        filters={},
    )

    assert result["records_processed"] == 1
    state_records = agent.sync_state_store.list("tenant-a")
    assert any(record["entity_type"] == "projects" for record in state_records)
