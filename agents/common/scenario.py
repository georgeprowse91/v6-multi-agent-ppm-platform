"""Shared scenario simulation engine for what-if and Monte Carlo analysis."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Iterable

Sampler = Callable[[int], Awaitable[float] | float]
ScenarioBuilder = Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]] | dict[str, Any]]
MetricsBuilder = Callable[[dict[str, Any]], Awaitable[dict[str, Any]] | dict[str, Any]]
ComparisonBuilder = Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]] | dict[str, Any]]
RecommendationBuilder = Callable[[dict[str, Any]], Awaitable[str] | str]


@dataclass
class MonteCarloResult:
    iterations: int
    results: list[float]
    percentiles: dict[int, float]
    statistics: dict[str, float]


class ScenarioEngine:
    """Utility class for scenario simulations shared across agents."""

    async def run_monte_carlo(
        self,
        *,
        iterations: int,
        sampler: Sampler,
        percentiles: Iterable[int] = (50, 80, 90, 95),
    ) -> MonteCarloResult:
        """Run a Monte Carlo simulation using the provided sampler."""
        results: list[float] = []
        for index in range(iterations):
            value = sampler(index)
            if asyncio.iscoroutine(value):
                value = await value
            results.append(float(value))

        percentile_values = {
            percentile: self._calculate_percentile(results, percentile)
            for percentile in percentiles
        }
        statistics = {
            "min": min(results) if results else 0.0,
            "max": max(results) if results else 0.0,
            "mean": sum(results) / len(results) if results else 0.0,
            "std_dev": self._calculate_std_dev(results),
        }
        return MonteCarloResult(
            iterations=iterations,
            results=results,
            percentiles=percentile_values,
            statistics=statistics,
        )

    async def run_scenario(
        self,
        *,
        baseline: dict[str, Any],
        scenario_params: dict[str, Any],
        scenario_builder: ScenarioBuilder,
        metrics_builder: MetricsBuilder,
        comparison_builder: ComparisonBuilder,
        recommendation_builder: RecommendationBuilder | None = None,
    ) -> dict[str, Any]:
        """Run a scenario comparison from baseline data."""
        scenario = scenario_builder(baseline, scenario_params)
        if asyncio.iscoroutine(scenario):
            scenario = await scenario

        baseline_metrics = metrics_builder(baseline)
        if asyncio.iscoroutine(baseline_metrics):
            baseline_metrics = await baseline_metrics

        scenario_metrics = metrics_builder(scenario)
        if asyncio.iscoroutine(scenario_metrics):
            scenario_metrics = await scenario_metrics

        comparison = comparison_builder(baseline_metrics, scenario_metrics)
        if asyncio.iscoroutine(comparison):
            comparison = await comparison

        recommendation = None
        if recommendation_builder:
            recommendation = recommendation_builder(comparison)
            if asyncio.iscoroutine(recommendation):
                recommendation = await recommendation

        return {
            "baseline": baseline,
            "scenario": scenario,
            "baseline_metrics": baseline_metrics,
            "scenario_metrics": scenario_metrics,
            "comparison": comparison,
            "recommendation": recommendation,
        }

    async def run_metric_scenario(
        self,
        *,
        baseline_metrics: dict[str, Any],
        scenario_params: dict[str, Any],
        scenario_metrics_builder: ScenarioBuilder,
        comparison_builder: ComparisonBuilder,
        recommendation_builder: RecommendationBuilder | None = None,
    ) -> dict[str, Any]:
        """Run a scenario analysis where metrics are derived from baseline metrics."""
        scenario_metrics = scenario_metrics_builder(baseline_metrics, scenario_params)
        if asyncio.iscoroutine(scenario_metrics):
            scenario_metrics = await scenario_metrics

        comparison = comparison_builder(baseline_metrics, scenario_metrics)
        if asyncio.iscoroutine(comparison):
            comparison = await comparison

        recommendation = None
        if recommendation_builder:
            recommendation = recommendation_builder(comparison)
            if asyncio.iscoroutine(recommendation):
                recommendation = await recommendation

        return {
            "baseline_metrics": baseline_metrics,
            "scenario_metrics": scenario_metrics,
            "comparison": comparison,
            "recommendation": recommendation,
        }

    async def run_multi_scenarios(
        self,
        *,
        scenarios: list[dict[str, Any]],
        scenario_runner: Callable[[dict[str, Any]], Awaitable[dict[str, Any]] | dict[str, Any]],
        comparison_builder: Callable[[list[dict[str, Any]]], Awaitable[dict[str, Any]] | dict[str, Any]],
    ) -> dict[str, Any]:
        """Run a batch of scenarios and compare the outcomes."""
        results: list[dict[str, Any]] = []
        for scenario in scenarios:
            result = scenario_runner(scenario)
            if asyncio.iscoroutine(result):
                result = await result
            results.append(result)

        comparison = comparison_builder(results)
        if asyncio.iscoroutine(comparison):
            comparison = await comparison

        return {"scenarios": results, "comparison": comparison}

    def _calculate_percentile(self, data: list[float], percentile: int) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (percentile / 100)
        f = int(k)
        c = min(f + 1, len(sorted_data) - 1)
        if f == c:
            return float(sorted_data[int(k)])
        d0 = sorted_data[f] * (c - k)
        d1 = sorted_data[c] * (k - f)
        return float(d0 + d1)

    def _calculate_std_dev(self, data: list[float]) -> float:
        if not data:
            return 0.0
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return variance**0.5
