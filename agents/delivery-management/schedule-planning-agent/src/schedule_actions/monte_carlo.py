"""Action handler for run_monte_carlo and simulation helpers."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from schedule_utils import (
    persist_simulation,
    publish_schedule_simulated,
    simulation_cache_key,
)

from schedule_actions.critical_path import forward_pass, forward_pass_sync

if TYPE_CHECKING:
    from schedule_planning_agent import SchedulePlanningAgent


async def run_monte_carlo(
    agent: SchedulePlanningAgent, schedule_id: str, iterations: int = 1000
) -> dict[str, Any]:
    """
    Run Monte Carlo simulation for schedule risk analysis.

    Returns probabilistic completion dates.
    """
    agent.logger.info("Running Monte Carlo simulation for schedule: %s", schedule_id)

    if agent.cache_client:
        cached = agent.cache_client.get(simulation_cache_key(schedule_id))
        if cached and cached.get("iterations") == iterations:
            return {"schedule_id": schedule_id, **cached}

    schedule = agent.schedules.get(schedule_id)
    if not schedule:
        raise ValueError(f"Schedule not found: {schedule_id}")

    tasks = schedule.get("tasks", [])
    dependencies = schedule.get("dependencies", [])

    task_samples: dict[str, list[float]] = {task["task_id"]: [] for task in tasks}
    rng = random.Random(agent.simulation_seed)

    async def _sample_duration(_: int) -> float:
        sampled_tasks = await sample_task_durations(tasks, agent.simulation_seed, rng=rng)
        duration = await calculate_simulated_duration(sampled_tasks, dependencies)
        for task in sampled_tasks:
            task_samples[task["task_id"]].append(float(task.get("duration", 0)))
        return duration

    if agent.databricks_client:

        def _databricks_sampler(index: int, rng_local: random.Random) -> float:
            sampled_tasks = [
                dict(
                    task,
                    duration=rng_local.triangular(
                        float(task.get("optimistic_duration", task.get("duration", 0))),
                        float(task.get("pessimistic_duration", task.get("duration", 0))),
                        float(task.get("most_likely_duration", task.get("duration", 0))),
                    ),
                )
                for task in tasks
            ]
            forward = forward_pass_sync(sampled_tasks, dependencies)
            duration = max((task.get("early_finish", 0) for task in forward), default=0)
            for task in sampled_tasks:
                task_samples[task["task_id"]].append(float(task.get("duration", 0)))
            return float(duration)

        monte_carlo = agent.databricks_client.simulate(
            iterations=iterations,
            sampler=_databricks_sampler,
            percentiles=(50, 80, 90, 95),
            rng=rng,
        )
        simulation_results = monte_carlo.results
        p50 = monte_carlo.percentiles.get(50, 0)
        p80 = monte_carlo.percentiles.get(80, 0)
        p90 = monte_carlo.percentiles.get(90, 0)
        p95 = monte_carlo.percentiles.get(95, 0)
        distribution_stats = monte_carlo.statistics
    elif agent.ai_model_service and agent.enable_ml_simulation:
        simulation_results = await run_ml_simulation(
            agent, tasks, dependencies, iterations, task_samples
        )
        p50 = await calculate_percentile(simulation_results, 50)
        p80 = await calculate_percentile(simulation_results, 80)
        p90 = await calculate_percentile(simulation_results, 90)
        p95 = await calculate_percentile(simulation_results, 95)
        distribution_stats = {
            "min": min(simulation_results) if simulation_results else 0,
            "max": max(simulation_results) if simulation_results else 0,
            "mean": (
                sum(simulation_results) / len(simulation_results) if simulation_results else 0
            ),
        }
    else:
        monte_carlo = await agent.scenario_engine.run_monte_carlo(
            iterations=iterations,
            sampler=_sample_duration,
            percentiles=(50, 80, 90, 95),
        )
        simulation_results = monte_carlo.results
        p50 = monte_carlo.percentiles.get(50, 0)
        p80 = monte_carlo.percentiles.get(80, 0)
        p90 = monte_carlo.percentiles.get(90, 0)
        p95 = monte_carlo.percentiles.get(95, 0)
        distribution_stats = monte_carlo.statistics

    # Calculate risk metrics
    risk_score = await calculate_schedule_risk(
        simulation_results, schedule.get("project_duration_days", 0)
    )

    risk_drivers = await extract_risk_drivers(task_samples, simulation_results)

    schedule["simulation"] = {
        "iterations": iterations,
        "p50_duration": p50,
        "p80_duration": p80,
        "p90_duration": p90,
        "p95_duration": p95,
        "risk_score": risk_score,
        "distribution": distribution_stats,
    }
    if agent.enable_persistence and agent._sql_engine:
        await persist_simulation(
            agent, schedule, iterations, p50, p80, p90, p95, risk_score, distribution_stats
        )

    await publish_schedule_simulated(agent, schedule, iterations, p50, p80, p90, p95, risk_score)

    response = {
        "schedule_id": schedule_id,
        "iterations": iterations,
        "baseline_duration": schedule.get("project_duration_days", 0),
        "p50_duration": p50,
        "p80_duration": p80,
        "p90_duration": p90,
        "p95_duration": p95,
        "risk_score": risk_score,
        "risk_drivers": risk_drivers,
        "distribution": distribution_stats,
    }

    if agent.cache_client:
        cache_key = simulation_cache_key(schedule_id)
        agent.cache_client.set(cache_key, response, ttl_seconds=agent.cache_ttl_seconds)

    if agent.analytics_client:
        agent.analytics_client.record_metric(
            "schedule.monte_carlo_p80",
            float(p80),
            {"schedule_id": schedule_id},
        )
        agent.analytics_client.record_metric(
            "schedule.risk_score",
            float(risk_score),
            {"schedule_id": schedule_id},
        )

    return response


# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------


async def sample_task_durations(
    tasks: list[dict[str, Any]],
    simulation_seed: int,
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    """Sample task durations from probability distributions."""
    rng = rng or random.Random(simulation_seed)
    sampled_tasks = []
    for task in tasks:
        optimistic = task.get("optimistic_duration", task.get("duration", 0))
        most_likely = task.get("most_likely_duration", task.get("duration", 0))
        pessimistic = task.get("pessimistic_duration", task.get("duration", 0))
        duration = rng.triangular(float(optimistic), float(pessimistic), float(most_likely))
        sampled = dict(task)
        sampled["duration"] = duration
        sampled_tasks.append(sampled)
    return sampled_tasks


async def calculate_simulated_duration(
    tasks: list[dict[str, Any]], dependencies: list[dict[str, Any]]
) -> float:
    """Calculate project duration for simulated iteration."""
    forward = await forward_pass(tasks, dependencies)
    duration = max((task.get("early_finish", 0) for task in forward), default=0)
    return float(duration)


async def run_ml_simulation(
    agent: SchedulePlanningAgent,
    tasks: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    iterations: int,
    task_samples: dict[str, list[float]] | None = None,
) -> list[float]:
    rng = random.Random(agent.simulation_seed)
    results: list[float] = []
    for _ in range(iterations):
        sampled = []
        for task in tasks:
            base = float(task.get("duration", 0) or 0)
            variance = float(task.get("duration_estimate", {}).get("pessimistic", base)) - base
            variance = max(0.5, variance)
            duration = max(0.5, rng.gauss(base, variance / 2))
            sampled.append(dict(task, duration=duration))
        duration_total = await calculate_simulated_duration(sampled, dependencies)
        results.append(duration_total)
        if task_samples is not None:
            for task in sampled:
                task_id = task.get("task_id")
                if task_id in task_samples:
                    task_samples[task_id].append(float(task.get("duration", 0)))
    return results


async def calculate_percentile(data: list[float], percentile: int) -> float:
    """Calculate percentile value."""
    if not data:
        return 0
    sorted_data = sorted(data)
    index = int(len(sorted_data) * percentile / 100)
    return sorted_data[min(index, len(sorted_data) - 1)]


async def calculate_schedule_risk(
    simulation_results: list[float], baseline_duration: float
) -> float:
    """Calculate schedule risk score."""
    if not simulation_results or baseline_duration == 0:
        return 0.5

    exceeded_count = sum(1 for d in simulation_results if d > baseline_duration)
    risk_score = exceeded_count / len(simulation_results)
    return risk_score


async def calculate_std_dev(data: list[float]) -> float:
    """Calculate standard deviation."""
    if not data:
        return 0
    mean = sum(data) / len(data)
    variance = sum((x - mean) ** 2 for x in data) / len(data)
    return variance**0.5  # type: ignore


async def extract_risk_drivers(
    task_samples: dict[str, list[float]], totals: list[float]
) -> list[dict[str, Any]]:
    """Identify tasks contributing most to schedule risk."""
    if not totals:
        return []

    total_mean = sum(totals) / len(totals)
    total_variance = sum((t - total_mean) ** 2 for t in totals)
    drivers = []

    for task_id, samples in task_samples.items():
        if not samples:
            continue
        sample_mean = sum(samples) / len(samples)
        covariance = sum((s - sample_mean) * (t - total_mean) for s, t in zip(samples, totals))
        correlation = covariance / (total_variance or 1)
        spread = max(samples) - min(samples)
        drivers.append(
            {
                "task_id": task_id,
                "correlation": round(correlation, 3),
                "spread": round(spread, 2),
            }
        )

    def _driver_key(item: dict[str, Any]) -> tuple[float, float]:
        correlation = item.get("correlation")
        spread = item.get("spread")
        correlation_value = float(correlation) if correlation is not None else 0.0
        spread_value = float(spread) if spread is not None else 0.0
        return abs(correlation_value), spread_value

    drivers.sort(key=_driver_key, reverse=True)
    return drivers[:5]
