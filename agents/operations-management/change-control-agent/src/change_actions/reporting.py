"""Action handlers for dashboards, reports, metrics, and auditing."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from urllib import request

from change_actions.submit_change import publish_event

if TYPE_CHECKING:
    from change_configuration_agent import ChangeConfigurationAgent


async def audit_changes(agent: ChangeConfigurationAgent, filters: dict[str, Any]) -> dict[str, Any]:
    """Audit change history."""
    agent.logger.info("Auditing changes")

    # Filter changes
    changes_to_audit = []
    for change_id, change in agent.change_requests.items():
        if await matches_filters(change, filters):
            changes_to_audit.append(change)

    # Analyze change patterns
    patterns = await analyze_change_patterns(changes_to_audit)

    return {
        "total_changes": len(changes_to_audit),
        "approved_changes": len(
            [c for c in changes_to_audit if c.get("approval_status") == "Approved"]
        ),
        "rejected_changes": len(
            [c for c in changes_to_audit if c.get("approval_status") == "Rejected"]
        ),
        "emergency_changes": len([c for c in changes_to_audit if c.get("type") == "emergency"]),
        "patterns": patterns,
        "audit_date": datetime.now(timezone.utc).isoformat(),
    }


async def visualize_dependencies(
    agent: ChangeConfigurationAgent, ci_id: str | None
) -> dict[str, Any]:
    """Visualize CI dependencies."""
    agent.logger.info("Visualizing dependencies for CI: %s", ci_id)

    # Get CI and its dependencies
    if ci_id:
        ci = agent.cmdb.get(ci_id)
        if not ci:
            raise ValueError(f"CI not found: {ci_id}")

        # Build dependency graph
        dependency_graph = await build_dependency_graph(agent, ci_id)
    else:
        # Get full CMDB graph
        dependency_graph = await build_full_cmdb_graph(agent)

    return {
        "ci_id": ci_id,
        "dependency_graph": dependency_graph,
        "node_count": len(dependency_graph.get("nodes", [])),
        "edge_count": len(dependency_graph.get("edges", [])),
    }


async def get_change_dashboard(
    agent: ChangeConfigurationAgent, filters: dict[str, Any]
) -> dict[str, Any]:
    """Get change dashboard data."""
    agent.logger.info("Getting change dashboard")

    # Get open changes
    open_changes = []
    for change_id, change in agent.change_requests.items():
        if change.get("status") in ["Submitted", "Approved", "In Progress"]:
            if await matches_filters(change, filters):
                open_changes.append(change)

    # Get change statistics
    stats = await calculate_change_statistics(agent, filters)

    # Get CAB workload
    cab_workload = await calculate_cab_workload(agent)

    return {
        "open_changes": len(open_changes),
        "change_statistics": stats,
        "cab_workload": cab_workload,
        "recent_changes": open_changes[:10],
        "dashboard_generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def generate_change_report(
    agent: ChangeConfigurationAgent,
    report_type: str,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """Generate change management report."""
    agent.logger.info("Generating %s change report", report_type)

    if report_type == "summary":
        return await generate_summary_report(filters)
    elif report_type == "audit":
        return await audit_changes(agent, filters)
    else:
        raise ValueError(f"Unknown report type: {report_type}")


async def get_change_metrics(
    agent: ChangeConfigurationAgent, filters: dict[str, Any]
) -> dict[str, Any]:
    """Calculate trending metrics for change management."""
    changes = [c for c in agent.change_requests.values() if await matches_filters(c, filters)]
    type_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    monthly_trends: dict[str, int] = {}
    approval_times: list[float] = []
    success_count = 0
    for change in changes:
        change_type = change.get("type", "unknown")
        type_counts[change_type] = type_counts.get(change_type, 0) + 1
        category = change.get("classification", {}).get("category", "unclassified")
        category_counts[category] = category_counts.get(category, 0) + 1
        created_at = change.get("created_at")
        if created_at:
            created_dt = datetime.fromisoformat(created_at)
            month_key = created_dt.strftime("%Y-%m")
            monthly_trends[month_key] = monthly_trends.get(month_key, 0) + 1
        approved_at = change.get("approval_date")
        if created_at and approved_at:
            approved_dt = datetime.fromisoformat(approved_at)
            approval_times.append((approved_dt - created_dt).total_seconds() / 3600)
        if change.get("status") == "Implemented":
            success_count += 1
    average_approval_hours = sum(approval_times) / len(approval_times) if approval_times else 0.0
    success_rate = (success_count / len(changes)) if changes else 0.0
    metrics = {
        "total_changes": len(changes),
        "change_type_counts": type_counts,
        "change_category_counts": category_counts,
        "average_approval_time_hours": round(average_approval_hours, 2),
        "success_rate": round(success_rate, 2),
        "monthly_trends": dict(sorted(monthly_trends.items())),
    }
    await publish_change_metrics(agent, metrics)
    return metrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def matches_filters(change: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Check if change matches filters."""
    if "status" in filters and change.get("status") != filters["status"]:
        return False

    if "type" in filters and change.get("type") != filters["type"]:
        return False

    return True


async def analyze_change_patterns(changes: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze patterns in changes."""
    if not changes:
        return {
            "most_common_type": "unknown",
            "average_approval_time_days": 0,
            "rejection_rate": 0,
        }
    type_counts: dict[str, int] = {}
    approval_times: list[float] = []
    rejected = 0
    for change in changes:
        change_type = str(change.get("type", "unknown"))
        type_counts[change_type] = type_counts.get(change_type, 0) + 1
        if change.get("approval_date") and change.get("created_at"):
            approval_times.append(
                (
                    datetime.fromisoformat(change["approval_date"])
                    - datetime.fromisoformat(change["created_at"])
                ).days
            )
        if change.get("approval_status") == "Rejected":
            rejected += 1
    most_common_type = max(type_counts.items(), key=lambda item: item[1])[0]
    avg_approval = sum(approval_times) / len(approval_times) if approval_times else 0
    return {
        "most_common_type": most_common_type,
        "average_approval_time_days": avg_approval,
        "rejection_rate": rejected / len(changes),
    }


async def build_dependency_graph(agent: ChangeConfigurationAgent, ci_id: str) -> dict[str, Any]:
    """Build dependency graph for CI."""
    visited: set[str] = set()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        visited.add(node_id)
        ci = agent.cmdb.get(node_id, {"name": node_id, "relationships": []})
        nodes.append({"id": node_id, "label": ci.get("name"), "type": ci.get("type")})
        for rel in ci.get("relationships", []):
            target = rel.get("target_ci_id")
            if target:
                edges.append(
                    {
                        "source": node_id,
                        "target": target,
                        "type": rel.get("relationship_type"),
                    }
                )
                visit(target)

    visit(ci_id)
    return {"nodes": nodes, "edges": edges}


async def build_full_cmdb_graph(agent: ChangeConfigurationAgent) -> dict[str, Any]:
    """Build full CMDB dependency graph."""
    nodes = []
    edges = []

    for ci_id, ci in agent.cmdb.items():
        nodes.append({"id": ci_id, "label": ci.get("name"), "type": ci.get("type")})

        for rel in ci.get("relationships", []):
            edges.append(
                {
                    "source": ci_id,
                    "target": rel.get("target_ci_id"),
                    "type": rel.get("relationship_type"),
                }
            )

    return {"nodes": nodes, "edges": edges}


async def calculate_change_statistics(
    agent: ChangeConfigurationAgent, filters: dict[str, Any]
) -> dict[str, Any]:
    """Calculate change statistics."""
    changes = [c for c in agent.change_requests.values() if await matches_filters(c, filters)]
    total = len(changes)
    approved = len([c for c in changes if c.get("approval_status") == "Approved"])
    lead_times: list[float] = []
    for change in changes:
        created_at = change.get("created_at")
        implemented_at = change.get("implemented_at")
        if created_at and implemented_at:
            created_dt = datetime.fromisoformat(created_at)
            implemented_dt = datetime.fromisoformat(implemented_at)
            lead_times.append((implemented_dt - created_dt).total_seconds() / 3600)
    average_lead_time = sum(lead_times) / len(lead_times) if lead_times else 0.0
    return {
        "total_changes": total,
        "approved_rate": round(approved / total, 2) if total else 0.0,
        "average_lead_time_hours": round(average_lead_time, 2),
    }


async def calculate_cab_workload(agent: ChangeConfigurationAgent) -> dict[str, Any]:
    """Calculate CAB workload."""
    pending_reviews = len(
        [
            change
            for change in agent.change_requests.values()
            if change.get("approval_status") == "Pending"
        ]
    )
    return {
        "pending_reviews": pending_reviews,
        "next_meeting": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
    }


async def generate_summary_report(filters: dict[str, Any]) -> dict[str, Any]:
    """Generate summary change report."""
    return {
        "report_type": "summary",
        "data": {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def publish_change_metrics(agent: ChangeConfigurationAgent, metrics: dict[str, Any]) -> None:
    await publish_event(
        agent,
        "change.metrics",
        {
            "event_id": f"change.metrics:{datetime.now(timezone.utc).isoformat()}",
            "metrics": metrics,
        },
    )
    if not agent.metrics_endpoint:
        return
    payload = json.dumps(metrics).encode("utf-8")
    try:
        req = request.Request(agent.metrics_endpoint, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        request.urlopen(req, timeout=10)
    except OSError as exc:
        agent.logger.warning("Failed to publish change metrics: %s", exc)
