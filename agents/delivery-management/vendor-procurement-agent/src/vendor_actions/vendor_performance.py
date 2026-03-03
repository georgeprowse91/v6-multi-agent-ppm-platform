"""Action handlers: track_vendor_performance, get_vendor_scorecard"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from vendor_utils import (
    analyze_performance_trend,
    calculate_compliance_score,
    calculate_delivery_timeliness,
    calculate_overall_vendor_score,
    calculate_quality_rating,
    calculate_sla_adherence,
    collect_vendor_performance_data,
    generate_vendor_recommendations,
    get_vendor_contracts,
    get_vendor_issues,
    is_expiring_soon,
    publish_event,
    score_vendor_research,
)

if TYPE_CHECKING:
    from vendor_procurement_agent import VendorProcurementAgent


async def handle_track_vendor_performance(
    agent: VendorProcurementAgent,
    vendor_id: str,
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Track vendor performance metrics.

    Returns performance data and trends.
    """
    agent.logger.info("Tracking performance for vendor: %s", vendor_id)

    vendor = agent.vendors.get(vendor_id)
    if not vendor:
        raise ValueError(f"Vendor not found: {vendor_id}")

    # Collect performance data
    performance_data = await collect_vendor_performance_data(agent, vendor_id)

    # Calculate metrics
    metrics = {
        "delivery_timeliness": await calculate_delivery_timeliness(agent, vendor_id),
        "quality_rating": await calculate_quality_rating(agent, vendor_id),
        "compliance_score": await calculate_compliance_score(agent, vendor_id),
        "sla_adherence": await calculate_sla_adherence(agent, vendor_id),
        "dispute_count": performance_data.get("dispute_count", 0),
        "total_spend": performance_data.get("total_spend", 0),
        "contract_count": performance_data.get("contract_count", 0),
    }
    metrics["on_time_delivery_rate"] = metrics["delivery_timeliness"]
    metrics["compliance_rating"] = metrics["compliance_score"]

    ml_analysis = agent.ml_service.analyze_performance(metrics, vendor)
    adjusted_metrics = ml_analysis.get("adjusted_metrics", metrics)

    # Update vendor performance metrics
    vendor["performance_metrics"].update(adjusted_metrics)
    vendor["performance_metrics"]["ml_insights"] = ml_analysis.get("insights", [])
    vendor["performance_metrics"]["performance_trend"] = ml_analysis.get("trend")

    if agent.db_service:
        await agent.db_service.store(
            "vendor_performance",
            vendor_id,
            {
                "vendor_id": vendor_id,
                "metrics": adjusted_metrics,
                "ml_analysis": ml_analysis,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    agent.vendor_performance_store.upsert(
        tenant_id,
        vendor_id,
        {
            "vendor_id": vendor_id,
            "metrics": adjusted_metrics,
            "ml_analysis": ml_analysis,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await publish_event(
        agent,
        "vendor.performance_updated",
        payload={
            "vendor_id": vendor_id,
            "metrics": adjusted_metrics,
            "ml_analysis": ml_analysis,
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
        entity_id=vendor_id,
    )

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("legal_name"),
        "metrics": adjusted_metrics,
        "performance_trend": ml_analysis.get("trend")
        or await analyze_performance_trend(agent, vendor_id),
        "recommendations": await generate_vendor_recommendations(adjusted_metrics),
        "ml_analysis": ml_analysis,
    }


async def handle_get_vendor_scorecard(
    agent: VendorProcurementAgent,
    vendor_id: str,
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Generate comprehensive vendor scorecard.

    Returns detailed scorecard with visualizations.
    """
    agent.logger.info("Generating scorecard for vendor: %s", vendor_id)

    vendor = agent.vendors.get(vendor_id)
    if not vendor:
        raise ValueError(f"Vendor not found: {vendor_id}")

    # Get performance metrics
    performance = await handle_track_vendor_performance(
        agent,
        vendor_id,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
    )

    # Get contract history
    contracts = await get_vendor_contracts(agent, vendor_id)

    # Get recent issues
    recent_issues = await get_vendor_issues(agent, vendor_id)

    external_research = None
    external_adjustment: dict[str, Any] | None = None
    if agent.enable_vendor_research:
        external_research = await agent.research_vendor(
            vendor.get("legal_name", "vendor"), vendor.get("category", "general")
        )
        external_adjustment = score_vendor_research(external_research)

    # Calculate overall score
    overall_score = await calculate_overall_vendor_score(
        agent, vendor, external_adjustment=external_adjustment
    )

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.get("legal_name"),
        "overall_score": overall_score,
        "risk_score": vendor.get("risk_score"),
        "performance_metrics": performance.get("metrics"),
        "performance_trend": performance.get("performance_trend"),
        "contract_summary": {
            "active_contracts": len([c for c in contracts if c.get("status") == "Active"]),
            "total_value": sum(c.get("value", 0) for c in contracts),
            "expiring_soon": len([c for c in contracts if await is_expiring_soon(c)]),
        },
        "recent_issues": recent_issues,
        "recommendations": performance.get("recommendations"),
        "external_research": external_research,
        "external_research_adjustment": external_adjustment,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
