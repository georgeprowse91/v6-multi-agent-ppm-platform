import pytest
from process_mining_agent import ProcessMiningAgent


class WorkflowMock:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.events.append(input_data)
        return {"status": "ok"}


class EventBusMock:
    def __init__(self) -> None:
        self.subscribers: dict[str, list] = {}
        self.published: list[dict] = []

    def subscribe(self, topic: str, handler) -> None:
        self.subscribers.setdefault(topic, []).append(handler)

    async def publish(self, topic: str, payload: dict) -> None:
        self.published.append({"topic": topic, "payload": payload})

    async def emit(self, topic: str, payload: dict) -> None:
        for handler in self.subscribers.get(topic, []):
            result = handler(payload)
            if hasattr(result, "__await__"):
                await result

    def get_metrics(self) -> dict[str, int]:
        return {}

    def get_recent_events(self, topic: str | None = None) -> list:
        return []


@pytest.mark.asyncio
async def test_process_mining_persists_logs_and_emits_recommendations(tmp_path):
    workflow_mock = WorkflowMock()
    agent = ProcessMiningAgent(
        config={
            "event_log_store_path": tmp_path / "event_logs.json",
            "workflow_engine_agent": workflow_mock,
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
    assert workflow_mock.events
    assert workflow_mock.events[0]["action"] == "handle_event"


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
async def test_process_mining_discovers_and_checks_conformance(tmp_path):
    event_bus = EventBusMock()
    agent = ProcessMiningAgent(
        config={
            "event_log_store_path": tmp_path / "event_logs.json",
            "process_model_store_path": tmp_path / "process_models.json",
            "conformance_store_path": tmp_path / "conformance.json",
            "event_bus": event_bus,
        }
    )
    await agent.initialize()

    await agent.process(
        {
            "action": "ingest_event_log",
            "tenant_id": "tenant-process",
            "events": [
                {
                    "timestamp": "2024-01-01T00:00:00",
                    "activity": "A",
                    "process_id": "proc-2",
                    "case_id": "case-1",
                },
                {
                    "timestamp": "2024-01-01T01:00:00",
                    "activity": "C",
                    "process_id": "proc-2",
                    "case_id": "case-1",
                },
            ],
        }
    )

    discovery = await agent.process(
        {"action": "discover_process", "tenant_id": "tenant-process", "process_id": "proc-2"}
    )
    assert discovery["activities"] > 0

    report = await agent.process(
        {
            "action": "check_conformance",
            "tenant_id": "tenant-process",
            "process_id": "proc-2",
            "expected_model": {
                "activities": ["A", "B", "C"],
                "transitions": [{"from": "A", "to": "B"}, {"from": "B", "to": "C"}],
            },
        }
    )

    assert report["compliance_rate"] < 100


@pytest.mark.asyncio
async def test_process_mining_ingests_event_bus_events(tmp_path):
    event_bus = EventBusMock()
    agent = ProcessMiningAgent(
        config={
            "event_log_store_path": tmp_path / "event_logs.json",
            "event_bus": event_bus,
            "event_topics": ["task.started"],
        }
    )
    await agent.initialize()

    await event_bus.emit(
        "task.started",
        {
            "event_type": "task.started",
            "timestamp": "2024-01-01T00:00:00",
            "data": {"process_id": "proc-3", "case_id": "case-9", "tenant_id": "tenant-bus"},
        },
    )

    stored_logs = agent.event_log_store.list("tenant-bus")
    assert stored_logs


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
