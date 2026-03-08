"""
ROI & Scenario Analysis Action Handlers

Handlers for:
- calculate_roi
- run_scenario_analysis
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from business_case_utils import (
    build_cash_flow,
    calculate_payback_period,
    calculate_roi_percentage,
    calculate_tco,
    irr_from_cash_flows,
    npv_from_cash_flows,
    run_monte_carlo_simulation,
    run_sensitivity_analysis,
)

if TYPE_CHECKING:
    from business_case_investment_agent import BusinessCaseInvestmentAgent


async def calculate_roi(
    agent: BusinessCaseInvestmentAgent,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Calculate ROI metrics including NPV, IRR, payback period, and TCO.

    Returns detailed financial metrics.
    """
    agent.logger.info("Calculating ROI metrics")

    costs = input_data.get("costs", {})
    benefits = input_data.get("benefits", {})
    simulation_iterations = int(
        input_data.get("simulation_iterations", agent.simulation_iterations)
    )

    cash_flows = build_cash_flow(costs, benefits, agent.currency_rates)

    npv = npv_from_cash_flows(cash_flows, agent.discount_rate, agent.inflation_rate)
    irr = irr_from_cash_flows(cash_flows, agent.inflation_rate)
    payback_period = calculate_payback_period(cash_flows)
    tco = calculate_tco(costs, agent.currency_rates)
    roi = calculate_roi_percentage(costs, benefits, agent.currency_rates)

    monte_carlo_summary = run_monte_carlo_simulation(
        cash_flows, simulation_iterations, agent.discount_rate, agent.inflation_rate
    )
    sensitivity_analysis = run_sensitivity_analysis(
        costs,
        benefits,
        agent.currency_rates,
        agent.discount_rate,
        agent.inflation_rate,
        agent.sensitivity_variations,
    )

    return {
        "npv": npv,
        "irr": irr,
        "payback_period_months": payback_period,
        "tco": tco,
        "roi_percentage": roi,
        "discount_rate": agent.discount_rate,
        "assumptions": {
            "discount_rate": agent.discount_rate,
            "inflation_rate": agent.inflation_rate,
            "currency_rates": agent.currency_rates,
            "simulation_iterations": simulation_iterations,
        },
        "sensitivity_analysis": sensitivity_analysis,
        "monte_carlo_summary": monte_carlo_summary,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


async def run_scenario_analysis(
    agent: BusinessCaseInvestmentAgent,
    business_case_id: str,
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Run what-if scenario analysis with varying assumptions.

    Returns scenario comparison results.
    """
    agent.logger.info("Running scenario analysis for business case: %s", business_case_id)

    scenario_results: list[dict[str, Any]] = []

    for scenario in scenarios:
        scenario_name = scenario.get("name", "Unnamed Scenario")

        adjusted_costs = await agent._adjust_costs(scenario)
        adjusted_benefits = await agent._adjust_benefits(scenario)

        metrics = await agent._calculate_roi(
            {"costs": adjusted_costs, "benefits": adjusted_benefits}
        )

        cash_flows = build_cash_flow(adjusted_costs, adjusted_benefits, agent.currency_rates)
        simulations = run_monte_carlo_simulation(
            cash_flows,
            agent.simulation_iterations,
            agent.discount_rate,
            agent.inflation_rate,
        )
        sensitivity = run_sensitivity_analysis(
            adjusted_costs,
            adjusted_benefits,
            agent.currency_rates,
            agent.discount_rate,
            agent.inflation_rate,
            agent.sensitivity_variations,
        )
        scenario_results.append(
            {
                "scenario_name": scenario_name,
                "parameters": scenario.get("parameters", {}),
                "metrics": metrics,
                "simulation": simulations,
                "sensitivity_analysis": sensitivity,
                "risk_level": scenario.get("risk_level", "medium"),
            }
        )

    comparison = await agent._compare_scenarios(scenario_results)

    return {
        "business_case_id": business_case_id,
        "assumptions": {
            "discount_rate": agent.discount_rate,
            "inflation_rate": agent.inflation_rate,
            "currency_rates": agent.currency_rates,
            "simulation_iterations": agent.simulation_iterations,
        },
        "scenarios": scenario_results,
        "comparison": comparison,
        "recommendation": await agent._select_best_scenario(scenario_results),
    }
