from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[3]
SRC_DIR = TESTS_DIR.parent / "src"
OBSERVABILITY_SRC = REPO_ROOT / "packages" / "observability" / "src"
SECURITY_SRC = REPO_ROOT / "packages" / "security" / "src"
FEATURE_FLAGS_SRC = REPO_ROOT / "packages" / "feature-flags" / "src"
sys.path.extend([str(REPO_ROOT), str(SRC_DIR), str(OBSERVABILITY_SRC), str(SECURITY_SRC), str(FEATURE_FLAGS_SRC)])

import types
from typing import Any, Callable

_event_bus_stub = types.ModuleType("event_bus")
_event_bus_stub.EventHandler = Callable[[dict[str, Any]], None]
_event_bus_stub.EventRecord = dict[str, Any]


class _StubServiceBusEventBus:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.args = args
        self.kwargs = kwargs


def _stub_get_event_bus(*_args: object, **_kwargs: object) -> _StubServiceBusEventBus:
    return _StubServiceBusEventBus()


_event_bus_stub.ServiceBusEventBus = _StubServiceBusEventBus
_event_bus_stub.get_event_bus = _stub_get_event_bus
sys.modules.setdefault("event_bus", _event_bus_stub)

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


class _FakeSecret:
    def __init__(self, value: str | None) -> None:
        self.value = value


class _FakeSecretClient:
    def __init__(self, vault_url: str, credential: object) -> None:
        self._vault_url = vault_url

    def get_secret(self, name: str) -> _FakeSecret:
        values = {
            "https://vault-a": {"PLANVIEW_CLIENT_ID": "tenant-a-client"},
            "https://vault-b": {"PLANVIEW_CLIENT_ID": "tenant-b-client"},
        }
        return _FakeSecret(values.get(self._vault_url, {}).get(name))


@pytest.mark.anyio
async def test_keyvault_initialization_is_task_local_and_does_not_mutate_process_env(monkeypatch: pytest.MonkeyPatch) -> None:
    secret_names = [
        "PLANVIEW_CLIENT_ID",
        "PLANVIEW_CLIENT_SECRET",
        "PLANVIEW_REFRESH_TOKEN",
        "PLANVIEW_INSTANCE_URL",
        "SAP_USERNAME",
        "SAP_PASSWORD",
        "SAP_URL",
        "JIRA_EMAIL",
        "JIRA_API_TOKEN",
        "JIRA_INSTANCE_URL",
        "WORKDAY_CLIENT_ID",
        "WORKDAY_CLIENT_SECRET",
        "WORKDAY_REFRESH_TOKEN",
        "WORKDAY_API_URL",
    ]
    for secret_name in secret_names:
        monkeypatch.delenv(secret_name, raising=False)

    monkeypatch.setattr("data_sync_agent.DefaultAzureCredential", lambda: object())
    monkeypatch.setattr("data_sync_agent.SecretClient", _FakeSecretClient)

    agent_a = DataSyncAgent(config={"secrets": {"AZURE_KEY_VAULT_URL": "https://vault-a"}})
    agent_b = DataSyncAgent(config={"secrets": {"AZURE_KEY_VAULT_URL": "https://vault-b"}})

    await asyncio.gather(
        agent_a._initialize_key_vault_secrets(),
        agent_b._initialize_key_vault_secrets(),
    )

    assert agent_a.secret_context.get("PLANVIEW_CLIENT_ID") == "tenant-a-client"
    assert agent_b.secret_context.get("PLANVIEW_CLIENT_ID") == "tenant-b-client"
    assert os.getenv("PLANVIEW_CLIENT_ID") is None


@pytest.mark.anyio
async def test_get_setting_prefers_secret_context_over_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_SERVICE_BUS_CONNECTION_STRING", "from-env")
    agent = DataSyncAgent(config={"secrets": {"AZURE_SERVICE_BUS_CONNECTION_STRING": "from-context"}})

    assert agent._get_setting("AZURE_SERVICE_BUS_CONNECTION_STRING") == "from-context"
