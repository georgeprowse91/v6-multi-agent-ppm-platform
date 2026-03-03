"""Action handler for getting top risks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


async def get_top_risks(
    agent: RiskManagementAgent, project_id: str | None, limit: int = 10
) -> list[dict[str, Any]]:
    """
    Get top N risks by score.

    Returns list of top risks.
    """
    from actions.prioritize_risks import prioritize_risks

    # Filter and prioritize
    prioritization = await prioritize_risks(agent, project_id, None)

    # Return top N
    return prioritization["ranked_risks"][:limit]  # type: ignore
