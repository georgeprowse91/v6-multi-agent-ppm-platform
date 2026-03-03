"""Action handler: research_vendor"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vendor_procurement_agent import VendorProcurementAgent


async def handle_research_vendor(
    agent: VendorProcurementAgent,
    *,
    vendor_id: str | None,
    vendor_name: str | None,
    domain: str | None,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    vendor = agent.vendors.get(vendor_id) if vendor_id else None
    resolved_name = vendor_name or (vendor.get("legal_name") if vendor else None)
    resolved_domain = domain or (vendor.get("category") if vendor else "general")
    if not resolved_name:
        raise ValueError("Vendor name is required for research")

    try:
        research = await agent.research_vendor(resolved_name, resolved_domain)
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        agent.logger.warning(
            "Vendor research failed",
            extra={"error": str(exc), "vendor_id": vendor_id, "correlation_id": correlation_id},
        )
        return {
            "vendor_id": vendor_id,
            "vendor_name": resolved_name,
            "summary": "",
            "insights": [],
            "sources": [],
            "used_external_research": False,
            "notice": "External vendor research failed; internal evaluation is unchanged.",
            "correlation_id": correlation_id,
        }

    if vendor_id and vendor:
        vendor["external_research"] = research
        agent.vendor_store.upsert(tenant_id, vendor_id, vendor)

    return {
        "vendor_id": vendor_id,
        "vendor_name": resolved_name,
        **research,
        "notice": None,
        "correlation_id": correlation_id,
    }
