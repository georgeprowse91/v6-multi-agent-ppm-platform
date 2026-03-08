"""Response Orchestration Agent - Pure utility functions."""

from __future__ import annotations

import time
from typing import Any


def build_agent_activity(
    results: list[dict[str, Any]], execution_start: float
) -> list[dict[str, Any]]:
    """Build a timeline of agent activity from execution results.

    Args:
        results: List of agent invocation result dicts.
        execution_start: Unix timestamp (float) of when execution began.

    Returns:
        List of activity records with started_at, completed_at, duration_ms, and status.
    """
    activity: list[dict[str, Any]] = []
    cursor = execution_start
    for result in results:
        duration_seconds = float(result.get("duration_seconds", 0.001) or 0.001)
        if duration_seconds <= 0:
            duration_seconds = 0.001
        started_at = cursor
        completed_at = started_at + duration_seconds
        cursor = completed_at
        activity.append(
            {
                "agent_id": result.get("agent_id", "unknown"),
                "started_at": (
                    time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(started_at))
                    + f".{int((started_at % 1) * 1000):03d}Z"
                ),
                "completed_at": (
                    time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(completed_at))
                    + f".{int((completed_at % 1) * 1000):03d}Z"
                ),
                "duration_ms": int(duration_seconds * 1000),
                "status": "success" if result.get("success") else "failed",
            }
        )
    return activity


def aggregate_responses(results: list[dict[str, Any]]) -> str | dict[str, Any]:
    """Aggregate multiple agent response dicts into a single output.

    Returns a dict keyed by agent_id for successful results, or an error
    string if all agents failed.
    """
    successful_results = [r for r in results if r.get("success")]
    if not successful_results:
        return "Unable to process request - all agents failed"
    return {r.get("agent_id", "unknown"): r.get("data") or {} for r in successful_results}
