"""Financial Management Agent - Pure utility functions."""

import uuid
from datetime import datetime, timezone


def calculate_npv(total_cost: float, cash_flows: list[float], discount_rate: float = 0.10) -> float:
    """Calculate Net Present Value.

    Args:
        total_cost: The initial investment cost.
        cash_flows: List of future cash flows by period.
        discount_rate: The discount rate to apply (default 10%).

    Returns:
        Net present value as a float.
    """
    npv = -total_cost
    for i, cash_flow in enumerate(cash_flows, start=1):
        npv += cash_flow / ((1 + discount_rate) ** i)
    return npv


def calculate_irr(total_cost: float, cash_flows: list[float]) -> float:
    """Calculate Internal Rate of Return.

    Args:
        total_cost: The initial investment cost.
        cash_flows: List of future cash flows by period.

    Returns:
        Internal rate of return as a float.
    """
    cash_series = [-total_cost] + cash_flows

    def npv_for_rate(rate: float) -> float:
        return sum(value / ((1 + rate) ** idx) for idx, value in enumerate(cash_series))

    lower, upper = -0.9, 1.5
    for _ in range(50):
        mid = (lower + upper) / 2
        value = npv_for_rate(mid)
        if abs(value) < 1e-6:
            return mid
        if value > 0:
            lower = mid
        else:
            upper = mid
    return (lower + upper) / 2


def calculate_payback_period(total_cost: float, cash_flows: list[float]) -> int:
    """Calculate payback period in months.

    Args:
        total_cost: The initial investment cost.
        cash_flows: List of future cash flows by period (monthly).

    Returns:
        Number of periods to recover the investment, or 999 if not recovered.
    """
    if not cash_flows:
        return 999
    cumulative = 0.0
    for index, cash_flow in enumerate(cash_flows, start=1):
        cumulative += cash_flow
        if cumulative >= total_cost:
            return index
    return 999


def calculate_confidence_interval(monthly_forecast: list[float]) -> dict:
    """Calculate forecast confidence interval.

    Args:
        monthly_forecast: List of monthly forecast values.

    Returns:
        Dictionary with lower_bound, upper_bound, and confidence_level.
    """
    if not monthly_forecast:
        return {"lower_bound": 0, "upper_bound": 0, "confidence_level": 0.95}
    mean = sum(monthly_forecast) / len(monthly_forecast)
    variance = sum((x - mean) ** 2 for x in monthly_forecast) / len(monthly_forecast)
    std_dev = variance**0.5
    return {
        "lower_bound": max(0.0, mean - 1.28 * std_dev),
        "upper_bound": mean + 1.28 * std_dev,
        "confidence_level": 0.8,
    }


def generate_budget_id() -> str:
    """Generate unique budget ID.

    Returns:
        Budget ID string in format BDG-YYYYMMDDHHMMSS-xxxxxx.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"BDG-{timestamp}-{uuid.uuid4().hex[:6]}"
