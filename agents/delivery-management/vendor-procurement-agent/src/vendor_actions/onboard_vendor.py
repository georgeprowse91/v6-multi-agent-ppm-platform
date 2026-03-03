"""Action handler: onboard_vendor"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from vendor_utils import (
    calculate_vendor_risk,
    evaluate_compliance_checks,
    generate_vendor_id,
    initiate_mitigation_workflow,
    persist_vendor,
    publish_event,
    run_compliance_checks,
    validate_vendor_record,
)

if TYPE_CHECKING:
    from vendor_procurement_agent import VendorProcurementAgent


async def handle_onboard_vendor(
    agent: VendorProcurementAgent,
    vendor_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Onboard a new vendor with compliance checks.

    Returns vendor ID and onboarding status.
    """
    agent.logger.info("Onboarding vendor: %s", vendor_data.get("legal_name"))

    # Generate vendor ID
    vendor_id = await generate_vendor_id()

    # Run compliance checks
    compliance_checks = await run_compliance_checks(agent, vendor_data)

    # Calculate initial risk score
    risk_score = await calculate_vendor_risk(agent, vendor_data, compliance_checks)
    compliance_decision = await evaluate_compliance_checks(
        agent, compliance_checks, risk_score=risk_score
    )

    created_at = datetime.now(timezone.utc).isoformat()
    # Create vendor profile
    vendor = {
        "vendor_id": vendor_id,
        "legal_name": vendor_data.get("legal_name"),
        "tax_id": vendor_data.get("tax_id"),
        "contact_email": vendor_data.get("contact_email"),
        "contact_phone": vendor_data.get("contact_phone"),
        "address": vendor_data.get("address", {}),
        "category": vendor_data.get("category"),
        "certifications": vendor_data.get("certifications", []),
        "diversity_classification": vendor_data.get("diversity_classification"),
        "classification": vendor_data.get("classification", "internal"),
        "risk_score": risk_score,
        "compliance_checks": compliance_checks,
        "compliance_status": compliance_decision["status"],
        "status": compliance_decision["status"],
        "created_at": created_at,
        "created_by": vendor_data.get("requester", actor_id),
        "performance_metrics": {
            "total_contracts": 0,
            "total_spend": 0,
            "on_time_delivery_rate": 0,
            "quality_rating": 0,
            "compliance_rating": 0,
        },
    }

    validation = await validate_vendor_record(
        agent,
        vendor=vendor,
        tenant_id=tenant_id,
    )
    if not validation["is_valid"]:
        raise ValueError("Vendor schema validation failed")

    await persist_vendor(agent, vendor, tenant_id=tenant_id)
    await agent.ml_service.train_models(list(agent.vendors.values()))
    connector_results = agent.procurement_connector.sync_vendor(vendor)
    await publish_event(
        agent,
        "vendor.onboarded",
        payload={"vendor": vendor, "connector_results": connector_results},
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
        entity_id=vendor_id,
    )
    if compliance_decision["status"] in {"blocked", "flagged"}:
        await publish_event(
            agent,
            "vendor.compliance_failed",
            payload={
                "vendor_id": vendor_id,
                "compliance_status": compliance_decision["status"],
                "checks": compliance_checks,
                "risk_score": risk_score,
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=vendor_id,
        )
        await initiate_mitigation_workflow(
            agent,
            vendor=vendor,
            reason=compliance_decision.get("reason", "Compliance checks failed"),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

    return {
        "vendor_id": vendor_id,
        "status": vendor["status"],
        "legal_name": vendor["legal_name"],
        "risk_score": risk_score,
        "compliance_checks": compliance_checks,
        "data_quality": validation,
        "compliance_status": vendor["compliance_status"],
        "next_steps": compliance_decision.get("next_steps")
        or "Vendor pending approval. Submit required documentation.",
    }
