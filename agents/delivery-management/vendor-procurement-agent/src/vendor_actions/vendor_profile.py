"""Action handlers: get_vendor_profile, update_vendor_profile, list_vendor_profiles"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from vendor_utils import (
    matches_criteria,
    persist_vendor,
    publish_event,
    resolve_vendor,
)

if TYPE_CHECKING:
    from vendor_procurement_agent import VendorProcurementAgent


async def handle_get_vendor_profile(
    agent: VendorProcurementAgent,
    vendor_id: str,
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    vendor = await resolve_vendor(agent, vendor_id, tenant_id=tenant_id)
    if not vendor:
        raise ValueError(f"Vendor not found: {vendor_id}")
    return {
        "vendor": vendor,
        "correlation_id": correlation_id,
    }


async def handle_update_vendor_profile(
    agent: VendorProcurementAgent,
    vendor_id: str,
    updates: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    vendor = await resolve_vendor(agent, vendor_id, tenant_id=tenant_id)
    if not vendor:
        raise ValueError(f"Vendor not found: {vendor_id}")
    vendor.update(updates)
    vendor["updated_at"] = datetime.now(timezone.utc).isoformat()
    vendor.setdefault("updated_by", actor_id)
    await persist_vendor(agent, vendor, tenant_id=tenant_id)
    await publish_event(
        agent,
        "vendor.updated",
        payload={"vendor_id": vendor_id, "updates": updates},
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
        entity_id=vendor_id,
    )
    return {"vendor_id": vendor_id, "status": vendor.get("status"), "updates": updates}


async def handle_list_vendor_profiles(
    agent: VendorProcurementAgent,
    criteria: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    vendors = [
        vendor for vendor in agent.vendors.values() if await matches_criteria(vendor, criteria)
    ]
    return {
        "total_results": len(vendors),
        "vendors": vendors,
        "search_criteria": criteria,
        "tenant_id": tenant_id,
    }
