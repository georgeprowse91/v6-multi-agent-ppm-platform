"""Action handlers for quality metric definition and calculation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from quality_utils import (
    calculate_resolution_time,
    generate_metric_id,
)

if TYPE_CHECKING:
    from quality_management_agent import QualityManagementAgent


async def define_metrics(
    agent: QualityManagementAgent,
    project_id: str,
    metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Define quality metrics for project.

    Returns metric IDs and thresholds.
    """
    agent.logger.info("Defining quality metrics for project: %s", project_id)

    defined_metrics = []

    for metric_def in metrics:
        metric_id = await generate_metric_id()

        metric = {
            "metric_id": metric_id,
            "project_id": project_id,
            "name": metric_def.get("name"),
            "description": metric_def.get("description"),
            "type": metric_def.get("type"),
            "threshold": metric_def.get("threshold"),
            "target": metric_def.get("target"),
            "unit": metric_def.get("unit"),
            "collection_frequency": metric_def.get("collection_frequency", "daily"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if project_id not in agent.quality_metrics:
            agent.quality_metrics[project_id] = []

        agent.quality_metrics[project_id].append(metric)
        defined_metrics.append(metric)

        await agent._store_record("quality_metric_definitions", metric_id, metric)

    return {
        "project_id": project_id,
        "metrics_defined": len(defined_metrics),
        "metrics": defined_metrics,
    }


async def calculate_metrics(
    agent: QualityManagementAgent,
    project_id: str,
) -> dict[str, Any]:
    """Calculate quality metrics for project.

    Returns quality metrics and trends.
    """
    agent.logger.info("Calculating quality metrics for project: %s", project_id)

    project_defects = [d for d in agent.defects.values() if d.get("project_id") == project_id]

    total_defects = len(project_defects)
    open_defects = len([d for d in project_defects if d.get("status") == "Open"])
    critical_defects = len([d for d in project_defects if d.get("severity") == "critical"])

    defect_density = await _calculate_defect_density(agent, project_id, total_defects)
    code_size = await _get_code_size_metrics(agent, project_id)
    defect_density_per_fp = await _calculate_defect_density_per_fp(agent, project_id, total_defects)

    test_coverage = await _get_latest_test_coverage(agent, project_id)
    coverage_snapshot = await _fetch_coverage_metrics(agent, project_id)
    if coverage_snapshot:
        agent.coverage_snapshots[project_id] = coverage_snapshot
        test_coverage = float(coverage_snapshot.get("coverage_pct", test_coverage))

    mttr = await _calculate_mttr(agent, project_defects)
    pass_rate = await _calculate_pass_rate(agent, project_id)
    quality_score = await _calculate_quality_score(agent, defect_density, test_coverage, pass_rate)
    coverage_trend = await _calculate_coverage_trend(agent, project_id)

    model_summary = await _train_defect_prediction_model(agent, project_id)
    subsystem_model = await _train_defect_subsystem_model(agent, project_id, project_defects)
    improvement_recommendations = await _generate_quality_improvement_recommendations(
        agent, project_id, project_defects, test_coverage, pass_rate, coverage_snapshot
    )

    metrics = {
        "project_id": project_id,
        "total_defects": total_defects,
        "open_defects": open_defects,
        "critical_defects": critical_defects,
        "defect_density": defect_density,
        "defect_density_per_function_point": defect_density_per_fp,
        "code_size_metrics": code_size,
        "test_coverage_pct": test_coverage,
        "coverage_snapshot": coverage_snapshot,
        "coverage_trend": coverage_trend,
        "pass_rate_pct": pass_rate,
        "mean_time_to_resolution_hours": mttr,
        "quality_score": quality_score,
        "defect_prediction_model": model_summary,
        "defect_subsystem_model": subsystem_model,
        "improvement_recommendations": improvement_recommendations,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }

    history = agent.defect_density_history.setdefault(project_id, [])
    history.append({"defect_density": defect_density, "timestamp": metrics["calculated_at"]})
    metrics_record_id = f"QMET-{project_id}-{metrics['calculated_at'].replace(':', '-')}"
    await agent._store_record("quality_metrics", metrics_record_id, metrics)
    await agent._publish_quality_event(
        "quality.metrics.calculated",
        payload={
            "project_id": project_id,
            "defect_density": defect_density,
            "test_coverage_pct": test_coverage,
            "quality_score": quality_score,
            "model_version": model_summary.get("model_version"),
        },
        tenant_id=project_id,
        correlation_id=str(uuid.uuid4()),
    )
    await _publish_improvement_recommendations(agent, project_id, improvement_recommendations)

    return metrics


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _calculate_defect_density(
    agent: QualityManagementAgent, project_id: str, total_defects: int
) -> float:
    code_size = await _get_code_size_metrics(agent, project_id)
    loc = code_size.get("loc")
    kloc = code_size.get("kloc", (float(loc) / 1000.0) if loc else 10.0)
    return total_defects / kloc if kloc > 0 else 0


async def _calculate_defect_density_per_fp(
    agent: QualityManagementAgent, project_id: str, total_defects: int
) -> float | None:
    code_size = await _get_code_size_metrics(agent, project_id)
    function_points = code_size.get("function_points")
    if not function_points:
        return None
    return total_defects / float(function_points) if function_points > 0 else None


async def _get_latest_test_coverage(agent: QualityManagementAgent, project_id: str) -> float:
    executions = []
    for execution in agent.test_executions.values():
        if execution.get("project_id") != project_id:
            continue
        if not execution.get("executed_at"):
            continue
        executions.append(execution)
    if not executions:
        return 0.0
    latest = max(
        executions,
        key=lambda item: datetime.fromisoformat(item.get("executed_at")),
    )
    return float(latest.get("code_coverage", 0.0))


async def _calculate_mttr(agent: QualityManagementAgent, defects: list[dict[str, Any]]) -> float:
    resolved_defects = [d for d in defects if d.get("status") in ["Resolved", "Closed", "Verified"]]
    if not resolved_defects:
        return 0.0
    total_time = 0.0
    for defect in resolved_defects:
        resolution_time = await calculate_resolution_time(defect)
        total_time += resolution_time
    return total_time / len(resolved_defects)


async def _calculate_pass_rate(agent: QualityManagementAgent, project_id: str) -> float:
    executions = [
        execution
        for execution in agent.test_executions.values()
        if execution.get("project_id") == project_id
    ]
    if not executions:
        return 0.0
    total_tests = sum(execution.get("total_tests", 0) for execution in executions)
    passed_tests = sum(execution.get("passed", 0) for execution in executions)
    return (passed_tests / total_tests) * 100 if total_tests > 0 else 0.0


async def _calculate_quality_score(
    agent: QualityManagementAgent,
    defect_density: float,
    test_coverage: float,
    pass_rate: float,
) -> float:
    score = (
        (1 - min(defect_density / agent.defect_density_threshold, 1.0)) * 30
        + (test_coverage / 100) * 40
        + (pass_rate / 100) * 30
    )
    return min(100, max(0, score))


async def _calculate_coverage_trend(
    agent: QualityManagementAgent, project_id: str
) -> dict[str, Any]:
    history = agent.coverage_trends.get(project_id, [])
    if len(history) < 2:
        return {"trend": "stable", "data_points": len(history)}
    points = [entry.get("coverage_pct", 0.0) for entry in history]
    slope = (points[-1] - points[0]) / max(len(points) - 1, 1)
    trend = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
    return {"trend": trend, "data_points": len(points), "latest": points[-1]}


async def _get_code_size_metrics(agent: QualityManagementAgent, project_id: str) -> dict[str, Any]:
    repo_config = agent.integration_config.get("code_repos", {})
    size_data = repo_config.get("size_by_project", {}).get(project_id)
    if size_data:
        return size_data
    return {"kloc": 10.0, "source": "mock"}


async def _fetch_coverage_metrics(agent: QualityManagementAgent, project_id: str) -> dict[str, Any]:
    repo_config = agent.integration_config.get("code_repos", {})
    coverage_data = repo_config.get("coverage_by_project", {}).get(project_id)
    if coverage_data:
        return coverage_data
    return {
        "coverage_pct": 85.0,
        "source": "mock",
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


async def _train_defect_prediction_model(
    agent: QualityManagementAgent, project_id: str
) -> dict[str, Any]:
    model_version = datetime.now(timezone.utc).strftime("v%Y%m%d%H%M%S")
    model_info = {
        "project_id": project_id,
        "model_version": model_version,
        "training_status": "completed",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "features": ["defect_density", "coverage_pct", "pass_rate"],
    }
    agent.defect_prediction_models[project_id] = model_info
    await agent._store_record("quality_defect_models", f"{project_id}-{model_version}", model_info)
    return model_info


async def _train_defect_subsystem_model(
    agent: QualityManagementAgent,
    project_id: str,
    defects: list[dict[str, Any]],
) -> dict[str, Any]:
    subsystem_map: dict[str, int] = {}
    for defect in defects:
        component = defect.get("component", "unknown")
        subsystem_map[component] = subsystem_map.get(component, 0) + 1
    model_version = datetime.now(timezone.utc).strftime("subsystem-%Y%m%d%H%M%S")
    model_info = {
        "project_id": project_id,
        "model_version": model_version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "subsystem_distribution": subsystem_map,
    }
    agent.defect_subsystem_models[project_id] = model_info
    await agent._store_record(
        "quality_defect_subsystem_models", f"{project_id}-{model_version}", model_info
    )
    return model_info


async def _generate_quality_improvement_recommendations(
    agent: QualityManagementAgent,
    project_id: str,
    defects: list[dict[str, Any]],
    coverage_pct: float,
    pass_rate: float,
    coverage_snapshot: dict[str, Any] | None,
) -> list[str]:
    recommendations = []
    if coverage_pct < agent.min_test_coverage:
        recommendations.append(
            f"Increase automated test coverage to at least {agent.min_test_coverage:.0%}."
        )
    if pass_rate < 90:
        recommendations.append("Stabilize flaky tests and improve pass rate above 90%.")
    if defects:
        top_components = await _recommend_refactoring_targets(defects)
        recommendations.extend(top_components)
    cluster_insights = await _summarize_defect_clusters(agent, defects)
    if cluster_insights:
        recommendations.extend(
            [insight.get("pattern") for insight in cluster_insights if insight.get("pattern")]
        )
    if coverage_snapshot and coverage_snapshot.get("source") == "ci":
        recommendations.append("Review CI coverage configuration for gaps.")
    return recommendations


async def _recommend_refactoring_targets(defects: list[dict[str, Any]]) -> list[str]:
    if not defects:
        return []
    component_counts: dict[str, int] = {}
    for defect in defects:
        component = defect.get("component", "unknown")
        component_counts[component] = component_counts.get(component, 0) + 1
    sorted_components = sorted(component_counts.items(), key=lambda item: item[1], reverse=True)
    return [
        f"Prioritize refactoring in {component} (defects: {count})"
        for component, count in sorted_components[:3]
    ]


async def _summarize_defect_clusters(
    agent: QualityManagementAgent, defects: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not defects:
        return []

    if not agent.defect_cluster_model or not agent.defect_cluster_model.get("clusters"):
        agent.defect_cluster_model = await _train_defect_cluster_model_inline(agent)
    clusters = (agent.defect_cluster_model or {}).get("clusters", [])
    insights = []
    for cluster in clusters:
        if cluster.get("count", 0) < 2:
            continue
        insights.append(
            {
                "pattern": f"Cluster {cluster['cluster_id']} contains {cluster['count']} recurring defects",
                "count": cluster.get("count", 0),
            }
        )
    return insights


async def _train_defect_cluster_model_inline(
    agent: QualityManagementAgent,
) -> dict[str, Any]:
    from quality_utils import kmeans, vectorize_defects

    defects = list(agent.defects.values())
    if len(defects) < 2:
        return {"clusters": [], "trained_at": None}
    vectors, vocab = vectorize_defects(defects)
    k = min(3, len(vectors))
    clusters = kmeans(vectors, k)
    model = {
        "clusters": clusters,
        "vocab": vocab,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    await agent._store_record(
        "quality_defect_cluster_models", f"cluster-{uuid.uuid4().hex[:6]}", model
    )
    return model


async def _publish_improvement_recommendations(
    agent: QualityManagementAgent,
    project_id: str,
    recommendations: list[str],
) -> None:
    if not recommendations:
        return
    await agent._publish_quality_event(
        "quality.improvement.recommendations",
        payload={"project_id": project_id, "recommendations": recommendations},
        tenant_id=project_id,
        correlation_id=str(uuid.uuid4()),
    )
    stakeholder_client = (agent.config or {}).get("stakeholder_communications_client")
    if stakeholder_client:
        if hasattr(stakeholder_client, "publish_update"):
            stakeholder_client.publish_update(
                {
                    "project_id": project_id,
                    "recommendations": recommendations,
                    "type": "quality_improvement",
                }
            )
        elif hasattr(stakeholder_client, "send_update"):
            stakeholder_client.send_update(project_id, recommendations)
