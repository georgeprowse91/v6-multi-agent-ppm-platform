"""Event handlers for the VendorProcurementAgent event bus."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from vendor_utils import (
    initiate_mitigation_workflow,
    persist_vendor,
)

if TYPE_CHECKING:
    from vendor_procurement_agent import VendorProcurementAgent


def register_event_handlers(agent: VendorProcurementAgent) -> None:
    """Wire up all event-bus handlers for *agent*."""
    agent.event_bus.register_handler("delivery.delayed", _make_delivery_delayed(agent))
    agent.event_bus.register_handler("contract.signed", _make_contract_signed(agent))
    agent.event_bus.register_handler("vendor.flagged", _make_vendor_flagged(agent))
    agent.event_bus.register_handler("risk.alert", _make_risk_alert(agent))
    agent.event_bus.register_handler("compliance.violation", _make_compliance_violation(agent))
    agent.event_bus.register_handler("sanctions.hit", _make_sanctions_hit(agent))


# Each factory returns an async handler closure that captures *agent*.


def _make_delivery_delayed(agent: VendorProcurementAgent):
    async def _handle(event: dict[str, Any]) -> None:
        payload = event.get("payload", {})
        vendor_id = payload.get("vendor_id")
        if not vendor_id or vendor_id not in agent.vendors:
            return
        vendor = agent.vendors[vendor_id]
        metrics = vendor.get("performance_metrics", {})
        metrics["delivery_timeliness"] = max(0, metrics.get("delivery_timeliness", 100) - 5)
        metrics["on_time_delivery_rate"] = metrics["delivery_timeliness"]
        vendor["performance_metrics"] = metrics
        await persist_vendor(agent, vendor, tenant_id=event.get("tenant_id", "unknown"))
    return _handle


def _make_contract_signed(agent: VendorProcurementAgent):
    async def _handle(event: dict[str, Any]) -> None:
        payload = event.get("payload", {})
        contract_id = payload.get("contract_id")
        if contract_id and contract_id in agent.contracts:
            contract = agent.contracts[contract_id]
            contract["status"] = "Active"
            tenant_id = event.get("tenant_id", "unknown")
            agent.contract_store.upsert(tenant_id, contract_id, contract)
            if agent.db_service:
                await agent.db_service.store("contracts", contract_id, contract)
    return _handle


def _make_vendor_flagged(agent: VendorProcurementAgent):
    async def _handle(event: dict[str, Any]) -> None:
        payload = event.get("payload", {})
        vendor_id = payload.get("vendor_id")
        if not vendor_id or vendor_id not in agent.vendors:
            return
        vendor = agent.vendors[vendor_id]
        vendor["status"] = "flagged"
        vendor["risk_score"] = min(100, vendor.get("risk_score", 50) + 20)
        vendor["compliance_status"] = "flagged"
        await persist_vendor(agent, vendor, tenant_id=event.get("tenant_id", "unknown"))
        await initiate_mitigation_workflow(
            agent,
            vendor=vendor,
            reason=payload.get("reason", "Vendor flagged via risk event"),
            tenant_id=event.get("tenant_id", "unknown"),
            correlation_id=event.get("correlation_id", str(uuid.uuid4())),
        )
    return _handle


def _make_risk_alert(agent: VendorProcurementAgent):
    async def _handle(event: dict[str, Any]) -> None:
        payload = event.get("payload", {})
        vendor_id = payload.get("vendor_id")
        if not vendor_id or vendor_id not in agent.vendors:
            return
        vendor = agent.vendors[vendor_id]
        vendor["risk_score"] = min(100, payload.get("risk_score", vendor.get("risk_score", 50)))
        vendor["status"] = "flagged"
        vendor["compliance_status"] = "flagged"
        await persist_vendor(agent, vendor, tenant_id=event.get("tenant_id", "unknown"))
        await initiate_mitigation_workflow(
            agent,
            vendor=vendor,
            reason=payload.get("reason", "Risk alert received"),
            tenant_id=event.get("tenant_id", "unknown"),
            correlation_id=event.get("correlation_id", str(uuid.uuid4())),
        )
    return _handle


def _make_compliance_violation(agent: VendorProcurementAgent):
    async def _handle(event: dict[str, Any]) -> None:
        payload = event.get("payload", {})
        vendor_id = payload.get("vendor_id")
        if not vendor_id or vendor_id not in agent.vendors:
            return
        vendor = agent.vendors[vendor_id]
        vendor["status"] = (
            "blocked" if agent.compliance_policy.get("block_on_fail", True) else "flagged"
        )
        vendor["compliance_status"] = "failed"
        await persist_vendor(agent, vendor, tenant_id=event.get("tenant_id", "unknown"))
        await initiate_mitigation_workflow(
            agent,
            vendor=vendor,
            reason=payload.get("reason", "Compliance violation received"),
            tenant_id=event.get("tenant_id", "unknown"),
            correlation_id=event.get("correlation_id", str(uuid.uuid4())),
        )
    return _handle


def _make_sanctions_hit(agent: VendorProcurementAgent):
    async def _handle(event: dict[str, Any]) -> None:
        payload = event.get("payload", {})
        vendor_id = payload.get("vendor_id")
        if not vendor_id or vendor_id not in agent.vendors:
            return
        vendor = agent.vendors[vendor_id]
        vendor["status"] = "blocked"
        vendor["compliance_status"] = "sanctions_hit"
        vendor["risk_score"] = min(100, vendor.get("risk_score", 50) + 30)
        await persist_vendor(agent, vendor, tenant_id=event.get("tenant_id", "unknown"))
        await initiate_mitigation_workflow(
            agent,
            vendor=vendor,
            reason=payload.get("reason", "Sanctions list hit"),
            tenant_id=event.get("tenant_id", "unknown"),
            correlation_id=event.get("correlation_id", str(uuid.uuid4())),
        )
    return _handle
