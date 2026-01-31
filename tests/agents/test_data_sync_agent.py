import json

import pytest
from data_sync_agent import DataSyncAgent


class FakeEventBus:
    def __init__(self):
        self.published = []
        self.metrics = {}

    def subscribe(self, topic, handler):
        return None

    async def publish(self, topic, payload):
        self.published.append((topic, payload))
        self.metrics[topic] = self.metrics.get(topic, 0) + 1

    def get_metrics(self):
        return dict(self.metrics)

    def get_recent_events(self, topic=None):
        return []


@pytest.mark.asyncio
async def test_data_sync_persists_and_emits_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("LINEAGE_MASK_SALT", "unit-test-salt")
    event_bus = FakeEventBus()
    agent = DataSyncAgent(
        config={
            "master_record_store_path": tmp_path / "master.json",
            "sync_event_store_path": tmp_path / "events.json",
            "sync_lineage_store_path": tmp_path / "lineage.json",
            "sync_audit_store_path": tmp_path / "audit.json",
            "event_bus": event_bus,
        }
    )
    await agent.initialize()

    created = await agent.process(
        {
            "action": "create_master_record",
            "tenant_id": "tenant-sync",
            "entity_type": "project",
            "data": {"id": "proj-1", "name": "Apollo"},
        }
    )
    master_id = created["master_id"]
    assert agent.master_record_store.get("tenant-sync", master_id)

    await agent.process(
        {
            "action": "update_master_record",
            "tenant_id": "tenant-sync",
            "master_id": master_id,
            "data": {"owner": "jane.doe@example.com"},
            "source_system": "jira",
        }
    )

    audits = agent.sync_audit_store.list("tenant-sync")
    assert len(audits) >= 2

    sync = await agent.process(
        {
            "action": "sync_data",
            "tenant_id": "tenant-sync",
            "entity_type": "project",
            "data": {"id": "proj-2", "name": "Gemini", "email": "owner@example.com"},
            "source_system": "sap",
        }
    )
    assert agent.sync_event_store.get("tenant-sync", sync["sync_event_id"])
    assert sync["latency_seconds"] >= 0
    assert any(topic == "sync.started" for topic, _payload in event_bus.published)
    assert any(topic == "sync.succeeded" for topic, _payload in event_bus.published)

    lineage_records = agent.sync_lineage_store.list("tenant-sync")
    assert lineage_records
    assert "owner@example.com" not in json.dumps(lineage_records)


@pytest.mark.asyncio
async def test_data_sync_get_status_success(tmp_path):
    agent = DataSyncAgent(
        config={
            "master_record_store_path": tmp_path / "master.json",
            "sync_event_store_path": tmp_path / "events.json",
        }
    )
    await agent.initialize()

    response = await agent.process({"action": "get_sync_status", "tenant_id": "tenant-sync"})

    assert "total_sync_events" in response
    assert "success_rate" in response


@pytest.mark.asyncio
async def test_data_sync_validation_rejects_invalid_action(tmp_path):
    agent = DataSyncAgent(
        config={
            "master_record_store_path": tmp_path / "master.json",
            "sync_event_store_path": tmp_path / "events.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_data_sync_validation_rejects_missing_fields(tmp_path):
    agent = DataSyncAgent(
        config={
            "master_record_store_path": tmp_path / "master.json",
            "sync_event_store_path": tmp_path / "events.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "sync_data", "entity_type": "project"})

    assert valid is False


@pytest.mark.asyncio
async def test_data_sync_discards_duplicates(tmp_path):
    import os

    os.environ["LINEAGE_MASK_SALT"] = "unit-test-salt"
    event_bus = FakeEventBus()
    agent = DataSyncAgent(
        config={
            "master_record_store_path": tmp_path / "master.json",
            "sync_event_store_path": tmp_path / "events.json",
            "event_bus": event_bus,
        }
    )
    await agent.initialize()

    payload = {
        "action": "sync_data",
        "tenant_id": "tenant-sync",
        "entity_type": "project",
        "data": {"id": "proj-dup", "name": "Duplicated"},
        "source_system": "jira",
    }

    first = await agent.process(payload)
    second = await agent.process(payload)

    assert first["status"] == "success"
    assert second["status"] == "duplicate"
