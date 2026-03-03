"""Action handler for Monte Carlo simulation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from risk_utils import (
    calculate_percentile,
    fetch_financial_distribution,
    fetch_schedule_baseline,
    offload_or_simulate,
    publish_risk_event,
    store_risk_dataset,
)

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


async def run_monte_carlo(
    agent: RiskManagementAgent, project_id: str, iterations: int = 10000
) -> dict[str, Any]:
    """
    Run Monte Carlo simulation for schedule and cost risk.

    Returns probabilistic analysis results.
    """
    agent.logger.info("Running Monte Carlo simulation for project: %s", project_id)

    # Get project risks
    project_risks = [
        r for r in agent.risk_register.values() if r.get("project_id") == project_id
    ]

    schedule_distribution = await fetch_schedule_baseline(agent, project_id)
    financial_distribution = await fetch_financial_distribution(agent, project_id)
    simulation_results = await offload_or_simulate(
        agent,
        project_id,
        project_risks,
        iterations,
        schedule_distribution=schedule_distribution,
        financial_distribution=financial_distribution,
    )

    # Calculate percentiles
    schedule_p50 = await calculate_percentile(simulation_results["schedule"], 50)
    schedule_p80 = await calculate_percentile(simulation_results["schedule"], 80)
    schedule_p95 = await calculate_percentile(simulation_results["schedule"], 95)

    cost_p50 = await calculate_percentile(simulation_results["cost"], 50)
    cost_p80 = await calculate_percentile(simulation_results["cost"], 80)
    cost_p95 = await calculate_percentile(simulation_results["cost"], 95)

    await store_risk_dataset(
        agent,
        "monte_carlo",
        [
            {
                "project_id": project_id,
                "iterations": iterations,
                "schedule": simulation_results["schedule"][:100],
                "cost": simulation_results["cost"][:100],
                "schedule_distribution": schedule_distribution,
                "financial_distribution": financial_distribution,
            }
        ],
        domain="simulation",
    )
    simulation_record = {
        "project_id": project_id,
        "iterations": iterations,
        "schedule_p50": schedule_p50,
        "schedule_p80": schedule_p80,
        "schedule_p95": schedule_p95,
        "cost_p50": cost_p50,
        "cost_p80": cost_p80,
        "cost_p95": cost_p95,
        "schedule_sample": simulation_results["schedule"][:100],
        "cost_sample": simulation_results["cost"][:100],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if agent.db_service:
        record_id = (
            f"{project_id}-simulation-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        await agent.db_service.store("risk_simulations", record_id, simulation_record)
    await publish_risk_event(
        agent,
        "risk.simulation_completed",
        {"project_id": project_id, "iterations": iterations},
    )
    await publish_risk_event(
        agent,
        "risk.simulated",
        {
            "project_id": project_id,
            "iterations": iterations,
            "schedule_p80": schedule_p80,
            "cost_p80": cost_p80,
        },
    )
    return {
        "project_id": project_id,
        "iterations": iterations,
        "schedule_analysis": {
            "p50": schedule_p50,
            "p80": schedule_p80,
            "p95": schedule_p95,
            "mean": sum(simulation_results["schedule"]) / len(simulation_results["schedule"]),
        },
        "cost_analysis": {
            "p50": cost_p50,
            "p80": cost_p80,
            "p95": cost_p95,
            "mean": sum(simulation_results["cost"]) / len(simulation_results["cost"]),
        },
        "risks_analyzed": len(project_risks),
        "simulation_date": datetime.now(timezone.utc).isoformat(),
    }
