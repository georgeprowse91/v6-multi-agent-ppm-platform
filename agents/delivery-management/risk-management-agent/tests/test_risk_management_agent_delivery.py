from __future__ import annotations

import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[3]
SRC_DIR = TESTS_DIR.parent / "src"
sys.path.extend(
    [
        str(SRC_DIR),
        str(REPO_ROOT),
        str(REPO_ROOT / "packages" / "data-quality" / "src"),
        str(REPO_ROOT / "packages"),
    ]
)

from risk_management_agent import RiskManagementAgent, RiskNLPExtractor


class DummyEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, topic: str, payload: dict) -> None:
        self.published.append((topic, payload))


@pytest.mark.anyio
async def test_nlp_risk_extraction_heuristic() -> None:
    extractor = RiskNLPExtractor()
    documents = [
        {"content": "There is a risk of schedule delay due to vendor dependency."},
        "Budget overrun risk identified in the latest review.",
    ]
    risks = extractor.extract_risks(documents)
    assert risks
    assert any("risk" in risk["description"].lower() for risk in risks)


@pytest.mark.anyio
async def test_monte_carlo_simulation_uses_baseline() -> None:
    agent = RiskManagementAgent(
        config={
            "schedule_baseline_fixture": {"baseline_duration_days": 120.0},
            "financial_distribution_fixture": {"baseline_cost": 2_000_000.0},
        }
    )
    agent.risk_register["R1"] = {
        "risk_id": "R1",
        "project_id": "P1",
        "title": "Delay risk",
        "probability": 4,
        "impact": 4,
    }
    results = await agent._perform_monte_carlo_simulation(
        "P1",
        list(agent.risk_register.values()),
        200,
        schedule_distribution={"baseline_duration_days": 120.0},
        financial_distribution={"baseline_cost": 2_000_000.0},
    )
    assert len(results["schedule"]) == 200
    assert len(results["cost"]) == 200
    assert sum(results["schedule"]) / len(results["schedule"]) >= 120.0
    assert sum(results["cost"]) / len(results["cost"]) >= 2_000_000.0


@pytest.mark.anyio
async def test_quantitative_impact_calculation() -> None:
    agent = RiskManagementAgent(
        config={
            "schedule_baseline_fixture": {"baseline_duration_days": 90.0, "mean_delay_days": 12.0},
            "financial_distribution_fixture": {
                "baseline_cost": 500_000.0,
                "mean_cost_overrun": 50_000.0,
            },
        }
    )
    risk = {"risk_id": "R2", "project_id": "P2", "probability": 4, "impact": 5}
    impact = await agent._calculate_quantitative_impact(risk)
    assert impact["schedule_impact_days"] > 0
    assert impact["cost_impact"] > 0


@pytest.mark.anyio
async def test_risk_simulation_event_published() -> None:
    event_bus = DummyEventBus()
    agent = RiskManagementAgent(
        config={
            "event_bus": event_bus,
            "schedule_baseline_fixture": {"baseline_duration_days": 100.0},
            "financial_distribution_fixture": {"baseline_cost": 1_000_000.0},
        }
    )
    agent.event_bus = event_bus
    agent.risk_register["R3"] = {
        "risk_id": "R3",
        "project_id": "P3",
        "title": "Cost risk",
        "probability": 3,
        "impact": 4,
    }
    await agent._run_monte_carlo("P3", iterations=50)
    topics = [topic for topic, _payload in event_bus.published]
    assert "risk.simulated" in topics


class DummyPMService:
    async def create_tasks(self, project_id, tasks):
        return [
            {"status": "created", "task_id": f"T-{idx}"} for idx, _task in enumerate(tasks, start=1)
        ]


@pytest.mark.anyio
async def test_mitigation_plan_creates_tasks_and_event() -> None:
    event_bus = DummyEventBus()
    agent = RiskManagementAgent(
        config={
            "event_bus": event_bus,
        }
    )
    agent.project_management_services = {"jira": DummyPMService()}
    agent.event_bus = event_bus
    agent.risk_register["R4"] = {
        "risk_id": "R4",
        "project_id": "P4",
        "title": "Scope creep",
        "description": "Scope growth without approval.",
        "category": "scope",
        "probability": 4,
        "impact": 4,
        "score": 16,
    }
    plan = await agent._create_mitigation_plan("R4", {"strategy": "mitigate"})
    assert plan["created_tasks"]
    topics = [topic for topic, _payload in event_bus.published]
    assert "risk.mitigation.created" in topics


@pytest.mark.anyio
async def test_event_trigger_publishes_risk_triggered() -> None:
    event_bus = DummyEventBus()
    agent = RiskManagementAgent(config={"event_bus": event_bus})
    agent.event_bus = event_bus
    agent.risk_register["R5"] = {
        "risk_id": "R5",
        "project_id": "P5",
        "title": "Cost overrun",
        "probability": 3,
        "impact": 4,
        "score": 12,
    }
    await agent._handle_cost_overrun_event({"project_id": "P5", "cost_overrun_pct": 0.2})
    topics = [topic for topic, _payload in event_bus.published]
    assert "risk.triggered" in topics
