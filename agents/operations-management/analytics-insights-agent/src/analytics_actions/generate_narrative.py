"""Action handler for narrative generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from analytics_insights_agent import AnalyticsInsightsAgent


async def handle_generate_narrative(
    agent: AnalyticsInsightsAgent, tenant_id: str, data: dict[str, Any]
) -> dict[str, Any]:
    """
    Generate narrative summary using NLG.

    Returns narrative text.
    """
    agent.logger.info("Generating narrative summary")

    # Extract key insights
    key_insights = await _extract_key_insights(data)

    # Identify trends
    trends = await _identify_trends(data)

    # Generate narrative using AI
    narrative_text = await _generate_narrative_text(agent, key_insights, trends, data)
    narrative_id = f"narrative-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    narrative = {
        "narrative_id": narrative_id,
        "content": narrative_text,
        "data_summary": data,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    agent.analytics_output_store.upsert(tenant_id, narrative_id, narrative.copy())
    await agent.report_repository.store_narrative(narrative.copy())

    return narrative


async def _extract_key_insights(data: dict[str, Any]) -> list[str]:
    """Extract key insights from data."""
    return []


async def _identify_trends(data: dict[str, Any]) -> list[str]:
    """Identify trends in data."""
    return []


async def _generate_narrative_text(
    agent: AnalyticsInsightsAgent, insights: list[str], trends: list[str], data: dict[str, Any]
) -> str:
    """Generate narrative text using NLG."""
    prompt = (
        "Summarize analytics results, explain anomalies, and answer questions in plain language. "
        f"Insights: {insights}. Trends: {trends}. Data snapshot: {data}."
    )
    return await agent.narrative_service.generate_narrative(prompt)
