import pytest
from project_lifecycle_agent import ProjectLifecycleAgent


@pytest.mark.asyncio
async def test_project_lifecycle_gate_and_health():
    agent = ProjectLifecycleAgent()
    await agent.initialize()

    project_id = "proj-123"
    agent.projects[project_id] = {
        "project_id": project_id,
        "name": "Project Orion",
        "sponsor": "sponsor-1",
        "artifacts": {"charter": {"complete": True}, "deliverables": {"complete": True}},
        "approvals": {
            "charter": True,
            "scope_baseline": True,
            "schedule_baseline": True,
            "budget": True,
        },
        "metrics": {"quality_score": 0.9},
        "schedule": {"spi": 0.9, "variance_pct": -0.05},
        "cost": {"cpi": 0.92, "variance_pct": 0.02},
        "risk": {"risk_score": 0.8, "open_risks": 2},
        "quality": {"test_pass_rate": 0.95, "defects": 2},
        "resource": {"utilization": 0.85},
    }
    agent.lifecycle_states[project_id] = {"current_phase": "Initiate"}

    evaluation = await agent._evaluate_gate(project_id, "charter_gate")
    assert evaluation["criteria_met"] is True
    assert evaluation["readiness_score"] >= 0.9

    health = await agent._monitor_health(project_id)
    assert health["health_status"] in {"Healthy", "At Risk"}
