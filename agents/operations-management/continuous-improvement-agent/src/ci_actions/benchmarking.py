"""Benchmarking and best-practices action handlers."""

from __future__ import annotations

from typing import Any

from mining_models import MiningAgentProtocol


async def benchmark_performance(
    agent: MiningAgentProtocol, process_id: str, benchmark_criteria: dict[str, Any]
) -> dict[str, Any]:
    """
    Benchmark process performance.

    Returns benchmark comparison.
    """
    agent.logger.info("Benchmarking performance for process: %s", process_id)

    current_metrics = await _get_current_process_metrics(agent, process_id)
    benchmark_data = await _get_benchmark_data(agent, process_id, benchmark_criteria)
    comparison = await _compare_metrics(current_metrics, benchmark_data)
    gaps = await _identify_performance_gaps(comparison)

    return {
        "process_id": process_id,
        "current_metrics": current_metrics,
        "benchmark_metrics": benchmark_data,
        "comparison": comparison,
        "performance_gaps": gaps,
        "ranking": await _calculate_performance_ranking(comparison),
    }


async def share_best_practices(
    agent: MiningAgentProtocol, filters: dict[str, Any]
) -> dict[str, Any]:
    """
    Share best practices across teams.

    Returns best practices list.
    """
    agent.logger.info("Sharing best practices")

    top_performers = await _identify_top_performers(agent, filters)
    best_practices = await _extract_best_practices(top_performers)
    categorized_practices = await _categorize_best_practices(best_practices)

    templates = [
        {
            "title": "Process Improvement Checklist",
            "description": "Checklist for rolling out optimized processes",
        }
    ]
    if agent.knowledge_agent:
        await agent.knowledge_agent.process(
            {
                "action": "ingest_agent_output",
                "payload": {
                    "category": "best_practices",
                    "best_practices": best_practices,
                    "templates": templates,
                },
                "tenant_id": "shared",
            }
        )

    return {
        "total_practices": len(best_practices),
        "best_practices": best_practices,
        "categorized": categorized_practices,
        "top_performers": top_performers,
        "templates": templates,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_current_process_metrics(
    agent: MiningAgentProtocol, process_id: str
) -> dict[str, Any]:
    """Get current process metrics."""
    process_model = agent.process_models.get(process_id)
    if process_model:
        return process_model.get("metrics", {})  # type: ignore
    return {}


async def _get_benchmark_data(
    agent: MiningAgentProtocol, process_id: str, criteria: dict[str, Any]
) -> dict[str, Any]:
    """Get benchmark data for comparison."""
    stored = agent.benchmarks.get(process_id)
    if stored:
        return stored
    return {"median_cycle_time": 20.0, "throughput": 30.0, "avg_waiting_time": 1.8}


async def _compare_metrics(current: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    """Compare current metrics to benchmark."""
    comparison: dict[str, Any] = {}
    for key in benchmark.keys():
        if key in current:
            comparison[key] = {
                "current": current[key],
                "benchmark": benchmark[key],
                "variance": current[key] - benchmark[key],
            }
    return comparison


async def _identify_performance_gaps(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    """Identify performance gaps."""
    gaps: list[dict[str, Any]] = []
    for metric, data in comparison.items():
        if data.get("variance", 0) > 0:
            gaps.append(
                {
                    "metric": metric,
                    "gap": data["variance"],
                    "severity": "high" if abs(data["variance"]) > 10 else "medium",
                }
            )
    return gaps


async def _calculate_performance_ranking(comparison: dict[str, Any]) -> str:
    """Calculate performance ranking."""
    if not comparison:
        return "Unknown"
    score = 0
    for _metric, data in comparison.items():
        variance = data.get("variance", 0)
        if variance <= 0:
            score += 1
        elif variance < 5:
            score += 0
        else:
            score -= 1
    if score >= 2:
        return "Top Performer"
    if score <= -2:
        return "Below Benchmark"
    return "Average"


async def _identify_top_performers(
    agent: MiningAgentProtocol, filters: dict[str, Any]
) -> list[dict[str, Any]]:
    """Identify top-performing processes."""
    top_performers: list[dict[str, Any]] = []
    for process_id, model in agent.process_models.items():
        metrics = model.get("metrics", {})
        throughput = metrics.get("throughput", 0)
        if throughput and throughput >= filters.get("min_throughput", 5):
            top_performers.append({"process_id": process_id, "metrics": metrics})
    return top_performers


async def _extract_best_practices(
    top_performers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract best practices from top performers."""
    return [
        {"practice": "Automate manual approvals", "impact": "High"},
        {"practice": "Parallel processing where possible", "impact": "Medium"},
    ]


async def _categorize_best_practices(
    practices: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Categorize best practices."""
    categorized: dict[str, list[dict[str, Any]]] = {
        "automation": [],
        "optimization": [],
        "standardization": [],
    }
    for practice in practices:
        categorized["optimization"].append(practice)
    return categorized
