"""
Business Case & Investment Analysis Utilities

Pure computation functions used by the BusinessCaseInvestmentAgent and its action handlers.
All functions are stateless and accept only simple parameters.
"""

from __future__ import annotations

import random
import statistics
from typing import Any

# ---------------------------------------------------------------------------
# Currency helpers
# ---------------------------------------------------------------------------


def convert_currency_inputs(
    data: dict[str, Any], currency_rates: dict[str, float]
) -> dict[str, Any]:
    """Return a copy of `data` with monetary fields converted to the base currency (AUD)."""
    converted = dict(data)
    currency = str(converted.get("currency", "AUD")).upper()
    rate = float(currency_rates.get(currency, 1.0))
    for key in ("total_cost", "total_benefits", "operational_costs"):
        if key in converted:
            converted[key] = float(converted[key]) * rate
    if isinstance(converted.get("cash_flow"), list):
        converted["cash_flow"] = [float(amount) * rate for amount in converted["cash_flow"]]
    converted["base_currency"] = "AUD"
    return converted


# ---------------------------------------------------------------------------
# Cash-flow helpers
# ---------------------------------------------------------------------------


def build_cash_flow(
    costs: dict[str, Any],
    benefits: dict[str, Any],
    currency_rates: dict[str, float],
) -> list[float]:
    """Build annual net cash flows from cost and benefit dictionaries."""
    costs = convert_currency_inputs(costs, currency_rates)
    benefits = convert_currency_inputs(benefits, currency_rates)
    total_cost = float(costs.get("total_cost", 0))
    total_benefits = float(benefits.get("total_benefits", 0))
    horizon_years = int(costs.get("horizon_years", benefits.get("horizon_years", 3)))
    cost_flow = costs.get("cash_flow")
    benefit_flow = benefits.get("cash_flow")
    if isinstance(cost_flow, list) and isinstance(benefit_flow, list):
        return [
            float(benefit_flow[idx]) - float(cost_flow[idx])
            for idx in range(min(len(cost_flow), len(benefit_flow)))
        ]
    annual_cost = total_cost / max(horizon_years, 1)
    annual_benefit = total_benefits / max(horizon_years, 1)
    return [annual_benefit - annual_cost for _ in range(horizon_years)]


def inflate_adjust_cash_flows(cash_flows: list[float], inflation_rate: float) -> list[float]:
    """Apply inflation adjustment to a sequence of cash flows."""
    if inflation_rate == 0:
        return cash_flows
    return [
        cash_flow / ((1 + inflation_rate) ** period)
        for period, cash_flow in enumerate(cash_flows, start=1)
    ]


# ---------------------------------------------------------------------------
# NPV / IRR / ROI calculations
# ---------------------------------------------------------------------------


def npv_from_cash_flows(
    cash_flows: list[float],
    discount_rate: float,
    inflation_rate: float = 0.0,
) -> float:
    """
    Calculate Net Present Value for a sequence of annual cash flows.

    Args:
        cash_flows: Annual net cash flows (positive = inflow, negative = outflow).
        discount_rate: Discount rate as a decimal (e.g. 0.10 for 10 %).
        inflation_rate: Optional inflation rate to adjust flows (default 0).

    Returns:
        NPV as a float.
    """
    adjusted = inflate_adjust_cash_flows(cash_flows, inflation_rate)
    npv = 0.0
    for period, cash_flow in enumerate(adjusted, start=1):
        npv += cash_flow / ((1 + discount_rate) ** period)
    return npv


def irr_from_cash_flows(cash_flows: list[float], inflation_rate: float = 0.0) -> float:
    """
    Estimate the Internal Rate of Return via bisection search.

    Args:
        cash_flows: Annual net cash flows.
        inflation_rate: Optional inflation rate.

    Returns:
        IRR as a decimal (e.g. 0.15 for 15 %).
    """
    adjusted = inflate_adjust_cash_flows(cash_flows, inflation_rate)
    if not cash_flows:
        return 0.0
    low, high = -0.9, 1.0
    for _ in range(50):
        rate = (low + high) / 2
        npv = 0.0
        for period, cash_flow in enumerate(adjusted, start=1):
            npv += cash_flow / ((1 + rate) ** period)
        if npv > 0:
            low = rate
        else:
            high = rate
    return round((low + high) / 2, 4)


def calculate_payback_period(cash_flows: list[float]) -> int:
    """
    Calculate payback period in months.

    Args:
        cash_flows: Annual net cash flows.

    Returns:
        Number of months until cumulative cash flow turns positive, or 999 if never.
    """
    cumulative = 0.0
    for period, cash_flow in enumerate(cash_flows, start=1):
        cumulative += cash_flow
        if cumulative >= 0:
            return period * 12
    return 999


def calculate_tco(costs: dict[str, Any], currency_rates: dict[str, float]) -> float:
    """
    Calculate Total Cost of Ownership.

    Args:
        costs: Cost dictionary (must contain 'total_cost').
        currency_rates: Mapping of currency codes to exchange rates.

    Returns:
        TCO as a float in the base currency.
    """
    converted = convert_currency_inputs(costs, currency_rates)
    total_cost = float(converted.get("total_cost", 0))
    operational_costs = float(converted.get("operational_costs", total_cost * 0.15))
    return total_cost + operational_costs


def calculate_roi_percentage(
    costs: dict[str, Any],
    benefits: dict[str, Any],
    currency_rates: dict[str, float],
) -> float:
    """
    Calculate ROI percentage: (benefits - cost) / cost.

    Returns 0.0 if total_cost is zero.
    """
    converted_costs = convert_currency_inputs(costs, currency_rates)
    converted_benefits = convert_currency_inputs(benefits, currency_rates)
    total_cost = float(converted_costs.get("total_cost", 0))
    total_benefits = float(converted_benefits.get("total_benefits", 0))
    if total_cost == 0:
        return 0.0
    return (total_benefits - total_cost) / total_cost


# ---------------------------------------------------------------------------
# Simulation / sensitivity
# ---------------------------------------------------------------------------


def run_monte_carlo_simulation(
    cash_flows: list[float],
    iterations: int,
    discount_rate: float,
    inflation_rate: float = 0.0,
) -> dict[str, float]:
    """
    Run a Monte Carlo simulation on a set of cash flows.

    Each iteration perturbs each cash flow with Gaussian noise (10 % std-dev)
    and re-calculates NPV.

    Returns:
        Summary dict with mean_npv, stddev_npv, negative_npv_probability, iterations.
    """
    npv_results: list[float] = []
    for _ in range(iterations):
        simulated_flows = [random.gauss(flow, abs(flow) * 0.1 or 1.0) for flow in cash_flows]
        npv_results.append(npv_from_cash_flows(simulated_flows, discount_rate, inflation_rate))
    if not npv_results:
        return {
            "mean_npv": 0.0,
            "stddev_npv": 0.0,
            "negative_npv_probability": 0.0,
            "iterations": 0,
        }
    negative_count = sum(1 for npv in npv_results if npv < 0)
    return {
        "mean_npv": statistics.mean(npv_results),
        "stddev_npv": statistics.pstdev(npv_results),
        "negative_npv_probability": negative_count / len(npv_results),
        "iterations": len(npv_results),
    }


def run_sensitivity_analysis(
    costs: dict[str, Any],
    benefits: dict[str, Any],
    currency_rates: dict[str, float],
    discount_rate: float,
    inflation_rate: float,
    sensitivity_variations: list[float],
) -> list[dict[str, float | str]]:
    """
    Compute NPV and IRR for each combination of cost/benefit variation.

    Returns a list of rows, one per (parameter, variation) combination.
    """
    base_cost = float(costs.get("total_cost", 0))
    base_benefit = float(benefits.get("total_benefits", 0))
    sensitivity_rows: list[dict[str, float | str]] = []
    for variation in sensitivity_variations:
        cost_case_costs = {**costs, "total_cost": base_cost * (1 + variation)}
        cost_case_cash_flows = build_cash_flow(cost_case_costs, benefits, currency_rates)
        sensitivity_rows.append(
            {
                "parameter": "cost",
                "variation": variation,
                "cost_multiplier": 1 + variation,
                "benefit_multiplier": 1.0,
                "npv": npv_from_cash_flows(cost_case_cash_flows, discount_rate, inflation_rate),
                "irr": irr_from_cash_flows(cost_case_cash_flows, inflation_rate),
            }
        )

        benefit_case_benefits = {**benefits, "total_benefits": base_benefit * (1 + variation)}
        benefit_case_cash_flows = build_cash_flow(costs, benefit_case_benefits, currency_rates)
        sensitivity_rows.append(
            {
                "parameter": "revenue_growth",
                "variation": variation,
                "cost_multiplier": 1.0,
                "benefit_multiplier": 1 + variation,
                "npv": npv_from_cash_flows(benefit_case_cash_flows, discount_rate, inflation_rate),
                "irr": irr_from_cash_flows(benefit_case_cash_flows, inflation_rate),
            }
        )
    return sensitivity_rows


# ---------------------------------------------------------------------------
# Recommendation helpers
# ---------------------------------------------------------------------------


def calculate_confidence(
    metrics: dict[str, Any],
    historical_comparison: dict[str, Any],
    min_roi_threshold: float,
) -> float:
    """
    Derive a confidence score (0–0.95) for an investment recommendation.

    Args:
        metrics: Financial metrics dict (expects roi_percentage, npv).
        historical_comparison: Output from compare_to_historical (expects benchmark_roi).
        min_roi_threshold: Minimum acceptable ROI for the agent config.

    Returns:
        Confidence level as a float in [0, 0.95].
    """
    roi = metrics.get("roi_percentage", 0.0)
    npv = metrics.get("npv", 0.0)
    benchmark_roi = historical_comparison.get("benchmark_roi", 0.0)
    confidence = 0.6
    if roi >= min_roi_threshold:
        confidence += 0.15
    if npv > 0:
        confidence += 0.1
    if benchmark_roi and roi >= benchmark_roi:
        confidence += 0.1
    return min(confidence, 0.95)
