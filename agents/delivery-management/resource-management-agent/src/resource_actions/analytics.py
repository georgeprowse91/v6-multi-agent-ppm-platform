"""Action handlers: get_availability, get_utilization, identify_conflicts."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from resource_actions.helpers import (
    calculate_day_availability,
    generate_conflict_recommendations,
)

if TYPE_CHECKING:
    from resource_capacity_agent import ResourceCapacityAgent


async def handle_get_availability(
    agent: ResourceCapacityAgent,
    resource_id: str,
    date_range: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Get resource availability for a date range.

    Returns availability calendar.
    """
    agent.logger.info("Getting availability for resource: %s", resource_id)

    resource = agent.resource_pool.get(resource_id)
    if not resource:
        resource = agent.resource_store.get(tenant_id, resource_id)
        if resource:
            agent.resource_pool[resource_id] = resource
    if not resource:
        raise ValueError(f"Resource not found: {resource_id}")

    calendar = agent.capacity_calendar.get(resource_id, {})
    if not calendar:
        calendar = agent.calendar_store.get(tenant_id, resource_id) or {}
        if calendar:
            agent.capacity_calendar[resource_id] = calendar

    allocations = agent._load_allocations(resource_id)

    start_date_str = date_range.get("start_date")
    end_date_str = date_range.get("end_date")
    assert isinstance(start_date_str, str), "start_date must be a string"
    assert isinstance(end_date_str, str), "end_date must be a string"
    start_date = datetime.fromisoformat(start_date_str)
    end_date = datetime.fromisoformat(end_date_str)

    # Calculate availability for each day in range
    availability_by_day = []
    current_date = start_date

    while current_date <= end_date:
        day_availability = await calculate_day_availability(
            agent, resource_id, current_date, calendar, allocations
        )
        availability_by_day.append(day_availability)
        current_date += timedelta(days=1)

    return {
        "resource_id": resource_id,
        "resource_name": resource.get("name"),
        "date_range": date_range,
        "availability_by_day": availability_by_day,
        "average_availability": (
            sum(d.get("available_hours", 0) for d in availability_by_day) / len(availability_by_day)
            if availability_by_day
            else 0
        ),
    }


async def handle_get_utilization(
    agent: ResourceCapacityAgent,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """
    Get utilization metrics.

    Returns utilization data and trends.
    """
    agent.logger.info("Getting utilization metrics")

    # Calculate utilization for all resources
    utilization_data = []

    for resource_id, resource in agent.resource_pool.items():
        utilization = await agent._calculate_resource_utilization(
            resource_id, filters.get("risk_data")
        )
        utilization_data.append(
            {
                "resource_id": resource_id,
                "resource_name": resource.get("name"),
                "role": resource.get("role"),
                "utilization": utilization,
                "status": await agent._get_utilization_status(utilization),
            }
        )

    # Calculate aggregate metrics
    average_utilization = (
        sum(u["utilization"] for u in utilization_data) / len(utilization_data)
        if utilization_data
        else 0
    )

    over_allocated = [u for u in utilization_data if u["utilization"] > 1.0]
    under_utilized = [u for u in utilization_data if u["utilization"] < 0.5]

    result = {
        "total_resources": len(utilization_data),
        "average_utilization": average_utilization,
        "target_utilization": agent.utilization_target,
        "utilization_variance": average_utilization - agent.utilization_target,
        "over_allocated_count": len(over_allocated),
        "under_utilized_count": len(under_utilized),
        "over_allocated_resources": over_allocated,
        "under_utilized_resources": under_utilized,
        "utilization_by_resource": utilization_data,
    }
    if agent.analytics_client:
        agent.analytics_client.record_metric("utilization.average", average_utilization)
        agent.analytics_client.record_metric("utilization.over_allocated", len(over_allocated))
        agent.analytics_client.record_metric("utilization.under_utilized", len(under_utilized))
    return result


async def handle_identify_conflicts(
    agent: ResourceCapacityAgent,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """
    Identify resource allocation conflicts.

    Returns conflicts and resolution recommendations.
    """
    agent.logger.info("Identifying resource conflicts")

    conflicts = []

    for resource_id in agent.resource_pool.keys():
        resource_allocations = agent._load_allocations(resource_id)
        # Check for overlapping allocations
        for i, alloc1 in enumerate(resource_allocations):
            for alloc2 in resource_allocations[i + 1 :]:
                from resource_actions.helpers import check_allocation_overlap

                overlap = await check_allocation_overlap(alloc1, alloc2)

                if overlap.get("has_overlap"):
                    # Calculate over-allocation
                    total_allocation = alloc1.get("allocation_percentage", 0) + alloc2.get(
                        "allocation_percentage", 0
                    )

                    if total_allocation > 100:
                        conflicts.append(
                            {
                                "resource_id": resource_id,
                                "resource_name": agent.resource_pool.get(resource_id, {}).get(
                                    "name"
                                ),
                                "allocation_1": alloc1,
                                "allocation_2": alloc2,
                                "overlap_period": overlap.get("period"),
                                "over_allocation_percentage": total_allocation - 100,
                                "severity": "high" if total_allocation > 150 else "medium",
                            }
                        )

    # Generate resolution recommendations
    recommendations = await generate_conflict_recommendations(conflicts)

    return {
        "total_conflicts": len(conflicts),
        "conflicts": conflicts,
        "recommendations": recommendations,
    }
