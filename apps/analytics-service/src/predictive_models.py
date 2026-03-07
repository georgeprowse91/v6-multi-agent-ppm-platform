"""Pydantic models for predictive analytics."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SimulationResult(BaseModel):
    """Monte Carlo simulation output."""

    project_id: str
    iterations: int
    p10_completion_days: float
    p50_completion_days: float
    p90_completion_days: float
    p10_cost: float
    p50_cost: float
    p90_cost: float
    on_time_probability: float
    on_budget_probability: float
    distribution: list[dict[str, float]] = Field(default_factory=list)


class ForecastResult(BaseModel):
    """Trend forecast output."""

    metric_name: str
    periods: int
    forecast_values: list[float]
    confidence_lower: list[float]
    confidence_upper: list[float]


class HealthPrediction(BaseModel):
    """Project health prediction."""

    project_id: str
    project_name: str
    current_health_score: float
    predicted_health_30d: float
    predicted_health_60d: float
    predicted_health_90d: float
    risk_signal: float
    schedule_signal: float
    budget_signal: float
    resource_signal: float
    trend: str  # improving, stable, declining


class BottleneckPrediction(BaseModel):
    """Resource bottleneck prediction."""

    resource_type: str
    skill_area: str
    bottleneck_start_date: str
    bottleneck_end_date: str
    severity: str  # low, medium, high, critical
    affected_projects: list[str]
    demand_capacity_ratio: float


class RiskHeatmapCell(BaseModel):
    """Single cell in a risk heatmap."""

    project_id: str
    project_name: str
    risk_category: str
    risk_score: float
    trend: str  # up, stable, down


class HealthScoreBreakdown(BaseModel):
    """Detailed breakdown of a health score by signal dimension."""

    risk_score: float = Field(ge=0.0, le=1.0)
    risk_weight: float = 0.3
    schedule_score: float = Field(ge=0.0, le=1.0)
    schedule_weight: float = 0.25
    budget_score: float = Field(ge=0.0, le=1.0)
    budget_weight: float = 0.25
    resource_score: float = Field(ge=0.0, le=1.0)
    resource_weight: float = 0.2
    composite_score: float = Field(ge=0.0, le=1.0)
    contributing_factors: list[str] = Field(default_factory=list)


class HealthAlert(BaseModel):
    """Threshold-based health alert raised when a score crosses a boundary."""

    alert_id: str
    project_id: str
    project_name: str
    previous_score: float
    current_score: float
    threshold: float
    severity: str  # critical, warning, info
    trigger: str  # crossed_below, rapid_decline, sustained_decline
    signals: HealthScoreBreakdown
    message: str
    recommended_actions: list[str] = Field(default_factory=list)
    detected_at: str


class HealthTrendAnalysis(BaseModel):
    """Trend analysis over a series of health snapshots."""

    project_id: str
    project_name: str
    current_score: float
    score_7d_ago: float | None = None
    score_30d_ago: float | None = None
    trend_direction: str  # improving, stable, declining, rapidly_declining
    trend_slope: float
    volatility: float
    predicted_score_30d: float
    predicted_score_60d: float
    predicted_score_90d: float
    confidence: float
    at_risk: bool
    risk_factors: list[str] = Field(default_factory=list)


class ScenarioComparison(BaseModel):
    """Side-by-side scenario comparison."""

    scenario_id: str
    scenario_name: str
    total_cost: float
    total_duration_days: float
    risk_score: float
    resource_utilization: float
    npv: float
    roi_percentage: float
