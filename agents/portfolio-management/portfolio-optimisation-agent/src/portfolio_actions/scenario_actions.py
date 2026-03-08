"""
Portfolio Scenario Action Handlers

Handlers for:
- run_scenario_analysis
- compare_scenarios
- upsert_scenario
- get_scenario
- list_scenarios
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from portfolio_utils import (
    apply_scenario_multipliers,
    generate_scenario_comparison,
    identify_trade_offs,
    recommend_best_scenario,
)

if TYPE_CHECKING:
    from portfolio_strategy_agent import PortfolioStrategyAgent


async def run_scenario_analysis(
    agent: PortfolioStrategyAgent,
    scenarios: list[dict[str, Any]],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """
    Generate alternate portfolios under different scenarios and compare outcomes.

    Returns scenario analysis with trade-off details.
    """
    agent.logger.info("Running scenario analysis for %s scenarios", len(scenarios))

    async def _run_single_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
        scenario_index = len(agent.optimization_scenarios)
        scenario_id = scenario.get("id", f"scenario_{scenario_index}")
        scenario_name = scenario.get("name", f"Scenario {scenario_index + 1}")

        budget_multiplier = scenario.get("budget_multiplier", 1.0)
        capacity_multiplier = scenario.get("capacity_multiplier", 1.0)
        priority_shift = scenario.get("priority_shift", {})
        parameter_multipliers = scenario.get("parameter_multipliers", {})

        base_resource_capacity = scenario.get("resource_capacity", {})
        adjusted_resource_capacity = {
            resource: value * capacity_multiplier
            for resource, value in base_resource_capacity.items()
        }
        adjusted_constraints = {
            "budget_ceiling": scenario.get("budget_ceiling", 1000000) * budget_multiplier,
            "resource_capacity": adjusted_resource_capacity,
            "min_compliance_spend": scenario.get("min_compliance_spend", 0),
            "risk_appetite": scenario.get("risk_appetite", 0.6),
            "min_alignment_score": scenario.get("min_alignment_score", 0.3),
            "optimization_method": scenario.get("optimization_method", "integer_programming"),
            "risk_aversion": scenario.get("risk_aversion", 0.5),
            "objective_weights": scenario.get("objective_weights", {}),
        }

        adjusted_weights = agent.default_weights.copy()
        for criterion, adjustment in priority_shift.items():
            if criterion in adjusted_weights:
                adjusted_weights[criterion] *= adjustment

        total_weight = sum(adjusted_weights.values())
        if total_weight > 0:
            adjusted_weights = {k: v / total_weight for k, v in adjusted_weights.items()}

        scenario_projects = apply_scenario_multipliers(
            scenario.get("projects", []), parameter_multipliers
        )
        optimization_result = await agent._optimize_portfolio(
            scenario_projects,
            adjusted_constraints,
            tenant_id=scenario.get("tenant_id", tenant_id),
            correlation_id=scenario.get("correlation_id", scenario_id),
        )

        result = {
            "scenario_id": scenario_id,
            "scenario_name": scenario_name,
            "parameters": scenario,
            "results": optimization_result,
            "trade_offs": identify_trade_offs(optimization_result),
        }

        agent.optimization_scenarios[scenario_id] = {
            "name": scenario_name,
            "results": optimization_result,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if agent.db_service:
            await agent.db_service.store(
                "portfolio_scenarios",
                scenario_id,
                {
                    "scenario_id": scenario_id,
                    "scenario_name": scenario_name,
                    "parameters": scenario,
                    "results": optimization_result,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        return result

    scenario_output = await agent.scenario_engine.run_multi_scenarios(
        scenarios=scenarios,
        scenario_runner=_run_single_scenario,
        comparison_builder=generate_scenario_comparison,
    )
    scenario_results = scenario_output["scenarios"]
    comparison = scenario_output["comparison"]

    await agent.event_bus.publish(
        "portfolio.scenario.generated",
        {
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "scenarios": scenario_results,
            "comparison": comparison,
        },
    )

    return {
        "scenarios": scenario_results,
        "comparison": comparison,
        "recommendation": recommend_best_scenario(scenario_results),
    }


async def compare_scenarios(
    agent: PortfolioStrategyAgent,
    scenario_ids: list[str],
) -> dict[str, Any]:
    """Compare multiple scenarios side-by-side."""
    agent.logger.info("Comparing %s scenarios", len(scenario_ids))

    scenarios = []
    for scenario_id in scenario_ids:
        if scenario_id in agent.optimization_scenarios:
            scenarios.append(agent.optimization_scenarios[scenario_id])

    comparison = generate_scenario_comparison(scenarios)
    return {"scenarios": scenarios, "comparison": comparison}


async def upsert_scenario(
    agent: PortfolioStrategyAgent,
    scenario: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Create or update a named scenario definition."""
    scenario_id = scenario.get("id") or f"scenario_{uuid.uuid4().hex}"
    definition = {
        "scenario_id": scenario_id,
        "scenario": scenario,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.scenario_definitions[scenario_id] = definition
    if agent.db_service:
        await agent.db_service.store("portfolio_scenario_definitions", scenario_id, definition)
    await agent.event_bus.publish(
        "portfolio.scenario.updated",
        {
            "scenario_id": scenario_id,
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "scenario": scenario,
        },
    )
    return definition


async def get_scenario(
    agent: PortfolioStrategyAgent,
    scenario_id: str,
) -> dict[str, Any]:
    """Retrieve a scenario definition by ID."""
    if scenario_id in agent.scenario_definitions:
        return agent.scenario_definitions[scenario_id]
    return {"scenario_id": scenario_id, "scenario": {}, "status": "not_found"}


async def list_scenarios(agent: PortfolioStrategyAgent) -> dict[str, Any]:
    """Return all stored scenario definitions."""
    return {"scenarios": list(agent.scenario_definitions.values())}


# ---------------------------------------------------------------------------
# Scenario template presets
# ---------------------------------------------------------------------------

SCENARIO_TEMPLATES: dict[str, dict[str, Any]] = {
    "cost_reduction": {
        "name": "Cost Reduction (-15%)",
        "description": "Simulate a 15% across-the-board cost reduction programme.",
        "budget_multiplier": 0.85,
        "capacity_multiplier": 1.0,
        "priority_shift": {"roi": 1.3, "strategic_alignment": 0.9},
        "parameter_multipliers": {"cost": 0.85},
        "risk_appetite": 0.5,
        "optimization_method": "integer_programming",
    },
    "aggressive_growth": {
        "name": "Aggressive Growth (+30% budget)",
        "description": "Model the impact of increasing portfolio investment by 30%.",
        "budget_multiplier": 1.3,
        "capacity_multiplier": 1.15,
        "priority_shift": {"strategic_alignment": 1.4, "roi": 1.0},
        "parameter_multipliers": {"cost": 1.0},
        "risk_appetite": 0.7,
        "optimization_method": "integer_programming",
    },
    "risk_averse": {
        "name": "Risk-Averse Portfolio",
        "description": "Minimise portfolio risk by filtering high-risk projects and favouring proven approaches.",
        "budget_multiplier": 1.0,
        "capacity_multiplier": 1.0,
        "priority_shift": {"risk": 1.8, "roi": 0.8, "compliance": 1.3},
        "parameter_multipliers": {},
        "risk_appetite": 0.3,
        "risk_aversion": 0.8,
        "optimization_method": "mean_variance",
    },
    "innovation_focused": {
        "name": "Innovation-Focused Rebalance",
        "description": "Shift portfolio mix toward innovation and R&D at the expense of BAU.",
        "budget_multiplier": 1.1,
        "capacity_multiplier": 1.05,
        "priority_shift": {"strategic_alignment": 1.5, "compliance": 0.7},
        "parameter_multipliers": {"projections": {"innovation_score": 1.3}},
        "risk_appetite": 0.65,
        "optimization_method": "multi_objective",
        "objective_weights": {"value": 0.25, "alignment": 0.4, "roi": 0.15, "risk": 0.2},
    },
    "headcount_freeze": {
        "name": "Headcount Freeze",
        "description": "Model portfolio impact when resource capacity is frozen at current levels.",
        "budget_multiplier": 1.0,
        "capacity_multiplier": 0.85,
        "priority_shift": {"resource_feasibility": 1.5},
        "parameter_multipliers": {},
        "risk_appetite": 0.5,
        "optimization_method": "integer_programming",
    },
    "regulatory_compliance": {
        "name": "Compliance-First",
        "description": "Prioritise regulatory and compliance projects above all discretionary spend.",
        "budget_multiplier": 1.0,
        "capacity_multiplier": 1.0,
        "priority_shift": {"compliance": 2.0, "roi": 0.6, "strategic_alignment": 0.8},
        "parameter_multipliers": {},
        "risk_appetite": 0.4,
        "min_compliance_spend": 200000,
        "optimization_method": "integer_programming",
    },
}


async def list_scenario_templates(
    agent: PortfolioStrategyAgent,
) -> dict[str, Any]:
    """Return the catalogue of pre-built scenario templates.

    Each template contains ready-to-use parameters that can be passed
    directly to ``run_scenario_analysis`` or customised by the user first.
    """
    templates = []
    for template_id, template in SCENARIO_TEMPLATES.items():
        templates.append(
            {
                "template_id": template_id,
                "name": template["name"],
                "description": template["description"],
                **{k: v for k, v in template.items() if k not in ("name", "description")},
            }
        )
    return {"templates": templates}


async def create_scenario_from_template(
    agent: PortfolioStrategyAgent,
    template_id: str,
    overrides: dict[str, Any] | None = None,
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Instantiate a scenario from a preset template, optionally applying overrides.

    Args:
        agent: The owning PortfolioStrategyAgent instance.
        template_id: One of the keys in ``SCENARIO_TEMPLATES``.
        overrides: Optional dict of parameter overrides to merge on top of the
            template defaults (e.g. ``{"budget_multiplier": 0.9}``).
        tenant_id: Tenant scope.
        correlation_id: Request correlation ID.

    Returns:
        The created scenario definition.
    """
    if template_id not in SCENARIO_TEMPLATES:
        available = ", ".join(sorted(SCENARIO_TEMPLATES))
        raise ValueError(f"Unknown template: {template_id}. Available templates: {available}")

    template = dict(SCENARIO_TEMPLATES[template_id])
    if overrides:
        template.update(overrides)

    scenario_id = f"template-{template_id}-{uuid.uuid4().hex[:8]}"
    scenario = {"id": scenario_id, **template}

    return await upsert_scenario(
        agent,
        scenario,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )
