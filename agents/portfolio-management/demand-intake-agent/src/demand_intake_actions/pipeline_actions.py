"""Pipeline query action handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from demand_intake_agent import DemandIntakeAgent


async def get_pipeline(
    agent: DemandIntakeAgent,
    filters: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """Get current demand pipeline status.

    Returns pipeline statistics and items by stage.
    """
    query = filters.get("query", "")
    status_filter = filters.get("status")
    items = agent.demand_store.list(tenant_id)

    if status_filter:
        items = [item for item in items if item.get("status") == status_filter]

    if query:
        corpus = [agent._combine_text(item) for item in items]
        scores = agent._semantic_similarity(query, corpus)
        scored_items = [(item, score) for item, score in zip(items, scores) if score > 0.05]
        scored_items.sort(key=lambda x: x[1], reverse=True)
        items = [item for item, _ in scored_items]

    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for item in items:
        by_status[item.get("status", "Unknown")] = (
            by_status.get(item.get("status", "Unknown"), 0) + 1
        )
        by_category[item.get("category", "unknown")] = (
            by_category.get(item.get("category", "unknown"), 0) + 1
        )

    return {
        "total_requests": len(items),
        "by_status": by_status,
        "by_category": by_category,
        "items": items,
    }
