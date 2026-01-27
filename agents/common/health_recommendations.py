"""Shared concern detection and recommendation logic for health monitoring."""

from __future__ import annotations

from typing import Any


def identify_health_concerns(metrics: dict[str, float]) -> list[str]:
    """Identify health concerns from normalized metric scores."""
    concerns: list[str] = []
    if metrics.get("schedule", 1.0) < 0.70:
        concerns.append("Schedule variance exceeds acceptable threshold")
    if metrics.get("cost", 1.0) < 0.70:
        concerns.append("Cost variance indicates budget overrun risk")
    if metrics.get("risk", 1.0) < 0.70:
        concerns.append("High-priority risks not adequately mitigated")
    if metrics.get("quality", 1.0) < 0.70:
        concerns.append("Quality metrics below acceptable standards")
    if metrics.get("resource", 1.0) < 0.70:
        concerns.append("Resource constraints affecting delivery")
    return concerns


def generate_recommendations(concerns: list[str]) -> list[str]:
    """Generate actionable recommendations based on health concerns."""
    recommendations: list[str] = []
    for concern in concerns:
        if "schedule" in concern.lower():
            recommendations.append("Review critical path and consider fast-tracking or crashing")
        if "cost" in concern.lower():
            recommendations.append(
                "Conduct budget review and identify cost reduction opportunities"
            )
        if "risk" in concern.lower():
            recommendations.append("Escalate high-priority risks to steering committee")
        if "quality" in concern.lower():
            recommendations.append("Implement additional quality controls and testing")
        if "resource" in concern.lower():
            recommendations.append("Review resource allocation and consider augmentation")
    return recommendations
