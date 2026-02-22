import pytest
from resource_capacity_agent import ResourceCapacityAgent
from risk_management_agent import RiskManagementAgent
from schedule_planning_agent import SchedulePlanningAgent


@pytest.mark.asyncio
async def test_risk_management_dashboard_exposes_risk_data(tmp_path):
    agent = RiskManagementAgent(config={"risk_store_path": tmp_path / "risk.json"})
    await agent.initialize()

    await agent.process(
        {
            "action": "identify_risk",
            "tenant_id": "tenant-r",
            "risk": {
                "title": "Integration instability",
                "description": "Integration points are unstable.",
                "project_id": "proj-risk",
                "task_id": "task-high",
                "probability": 5,
                "impact": 5,
            },
        }
    )

    dashboard = await agent.process(
        {
            "action": "get_risk_dashboard",
            "tenant_id": "tenant-r",
            "project_id": "proj-risk",
        }
    )

    assert dashboard["risk_data"]["project_risk_level"] in {"high", "medium", "low"}
    assert dashboard["risk_data"]["task_risks"][0]["task_id"] == "task-high"


@pytest.mark.asyncio
async def test_schedule_planning_applies_risk_buffer_to_task_duration(tmp_path):
    agent = SchedulePlanningAgent(
        config={
            "schedule_store_path": tmp_path / "schedules.json",
            "schedule_baseline_store_path": tmp_path / "baselines.json",
        }
    )
    await agent.initialize()

    adjusted = agent._apply_risk_adjustments_to_tasks(
        [
            {"task_id": "task-high", "duration": 10},
            {"task_id": "task-low", "duration": 10},
        ],
        {
            "project_risk_level": "low",
            "task_risks": [
                {"task_id": "task-high", "risk_level": "high"},
                {"task_id": "task-low", "risk_level": "low"},
            ],
        },
    )

    by_id = {task["task_id"]: task for task in adjusted}
    assert by_id["task-high"]["duration"] == pytest.approx(12.0)
    assert by_id["task-low"]["duration"] == pytest.approx(10.5)


@pytest.mark.asyncio
async def test_resource_capacity_applies_risk_load_factor(tmp_path):
    agent = ResourceCapacityAgent(
        config={
            "resource_store_path": tmp_path / "resources.json",
            "allocation_store_path": tmp_path / "allocations.json",
            "default_tenant_id": "tenant-r",
        }
    )
    await agent.initialize()

    agent.allocations["res-1"] = [
        {
            "resource_id": "res-1",
            "project_id": "proj-risk",
            "task_id": "task-high",
            "allocation_percentage": 80,
            "status": "Active",
        }
    ]

    utilization = await agent._calculate_resource_utilization(
        "res-1",
        {
            "project_risk_level": "high",
            "task_risks": [{"task_id": "task-high", "risk_level": "high"}],
        },
    )

    assert utilization == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_resource_capacity_plan_includes_risk_recommendations(tmp_path):
    agent = ResourceCapacityAgent(
        config={
            "resource_store_path": tmp_path / "resources.json",
            "allocation_store_path": tmp_path / "allocations.json",
            "default_tenant_id": "tenant-r",
        }
    )
    await agent.initialize()

    plan = await agent.process(
        {
            "action": "plan_capacity",
            "planning_horizon": {
                "months": 3,
                "risk_data": {"project_risk_level": "high", "task_risks": []},
            },
        }
    )

    assert plan["risk_based_recommendations"]
