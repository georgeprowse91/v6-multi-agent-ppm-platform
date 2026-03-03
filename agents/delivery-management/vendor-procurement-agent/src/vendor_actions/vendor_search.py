"""Action handlers: search_vendors, get_procurement_status"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vendor_utils import matches_criteria

if TYPE_CHECKING:
    from vendor_procurement_agent import VendorProcurementAgent


async def handle_search_vendors(
    agent: VendorProcurementAgent,
    criteria: dict[str, Any],
) -> dict[str, Any]:
    """
    Search vendors by criteria.

    Returns list of matching vendors.
    """
    agent.logger.info("Searching vendors")

    # Filter vendors
    matching_vendors = []
    for vendor_id, vendor in agent.vendors.items():
        if await matches_criteria(vendor, criteria):
            matching_vendors.append(
                {
                    "vendor_id": vendor_id,
                    "legal_name": vendor.get("legal_name"),
                    "category": vendor.get("category"),
                    "risk_score": vendor.get("risk_score"),
                    "performance_rating": vendor.get("performance_metrics", {}).get(
                        "quality_rating", 0
                    ),
                    "status": vendor.get("status"),
                }
            )

    # Sort by relevance
    if agent.enable_ai_vendor_ranking:
        sorted_vendors = agent.ml_service.rank_vendors(matching_vendors)
    else:
        sorted_vendors = sorted(
            matching_vendors,
            key=lambda x: (x.get("performance_rating", 0), -x.get("risk_score", 100)),
            reverse=True,
        )

    return {
        "total_results": len(sorted_vendors),
        "vendors": sorted_vendors,
        "search_criteria": criteria,
    }


async def handle_get_procurement_status(
    agent: VendorProcurementAgent,
    request_id: str,
) -> dict[str, Any]:
    """
    Get procurement request status.

    Returns detailed status information.
    """
    agent.logger.info("Getting procurement status for request: %s", request_id)

    request = agent.procurement_requests.get(request_id)
    if not request:
        raise ValueError(f"Procurement request not found: {request_id}")

    # Find related RFP
    related_rfp = None
    for rfp_id, rfp in agent.rfps.items():
        if rfp.get("request_id") == request_id:
            related_rfp = rfp
            break

    # Find related PO
    related_po = None
    if related_rfp and related_rfp.get("selected_vendor_id"):
        for po_number, po in agent.purchase_orders.items():
            if po.get("vendor_id") == related_rfp.get("selected_vendor_id"):
                related_po = po
                break

    return {
        "request_id": request_id,
        "status": request.get("status"),
        "requester": request.get("requester"),
        "description": request.get("description"),
        "estimated_cost": request.get("estimated_cost"),
        "rfp_status": related_rfp.get("status") if related_rfp else None,
        "rfp_id": related_rfp.get("rfp_id") if related_rfp else None,
        "proposals_received": (
            len(related_rfp.get("proposals_received", [])) if related_rfp else 0
        ),
        "selected_vendor": related_rfp.get("selected_vendor_id") if related_rfp else None,
        "po_number": related_po.get("po_number") if related_po else None,
        "po_status": related_po.get("status") if related_po else None,
    }
