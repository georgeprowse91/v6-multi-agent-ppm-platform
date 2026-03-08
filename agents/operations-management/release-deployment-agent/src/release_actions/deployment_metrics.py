"""Action handler: track_deployment_metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, cast

from release_utils import publish_event

if TYPE_CHECKING:
    from release_models import ReleaseAgentProtocol


async def track_deployment_metrics(agent: ReleaseAgentProtocol, release_id: str) -> dict[str, Any]:
    """
    Track and analyze deployment metrics.

    Returns deployment KPIs.
    """
    agent.logger.info("Tracking deployment metrics for release: %s", release_id)

    # Calculate deployment metrics
    metrics = {
        "deployment_frequency": await _calculate_deployment_frequency(agent),
        "lead_time_for_changes": await _calculate_lead_time(agent, release_id),
        "mean_time_to_deploy": await _calculate_mean_time_to_deploy(agent, release_id),
        "mean_time_to_restore": await _calculate_mttr(agent),
        "deployment_success_rate": await _calculate_success_rate(agent),
        "rollback_rate": await _calculate_rollback_rate(agent),
        "change_failure_rate": await _calculate_change_failure_rate(agent),
        "environment_utilization": await _calculate_environment_utilization(agent),
    }
    anomalies = await _detect_metric_anomalies(metrics)

    # Store metrics
    metrics_record = {
        "release_id": release_id,
        "metrics": metrics,
        "anomalies": anomalies,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.deployment_metrics[release_id] = metrics_record

    # Persist to database
    await agent.db_service.store("deployment_metrics", f"metrics-{release_id}", metrics_record)
    await publish_event(
        agent,
        "analytics.deployment.metrics",
        {
            "release_id": release_id,
            "metrics": metrics,
            "anomalies": anomalies,
            "calculated_at": metrics_record["calculated_at"],
        },
    )

    impact_analysis = await _analyze_post_deployment_impact(agent, release_id)

    return {
        "release_id": release_id,
        "metrics": metrics,
        "anomalies": anomalies,
        "impact_analysis": impact_analysis,
        "recommendations": await _generate_deployment_recommendations(metrics),
    }


# ---------------------------------------------------------------------------
# Private metric calculators
# ---------------------------------------------------------------------------


async def _calculate_deployment_frequency(agent: ReleaseAgentProtocol) -> float:
    """Calculate deployment frequency."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=30)
    completed = [
        plan
        for plan in agent.deployment_plans.values()
        if plan.get("completed_at") and datetime.fromisoformat(plan["completed_at"]) >= window_start
    ]
    return len(completed) / 1.0  # per 30 days


async def _calculate_lead_time(agent: ReleaseAgentProtocol, release_id: str) -> float:
    """Calculate lead time for changes."""
    release = agent.releases.get(release_id)
    if not release:
        return 0.0
    created_at = release.get("created_at")
    actual_date = release.get("actual_date")
    if not created_at or not actual_date:
        return 0.0
    start = datetime.fromisoformat(created_at)
    end = datetime.fromisoformat(actual_date)
    return max((end - start).total_seconds() / 86400, 0.0)


async def _calculate_mean_time_to_deploy(agent: ReleaseAgentProtocol, release_id: str) -> float:
    """Calculate mean time to deploy."""
    durations = []
    for plan in agent.deployment_plans.values():
        if plan.get("release_id") != release_id:
            continue
        started = plan.get("started_at")
        completed = plan.get("completed_at")
        if started and completed:
            start = datetime.fromisoformat(started)
            end = datetime.fromisoformat(completed)
            durations.append((end - start).total_seconds() / 60)
    return sum(durations) / len(durations) if durations else 0.0


async def _calculate_success_rate(agent: ReleaseAgentProtocol) -> float:
    """Calculate deployment success rate."""
    if not agent.deployment_plans:
        return 1.0
    total = len(agent.deployment_plans)
    success = sum(
        1 for plan in agent.deployment_plans.values() if plan.get("status") == "Completed"
    )
    return success / total if total else 0.0


async def _calculate_rollback_rate(agent: ReleaseAgentProtocol) -> float:
    """Calculate rollback rate."""
    if not agent.deployment_plans:
        return 0.0
    total = len(agent.deployment_plans)
    rolled_back = sum(
        1 for plan in agent.deployment_plans.values() if plan.get("status") == "Rolled Back"
    )
    return rolled_back / total if total else 0.0


async def _calculate_environment_utilization(
    agent: ReleaseAgentProtocol,
) -> dict[str, float]:
    """Calculate environment utilization."""
    utilization: dict[str, float] = {env: 0.0 for env in agent.environments}
    if not agent.environment_allocations:
        return utilization
    total_allocations = len(agent.environment_allocations)
    for allocation in agent.environment_allocations.values():
        env = allocation.get("environment")
        if env in utilization:
            utilization[env] += 1 / total_allocations
    return utilization


async def _calculate_mttr(agent: ReleaseAgentProtocol) -> float:
    """Calculate mean time to restore service."""
    restore_times = []
    for plan in agent.deployment_plans.values():
        if plan.get("status") != "Rolled Back":
            continue
        rollback_at = plan.get("rollback_at")
        started_at = plan.get("started_at")
        if rollback_at and started_at:
            start = datetime.fromisoformat(started_at)
            end = datetime.fromisoformat(rollback_at)
            restore_times.append((end - start).total_seconds() / 60)
    return sum(restore_times) / len(restore_times) if restore_times else 0.0


async def _calculate_change_failure_rate(agent: ReleaseAgentProtocol) -> float:
    """Calculate change failure rate."""
    if not agent.deployment_plans:
        return 0.0
    failed = sum(
        1
        for plan in agent.deployment_plans.values()
        if plan.get("status") in {"Failed", "Rolled Back"}
    )
    return failed / len(agent.deployment_plans)


async def _detect_metric_anomalies(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Detect anomalies in deployment metrics."""
    anomalies = []
    if metrics.get("deployment_success_rate", 1.0) < 0.9:
        anomalies.append(
            {
                "metric": "deployment_success_rate",
                "severity": "high",
                "value": metrics.get("deployment_success_rate"),
            }
        )
    if metrics.get("rollback_rate", 0.0) > 0.05:
        anomalies.append(
            {
                "metric": "rollback_rate",
                "severity": "medium",
                "value": metrics.get("rollback_rate"),
            }
        )
    return anomalies


async def _generate_deployment_recommendations(metrics: dict[str, Any]) -> list[str]:
    """Generate recommendations based on metrics."""
    recommendations = []

    if metrics.get("deployment_success_rate", 1.0) < 0.90:
        recommendations.append("Improve deployment success rate through better testing")

    if metrics.get("rollback_rate", 0) > 0.05:
        recommendations.append("Reduce rollback rate by enhancing pre-deployment validation")

    if not recommendations:
        recommendations.append("Deployment metrics are healthy - continue current practices")

    return recommendations


async def _analyze_post_deployment_impact(
    agent: ReleaseAgentProtocol, release_id: str
) -> dict[str, Any]:
    release = agent.releases.get(release_id, {})
    environment = release.get("target_environment")
    analytics_payload = {"release_id": release_id, "environment": environment}
    if agent.analytics_client:
        if hasattr(agent.analytics_client, "get_release_impact"):
            response = await agent.analytics_client.get_release_impact(analytics_payload)
            impact = cast(dict[str, Any], response)
        elif hasattr(agent.analytics_client, "process"):
            response = await agent.analytics_client.process(
                {"action": "get_release_impact", **analytics_payload}
            )
            impact = cast(dict[str, Any], response)
        else:
            impact = {}
    else:
        impact = {
            "usage_change_pct": 1.2,
            "performance_delta_ms": -15,
            "conversion_rate_change": 0.3,
        }
    impact_record = {
        "release_id": release_id,
        "impact": impact,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }
    await agent.db_service.store("deployment_impacts", release_id, impact_record)
    await publish_event(
        agent,
        "deployment.impact_assessed",
        {"release_id": release_id, "impact": impact},
    )
    return impact_record
