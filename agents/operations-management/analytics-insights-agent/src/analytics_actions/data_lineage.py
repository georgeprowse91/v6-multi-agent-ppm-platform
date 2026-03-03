"""Action handler for data lineage tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from security.lineage import mask_lineage_payload

from analytics_utils import generate_lineage_id

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


async def handle_update_data_lineage(
    agent: AnalyticsInsightsAgent, tenant_id: str, lineage_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Update data lineage tracking.

    Returns lineage information.
    """
    agent.logger.info("Updating data lineage")

    # Generate lineage ID
    lineage_id = await generate_lineage_id()

    # Record lineage
    lineage = {
        "lineage_id": lineage_id,
        "source_systems": lineage_data.get("sources", []),
        "transformations": lineage_data.get("transformations", []),
        "target_dataset": lineage_data.get("target"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    masked_lineage = mask_lineage_payload(lineage)
    agent.data_lineage[lineage_id] = masked_lineage
    agent.analytics_lineage_store.upsert(tenant_id, lineage_id, masked_lineage)

    return {
        "lineage_id": lineage_id,
        "sources": len(lineage.get("source_systems", [])),
        "transformations": len(lineage.get("transformations", [])),
    }
