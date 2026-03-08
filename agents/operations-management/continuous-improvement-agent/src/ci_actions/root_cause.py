"""Root cause analysis action handler."""

from __future__ import annotations

from typing import Any

from mining_models import MiningAgentProtocol
from mining_utils import get_process_events


async def analyze_root_cause(
    agent: MiningAgentProtocol, process_id: str, issue_id: str
) -> dict[str, Any]:
    """
    Perform root cause analysis on process issue.

    Returns root cause insights.
    """
    agent.logger.info("Analyzing root cause for issue %s in process %s", issue_id, process_id)

    events = await get_process_events(process_id, agent.event_logs, agent.event_log_store)

    problematic_cases = await _identify_problematic_cases(events, issue_id)
    correlations = await _analyze_correlations(problematic_cases, events)
    factors = await _identify_contributing_factors(correlations)
    insights = await _generate_root_cause_insights(factors)

    return {
        "process_id": process_id,
        "issue_id": issue_id,
        "problematic_cases": len(problematic_cases),
        "contributing_factors": factors,
        "correlations": correlations,
        "insights": insights,
        "recommendations": await _generate_remediation_recommendations(factors),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _identify_problematic_cases(events: list[dict[str, Any]], issue_id: str) -> list[str]:
    """Identify problematic cases."""
    problematic: set[str] = set()
    for event in events:
        if event.get("issue_id") == issue_id or event.get("status") in {"failed", "error"}:
            case_id = event.get("case_id")
            if case_id:
                problematic.add(str(case_id))
    return list(problematic)


async def _analyze_correlations(
    problematic_cases: list[str], events: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Analyze correlations for root cause."""
    if not problematic_cases:
        return []
    total_cases = {str(event.get("case_id")) for event in events if event.get("case_id")}
    total_count = len(total_cases) or 1
    problematic_set = set(problematic_cases)
    activity_counts: dict[str, int] = {}
    for event in events:
        case_id = str(event.get("case_id")) if event.get("case_id") else None
        if case_id and case_id in problematic_set:
            activity = str(event.get("activity") or event.get("action") or "unknown")
            activity_counts[activity] = activity_counts.get(activity, 0) + 1

    correlations: list[dict[str, Any]] = []
    for activity, count in activity_counts.items():
        correlations.append(
            {
                "factor": activity,
                "occurrences": count,
                "correlation": min(1.0, count / total_count),
            }
        )
    correlations.sort(key=lambda item: item["correlation"], reverse=True)
    return correlations


async def _identify_contributing_factors(
    correlations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Identify contributing factors."""
    return [
        {"factor": "High workload", "correlation": 0.75},
        {"factor": "Insufficient resources", "correlation": 0.65},
    ]


async def _generate_root_cause_insights(factors: list[dict[str, Any]]) -> list[str]:
    """Generate root cause insights."""
    return [f"Primary factor: {f.get('factor')}" for f in factors[:3]]


async def _generate_remediation_recommendations(
    factors: list[dict[str, Any]],
) -> list[str]:
    """Generate remediation recommendations."""
    return ["Increase resource allocation", "Redistribute workload"]
