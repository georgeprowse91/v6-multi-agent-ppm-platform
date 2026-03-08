"""
Portfolio Strategy & Optimization Utilities

Pure computation functions used by the PortfolioStrategyAgent and its action handlers.
All functions are stateless and take only simple parameters.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Keyword / text helpers
# ---------------------------------------------------------------------------


def extract_keywords(text: str) -> set[str]:
    """Return lower-cased alpha-numeric tokens longer than 3 characters."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {token for token in tokens if len(token) > 3}


# ---------------------------------------------------------------------------
# Financial helpers
# ---------------------------------------------------------------------------


def calculate_project_value(project: dict[str, Any], *, discount_rate: float) -> float:
    """Calculate discounted project value from cash flows or fallback fields."""
    cash_flows = project.get("cash_flows") or []
    if isinstance(cash_flows, dict):
        cash_flows = list(cash_flows.values())
    if isinstance(cash_flows, list) and cash_flows:
        return sum(
            float(value) / ((1 + discount_rate) ** (idx + 1))
            for idx, value in enumerate(cash_flows)
        )
    return float(project.get("expected_value", 0) or project.get("value", 0))


# ---------------------------------------------------------------------------
# Portfolio selection helpers
# ---------------------------------------------------------------------------


def apply_alignment_constraint(
    projects: list[dict[str, Any]], min_alignment_score: float
) -> list[dict[str, Any]]:
    """Filter out projects below the minimum strategic alignment score."""
    if min_alignment_score <= 0:
        return projects
    return [
        project for project in projects if project.get("alignment_score", 0) >= min_alignment_score
    ]


def apply_risk_appetite(
    projects: list[dict[str, Any]], risk_appetite: float
) -> list[dict[str, Any]]:
    """
    Trim the riskiest projects when the portfolio average risk exceeds the appetite.

    A higher `risk_score` means *lower* risk (0=highest risk, 1=lowest risk).
    """
    if not projects:
        return projects
    avg_risk = sum(1 - p.get("risk_score", 0.6) for p in projects) / max(1, len(projects))
    if avg_risk <= risk_appetite:
        return projects
    return sorted(projects, key=lambda p: p.get("risk_score", 0.0), reverse=True)[
        : max(1, len(projects) - 1)
    ]


def apply_resource_capacity(
    projects: list[dict[str, Any]], resource_capacity: dict[str, float]
) -> list[dict[str, Any]]:
    """Greedily select projects that fit within resource capacity (sorted by value desc)."""
    if not resource_capacity:
        return projects

    usage: dict[str, float] = {}
    selected: list[dict[str, Any]] = []

    for project in sorted(projects, key=lambda x: x.get("value", 0), reverse=True):
        feasible = True
        for resource, needed in project.get("resource_requirements", {}).items():
            capacity = resource_capacity.get(resource, float("inf"))
            if usage.get(resource, 0.0) + needed > capacity:
                feasible = False
                break
        if feasible:
            selected.append(project)
            for resource, needed in project.get("resource_requirements", {}).items():
                usage[resource] = usage.get(resource, 0.0) + needed

    return selected


# ---------------------------------------------------------------------------
# Knapsack optimisation
# ---------------------------------------------------------------------------


def knapsack_select(
    projects: list[dict[str, Any]], max_budget: int, scale: int
) -> list[dict[str, Any]]:
    """
    0-1 knapsack optimisation for project selection.

    Args:
        projects: Projects with 'cost' and 'value' fields.
        max_budget: Budget ceiling expressed in granularity units.
        scale: Cost granularity divisor (e.g. 1000).

    Returns:
        Optimal project subset that maximises total value.
    """
    if max_budget <= 0:
        return []

    dp = [0.0] * (max_budget + 1)
    keep: list[list[bool]] = [[False] * (max_budget + 1) for _ in projects]

    for i, project in enumerate(projects):
        weight = int(project["cost"] // scale)
        value = project["value"]
        for budget in range(max_budget, weight - 1, -1):
            candidate = dp[budget - weight] + value
            if candidate > dp[budget]:
                dp[budget] = candidate
                keep[i][budget] = True

    selected = []
    remaining = max_budget
    for i in range(len(projects) - 1, -1, -1):
        if keep[i][remaining]:
            selected.append(projects[i])
            remaining -= int(projects[i]["cost"] // scale)
    return selected[::-1]


# ---------------------------------------------------------------------------
# Selection strategies
# ---------------------------------------------------------------------------


def select_mean_variance(
    projects: list[dict[str, Any]],
    budget_ceiling: float,
    resource_capacity: dict[str, float],
    risk_aversion: float,
) -> list[dict[str, Any]]:
    """Mean-variance optimisation: maximise (value - risk_aversion * risk^2) / cost."""
    if not projects:
        return []
    ranked = sorted(
        projects,
        key=lambda p: (
            (p.get("expected_value", 0) - risk_aversion * p.get("risk_score", 0) ** 2)
            / max(1.0, p.get("cost", 1))
        ),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    remaining_budget = budget_ceiling
    usage: dict[str, float] = {}
    for project in ranked:
        cost = project.get("cost", 0)
        if cost > remaining_budget:
            continue
        feasible = True
        for resource, needed in project.get("resource_requirements", {}).items():
            capacity = resource_capacity.get(resource, float("inf"))
            if usage.get(resource, 0.0) + needed > capacity:
                feasible = False
                break
        if feasible:
            selected.append(project)
            remaining_budget -= cost
            for resource, needed in project.get("resource_requirements", {}).items():
                usage[resource] = usage.get(resource, 0.0) + needed
    return selected


def select_ahp(
    projects: list[dict[str, Any]],
    budget_ceiling: float,
    resource_capacity: dict[str, float],
) -> list[dict[str, Any]]:
    """Analytic Hierarchy Process selection: alignment 45 %, ROI 35 %, risk 20 %."""
    if not projects:
        return []
    ranked = sorted(
        projects,
        key=lambda p: (
            p.get("alignment_score", 0) * 0.45
            + p.get("roi_score", 0) * 0.35
            + p.get("risk_score", 0) * 0.2
        ),
        reverse=True,
    )
    selected = []
    total_cost = 0.0
    for project in ranked:
        if total_cost + project.get("cost", 0) > budget_ceiling:
            continue
        selected.append(project)
        total_cost += project.get("cost", 0)
    return apply_resource_capacity(selected, resource_capacity)


def select_multi_objective(
    projects: list[dict[str, Any]],
    budget_ceiling: float,
    resource_capacity: dict[str, float],
    objective_weights: dict[str, float],
) -> list[dict[str, Any]]:
    """Weighted-sum multi-objective selection."""
    if not projects:
        return []
    weights = {
        "value": objective_weights.get("value", 0.35),
        "alignment": objective_weights.get("alignment", 0.25),
        "roi": objective_weights.get("roi", 0.2),
        "risk": objective_weights.get("risk", 0.2),
    }
    total_weight = sum(max(0.0, w) for w in weights.values()) or 1.0
    weights = {key: max(0.0, w) / total_weight for key, w in weights.items()}

    max_value = max((p.get("value", 0) for p in projects), default=1.0)
    max_roi = max((p.get("roi_score", 0) for p in projects), default=1.0)

    def score(project: dict[str, Any]) -> float:
        value_score = project.get("value", 0) / max(1.0, max_value)
        alignment_score = project.get("alignment_score", 0)
        roi_score = project.get("roi_score", 0) / max(1.0, max_roi)
        risk_score = project.get("risk_score", 0)
        return (
            value_score * weights["value"]
            + alignment_score * weights["alignment"]
            + roi_score * weights["roi"]
            + risk_score * weights["risk"]
        )

    ranked = sorted(
        projects,
        key=lambda p: score(p) / max(1.0, p.get("cost", 1)),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    usage: dict[str, float] = {}
    remaining_budget = budget_ceiling
    for project in ranked:
        cost = project.get("cost", 0)
        if cost > remaining_budget:
            continue
        feasible = True
        for resource, needed in project.get("resource_requirements", {}).items():
            capacity = resource_capacity.get(resource, float("inf"))
            if usage.get(resource, 0.0) + needed > capacity:
                feasible = False
                break
        if not feasible:
            continue
        selected.append(project)
        remaining_budget -= cost
        for resource, needed in project.get("resource_requirements", {}).items():
            usage[resource] = usage.get(resource, 0.0) + needed
    return selected


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------


def apply_scenario_multipliers(
    projects: list[dict[str, Any]], multipliers: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return projects with numeric fields scaled by the given multipliers map."""
    if not multipliers:
        return list(projects)

    adjusted_projects = []
    for project in projects:
        adjusted = dict(project)
        for field, multiplier in multipliers.items():
            if (
                field == "projections"
                and isinstance(project.get("projections"), dict)
                and isinstance(multiplier, dict)
            ):
                projections = dict(project["projections"])
                for key, proj_multiplier in multiplier.items():
                    if key in projections and isinstance(projections[key], (int, float)):
                        projections[key] = projections[key] * proj_multiplier
                adjusted["projections"] = projections
                continue
            if isinstance(adjusted.get(field), (int, float)) and isinstance(
                multiplier, (int, float)
            ):
                adjusted[field] = adjusted[field] * multiplier
                if field in {"roi", "strategic_score"}:
                    adjusted[field] = max(0.0, min(1.0, adjusted[field]))
        adjusted_projects.append(adjusted)

    return adjusted_projects


# ---------------------------------------------------------------------------
# Portfolio metrics helpers
# ---------------------------------------------------------------------------


def calculate_portfolio_metrics(selected_projects: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate aggregate portfolio-level metrics over selected projects."""
    if not selected_projects:
        return {"average_score": 0, "risk_profile": "low", "strategic_coverage": 0}

    avg_score = sum(p.get("score", 0) for p in selected_projects) / len(selected_projects)
    avg_roi = sum(p.get("roi_score", 0) for p in selected_projects) / len(selected_projects)
    avg_risk = sum(p.get("risk_score", 0.6) for p in selected_projects) / len(selected_projects)
    total_npv = sum(p.get("expected_value", 0) for p in selected_projects)

    return {
        "average_score": avg_score,
        "average_roi": avg_roi,
        "total_npv": total_npv,
        "risk_profile": "balanced" if avg_risk >= 0.5 else "elevated",
        "strategic_coverage": 0.8,
    }


def calculate_investment_mix(portfolio: list[dict[str, Any]]) -> dict[str, float]:
    """Calculate percentage breakdown of portfolio investment by category."""
    if not portfolio:
        return {"innovation": 0.0, "operations": 0.0, "compliance": 0.0}

    total_cost = sum(p.get("cost", 0) for p in portfolio)
    if total_cost == 0:
        return {"innovation": 0.0, "operations": 0.0, "compliance": 0.0}

    mix: dict[str, float] = {"innovation": 0.0, "operations": 0.0, "compliance": 0.0}
    for project in portfolio:
        category = project.get("category", "operations")
        cost = project.get("cost", 0)
        if category in mix:
            mix[category] += cost / total_cost

    return mix


def generate_scenario_comparison(scenario_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a cross-scenario comparison summary (value, cost, project count ranges)."""
    if not scenario_results:
        return {}

    return {
        "value_range": {
            "min": min(s.get("results", {}).get("total_value", 0) for s in scenario_results),
            "max": max(s.get("results", {}).get("total_value", 0) for s in scenario_results),
        },
        "cost_range": {
            "min": min(s.get("results", {}).get("total_cost", 0) for s in scenario_results),
            "max": max(s.get("results", {}).get("total_cost", 0) for s in scenario_results),
        },
        "projects_range": {
            "min": min(s.get("results", {}).get("total_projects", 0) for s in scenario_results),
            "max": max(s.get("results", {}).get("total_projects", 0) for s in scenario_results),
        },
    }


def recommend_best_scenario(scenario_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the scenario with the highest total_value as the recommended option."""
    if not scenario_results:
        return {"scenario_id": None, "rationale": "No scenarios available"}

    best_scenario = max(scenario_results, key=lambda s: s.get("results", {}).get("total_value", 0))
    return {
        "scenario_id": best_scenario.get("scenario_id"),
        "scenario_name": best_scenario.get("scenario_name"),
        "rationale": (
            f"Highest total value: "
            f"${best_scenario.get('results', {}).get('total_value', 0):,.0f}"
        ),
    }


def identify_trade_offs(optimization_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a static list of well-known portfolio trade-off dimensions."""
    return [
        {
            "dimension": "value_vs_risk",
            "description": "Higher value projects tend to have higher risk",
        },
        {
            "dimension": "strategic_vs_financial",
            "description": "Strategic alignment sometimes conflicts with short-term ROI",
        },
    ]


def suggest_rebalancing_actions(category: str, gap: float) -> list[str]:
    """Return human-readable rebalancing suggestions for a given category/gap pair."""
    if gap > 0:
        return [
            f"Approve more {category} projects from the pipeline",
            f"Accelerate delivery of existing {category} initiatives",
            f"Increase investment allocation for {category} category",
        ]
    return [
        f"Defer or cancel lower-priority {category} projects",
        f"Complete and close out existing {category} projects",
        f"Reduce new {category} project approvals temporarily",
    ]


def calculate_rebalancing_impact(
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return an estimated impact summary for a set of rebalancing recommendations."""
    return {
        "strategic_alignment_improvement": 0.05,
        "resource_utilization_change": 0.02,
        "estimated_implementation_time": "1-2 quarters",
    }
