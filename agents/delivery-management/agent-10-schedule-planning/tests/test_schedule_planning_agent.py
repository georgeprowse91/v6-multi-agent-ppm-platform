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


def _load_agent_class() -> type:
    repo_root = REPO_ROOT
    sys.path.append(
        str(
            repo_root
            / "agents"
            / "operations-management"
            / "agent-17-change-configuration"
            / "src"
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
    SchedulePlanningAgent = _load_agent_class()
    agent = SchedulePlanningAgent(
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
    SchedulePlanningAgent = _load_agent_class()
    agent = SchedulePlanningAgent(
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
    SchedulePlanningAgent = _load_agent_class()
    agent = SchedulePlanningAgent(
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
    SchedulePlanningAgent = _load_agent_class()
    provider = InMemoryEventBusProvider()
    event_bus = EventBusClient(provider=provider)
    agent = SchedulePlanningAgent(
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
    SchedulePlanningAgent = _load_agent_class()
    agent = SchedulePlanningAgent(
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
