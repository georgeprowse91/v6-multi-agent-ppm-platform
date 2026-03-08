"""Predictive analytics engine — Monte Carlo, health forecasting, bottleneck detection."""

from __future__ import annotations

import math
import random
from typing import Any

from predictive_models import (
    BottleneckPrediction,
    ForecastResult,
    HealthPrediction,
    HealthTrendAnalysis,
    RiskHeatmapCell,
    SimulationResult,
)


class MonteCarloSimulator:
    """Run Monte Carlo simulations on project schedule/cost distributions."""

    def simulate(
        self,
        project_data: dict[str, Any],
        iterations: int = 1000,
    ) -> SimulationResult:
        base_duration = float(project_data.get("estimated_duration_days", 90))
        base_cost = float(project_data.get("estimated_cost", 100000))
        duration_std = base_duration * 0.2
        cost_std = base_cost * 0.15

        durations = sorted(
            random.gauss(base_duration, duration_std) for _ in range(iterations)
        )
        costs = sorted(random.gauss(base_cost, cost_std) for _ in range(iterations))

        target_duration = float(project_data.get("target_duration_days", base_duration))
        target_cost = float(project_data.get("target_cost", base_cost))
        on_time = sum(1 for d in durations if d <= target_duration) / iterations
        on_budget = sum(1 for c in costs if c <= target_cost) / iterations

        return SimulationResult(
            project_id=project_data.get("project_id", "unknown"),
            iterations=iterations,
            p10_completion_days=durations[int(iterations * 0.1)],
            p50_completion_days=durations[int(iterations * 0.5)],
            p90_completion_days=durations[int(iterations * 0.9)],
            p10_cost=costs[int(iterations * 0.1)],
            p50_cost=costs[int(iterations * 0.5)],
            p90_cost=costs[int(iterations * 0.9)],
            on_time_probability=round(on_time, 3),
            on_budget_probability=round(on_budget, 3),
        )


class TrendForecaster:
    """Simple linear regression + exponential smoothing forecaster."""

    def forecast(
        self,
        timeseries: list[float],
        periods: int = 6,
    ) -> ForecastResult:
        n = len(timeseries)
        if n < 2:
            return ForecastResult(
                metric_name="metric",
                periods=periods,
                forecast_values=timeseries * periods,
                confidence_lower=timeseries * periods,
                confidence_upper=timeseries * periods,
            )

        x_mean = (n - 1) / 2
        y_mean = sum(timeseries) / n
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(timeseries))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator else 0
        intercept = y_mean - slope * x_mean

        residuals = [y - (slope * i + intercept) for i, y in enumerate(timeseries)]
        std_err = math.sqrt(sum(r**2 for r in residuals) / max(n - 2, 1))

        forecast_values = [slope * (n + i) + intercept for i in range(periods)]
        confidence_lower = [v - 1.96 * std_err for v in forecast_values]
        confidence_upper = [v + 1.96 * std_err for v in forecast_values]

        return ForecastResult(
            metric_name="metric",
            periods=periods,
            forecast_values=[round(v, 2) for v in forecast_values],
            confidence_lower=[round(v, 2) for v in confidence_lower],
            confidence_upper=[round(v, 2) for v in confidence_upper],
        )


class HealthPredictor:
    """Predict project health from multi-signal inputs."""

    WEIGHTS = {"risk": 0.3, "schedule": 0.25, "budget": 0.25, "resource": 0.2}

    def predict_health(
        self,
        project_id: str,
        project_name: str,
        signals: dict[str, float],
    ) -> HealthPrediction:
        risk = signals.get("risk", 0.5)
        schedule = signals.get("schedule", 0.5)
        budget = signals.get("budget", 0.5)
        resource = signals.get("resource", 0.5)

        current = (
            self.WEIGHTS["risk"] * (1 - risk)
            + self.WEIGHTS["schedule"] * schedule
            + self.WEIGHTS["budget"] * budget
            + self.WEIGHTS["resource"] * resource
        )

        decay_30d = signals.get("trend_decay", 0.02)
        pred_30 = max(0, min(1, current - decay_30d))
        pred_60 = max(0, min(1, current - decay_30d * 2))
        pred_90 = max(0, min(1, current - decay_30d * 3))

        if decay_30d > 0.03:
            trend = "declining"
        elif decay_30d < -0.01:
            trend = "improving"
        else:
            trend = "stable"

        return HealthPrediction(
            project_id=project_id,
            project_name=project_name,
            current_health_score=round(current, 3),
            predicted_health_30d=round(pred_30, 3),
            predicted_health_60d=round(pred_60, 3),
            predicted_health_90d=round(pred_90, 3),
            risk_signal=risk,
            schedule_signal=schedule,
            budget_signal=budget,
            resource_signal=resource,
            trend=trend,
        )

    def analyze_trend(
        self,
        project_id: str,
        project_name: str,
        history: list[dict[str, Any]],
        signals: dict[str, float] | None = None,
    ) -> HealthTrendAnalysis:
        """Analyze health trend from historical snapshots.

        Uses linear regression on historical scores to determine trend slope,
        volatility, and predicted future scores with confidence levels.
        """
        scores = [entry.get("composite_score", 0.5) for entry in history]
        n = len(scores)
        current_score = scores[-1] if scores else 0.5

        # Compute trend slope via least squares
        if n >= 2:
            x_mean = (n - 1) / 2.0
            y_mean = sum(scores) / n
            numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(scores))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            slope = numerator / denominator if denominator else 0.0
        else:
            slope = 0.0

        # Compute volatility
        if n >= 3:
            deltas = [scores[i] - scores[i - 1] for i in range(1, n)]
            mean_delta = sum(deltas) / len(deltas)
            variance = sum((d - mean_delta) ** 2 for d in deltas) / len(deltas)
            volatility = math.sqrt(variance)
        else:
            volatility = 0.0

        # Determine trend direction
        if slope > 0.02:
            trend_direction = "improving"
        elif slope < -0.05:
            trend_direction = "rapidly_declining"
        elif slope < -0.01:
            trend_direction = "declining"
        else:
            trend_direction = "stable"

        # Predict future scores
        decay = slope * -1
        pred_30 = max(0.0, min(1.0, current_score - decay))
        pred_60 = max(0.0, min(1.0, current_score - decay * 1.8))
        pred_90 = max(0.0, min(1.0, current_score - decay * 2.5))

        # Confidence based on history length and volatility
        confidence = min(0.95, max(0.3, 0.5 + n * 0.05 - volatility * 2))

        # Historical lookback
        score_7d = scores[-7] if n >= 7 else None
        score_30d = scores[-30] if n >= 30 else None

        # Risk factors
        risk_factors: list[str] = []
        if current_score < 0.4:
            risk_factors.append("Health score in critical range")
        elif current_score < 0.6:
            risk_factors.append("Health score below warning threshold")
        if trend_direction in ("declining", "rapidly_declining"):
            risk_factors.append(f"Trend is {trend_direction.replace('_', ' ')}")
        if volatility > 0.05:
            risk_factors.append("High score volatility detected")
        if signals:
            if signals.get("risk", 0) > 0.7:
                risk_factors.append("Elevated risk signal")
            if signals.get("schedule", 1) < 0.4:
                risk_factors.append("Schedule health critically low")
            if signals.get("budget", 1) < 0.4:
                risk_factors.append("Budget health critically low")

        at_risk = current_score < 0.6 or trend_direction in ("declining", "rapidly_declining")

        return HealthTrendAnalysis(
            project_id=project_id,
            project_name=project_name,
            current_score=round(current_score, 4),
            score_7d_ago=round(score_7d, 4) if score_7d is not None else None,
            score_30d_ago=round(score_30d, 4) if score_30d is not None else None,
            trend_direction=trend_direction,
            trend_slope=round(slope, 4),
            volatility=round(volatility, 4),
            predicted_score_30d=round(pred_30, 4),
            predicted_score_60d=round(pred_60, 4),
            predicted_score_90d=round(pred_90, 4),
            confidence=round(confidence, 3),
            at_risk=at_risk,
            risk_factors=risk_factors,
        )


class ResourceBottleneckDetector:
    """Detect future resource capacity crunches."""

    def detect(
        self,
        allocations: list[dict[str, Any]],
        horizon_days: int = 90,
    ) -> list[BottleneckPrediction]:
        bottlenecks: list[BottleneckPrediction] = []
        skill_demand: dict[str, float] = {}
        skill_capacity: dict[str, float] = {}

        for alloc in allocations:
            skill = alloc.get("skill_area", "general")
            demand = float(alloc.get("demand", 0))
            capacity = float(alloc.get("capacity", 1))
            skill_demand[skill] = skill_demand.get(skill, 0) + demand
            skill_capacity[skill] = skill_capacity.get(skill, 0) + capacity

        for skill, demand in skill_demand.items():
            capacity = skill_capacity.get(skill, 1)
            ratio = demand / capacity if capacity > 0 else 10.0
            if ratio > 0.85:
                severity = (
                    "critical" if ratio > 1.2 else "high" if ratio > 1.0 else "medium"
                )
                bottlenecks.append(
                    BottleneckPrediction(
                        resource_type="skill",
                        skill_area=skill,
                        bottleneck_start_date="2026-04-01",
                        bottleneck_end_date="2026-06-30",
                        severity=severity,
                        affected_projects=[],
                        demand_capacity_ratio=round(ratio, 2),
                    )
                )

        return bottlenecks
