"""Scenario what-if analysis routes.

Provides REST endpoints for running project-level and portfolio-level
what-if scenario analyses, listing preset templates, and calculating
cross-project cascade impacts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from routes._deps import (
    SCENARIOS_STORE_PATH,
    STORAGE_DIR,
    _audit_record,
    _load_store,
    _require_session,
    _write_json,
    permission_required,
)

router = APIRouter(prefix="/v1/api/scenarios", tags=["scenarios"])


# ---------------------------------------------------------------------------
# Scenario templates
# ---------------------------------------------------------------------------

SCENARIO_TEMPLATES: list[dict[str, Any]] = [
    {
        "template_id": "cost_reduction",
        "name": "Cost Reduction (-15%)",
        "description": "Simulate a 15% across-the-board cost reduction programme.",
        "domain": "financial",
        "parameters": {
            "budget_multiplier": 0.85,
            "budget_delta": 0,
            "cost_multiplier": 0.85,
        },
    },
    {
        "template_id": "aggressive_growth",
        "name": "Aggressive Growth (+30% budget)",
        "description": "Model the impact of increasing portfolio investment by 30%.",
        "domain": "financial",
        "parameters": {
            "budget_multiplier": 1.3,
            "budget_delta": 0,
            "cost_multiplier": 1.0,
        },
    },
    {
        "template_id": "risk_averse",
        "name": "Risk-Averse Portfolio",
        "description": "Minimise portfolio risk by filtering high-risk projects.",
        "domain": "portfolio",
        "parameters": {
            "budget_multiplier": 1.0,
            "risk_appetite": 0.3,
            "risk_aversion": 0.8,
        },
    },
    {
        "template_id": "innovation_focused",
        "name": "Innovation-Focused Rebalance",
        "description": "Shift portfolio mix toward innovation and R&D.",
        "domain": "portfolio",
        "parameters": {
            "budget_multiplier": 1.1,
            "priority_shift": {"strategic_alignment": 1.5, "compliance": 0.7},
        },
    },
    {
        "template_id": "headcount_freeze",
        "name": "Headcount Freeze",
        "description": "Model impact when resource capacity is frozen at current levels.",
        "domain": "resource",
        "parameters": {
            "capacity_multiplier": 0.85,
            "budget_multiplier": 1.0,
        },
    },
    {
        "template_id": "schedule_compression",
        "name": "Schedule Compression (-20%)",
        "description": "Model the impact of compressing all task durations by 20%.",
        "domain": "schedule",
        "parameters": {
            "duration_multiplier": 0.8,
            "task_duration_multiplier": 0.8,
        },
    },
]


@router.get("/templates")
@permission_required("analytics.view")
async def list_templates(request: Request) -> dict[str, Any]:
    """Return available scenario template presets."""
    _require_session(request)
    return {"templates": SCENARIO_TEMPLATES}


# ---------------------------------------------------------------------------
# Run a what-if scenario
# ---------------------------------------------------------------------------


@router.post("/run")
@permission_required("analytics.view")
async def run_scenario(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """Run a what-if scenario analysis.

    Accepts either a ``template_id`` to use a preset template, or a custom
    ``parameters`` dict.  When both are provided the template is used as a
    base and ``parameters`` are merged on top as overrides.

    Required fields:
        - ``project_id`` or ``portfolio_id`` — the entity to analyse
        - ``template_id`` (str) OR ``parameters`` (dict)

    Optional fields:
        - ``name`` — human-readable scenario label
        - ``linked_project_ids`` — for cascade impact analysis
    """
    _require_session(request)

    project_id = payload.get("project_id")
    portfolio_id = payload.get("portfolio_id")
    if not project_id and not portfolio_id:
        raise HTTPException(
            status_code=400,
            detail="Either project_id or portfolio_id is required",
        )

    template_id = payload.get("template_id")
    custom_params = payload.get("parameters", {})

    # Resolve parameters from template if specified
    params: dict[str, Any] = {}
    if template_id:
        template = next(
            (t for t in SCENARIO_TEMPLATES if t["template_id"] == template_id),
            None,
        )
        if template is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown template: {template_id}",
            )
        params = dict(template.get("parameters", {}))

    # Merge custom overrides
    params.update(custom_params)

    entity_id = project_id or portfolio_id
    scenario_name = payload.get("name") or (
        next(
            (t["name"] for t in SCENARIO_TEMPLATES if t["template_id"] == template_id),
            "Custom Scenario",
        )
        if template_id
        else "Custom Scenario"
    )
    scenario_id = f"scn-{uuid4().hex[:8]}"

    # Compute baseline and scenario metrics
    baseline = _get_entity_baseline(entity_id or "")
    scenario_metrics = _apply_scenario_params(baseline, params)
    comparison = _compute_comparison(baseline, scenario_metrics)

    # Cascade impact across linked projects
    cascade = None
    linked_ids = payload.get("linked_project_ids", [])
    if linked_ids and project_id:
        cascade = _compute_cascade(project_id, params, linked_ids)

    result: dict[str, Any] = {
        "scenario_id": scenario_id,
        "name": scenario_name,
        "template_id": template_id,
        "entity_id": entity_id,
        "entity_type": "project" if project_id else "portfolio",
        "parameters": params,
        "baseline": baseline,
        "scenario": scenario_metrics,
        "comparison": comparison,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if cascade is not None:
        result["cascade_impacts"] = cascade

    # Persist
    store = _load_store(SCENARIOS_STORE_PATH, {"scenarios": [], "published_decisions": []})
    store.setdefault("scenarios", []).append(result)
    _write_json(SCENARIOS_STORE_PATH, store)

    _audit_record(
        request,
        "scenario.run",
        {"resource": "scenario", "scenario_id": scenario_id, "entity_id": entity_id},
    )

    return result


# ---------------------------------------------------------------------------
# Compare multiple scenarios side-by-side
# ---------------------------------------------------------------------------


@router.post("/compare")
@permission_required("analytics.view")
async def compare_scenarios(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """Compare two or more previously-run scenarios side-by-side.

    Required fields:
        - ``scenario_ids`` — list of scenario IDs to compare
    """
    _require_session(request)
    scenario_ids = payload.get("scenario_ids", [])
    if len(scenario_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 scenario_ids are required for comparison",
        )

    store = _load_store(SCENARIOS_STORE_PATH, {"scenarios": []})
    all_scenarios = store.get("scenarios", [])
    by_id = {s.get("scenario_id"): s for s in all_scenarios if isinstance(s, dict)}

    matched = []
    for sid in scenario_ids:
        if sid in by_id:
            matched.append(by_id[sid])

    if len(matched) < 2:
        raise HTTPException(
            status_code=404,
            detail="Not enough matching scenarios found",
        )

    # Build comparison summary
    metrics_keys = ["budget", "forecast_eac", "schedule_days", "cost_performance_index"]
    comparison_table: list[dict[str, Any]] = []
    for scenario in matched:
        row: dict[str, Any] = {
            "scenario_id": scenario.get("scenario_id"),
            "name": scenario.get("name"),
        }
        s_metrics = scenario.get("scenario", {})
        for key in metrics_keys:
            row[key] = s_metrics.get(key)
        comparison_table.append(row)

    return {
        "scenarios": matched,
        "comparison_table": comparison_table,
    }


# ---------------------------------------------------------------------------
# List all saved scenarios for an entity
# ---------------------------------------------------------------------------


@router.get("/list")
@permission_required("analytics.view")
async def list_scenarios(
    request: Request,
    project_id: str | None = None,
    portfolio_id: str | None = None,
) -> dict[str, Any]:
    """List saved scenarios, optionally filtered by entity."""
    _require_session(request)
    store = _load_store(SCENARIOS_STORE_PATH, {"scenarios": []})
    all_scenarios = store.get("scenarios", [])

    if project_id:
        filtered = [
            s
            for s in all_scenarios
            if s.get("entity_id") == project_id or s.get("project_id") == project_id
        ]
    elif portfolio_id:
        filtered = [
            s
            for s in all_scenarios
            if s.get("entity_id") == portfolio_id or s.get("portfolio_id") == portfolio_id
        ]
    else:
        filtered = all_scenarios

    return {"scenarios": filtered}


# ---------------------------------------------------------------------------
# Cascade impact endpoint
# ---------------------------------------------------------------------------


@router.post("/cascade-impact")
@permission_required("analytics.view")
async def cascade_impact(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """Calculate the cascade impact of a change in one project on linked projects.

    Required fields:
        - ``source_project_id`` — originating project
        - ``delta`` — change parameters (budget_delta, schedule_delta_days, cost_multiplier)
        - ``linked_project_ids`` — list of affected project IDs
    """
    _require_session(request)
    source_project_id = payload.get("source_project_id")
    if not source_project_id:
        raise HTTPException(status_code=400, detail="source_project_id is required")

    delta = payload.get("delta", {})
    linked_ids = payload.get("linked_project_ids", [])
    if not linked_ids:
        raise HTTPException(status_code=400, detail="linked_project_ids is required")

    impacts = _compute_cascade(source_project_id, delta, linked_ids)
    _audit_record(
        request,
        "scenario.cascade",
        {"resource": "scenario", "source_project_id": source_project_id},
    )
    return impacts


# ---------------------------------------------------------------------------
# Internal computation helpers
# ---------------------------------------------------------------------------


def _get_entity_baseline(entity_id: str) -> dict[str, Any]:
    """Load baseline metrics for an entity.

    In production this would call the Data Service; here we use the
    scenario store or sensible defaults.
    """
    path = STORAGE_DIR / "finance_budget.json"
    budget_store = _load_store(path, {"budgets": []})
    for budget in budget_store.get("budgets", []):
        if budget.get("workspace_id") == entity_id:
            return {
                "budget": float(budget.get("amounts", {}).get("total", 0) or 0),
                "forecast_eac": float(budget.get("amounts", {}).get("total", 0) or 0),
                "actual_cost": float(budget.get("amounts", {}).get("actual", 0) or 0),
                "schedule_days": 180,
                "cost_performance_index": 1.0,
                "schedule_performance_index": 1.0,
            }

    # Sensible defaults when no real data exists
    return {
        "budget": 1_000_000,
        "forecast_eac": 1_000_000,
        "actual_cost": 450_000,
        "schedule_days": 180,
        "cost_performance_index": 1.0,
        "schedule_performance_index": 1.0,
    }


def _apply_scenario_params(baseline: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """Apply scenario parameters to baseline metrics and return adjusted values."""
    scenario = dict(baseline)

    budget = float(baseline.get("budget", 0))
    eac = float(baseline.get("forecast_eac", 0))
    schedule = float(baseline.get("schedule_days", 0))

    budget_delta = float(params.get("budget_delta", 0) or 0)
    budget_mult = float(params.get("budget_multiplier", 1.0) or 1.0)
    cost_mult = float(params.get("cost_multiplier", 1.0) or 1.0)
    duration_mult = float(params.get("duration_multiplier", 1.0) or 1.0)
    duration_delta = float(params.get("schedule_delta_days", 0) or 0)

    scenario["budget"] = round((budget + budget_delta) * budget_mult, 2)
    scenario["forecast_eac"] = round(eac * cost_mult * budget_mult, 2)
    scenario["schedule_days"] = round((schedule + duration_delta) * duration_mult, 1)

    # Recalculate performance indices
    new_budget = scenario["budget"]
    new_eac = scenario["forecast_eac"]
    if new_eac > 0:
        scenario["cost_performance_index"] = round(new_budget / new_eac, 4)
    if schedule > 0 and scenario["schedule_days"] > 0:
        scenario["schedule_performance_index"] = round(schedule / scenario["schedule_days"], 4)

    return scenario


def _compute_comparison(baseline: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    """Build a comparison dict showing deltas between baseline and scenario."""
    return {
        "budget_variance": round(scenario.get("budget", 0) - baseline.get("budget", 0), 2),
        "budget_variance_pct": round(
            (
                (scenario.get("budget", 0) - baseline.get("budget", 0))
                / max(baseline.get("budget", 1), 1)
            )
            * 100,
            2,
        ),
        "eac_variance": round(scenario.get("forecast_eac", 0) - baseline.get("forecast_eac", 0), 2),
        "schedule_variance_days": round(
            scenario.get("schedule_days", 0) - baseline.get("schedule_days", 0), 1
        ),
        "cpi_delta": round(
            scenario.get("cost_performance_index", 1.0)
            - baseline.get("cost_performance_index", 1.0),
            4,
        ),
        "spi_delta": round(
            scenario.get("schedule_performance_index", 1.0)
            - baseline.get("schedule_performance_index", 1.0),
            4,
        ),
    }


def _compute_cascade(
    source_project_id: str,
    params: dict[str, Any],
    linked_ids: list[str],
) -> dict[str, Any]:
    """Calculate cascade impacts across linked projects."""
    budget_delta = float(params.get("budget_delta", 0) or 0)
    schedule_delta = float(params.get("schedule_delta_days", 0) or 0)
    budget_mult = float(params.get("budget_multiplier", 1.0) or 1.0)

    # Derive an effective budget delta from the multiplier if no absolute delta
    if budget_delta == 0 and budget_mult != 1.0:
        budget_delta = 1_000_000 * (budget_mult - 1.0)

    impacts: list[dict[str, Any]] = []
    total_budget_impact = 0.0

    for linked_id in linked_ids:
        baseline = _get_entity_baseline(linked_id)
        linked_budget = baseline.get("budget", 1_000_000)
        weight = 0.5  # Default propagation weight
        cascaded_budget = round(budget_delta * weight, 2)
        cascaded_schedule = round(schedule_delta * weight, 1)
        total_budget_impact += cascaded_budget

        impacts.append(
            {
                "project_id": linked_id,
                "propagation_weight": weight,
                "original_budget": linked_budget,
                "cascaded_budget_delta": cascaded_budget,
                "cascaded_schedule_delta_days": cascaded_schedule,
                "adjusted_eac": round(linked_budget + cascaded_budget, 2),
                "risk_indicator": "high" if abs(cascaded_budget) > linked_budget * 0.1 else "low",
            }
        )

    return {
        "source_project_id": source_project_id,
        "total_linked_projects": len(linked_ids),
        "total_cascaded_budget_impact": round(total_budget_impact, 2),
        "impacts": impacts,
    }
