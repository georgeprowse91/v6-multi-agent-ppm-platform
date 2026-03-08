"""Action handler for scenario / what-if analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from analytics_utils import generate_scenario_id

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


async def handle_scenario_analysis(
    agent: AnalyticsInsightsAgent, tenant_id: str, scenario: dict[str, Any]
) -> dict[str, Any]:
    """
    Perform what-if scenario analysis.

    Returns scenario comparison.
    """
    agent.logger.info("Running scenario analysis: %s", scenario.get("name"))

    # Generate scenario ID
    scenario_id = await generate_scenario_id()

    # Get baseline metrics
    baseline = await _get_baseline_metrics(scenario)

    scenario_output = await agent.scenario_engine.run_metric_scenario(
        baseline_metrics=baseline,
        scenario_params=scenario.get("parameters", {}),
        scenario_metrics_builder=lambda b, p: _calculate_scenario_metrics(agent, b, p),
        comparison_builder=_compare_scenarios,
        recommendation_builder=_calculate_scenario_impact,
    )
    scenario_metrics = scenario_output["scenario_metrics"]
    comparison = scenario_output["comparison"]
    impact = scenario_output.get("recommendation")

    simulations = await _run_metric_simulations(agent, tenant_id, scenario.get("simulations", []))
    simulation_summary = await _summarize_simulation_results(simulations)

    # Store scenario
    scenario_record = {
        "scenario_id": scenario_id,
        "name": scenario.get("name"),
        "parameters": scenario.get("parameters"),
        "baseline": baseline,
        "scenario_metrics": scenario_metrics,
        "comparison": comparison,
        "impact": impact,
        "simulations": simulations,
        "simulation_summary": simulation_summary,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.scenarios[scenario_id] = scenario_record
    agent.analytics_output_store.upsert(tenant_id, scenario_id, scenario_record.copy())

    return {
        "scenario_id": scenario_id,
        "name": scenario.get("name"),
        "baseline": baseline,
        "scenario_metrics": scenario_metrics,
        "comparison": comparison,
        "impact": impact,
        "simulations": simulations,
        "simulation_summary": simulation_summary,
        "recommendations": await _generate_scenario_recommendations(impact),
    }


async def _get_baseline_metrics(scenario: dict[str, Any]) -> dict[str, Any]:
    """Get baseline metrics for scenario."""
    return {"metric_1": 100, "metric_2": 200}


async def _calculate_scenario_metrics(
    agent: AnalyticsInsightsAgent, baseline: dict[str, Any], parameters: dict[str, Any]
) -> dict[str, Any]:
    """Calculate metrics under scenario."""
    scenario_metrics = baseline.copy()
    assumptions = parameters.get("assumptions", {})
    for metric, adjustment in assumptions.items():
        if metric in scenario_metrics and isinstance(adjustment, (int, float)):
            scenario_metrics[metric] = scenario_metrics[metric] + adjustment

    kpi_models = parameters.get("kpi_models", [])
    for kpi_model in kpi_models:
        model_type = kpi_model.get("model_type")
        if not model_type:
            continue
        input_payload = kpi_model.get("input_data", {})
        input_payload.update(assumptions)
        # Call through agent delegate so tests can monkey-patch _run_prediction
        prediction = await agent._run_prediction(
            input_payload.get("tenant_id", "default"), model_type, input_payload
        )
        scenario_metrics[model_type] = prediction.get("prediction")

    return scenario_metrics


async def _compare_scenarios(baseline: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    """Compare baseline to scenario."""
    comparison = {}
    for key in baseline.keys():
        if key in scenario:
            comparison[key] = {
                "baseline": baseline[key],
                "scenario": scenario[key],
                "delta": scenario[key] - baseline[key],
                "delta_pct": (
                    ((scenario[key] - baseline[key]) / baseline[key] * 100)
                    if baseline[key] != 0
                    else 0
                ),
            }
    return comparison


async def _calculate_scenario_impact(comparison: dict[str, Any]) -> str:
    """Calculate overall scenario impact."""
    return "Moderate positive impact"


async def _generate_scenario_recommendations(impact: str | None) -> list[str]:
    """Generate recommendations based on scenario."""
    if not impact:
        return ["Scenario impact is neutral - monitor outcomes before acting"]
    return [f"Scenario shows {impact} - consider implementation"]


async def _run_metric_simulations(
    agent: AnalyticsInsightsAgent, tenant_id: str, simulations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Invoke scenario simulations across domain agents."""
    results: list[dict[str, Any]] = []
    for simulation in simulations:
        sim_type = simulation.get("type")
        agent_key = simulation.get("agent")
        agent_client = agent.metric_agents.get(agent_key) if agent_key else None
        if not agent_client:
            continue
        payload = {
            "tenant_id": tenant_id,
            "action": simulation.get("action"),
        }
        payload.update(simulation.get("payload", {}))
        response = await agent_client.process(payload)
        results.append(
            {
                "type": sim_type,
                "agent": agent_key,
                "response": response,
            }
        )
    return results


async def _summarize_simulation_results(simulations: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize simulation outcomes across metrics."""
    return {
        "simulation_count": len(simulations),
        "simulation_types": [simulation.get("type") for simulation in simulations],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
