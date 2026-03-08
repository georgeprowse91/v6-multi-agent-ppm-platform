"""Action handlers for defect trend analysis and root cause analysis."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from quality_management_agent import QualityManagementAgent


async def analyze_defect_trends(
    agent: QualityManagementAgent,
    project_id: str,
) -> dict[str, Any]:
    """Analyze defect trends and patterns.  Returns trend analysis and patterns."""
    agent.logger.info("Analyzing defect trends for project: %s", project_id)

    project_defects = [d for d in agent.defects.values() if d.get("project_id") == project_id]

    trends = await _calculate_defect_trends_over_time(project_defects)
    patterns = await _identify_defect_patterns(agent, project_defects)
    anomalies = await _detect_defect_anomalies(project_defects)
    defect_density_prediction = await _predict_defect_density(agent, project_id)

    return {
        "project_id": project_id,
        "trends": trends,
        "patterns": patterns,
        "anomalies": anomalies,
        "defect_density_prediction": defect_density_prediction,
        "total_defects_analyzed": len(project_defects),
        "cluster_insights": await _summarize_defect_clusters(agent, project_defects),
    }


async def perform_root_cause_analysis(
    agent: QualityManagementAgent,
    defect_ids: list[str],
) -> dict[str, Any]:
    """Perform root cause analysis on defects.  Returns RCA results and recommendations."""
    agent.logger.info("Performing RCA on %s defects", len(defect_ids))

    defects_to_analyze = [
        agent.defects.get(defect_id) for defect_id in defect_ids if defect_id in agent.defects
    ]

    root_causes = await _identify_root_causes(defects_to_analyze)  # type: ignore
    pareto_analysis = await _perform_pareto_analysis(root_causes)
    recommendations = await _generate_improvement_recommendations(root_causes, pareto_analysis)
    subsystem_recommendations = await _recommend_refactoring_targets(defects_to_analyze)

    return {
        "defects_analyzed": len(defects_to_analyze),
        "root_causes": root_causes,
        "pareto_analysis": pareto_analysis,
        "recommendations": recommendations,
        "refactoring_recommendations": subsystem_recommendations,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _calculate_defect_trends_over_time(
    defects: list[dict[str, Any]],
) -> dict[str, Any]:
    if not defects:
        return {"trend": "stable", "weekly_average": 0, "peak_week": None}
    weekly_counts: dict[int, int] = {}
    for defect in defects:
        logged_at = defect.get("logged_at")
        if not logged_at:
            continue
        week_num = datetime.fromisoformat(logged_at).isocalendar()[1]
        weekly_counts[week_num] = weekly_counts.get(week_num, 0) + 1
    if not weekly_counts:
        return {"trend": "stable", "weekly_average": 0, "peak_week": None}
    sorted_weeks = sorted(weekly_counts)
    counts = [weekly_counts[week] for week in sorted_weeks]
    trend = (
        "increasing"
        if counts[-1] > counts[0]
        else "decreasing" if counts[-1] < counts[0] else "stable"
    )
    return {
        "trend": trend,
        "weekly_average": sum(counts) / len(counts),
        "peak_week": max(weekly_counts, key=weekly_counts.get),
    }


async def _identify_defect_patterns(
    agent: QualityManagementAgent,
    defects: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not defects:
        return []
    component_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for defect in defects:
        component = defect.get("component", "unknown")
        category = defect.get("root_cause", "unknown")
        component_counts[component] = component_counts.get(component, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1
    patterns = [
        {"pattern": f"Defects clustered in component '{component}'", "count": count}
        for component, count in sorted(
            component_counts.items(), key=lambda item: item[1], reverse=True
        )
    ]
    patterns.extend(
        {
            "pattern": f"Root cause '{category}' appears frequently",
            "count": count,
        }
        for category, count in sorted(
            category_counts.items(), key=lambda item: item[1], reverse=True
        )
    )
    cluster_patterns = await _summarize_defect_clusters(agent, defects)
    patterns.extend(cluster_patterns)
    return patterns[:5]


async def _detect_defect_anomalies(
    defects: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not defects:
        return []
    weekly_counts: dict[int, int] = {}
    for defect in defects:
        logged_at = defect.get("logged_at")
        if not logged_at:
            continue
        week_num = datetime.fromisoformat(logged_at).isocalendar()[1]
        weekly_counts[week_num] = weekly_counts.get(week_num, 0) + 1
    if len(weekly_counts) < 2:
        return []
    counts = list(weekly_counts.values())
    mean = sum(counts) / len(counts)
    variance = sum((count - mean) ** 2 for count in counts) / len(counts)
    std_dev = math.sqrt(variance)
    threshold = mean + 2 * std_dev
    anomalies = [
        {"week": week, "count": count, "reason": "defect_spike"}
        for week, count in weekly_counts.items()
        if count > threshold
    ]
    return anomalies


async def _predict_defect_density(agent: QualityManagementAgent, project_id: str) -> dict[str, Any]:
    history = agent.defect_density_history.get(project_id, [])
    if not history:
        return {"predicted_defect_density": 0.0, "trend": "unknown", "data_points": 0}
    densities = [entry["defect_density"] for entry in history]
    if len(densities) == 1:
        return {
            "predicted_defect_density": densities[0],
            "trend": "stable",
            "data_points": 1,
        }
    slope = (densities[-1] - densities[0]) / max(len(densities) - 1, 1)
    prediction = max(densities[-1] + slope, 0.0)
    trend = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
    return {
        "predicted_defect_density": prediction,
        "trend": trend,
        "data_points": len(densities),
    }


async def _identify_root_causes(defects: list[dict[str, Any]]) -> dict[str, int]:
    root_causes = {}  # type: ignore
    for defect in defects:
        cause = defect.get("root_cause", "unknown")
        root_causes[cause] = root_causes.get(cause, 0) + 1
    return root_causes


async def _perform_pareto_analysis(root_causes: dict[str, int]) -> dict[str, Any]:
    total = sum(root_causes.values())
    sorted_causes = sorted(root_causes.items(), key=lambda x: x[1], reverse=True)
    pareto = []
    cumulative_pct = 0.0
    for cause, count in sorted_causes:
        pct = (count / total) * 100 if total > 0 else 0
        cumulative_pct += pct
        pareto.append(
            {
                "root_cause": cause,
                "count": count,
                "percentage": pct,
                "cumulative_percentage": cumulative_pct,
            }
        )
    return {
        "pareto_chart": pareto,
        "vital_few": [p for p in pareto if p["cumulative_percentage"] <= 80],  # type: ignore
    }


async def _generate_improvement_recommendations(
    root_causes: dict[str, int], pareto_analysis: dict[str, Any]
) -> list[str]:
    recommendations = []
    vital_few = pareto_analysis.get("vital_few", [])
    for item in vital_few:
        recommendations.append(
            f"Focus on addressing {item['root_cause']} (accounts for {item['percentage']:.1f}% of defects)"
        )
    return recommendations


async def _recommend_refactoring_targets(defects: list[dict[str, Any]]) -> list[str]:
    if not defects:
        return []
    component_counts: dict[str, int] = {}
    for defect in defects:
        if not defect:
            continue
        component = defect.get("component", "unknown")
        component_counts[component] = component_counts.get(component, 0) + 1
    sorted_components = sorted(component_counts.items(), key=lambda item: item[1], reverse=True)
    return [
        f"Prioritize refactoring in {component} (defects: {count})"
        for component, count in sorted_components[:3]
    ]


async def _summarize_defect_clusters(
    agent: QualityManagementAgent,
    defects: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not defects:
        return []
    from quality_utils import kmeans, vectorize_defects

    if not agent.defect_cluster_model or not agent.defect_cluster_model.get("clusters"):
        defect_list = list(agent.defects.values())
        if len(defect_list) < 2:
            return []
        vectors, vocab = vectorize_defects(defect_list)
        k = min(3, len(vectors))
        clusters = kmeans(vectors, k)
        agent.defect_cluster_model = {
            "clusters": clusters,
            "vocab": vocab,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
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
