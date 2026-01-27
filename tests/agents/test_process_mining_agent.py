import pytest
from process_mining_agent import ProcessMiningAgent


class WorkflowStub:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.events.append(input_data)
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_process_mining_persists_logs_and_emits_recommendations(tmp_path):
    workflow_stub = WorkflowStub()
    agent = ProcessMiningAgent(
        config={
            "event_log_store_path": tmp_path / "event_logs.json",
            "workflow_engine_agent": workflow_stub,
        }
    )
    await agent.initialize()

    ingest = await agent.process(
        {
            "action": "ingest_event_log",
            "tenant_id": "tenant-process",
            "events": [
                {
                    "timestamp": "2024-01-01T00:00:00",
                    "activity": "start",
                    "process_id": "proc-1",
                }
            ],
        }
    )
    assert agent.event_log_store.get("tenant-process", ingest["log_id"]) is not None

    improvement = await agent.process(
        {
            "action": "create_improvement",
            "tenant_id": "tenant-process",
            "improvement": {
                "title": "Reduce cycle time",
                "description": "Address approval bottleneck",
                "process_id": "proc-1",
                "category": "throughput",
            },
        }
    )

    assert improvement["improvement_id"]
    assert workflow_stub.events
    assert workflow_stub.events[0]["action"] == "handle_event"


@pytest.mark.asyncio
async def test_process_mining_get_insights_success(tmp_path):
    agent = ProcessMiningAgent(config={"event_log_store_path": tmp_path / "event_logs.json"})
    await agent.initialize()

    await agent.process(
        {
            "action": "ingest_event_log",
            "tenant_id": "tenant-process",
            "events": [
                {
                    "timestamp": "2024-01-01T00:00:00",
                    "activity": "start",
                    "process_id": "proc-1",
                }
            ],
        }
    )

    response = await agent.process(
        {
            "action": "get_process_insights",
            "tenant_id": "tenant-process",
            "process_id": "proc-1",
        }
    )

    assert response["process_id"] == "proc-1"


@pytest.mark.asyncio
async def test_process_mining_validation_rejects_invalid_action(tmp_path):
    agent = ProcessMiningAgent(config={"event_log_store_path": tmp_path / "event_logs.json"})
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_process_mining_validation_rejects_missing_events(tmp_path):
    agent = ProcessMiningAgent(config={"event_log_store_path": tmp_path / "event_logs.json"})
    await agent.initialize()

    valid = await agent.validate_input({"action": "ingest_event_log"})

    assert valid is False
