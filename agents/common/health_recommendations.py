"""Shared concern detection and recommendation logic for health monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HealthThreshold:
    """Configurable threshold for a health metric dimension."""

    warning: float = 0.70
    critical: float = 0.50


DEFAULT_THRESHOLDS: dict[str, HealthThreshold] = {
    "schedule": HealthThreshold(warning=0.70, critical=0.50),
    "cost": HealthThreshold(warning=0.70, critical=0.50),
    "risk": HealthThreshold(warning=0.70, critical=0.50),
    "quality": HealthThreshold(warning=0.70, critical=0.50),
    "resource": HealthThreshold(warning=0.70, critical=0.50),
}

_CONCERN_LABELS: dict[str, str] = {
    "schedule": "Schedule variance exceeds acceptable threshold",
    "cost": "Cost variance indicates budget overrun risk",
    "risk": "High-priority risks not adequately mitigated",
    "quality": "Quality metrics below acceptable standards",
    "resource": "Resource constraints affecting delivery",
}

_RECOMMENDATION_MAP: dict[str, str] = {
    "schedule": "Review critical path and consider fast-tracking or crashing",
    "cost": "Conduct budget review and identify cost reduction opportunities",
    "risk": "Escalate high-priority risks to steering committee",
    "quality": "Implement additional quality controls and testing",
    "resource": "Review resource allocation and consider augmentation",
}

_CRITICAL_RECOMMENDATION_MAP: dict[str, str] = {
    "schedule": "Initiate schedule recovery plan; engage steering committee for scope trade-offs",
    "cost": "Freeze discretionary spend and escalate budget overrun to finance leadership",
    "risk": "Activate risk response plans for all critical-severity risks immediately",
    "quality": "Halt further development until quality baseline is restored",
    "resource": "Request emergency resource augmentation from portfolio office",
}


@dataclass(frozen=True)
class HealthConcern:
    """A detected health concern with severity context."""

    dimension: str
    score: float
    severity: str  # "warning" or "critical"
    description: str


def identify_health_concerns(
    metrics: dict[str, float],
    thresholds: dict[str, HealthThreshold] | None = None,
) -> list[str]:
    """Identify health concerns from normalized metric scores.

    This function preserves the original return type (list of description
    strings) for backwards compatibility.  Use :func:`identify_health_concerns_detailed`
    for richer output.
    """
    return [concern.description for concern in identify_health_concerns_detailed(metrics, thresholds)]


def identify_health_concerns_detailed(
    metrics: dict[str, float],
    thresholds: dict[str, HealthThreshold] | None = None,
) -> list[HealthConcern]:
    """Identify health concerns with severity classification."""
    effective_thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    concerns: list[HealthConcern] = []

    for dimension, threshold in effective_thresholds.items():
        score = metrics.get(dimension, 1.0)
        if score < threshold.critical:
            concerns.append(
                HealthConcern(
                    dimension=dimension,
                    score=score,
                    severity="critical",
                    description=f"CRITICAL: {_CONCERN_LABELS.get(dimension, f'{dimension} below critical threshold')}",
                )
            )
        elif score < threshold.warning:
            concerns.append(
                HealthConcern(
                    dimension=dimension,
                    score=score,
                    severity="warning",
                    description=_CONCERN_LABELS.get(dimension, f"{dimension} below warning threshold"),
                )
            )

    # Sort critical first, then by score ascending
    concerns.sort(key=lambda c: (0 if c.severity == "critical" else 1, c.score))
    return concerns


def generate_recommendations(concerns: list[str]) -> list[str]:
    """Generate actionable recommendations based on health concerns."""
    recommendations: list[str] = []
    for concern in concerns:
        concern_lower = concern.lower()
        for dimension, recommendation in _RECOMMENDATION_MAP.items():
            if dimension in concern_lower:
                if concern_lower.startswith("critical"):
                    recommendations.append(
                        _CRITICAL_RECOMMENDATION_MAP.get(dimension, recommendation)
                    )
                else:
                    recommendations.append(recommendation)
    return recommendations


def generate_recommendations_detailed(concerns: list[HealthConcern]) -> list[dict[str, Any]]:
    """Generate structured recommendations from detailed health concerns."""
    results: list[dict[str, Any]] = []
    for concern in concerns:
        if concern.severity == "critical":
            rec = _CRITICAL_RECOMMENDATION_MAP.get(
                concern.dimension, _RECOMMENDATION_MAP.get(concern.dimension, "")
            )
        else:
            rec = _RECOMMENDATION_MAP.get(concern.dimension, "")
        if rec:
            results.append(
                {
                    "dimension": concern.dimension,
                    "severity": concern.severity,
                    "score": concern.score,
                    "recommendation": rec,
                }
            )
    return results
