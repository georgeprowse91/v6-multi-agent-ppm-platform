"""Action handler for data aggregation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from analytics_utils import (
    calculate_statistics,
    collect_from_sources,
    harmonize_data,
    record_data_lineage,
)

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


async def handle_aggregate_data(
    agent: AnalyticsInsightsAgent, tenant_id: str, data_sources: list[str]
) -> dict[str, Any]:
    """
    Aggregate data from multiple sources.

    Returns aggregated dataset.
    """
    agent.logger.info("Aggregating data from %s sources", len(data_sources))

    # Collect data from sources
    aggregated_data = await collect_from_sources(data_sources)

    # Harmonize data definitions
    harmonized_data = await harmonize_data(aggregated_data)

    # Calculate summary statistics
    statistics = await calculate_statistics(harmonized_data)

    # Track lineage
    lineage_id = await record_data_lineage(agent, tenant_id, data_sources, harmonized_data)
    data_lake_paths: list[dict[str, str]] = []
    for source in data_sources:
        data_lake_paths.append(
            agent.data_lake_manager.store_dataset(
                source=source,
                domain="analytics",
                payload=[
                    record for record in harmonized_data if record.get("source") == source
                ],
            )
        )
    synapse_details = agent.synapse_manager.ingest_dataset(
        "analytics_aggregated", harmonized_data
    )

    return {
        "record_count": len(harmonized_data),
        "data_sources": data_sources,
        "statistics": statistics,
        "lineage_id": lineage_id,
        "data_lake_paths": data_lake_paths,
        "synapse": synapse_details,
        "aggregated_at": datetime.now(timezone.utc).isoformat(),
    }
