"""Action handler for estimate_duration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from schedule_utils import duration_cache_key

from integrations.services.integration import ModelTask

if TYPE_CHECKING:
    from schedule_planning_agent import SchedulePlanningAgent


async def estimate_duration(
    agent: SchedulePlanningAgent,
    tasks: list[dict[str, Any]],
    project_context: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Estimate task durations using AI and historical data.

    Returns duration estimates with confidence intervals.
    """
    agent.logger.info("Estimating task durations")
    cached = await _get_cached_duration_estimates(agent, project_context, tasks)
    if cached:
        return cached

    team_performance = float(project_context.get("team_performance", 1.0))
    if agent.azure_ml_client and not agent.duration_model_id:
        historical = await _get_historical_durations("project", "medium")
        artifact = agent.azure_ml_client.train_duration_model(
            historical,
            team_performance,
            {"project_id": project_context.get("project_id")},
        )
        agent.duration_model_id = artifact.model_id

    if agent.ai_model_service and not agent.ai_duration_model_id:
        historical = await _get_historical_durations("project", "medium")
        training = agent.ai_model_service.train_model(ModelTask.SCHEDULE_ESTIMATION, historical)
        agent.ai_duration_model_id = training.record.model_id
        agent.ai_model_service.deploy_model(agent.ai_duration_model_id)

    duration_estimates: dict[str, dict[str, Any]] = {}

    for task in tasks:
        task_id = task.get("task_id")
        if not task_id:
            continue
        task_name = task.get("name", "")
        complexity = task.get("complexity", "medium")

        historical_data = await _get_historical_durations(task_name, complexity)

        ml_estimate = None
        if agent.ai_model_service and agent.ai_duration_model_id:
            features = _build_duration_features(agent, task, project_context)
            ml_estimate = agent.ai_model_service.predict(agent.ai_duration_model_id, features)

        azure_estimate = None
        if agent.azure_ml_client and agent.duration_model_id:
            azure_estimate = agent.azure_ml_client.predict_duration(
                agent.duration_model_id, complexity
            )

        base_estimate = await _combine_duration_estimates(
            historical_data, ml_estimate, azure_estimate
        )

        optimistic, most_likely, pessimistic = await _calculate_pert_estimate(
            task, historical_data, base_estimate
        )

        expected_duration = (optimistic + 4 * most_likely + pessimistic) / 6

        duration_estimates[task_id] = {
            "optimistic": optimistic,
            "most_likely": most_likely,
            "pessimistic": pessimistic,
            "expected": expected_duration,
            "confidence": await _estimate_confidence(historical_data),
            "unit": "days",
        }

    await _cache_duration_estimates(agent, project_context, tasks, duration_estimates)
    return duration_estimates


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_historical_durations(task_name: str, complexity: str) -> list[float]:
    """Query historical task durations."""
    return [5.0, 7.0, 6.0]  # Baseline


async def _get_cached_duration_estimates(
    agent: SchedulePlanningAgent,
    project_context: dict[str, Any],
    tasks: list[dict[str, Any]],
) -> dict[str, dict[str, Any]] | None:
    if not agent.cache_client:
        return None
    project_id = project_context.get("project_id", "default")
    signature = ",".join(sorted(task.get("task_id", "") for task in tasks))
    cache_key = duration_cache_key(project_id, signature)
    cached = agent.cache_client.get(cache_key)
    return cached  # type: ignore


async def _cache_duration_estimates(
    agent: SchedulePlanningAgent,
    project_context: dict[str, Any],
    tasks: list[dict[str, Any]],
    estimates: dict[str, dict[str, Any]],
) -> None:
    if not agent.cache_client:
        return
    project_id = project_context.get("project_id", "default")
    signature = ",".join(sorted(task.get("task_id", "") for task in tasks))
    cache_key = duration_cache_key(project_id, signature)
    agent.cache_client.set(cache_key, estimates, ttl_seconds=agent.cache_ttl_seconds)


def _build_duration_features(
    agent: SchedulePlanningAgent,
    task: dict[str, Any],
    project_context: dict[str, Any],
) -> dict[str, Any]:
    complexity = task.get("complexity", "medium")
    complexity_factor = {"low": 0.8, "medium": 1.0, "high": 1.3}.get(complexity, 1.0)
    resources = task.get("resources", []) or project_context.get("resources", [])
    skill_factor = _calculate_skill_factor(resources)
    performance_factor = _calculate_performance_factor(resources, project_context)
    return {
        "weight": skill_factor * performance_factor,
        "complexity": complexity_factor,
    }


def _calculate_skill_factor(resources: list[dict[str, Any]]) -> float:
    if not resources:
        return 1.0
    scores = [float(resource.get("skill_level", 1.0)) for resource in resources]
    return max(0.5, min(1.5, sum(scores) / len(scores)))


def _calculate_performance_factor(
    resources: list[dict[str, Any]], project_context: dict[str, Any]
) -> float:
    team_performance = float(project_context.get("team_performance", 1.0))
    resource_scores = [
        float(resource.get("performance", team_performance)) for resource in resources
    ] or [team_performance]
    avg = sum(resource_scores) / len(resource_scores)
    return max(0.5, min(1.5, 1 / avg if avg > 0 else 1.0))


async def _combine_duration_estimates(
    historical_data: list[float],
    ml_estimate: float | None,
    azure_estimate: float | None,
) -> float:
    candidates = [value for value in [ml_estimate, azure_estimate] if value]
    if historical_data:
        candidates.append(sum(historical_data) / len(historical_data))
    if not candidates:
        return 5.0
    return sum(candidates) / len(candidates)


async def _estimate_confidence(historical_data: list[float]) -> float:
    if len(historical_data) < 2:
        return 0.7
    avg = sum(historical_data) / len(historical_data)
    variance = sum((value - avg) ** 2 for value in historical_data) / len(historical_data)
    spread = variance**0.5
    confidence = 1.0 - min(0.5, spread / max(avg, 1.0))
    return max(0.5, min(0.95, confidence))


async def _calculate_pert_estimate(
    task: dict[str, Any], historical_data: list[float], base_estimate: float
) -> tuple[float, float, float]:
    """Calculate PERT estimates (optimistic, most likely, pessimistic)."""
    if historical_data:
        avg = sum(historical_data) / len(historical_data)
        variance = sum((value - avg) ** 2 for value in historical_data) / len(historical_data)
        spread = max(0.5, variance**0.5)
    else:
        avg = base_estimate or 5.0
        spread = max(1.0, avg * 0.25)

    base = base_estimate or avg
    complexity = task.get("complexity", "medium")
    complexity_factor = {"low": 0.9, "medium": 1.0, "high": 1.2}.get(complexity, 1.0)
    base *= complexity_factor

    optimistic = max(0.5, base - spread)
    most_likely = max(0.5, base)
    pessimistic = max(optimistic + 0.5, base + spread * 1.3)

    return optimistic, most_likely, pessimistic
