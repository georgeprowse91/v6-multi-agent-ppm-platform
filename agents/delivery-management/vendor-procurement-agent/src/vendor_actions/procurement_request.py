"""Action handler: create_procurement_request"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from vendor_utils import (
    categorize_procurement_request,
    check_budget_availability,
    determine_approval_path,
    generate_request_id,
    suggest_vendors,
)

if TYPE_CHECKING:
    from vendor_procurement_agent import VendorProcurementAgent


async def handle_create_procurement_request(
    agent: VendorProcurementAgent,
    request_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Create a new procurement request.

    Returns request ID and workflow status.
    """
    agent.logger.info("Creating procurement request: %s", request_data.get("description"))

    # Generate request ID
    request_id = await generate_request_id()

    # Categorize request
    category = await categorize_procurement_request(agent, request_data)

    # Check budget availability
    budget_check = await check_budget_availability(agent, request_data)

    # Suggest preferred vendors
    suggested_vendors = await suggest_vendors(agent, category, request_data)

    # Determine approval path
    approval_path = await determine_approval_path(agent, request_data.get("estimated_cost", 0))

    approval_required = request_data.get("estimated_cost", 0) > agent.procurement_threshold
    approval_payload = None
    if approval_required:
        approval_payload = await agent.approval_agent.process(
            {
                "request_type": "procurement",
                "request_id": request_id,
                "requester": request_data.get("requester", actor_id),
                "details": {
                    "amount": request_data.get("estimated_cost", 0),
                    "description": request_data.get("description"),
                    "justification": request_data.get("justification"),
                    "urgency": request_data.get("urgency", "medium"),
                },
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
            }
        )

    # Create procurement request
    request = {
        "request_id": request_id,
        "requester": request_data.get("requester"),
        "project_id": request_data.get("project_id"),
        "program_id": request_data.get("program_id"),
        "description": request_data.get("description"),
        "quantity": request_data.get("quantity", 1),
        "estimated_cost": request_data.get("estimated_cost"),
        "currency": request_data.get("currency", agent.default_currency),
        "required_date": request_data.get("required_date"),
        "justification": request_data.get("justification"),
        "category": category,
        "suggested_vendors": suggested_vendors,
        "budget_available": budget_check.get("available", False),
        "approval_path": approval_path,
        "status": "Pending Approval" if approval_required else "Draft",
        "approval": approval_payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store request
    agent.procurement_requests[request_id] = request

    if agent.db_service:
        await agent.db_service.store("procurement_requests", request_id, request)

    return {
        "request_id": request_id,
        "status": request["status"],
        "category": category,
        "estimated_cost": request["estimated_cost"],
        "budget_available": budget_check.get("available", False),
        "suggested_vendors": suggested_vendors,
        "approval_required": approval_required,
        "approval": approval_payload,
        "next_steps": (
            "Await approvals before generating RFP"
            if approval_required
            else "Review suggested vendors or generate RFP"
        ),
    }
