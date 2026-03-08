"""Tests for predictive analytics engine (Enhancement 2)."""

from __future__ import annotations

from predictive import (
    HealthPredictor,
    MonteCarloSimulator,
    ResourceBottleneckDetector,
    TrendForecaster,
)


def test_monte_carlo_basic():
    simulator = MonteCarloSimulator()
    result = simulator.simulate(
        {"project_id": "test", "estimated_duration_days": 100, "estimated_cost": 200000},
        iterations=500,
    )
    assert result.project_id == "test"
    assert result.iterations == 500
    assert result.p10_completion_days < result.p50_completion_days < result.p90_completion_days
    assert 0 <= result.on_time_probability <= 1
    assert 0 <= result.on_budget_probability <= 1


def test_trend_forecaster():
    forecaster = TrendForecaster()
    result = forecaster.forecast([10, 20, 30, 40, 50], periods=3)
    assert result.periods == 3
    assert len(result.forecast_values) == 3
    assert len(result.confidence_lower) == 3
    assert len(result.confidence_upper) == 3
    # Trend is upward, so forecasts should be >50
    assert all(v > 50 for v in result.forecast_values)


def test_trend_forecaster_single_point():
    forecaster = TrendForecaster()
    result = forecaster.forecast([42], periods=2)
    assert len(result.forecast_values) == 2


def test_health_predictor():
    predictor = HealthPredictor()
    result = predictor.predict_health(
        "proj-1",
        "Test Project",
        {"risk": 0.3, "schedule": 0.8, "budget": 0.7, "resource": 0.6, "trend_decay": 0.01},
    )
    assert result.project_id == "proj-1"
    assert 0 <= result.current_health_score <= 1
    assert result.trend == "stable"


def test_health_predictor_declining():
    predictor = HealthPredictor()
    result = predictor.predict_health(
        "proj-2",
        "Declining",
        {"risk": 0.8, "schedule": 0.3, "budget": 0.3, "resource": 0.2, "trend_decay": 0.05},
    )
    assert result.trend == "declining"
    assert result.predicted_health_90d <= result.current_health_score


def test_bottleneck_detector():
    detector = ResourceBottleneckDetector()
    allocs = [
        {"skill_area": "Python", "demand": 15, "capacity": 10},
        {"skill_area": "Go", "demand": 3, "capacity": 10},
    ]
    bottlenecks = detector.detect(allocs)
    assert len(bottlenecks) == 1
    assert bottlenecks[0].skill_area == "Python"
    assert bottlenecks[0].demand_capacity_ratio > 1.0


def test_bottleneck_detector_no_bottleneck():
    detector = ResourceBottleneckDetector()
    allocs = [{"skill_area": "Rust", "demand": 2, "capacity": 10}]
    assert detector.detect(allocs) == []


# --- Error path and edge case tests ---


def test_monte_carlo_high_iterations():
    """Higher iterations should still produce valid percentile ordering."""
    simulator = MonteCarloSimulator()
    result = simulator.simulate(
        {"project_id": "stress", "estimated_duration_days": 200, "estimated_cost": 500000},
        iterations=5000,
    )
    assert result.p10_completion_days < result.p90_completion_days
    assert result.p10_cost < result.p90_cost


def test_monte_carlo_minimal_data():
    """Simulation should handle minimal project data without crashing."""
    simulator = MonteCarloSimulator()
    result = simulator.simulate({"project_id": "minimal"}, iterations=100)
    assert result.project_id == "minimal"
    assert result.iterations == 100


def test_monte_carlo_probabilities_bounded():
    """Probabilities must always be in [0, 1]."""
    simulator = MonteCarloSimulator()
    for cost in [1000, 100000, 10000000]:
        result = simulator.simulate(
            {"project_id": f"p-{cost}", "estimated_duration_days": 30, "estimated_cost": cost},
            iterations=200,
        )
        assert 0.0 <= result.on_time_probability <= 1.0
        assert 0.0 <= result.on_budget_probability <= 1.0


def test_trend_forecaster_constant_series():
    """A constant series should forecast approximately the same value."""
    forecaster = TrendForecaster()
    result = forecaster.forecast([50, 50, 50, 50], periods=3)
    assert len(result.forecast_values) == 3
    for v in result.forecast_values:
        assert abs(v - 50) < 20


def test_trend_forecaster_downward():
    """A downward trend should forecast decreasing values."""
    forecaster = TrendForecaster()
    result = forecaster.forecast([100, 80, 60, 40, 20], periods=3)
    assert result.forecast_values[0] < 20


def test_trend_forecaster_confidence_ordering():
    """Lower bounds should be less than upper bounds."""
    forecaster = TrendForecaster()
    result = forecaster.forecast([10, 20, 30, 40, 50], periods=3)
    for lo, hi in zip(result.confidence_lower, result.confidence_upper):
        assert lo <= hi


def test_health_predictor_all_healthy():
    """Project with strong signals should have high health score."""
    predictor = HealthPredictor()
    result = predictor.predict_health(
        "healthy-proj",
        "Healthy",
        {"risk": 0.1, "schedule": 0.9, "budget": 0.9, "resource": 0.9, "trend_decay": -0.01},
    )
    assert result.current_health_score > 0.5
    assert result.trend in ("stable", "improving")


def test_health_predictor_predicted_90d_bounded():
    """90-day prediction should always be in [0, 1]."""
    predictor = HealthPredictor()
    for decay in [-0.05, 0.0, 0.05, 0.1]:
        result = predictor.predict_health(
            "bound-test",
            "Test",
            {"risk": 0.5, "schedule": 0.5, "budget": 0.5, "resource": 0.5, "trend_decay": decay},
        )
        assert 0.0 <= result.predicted_health_90d <= 1.0


def test_bottleneck_detector_exact_capacity():
    """Demand exactly matching capacity should not be a bottleneck."""
    detector = ResourceBottleneckDetector()
    allocs = [{"skill_area": "Java", "demand": 10, "capacity": 10}]
    bottlenecks = detector.detect(allocs)
    assert all(b.skill_area != "Java" or b.demand_capacity_ratio <= 1.0 for b in bottlenecks)


def test_bottleneck_detector_multiple():
    """Multiple skills can be bottlenecked simultaneously."""
    detector = ResourceBottleneckDetector()
    allocs = [
        {"skill_area": "Python", "demand": 20, "capacity": 10},
        {"skill_area": "React", "demand": 15, "capacity": 8},
        {"skill_area": "Go", "demand": 2, "capacity": 10},
    ]
    bottlenecks = detector.detect(allocs)
    bottleneck_skills = {b.skill_area for b in bottlenecks}
    assert "Python" in bottleneck_skills
    assert "React" in bottleneck_skills
    assert "Go" not in bottleneck_skills


def test_bottleneck_detector_empty_input():
    """Empty allocations should return empty list."""
    detector = ResourceBottleneckDetector()
    assert detector.detect([]) == []
