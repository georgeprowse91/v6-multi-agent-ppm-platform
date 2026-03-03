"""Action handler: verify_post_deployment."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from release_utils import (
    check_application_health,
    fetch_baseline_metrics,
    fetch_monitoring_metrics,
)

if TYPE_CHECKING:
    from release_models import ReleaseAgentProtocol


async def verify_post_deployment(
    agent: ReleaseAgentProtocol,
    deployment_plan_id: str,
    verification_params: dict[str, Any],
) -> dict[str, Any]:
    """
    Verify application health post-deployment.

    Returns verification results.
    """
    agent.logger.info("Verifying post-deployment for: %s", deployment_plan_id)

    deployment_plan = agent.deployment_plans.get(deployment_plan_id)
    if not deployment_plan:
        raise ValueError(f"Deployment plan not found: {deployment_plan_id}")

    health_check = await check_application_health(agent, deployment_plan)

    metrics_comparison = await _compare_metrics_to_baseline(agent, deployment_plan)
    anomalies = await _detect_post_deployment_anomalies(agent, deployment_plan)

    verification_passed = (
        health_check.get("healthy", False)
        and metrics_comparison.get("acceptable", False)
        and len(anomalies) == 0
    )

    return {
        "deployment_plan_id": deployment_plan_id,
        "verification_passed": verification_passed,
        "health_check": health_check,
        "metrics_comparison": metrics_comparison,
        "anomalies": anomalies,
        "recommendations": (
            "Deployment successful" if verification_passed else "Investigate anomalies"
        ),
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _compare_metrics_to_baseline(
    agent: ReleaseAgentProtocol, deployment_plan: dict[str, Any]
) -> dict[str, Any]:
    """Compare metrics to baseline."""
    metrics = await fetch_monitoring_metrics(agent, deployment_plan)
    baseline = await fetch_baseline_metrics(agent, deployment_plan)
    if not baseline:
        return {"acceptable": True, "variance": 0.0, "metrics": metrics}
    variance = {}
    acceptable = True
    for metric, value in metrics.items():
        base = baseline.get(metric, {})
        baseline_value = base.get("mean", base.get("value"))
        if baseline_value is None:
            continue
        diff = value - baseline_value
        variance[metric] = diff
        if abs(diff) > base.get("threshold", baseline_value * 0.2):
            acceptable = False
    return {"acceptable": acceptable, "variance": variance, "metrics": metrics}


async def _detect_post_deployment_anomalies(
    agent: ReleaseAgentProtocol, deployment_plan: dict[str, Any]
) -> list[dict[str, Any]]:
    """Detect post-deployment anomalies."""
    metrics = await fetch_monitoring_metrics(agent, deployment_plan)
    baseline = await fetch_baseline_metrics(agent, deployment_plan)
    anomalies = []
    for metric, value in metrics.items():
        base = baseline.get(metric, {}) if baseline else {}
        mean = base.get("mean", base.get("value"))
        std = base.get("std", 0.0)
        threshold = base.get("threshold")
        if mean is None:
            continue
        if threshold is None:
            threshold = mean + (2 * std)
        if value > threshold:
            anomalies.append(
                {
                    "metric": metric,
                    "value": value,
                    "baseline_mean": mean,
                    "threshold": threshold,
                    "severity": "high" if value > threshold * 1.2 else "medium",
                }
            )
    if metrics.get("error_rate", 0) > 0.02:
        anomalies.append(
            {
                "metric": "error_rate",
                "value": metrics.get("error_rate"),
                "threshold": 0.02,
                "severity": "high",
            }
        )
    return anomalies
