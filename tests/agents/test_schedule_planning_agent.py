import pytest
from schedule_planning_agent import SchedulePlanningAgent


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
