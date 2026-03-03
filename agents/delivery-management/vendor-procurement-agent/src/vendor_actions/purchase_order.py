"""Action handler: create_purchase_order"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from vendor_utils import (
    calculate_po_total,
    generate_po_number,
    publish_event,
)

if TYPE_CHECKING:
    from vendor_procurement_agent import VendorProcurementAgent


async def handle_create_purchase_order(
    agent: VendorProcurementAgent,
    po_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Create purchase order from approved procurement.

    Returns PO number and approval status.
    """
    agent.logger.info("Creating purchase order for vendor: %s", po_data.get("vendor_id"))

    # Generate PO number
    po_number = await generate_po_number()

    total_value = await calculate_po_total(po_data.get("items", []))
    approval_required = total_value > agent.procurement_threshold
    approval_payload = None
    if approval_required:
        approval_payload = await agent.approval_agent.process(
            {
                "request_type": "procurement",
                "request_id": po_number,
                "requester": po_data.get("requester", actor_id),
                "details": {
                    "amount": total_value,
                    "description": "Purchase order approval",
                    "justification": po_data.get("justification"),
                    "urgency": po_data.get("urgency", "medium"),
                },
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
            }
        )

    # Create PO
    purchase_order_status = "Pending Approval" if approval_required else "Released"
    purchase_order = {
        "po_number": po_number,
        "vendor_id": po_data.get("vendor_id"),
        "contract_id": po_data.get("contract_id"),
        "project_id": po_data.get("project_id"),
        "items": po_data.get("items", []),
        "total_value": total_value,
        "currency": po_data.get("currency", agent.default_currency),
        "delivery_schedule": po_data.get("delivery_schedule"),
        "delivery_address": po_data.get("delivery_address"),
        "payment_terms": po_data.get("payment_terms"),
        "approval_history": [],
        "approval": approval_payload,
        "status": purchase_order_status,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store PO
    agent.purchase_orders[po_number] = purchase_order

    if agent.db_service:
        await agent.db_service.store("purchase_orders", po_number, purchase_order)
    connector_results = []
    if purchase_order_status == "Released":
        connector_results = agent.procurement_connector.release_purchase_order(purchase_order)
        await publish_event(
            agent,
            "po.released",
            payload={"purchase_order": purchase_order, "connector_results": connector_results},
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=po_number,
        )

    return {
        "po_number": po_number,
        "vendor_id": purchase_order["vendor_id"],
        "total_value": purchase_order["total_value"],
        "status": purchase_order["status"],
        "items_count": len(purchase_order["items"]),
        "approval": approval_payload,
        "next_steps": (
            "Await approval before release to vendor."
            if approval_required
            else "Release to vendor."
        ),
    }
