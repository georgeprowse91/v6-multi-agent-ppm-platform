import importlib.util
import sys
from pathlib import Path

import pytest


class DummyEventBus:
    async def publish(self, *args, **kwargs) -> None:
        return None


def _load_agent_class() -> type:
    repo_root = Path(__file__).resolve().parents[4]
    sys.path.append(str(repo_root))
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
