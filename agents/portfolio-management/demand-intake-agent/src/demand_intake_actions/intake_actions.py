"""Intake request action handlers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from demand_intake_utils import generate_demand_id, strip_duplicate_rationale

if TYPE_CHECKING:
    from demand_intake_agent import DemandIntakeAgent


async def submit_request(
    agent: DemandIntakeAgent,
    request_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Submit a new demand intake request.

    Returns demand ID and categorization results.
    """
    agent.logger.info("Processing new demand intake request")

    # Categorize the request
    category = await agent._categorize_request(request_data)

    # Check for duplicates
    duplicates = await agent._find_duplicates(
        request_data,
        tenant_id=tenant_id,
        include_rationale=agent.duplicate_resolution_enabled,
    )
    similar_requests = strip_duplicate_rationale(duplicates)

    # Generate demand ID
    demand_id = generate_demand_id()

    # Store the request
    demand_item = {
        "demand_id": demand_id,
        "title": request_data.get("title"),
        "description": request_data.get("description"),
        "business_objective": request_data.get("business_objective"),
        "category": category,
        "status": "Received",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": request_data.get("requester", "unknown"),
        "business_unit": request_data.get("business_unit", ""),
        "urgency": request_data.get("urgency", "Medium"),
        "source": request_data.get("source", "unknown"),
    }
    agent.demand_store.upsert(tenant_id, demand_id, demand_item)
    agent.vector_index.add(demand_id, agent._combine_text(demand_item), demand_item)
    agent.logger.info("Created demand request: %s", demand_id)

    await agent.notification_service.send(
        {
            "recipient": demand_item.get("created_by"),
            "subject": f"Demand request {demand_id} received",
            "body": (
                "Your request has been received and routed for screening. " f"Category: {category}."
            ),
            "metadata": {"demand_id": demand_id, "tenant_id": tenant_id},
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    await agent._publish_demand_created(
        demand_item,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    response: dict[str, Any] = {
        "demand_id": demand_id,
        "category": category,
        "status": "Received",
        "duplicates_found": len(duplicates) > 0,
        "similar_requests": similar_requests[:5],  # Top 5 most similar
        "next_steps": "Request is in screening queue. You will be notified of status updates.",
    }
    if agent.duplicate_resolution_enabled:
        response["duplicate_candidates"] = duplicates[:5]
    return response


async def check_duplicates(
    agent: DemandIntakeAgent,
    request_data: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """Check for duplicate requests without submitting.

    Returns list of similar requests.
    """
    duplicates = await agent._find_duplicates(
        request_data,
        tenant_id=tenant_id,
        include_rationale=agent.duplicate_resolution_enabled,
    )
    similar_requests = strip_duplicate_rationale(duplicates)

    response: dict[str, Any] = {
        "duplicates_found": len(duplicates) > 0,
        "similar_requests": similar_requests,
    }
    if agent.duplicate_resolution_enabled:
        response["duplicate_candidates"] = duplicates
    return response
