import pytest
from schedule_planning_agent import SchedulePlanningAgent


class EventCollector:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.events.append((topic, payload))


class ChangeStub:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def process(self, input_data: dict) -> dict:
        self.requests.append(input_data)
        return {"change_id": "chg-1", "status": "submitted"}


@pytest.mark.asyncio
async def test_schedule_planning_cpm_and_monte_carlo():
    agent = SchedulePlanningAgent(config={"simulation_seed": 7})
    await agent.initialize()

    tasks = [
        {"task_id": "A", "duration": 5, "optimistic_duration": 4, "most_likely_duration": 5},
        {"task_id": "B", "duration": 3, "optimistic_duration": 2, "most_likely_duration": 3},
        {"task_id": "C", "duration": 2, "optimistic_duration": 1, "most_likely_duration": 2},
    ]
    dependencies = [
        {"predecessor": "A", "successor": "B"},
        {"predecessor": "B", "successor": "C"},
    ]

    forward = await agent._forward_pass(tasks, dependencies)
    backward = await agent._backward_pass(forward, dependencies)

    assert all("early_start" in task for task in forward)
    assert all("late_start" in task for task in backward)

    schedule_id = "sched-1"
    agent.schedules[schedule_id] = {
        "tasks": tasks,
        "dependencies": dependencies,
        "project_duration_days": 10,
    }

    results = await agent._run_monte_carlo(schedule_id, iterations=50)
    assert results["iterations"] == 50
    assert results["risk_drivers"]


@pytest.mark.asyncio
async def test_schedule_baseline_and_variance_events(tmp_path):
    event_bus = EventCollector()
    change_stub = ChangeStub()
    agent = SchedulePlanningAgent(
        config={
            "event_bus": event_bus,
            "change_agent": change_stub,
            "schedule_store_path": tmp_path / "schedules.json",
            "schedule_baseline_store_path": tmp_path / "baselines.json",
        }
    )
    await agent.initialize()

    schedule_id = "sched-1"
    agent.schedules[schedule_id] = {
        "schedule_id": schedule_id,
        "project_id": "proj-1",
        "tasks": [],
        "dependencies": [],
        "milestones": [],
        "project_duration_days": 10,
        "start_date": "2024-01-01T00:00:00",
        "end_date": "2024-01-11T00:00:00",
    }
    agent.schedule_store.upsert("tenant-a", schedule_id, agent.schedules[schedule_id])

    baseline = await agent._manage_baseline(
        schedule_id, tenant_id="tenant-a", correlation_id="corr-1"
    )
    assert baseline["baseline_id"]
    assert any(topic == "schedule.baseline.locked" for topic, _ in event_bus.events)

    agent.schedules[schedule_id]["project_duration_days"] = 15
    agent.schedule_store.upsert("tenant-a", schedule_id, agent.schedules[schedule_id])

    variance = await agent._track_variance(
        schedule_id, tenant_id="tenant-a", correlation_id="corr-2"
    )
    assert variance["schedule_variance_days"] < 0
    assert any(topic == "schedule.delay" for topic, _ in event_bus.events)
    assert change_stub.requests


@pytest.mark.asyncio
async def test_schedule_planning_get_schedule(tmp_path):
    agent = SchedulePlanningAgent(
        config={
            "schedule_store_path": tmp_path / "schedules.json",
            "schedule_baseline_store_path": tmp_path / "baselines.json",
        }
    )
    await agent.initialize()

    schedule_id = "sched-2"
    agent.schedules[schedule_id] = {
        "schedule_id": schedule_id,
        "project_id": "proj-2",
        "tasks": [],
        "dependencies": [],
        "milestones": [],
        "project_duration_days": 5,
        "start_date": "2024-01-01T00:00:00",
        "end_date": "2024-01-06T00:00:00",
    }
    agent.schedule_store.upsert("tenant-a", schedule_id, agent.schedules[schedule_id])

    response = await agent.process(
        {"action": "get_schedule", "tenant_id": "tenant-a", "schedule_id": schedule_id}
    )

    assert response["schedule_id"] == schedule_id


@pytest.mark.asyncio
async def test_schedule_planning_validation_rejects_invalid_action(tmp_path):
    agent = SchedulePlanningAgent(
        config={
            "schedule_store_path": tmp_path / "schedules.json",
            "schedule_baseline_store_path": tmp_path / "baselines.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "invalid"})

    assert valid is False


@pytest.mark.asyncio
async def test_schedule_planning_validation_rejects_missing_fields(tmp_path):
    agent = SchedulePlanningAgent(
        config={
            "schedule_store_path": tmp_path / "schedules.json",
            "schedule_baseline_store_path": tmp_path / "baselines.json",
        }
    )
    await agent.initialize()

    valid = await agent.validate_input({"action": "create_schedule", "project_id": "proj-1"})

    assert valid is False
