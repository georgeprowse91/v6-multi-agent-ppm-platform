"""Action handlers for what_if_analysis and generate_schedule_variants."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from schedule_planning_agent import SchedulePlanningAgent


async def what_if_analysis(
    agent: SchedulePlanningAgent,
    schedule_id: str,
    what_if_params: dict[str, Any],
) -> dict[str, Any]:
    """
    Perform what-if scenario analysis.

    Returns scenario comparison results.
    """
    agent.logger.info("Running what-if analysis for schedule: %s", schedule_id)

    schedule = agent.schedules.get(schedule_id)
    if not schedule:
        raise ValueError(f"Schedule not found: {schedule_id}")

    scenario_output = await agent.scenario_engine.run_scenario(
        baseline=schedule,
        scenario_params=what_if_params,
        scenario_builder=create_scenario,
        metrics_builder=recalculate_schedule,
        comparison_builder=compare_schedules,
        recommendation_builder=generate_scenario_recommendation,
    )
    recalculated = scenario_output["scenario_metrics"]
    comparison = scenario_output["comparison"]

    return {
        "schedule_id": schedule_id,
        "scenario_params": what_if_params,
        "baseline_duration": schedule.get("project_duration_days", 0),
        "scenario_duration": recalculated.get("project_duration_days", 0),
        "duration_difference": comparison.get("duration_difference", 0),
        "cost_impact": comparison.get("cost_impact", 0),
        "resource_impact": comparison.get("resource_impact", {}),
        "recommendation": scenario_output.get("recommendation"),
    }


async def generate_schedule_variants(
    agent: SchedulePlanningAgent,
    schedule_id: str,
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate scenario variants for a schedule and compare outcomes."""
    agent.logger.info("Generating schedule variants for %s", schedule_id)

    schedule = agent.schedules.get(schedule_id)
    if not schedule:
        raise ValueError(f"Schedule not found: {schedule_id}")

    baseline_metrics = await recalculate_schedule(schedule)

    async def _run_variant(variant: dict[str, Any], index: int) -> dict[str, Any]:
        scenario_params = variant.get("params") or variant
        scenario_name = variant.get("name") or f"Scenario {index + 1}"
        scenario_id = variant.get("scenario_id") or f"{schedule_id}-scenario-{index + 1}"
        scenario_output = await agent.scenario_engine.run_scenario(
            baseline=schedule,
            scenario_params=scenario_params,
            scenario_builder=create_scenario,
            metrics_builder=recalculate_schedule,
            comparison_builder=compare_schedules,
            recommendation_builder=generate_scenario_recommendation,
        )
        return {
            "scenario_id": scenario_id,
            "name": scenario_name,
            "params": scenario_params,
            "metrics": scenario_output["scenario_metrics"],
            "comparison": scenario_output["comparison"],
            "recommendation": scenario_output.get("recommendation"),
        }

    scenario_results = [
        await _run_variant(variant, index) for index, variant in enumerate(scenarios)
    ]
    durations = [result["metrics"].get("project_duration_days", 0) for result in scenario_results]
    duration_summary = {
        "baseline_duration": baseline_metrics.get("project_duration_days", 0),
        "best_case": min(durations) if durations else 0,
        "worst_case": max(durations) if durations else 0,
        "average": sum(durations) / len(durations) if durations else 0,
    }

    return {
        "schedule_id": schedule_id,
        "baseline_metrics": baseline_metrics,
        "scenarios": scenario_results,
        "duration_summary": duration_summary,
    }


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------


async def create_scenario(schedule: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """Create scenario schedule with modified parameters."""
    scenario = dict(schedule)
    tasks = [dict(task) for task in schedule.get("tasks", [])]
    scenario["tasks"] = tasks

    duration_delta_days = float(params.get("duration_delta_days", 0) or 0)
    duration_multiplier = params.get("duration_multiplier")
    task_delta = float(params.get("task_duration_delta_days", 0) or 0)
    task_multiplier = params.get("task_duration_multiplier")

    if task_delta or task_multiplier:
        for task in tasks:
            current = float(task.get("duration_days", 0) or 0)
            updated = current + task_delta
            if task_multiplier:
                updated *= float(task_multiplier)
            task["duration_days"] = max(updated, 0)

    baseline_duration = float(schedule.get("project_duration_days", 0) or 0)
    updated_duration = baseline_duration + duration_delta_days
    if duration_multiplier:
        updated_duration *= float(duration_multiplier)

    scenario["project_duration_days"] = max(updated_duration, 0)
    scenario["scenario_notes"] = params.get("notes")
    scenario["scenario_adjustments"] = params
    return scenario


async def recalculate_schedule(schedule: dict[str, Any]) -> dict[str, Any]:
    """Recalculate schedule with changes."""
    return schedule


async def compare_schedules(baseline: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    """Compare two schedules."""
    return {
        "duration_difference": scenario.get("project_duration_days", 0)
        - baseline.get("project_duration_days", 0),
        "cost_impact": 0,
        "resource_impact": {},
    }


async def generate_scenario_recommendation(comparison: dict[str, Any]) -> str:
    """Generate recommendation based on scenario comparison."""
    if comparison.get("duration_difference", 0) < 0:
        return "Scenario reduces project duration. Consider implementing."
    else:
        return "Scenario increases project duration. Not recommended."
