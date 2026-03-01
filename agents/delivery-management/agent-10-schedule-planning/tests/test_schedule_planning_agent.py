import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.append(str(REPO_ROOT))

from integrations.services.integration.event_bus import EventBusClient, InMemoryEventBusProvider


class DummyEventBus:
    async def publish(self, *args, **kwargs) -> None:
        return None


class StubResourceCapacityAgent:
    def __init__(
        self, responses: dict[str, object] | None = None, raise_for: set[str] | None = None
    ):
        self.responses = responses or {}
        self.raise_for = raise_for or set()
        self.calls: list[dict[str, object]] = []

    async def process(self, payload: dict[str, object]) -> object:
        self.calls.append(payload)
        resource_id = str(payload.get("resource_id"))
        if resource_id in self.raise_for:
            raise RuntimeError(f"failed lookup for {resource_id}")
        return self.responses.get(resource_id, {})


def _load_agent_class() -> type:
    repo_root = REPO_ROOT
    sys.path.append(
        str(
            repo_root / "agents" / "operations-management" / "agent-17-change-control-agent" / "src"
        ),
    )
    sys.path.append(str(repo_root / "packages" / "contracts" / "src"))
    agent_path = Path(__file__).resolve().parents[1] / "src" / "schedule_planning_agent.py"
    spec = importlib.util.spec_from_file_location("schedule_planning_agent", agent_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.SchedulePlanningAgent


@pytest.mark.anyio
async def test_create_schedule_and_syncs(tmp_path: Path) -> None:
    agent_class = _load_agent_class()
    agent = agent_class(
        config={
            "schedule_store_path": str(tmp_path / "schedules.json"),
            "schedule_baseline_store_path": str(tmp_path / "baselines.json"),
            "enable_persistence": False,
            "enable_cache": True,
            "cache_provider": "in_memory",
            "enable_external_sync": True,
            "enable_calendar_sync": True,
            "enable_ms_project": True,
            "enable_outlook": True,
            "event_bus": DummyEventBus(),
        }
    )

    wbs = {
        "1": {"name": "Plan"},
        "2": {"name": "Design"},
        "3": {"name": "Build"},
    }
    result = await agent._create_schedule("project-1", wbs, tenant_id="tenant-a")

    schedule_id = result["schedule_id"]
    assert schedule_id in agent.schedules
    assert agent.cache_client is not None
    cached = agent.cache_client.get(f"schedule:tenant-a:{schedule_id}")
    assert cached is not None
    assert agent.external_sync_client is not None
    assert agent.external_sync_client.pushed
    assert agent.external_sync_client.calendar_events
    schedule = agent.schedules[schedule_id]
    task_id = schedule["tasks"][0]["task_id"]
    agent.external_sync_client.record_pull(
        "jira",
        schedule_id,
        {"tasks": [{"task_id": task_id, "duration": 10}]},
    )
    await agent._sync_external_tools(schedule)
    assert schedule["external_sync"]["conflicts"]
    assert schedule["tasks"][0]["duration"] == 10


@pytest.mark.anyio
async def test_duration_estimation_uses_ml(tmp_path: Path) -> None:
    agent_class = _load_agent_class()
    agent = agent_class(
        config={
            "schedule_store_path": str(tmp_path / "schedules.json"),
            "schedule_baseline_store_path": str(tmp_path / "baselines.json"),
            "enable_azure_ml": True,
            "event_bus": DummyEventBus(),
        }
    )

    estimates = await agent._estimate_duration(
        [{"task_id": "T1", "name": "Analyze", "complexity": "high"}],
        {"project_id": "proj-ml", "team_performance": 1.2},
    )
    assert "T1" in estimates
    assert estimates["T1"]["expected"] > 0


@pytest.mark.anyio
async def test_databricks_monte_carlo(tmp_path: Path) -> None:
    agent_class = _load_agent_class()
    agent = agent_class(
        config={
            "schedule_store_path": str(tmp_path / "schedules.json"),
            "schedule_baseline_store_path": str(tmp_path / "baselines.json"),
            "enable_databricks": True,
            "enable_persistence": False,
            "event_bus": DummyEventBus(),
        }
    )

    wbs = {
        "1": {"name": "Plan"},
        "2": {"name": "Implement"},
        "3": {"name": "Test"},
    }
    result = await agent._create_schedule("project-2", wbs, tenant_id="tenant-b")
    schedule_id = result["schedule_id"]
    simulation = await agent._run_monte_carlo(schedule_id, iterations=50)
    assert simulation["iterations"] == 50
    assert simulation["p80_duration"] >= 0


@pytest.mark.anyio
async def test_event_publishing_and_persistence(tmp_path: Path) -> None:
    agent_class = _load_agent_class()
    provider = InMemoryEventBusProvider()
    event_bus = EventBusClient(provider=provider)
    agent = agent_class(
        config={
            "schedule_store_path": str(tmp_path / "schedules.json"),
            "schedule_baseline_store_path": str(tmp_path / "baselines.json"),
            "enable_persistence": True,
            "sql_connection_string": f"sqlite+pysqlite:///{tmp_path / 'schedule.db'}",
            "integration_event_bus": event_bus,
            "event_bus": DummyEventBus(),
        }
    )

    wbs = {
        "1": {"name": "Plan"},
        "2": {"name": "Build"},
        "3": {"name": "Deploy"},
    }
    result = await agent._create_schedule("project-3", wbs, tenant_id="tenant-c")
    schedule_id = result["schedule_id"]
    agent.schedules[schedule_id]["critical_path"] = []
    await agent._calculate_critical_path(schedule_id)
    await agent._run_monte_carlo(schedule_id, iterations=25)

    events = list(provider.drain(event_bus.settings.service_bus_topic))
    event_types = {event["event_type"] for event in events}
    assert "schedule.created" in event_types
    assert "dependency.added" in event_types
    assert "critical_path.changed" in event_types
    assert "schedule.simulated" in event_types

    loaded = await agent._load_schedule_from_db(schedule_id)
    assert loaded is not None
    assert loaded["schedule_id"] == schedule_id


@pytest.mark.anyio
async def test_resource_leveling_rcpsp(tmp_path: Path) -> None:
    agent_class = _load_agent_class()
    agent = agent_class(
        config={
            "schedule_store_path": str(tmp_path / "schedules.json"),
            "schedule_baseline_store_path": str(tmp_path / "baselines.json"),
            "enable_persistence": False,
            "event_bus": DummyEventBus(),
        }
    )

    wbs = {
        "1": {"name": "Design"},
        "2": {"name": "Build"},
    }
    result = await agent._create_schedule("project-4", wbs, tenant_id="tenant-d")
    schedule_id = result["schedule_id"]
    resources = {"default": {"capacity": 1.0}}
    output = await agent._resource_constrained_schedule(schedule_id, resources)
    leveled = output["leveled_schedule"]
    assert all("resource_start" in task for task in leveled)
    assert all("resource_finish" in task for task in leveled)


@pytest.mark.anyio
async def test_get_resource_availability_uses_external_capacity_calendar(tmp_path: Path) -> None:
    agent_class = _load_agent_class()
    stub = StubResourceCapacityAgent(
        responses={
            "dev-1": {
                "resource_id": "dev-1",
                "availability_by_day": [
                    {"available_hours": 5},
                    {"available_hours": 6},
                ],
                "average_availability": 5.5,
            }
        }
    )
    agent = agent_class(
        config={
            "schedule_store_path": str(tmp_path / "schedules.json"),
            "schedule_baseline_store_path": str(tmp_path / "baselines.json"),
            "enable_persistence": False,
            "resource_capacity_agent": stub,
            "event_bus": DummyEventBus(),
        }
    )

    output = await agent._get_resource_availability(
        {"dev-1": {"capacity": 1.0}},
        context={"tenant_id": "tenant-z", "project_id": "proj-1"},
    )

    assert output["dev-1"]["capacity"] == pytest.approx(5.5)
    assert output["dev-1"]["period_availability"] == {0: 5.0, 1: 6.0}
    assert stub.calls[0]["tenant_id"] == "tenant-z"
    assert stub.calls[0]["project_id"] == "proj-1"


@pytest.mark.anyio
async def test_get_resource_availability_fallback_without_external_agent(tmp_path: Path) -> None:
    agent_class = _load_agent_class()
    agent = agent_class(
        config={
            "schedule_store_path": str(tmp_path / "schedules.json"),
            "schedule_baseline_store_path": str(tmp_path / "baselines.json"),
            "enable_persistence": False,
            "event_bus": DummyEventBus(),
        }
    )

    output = await agent._get_resource_availability(
        {"dev-2": {"capacity": 2.0, "period_availability": {"0": 2, "bad": "x"}}},
        context={"tenant_id": "tenant-a", "project_id": "proj-2"},
    )

    assert output["dev-2"]["capacity"] == pytest.approx(2.0)
    assert output["dev-2"]["period_availability"] == {0: 2.0}
    assert output["dev-2"]["warning"] == "resource_capacity_unavailable"


@pytest.mark.anyio
async def test_get_resource_availability_handles_malformed_and_exception(tmp_path: Path) -> None:
    agent_class = _load_agent_class()
    stub = StubResourceCapacityAgent(
        responses={
            "dev-3": {"resource_id": "dev-3", "availability_by_day": "bad"},
            "dev-4": {"resource_id": "mismatch", "availability_by_day": []},
        },
        raise_for={"dev-5"},
    )
    agent = agent_class(
        config={
            "schedule_store_path": str(tmp_path / "schedules.json"),
            "schedule_baseline_store_path": str(tmp_path / "baselines.json"),
            "enable_persistence": False,
            "resource_capacity_agent": stub,
            "event_bus": DummyEventBus(),
        }
    )

    output = await agent._get_resource_availability(
        {"dev-3": 1.0, "dev-4": 2.0, "dev-5": 3.0},
        context={"tenant_id": "tenant-b", "project_id": "proj-3"},
    )

    assert output["dev-3"]["warning"] == "resource_capacity_malformed_response"
    assert output["dev-4"]["warning"] in {
        "resource_capacity_id_mismatch",
        "resource_capacity_missing_data",
    }
    assert output["dev-5"]["capacity"] == pytest.approx(3.0)
    assert output["dev-5"]["warning"] == "resource_capacity_fetch_failed"
    assert "failed lookup" in output["dev-5"]["warning_details"]


@pytest.mark.anyio
async def test_resource_leveling_respects_period_availability(tmp_path: Path) -> None:
    agent_class = _load_agent_class()
    agent = agent_class(
        config={
            "schedule_store_path": str(tmp_path / "schedules.json"),
            "schedule_baseline_store_path": str(tmp_path / "baselines.json"),
            "enable_persistence": False,
            "event_bus": DummyEventBus(),
        }
    )

    tasks = [
        {
            "task_id": "T1",
            "duration": 1,
            "early_start": 0,
            "early_finish": 1,
            "resources": [{"id": "dev", "units": 1.0}],
        },
        {
            "task_id": "T2",
            "duration": 1,
            "early_start": 0,
            "early_finish": 1,
            "resources": [{"id": "dev", "units": 1.0}],
        },
    ]
    leveled = await agent._resource_leveling(
        tasks,
        [],
        {"dev": {"capacity": 1.0, "period_availability": {0: 0.0, 1: 1.0, 2: 1.0}}},
    )

    starts = {task["task_id"]: task["resource_start"] for task in leveled}
    assert starts["T1"] >= 1
    assert starts["T2"] >= 1
