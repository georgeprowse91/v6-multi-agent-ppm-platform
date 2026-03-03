"""Action handler for risk identification."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from agents.common.connector_integration import DocumentMetadata, GRCRisk

from risk_utils import (
    classify_risk_level,
    extract_risks_from_documents,
    generate_risk_id,
    initial_risk_assessment,
    map_rating_to_label,
    publish_risk_event,
    register_triggers,
    store_risk_dataset,
    train_risk_extractor,
    validate_risk_record,
)

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


async def identify_risk(
    agent: RiskManagementAgent,
    risk_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """
    Identify and capture a new risk.

    Returns risk ID and initial assessment.
    """
    agent.logger.info("Identifying risk: %s", risk_data.get("title"))

    # Generate risk ID
    risk_id = await generate_risk_id()

    # Extract risks from documents if provided
    documents = risk_data.get("documents", [])
    if documents:
        await train_risk_extractor(agent, documents)
    extracted_risks = await extract_risks_from_documents(agent, documents)

    # Perform initial classification and scoring
    initial_assessment_result = await initial_risk_assessment(risk_data)

    created_at = datetime.now(timezone.utc).isoformat()
    # Create risk entry
    risk = {
        "risk_id": risk_id,
        "project_id": risk_data.get("project_id"),
        "program_id": risk_data.get("program_id"),
        "portfolio_id": risk_data.get("portfolio_id"),
        "task_id": risk_data.get("task_id"),
        "title": risk_data.get("title"),
        "description": risk_data.get("description"),
        "category": risk_data.get("category"),
        "probability": initial_assessment_result.get("probability"),
        "impact": initial_assessment_result.get("impact"),
        "score": initial_assessment_result.get("score"),
        "proximity": risk_data.get("proximity", "medium_term"),
        "detectability": risk_data.get("detectability", "medium"),
        "owner": risk_data.get("owner") or "unassigned",
        "status": "open",
        "created_at": created_at,
        "created_by": risk_data.get("created_by", "unknown"),
        "triggers": risk_data.get("triggers", []),
        "mitigation_plan_id": None,
        "residual_risk": None,
        "classification": risk_data.get("classification", "internal"),
        "extracted_risks": extracted_risks,
    }

    validation = await validate_risk_record(agent, risk=risk, tenant_id=tenant_id)
    if not validation["is_valid"]:
        raise ValueError("Risk schema validation failed")

    # Store risk
    agent.risk_register[risk_id] = risk
    agent.risk_store.upsert(tenant_id, risk_id, risk)
    if risk.get("triggers"):
        await register_triggers(agent, risk_id, risk.get("triggers") or [])

    if agent.db_service:
        await agent.db_service.store("risks", risk_id, risk)
    await store_risk_dataset(agent, "risks", [risk], domain="risk_register")
    await publish_risk_event(
        agent,
        "risk.identified",
        {
            "risk_id": risk_id,
            "title": risk.get("title"),
            "category": risk.get("category"),
            "score": risk.get("score"),
            "status": risk.get("status"),
        },
    )
    grc_sync = None
    if agent.grc_service:
        grc_risk = GRCRisk(
            risk_id=risk_id,
            title=risk["title"],
            description=risk["description"],
            category=risk["category"],
            likelihood=map_rating_to_label(risk.get("probability")),
            impact=map_rating_to_label(risk.get("impact")),
            status=risk.get("status", "open"),
            owner=risk.get("owner") or "",
            mitigation_plan=risk.get("mitigation_plan_id") or "",
        )
        grc_sync = await agent.grc_service.sync_risk(grc_risk)
        risk["grc_sync"] = grc_sync

    document_results = []
    if agent.document_service and risk_data.get("documents"):
        for index, document in enumerate(risk_data.get("documents", []), start=1):
            if isinstance(document, dict):
                content = str(document.get("content") or document.get("text") or document)
                title = document.get("title") or f"{risk['title']} Document {index}"
            else:
                content = str(document)
                title = f"{risk['title']} Document {index}"
            metadata = DocumentMetadata(
                title=title,
                description=f"Risk document for {risk['title']}",
                classification=risk.get("classification", "internal"),
                tags=[risk.get("category", "risk"), "risk-register"],
                owner=risk.get("owner") or "",
            )
            result = await agent.document_service.publish_document(
                document_content=content,
                metadata=metadata,
                folder_path="Risk Management",
            )
            document_results.append(result)
        risk["document_refs"] = document_results
    await publish_risk_event(
        agent,
        "risk.identified",
        {"risk_id": risk_id, "title": risk["title"], "category": risk["category"]},
    )

    return {
        "risk_id": risk_id,
        "title": risk["title"],
        "category": risk["category"],
        "initial_score": risk["score"],
        "probability": risk["probability"],
        "impact": risk["impact"],
        "risk_level": await classify_risk_level(agent, risk["score"]),
        "extracted_risks": extracted_risks,
        "data_quality": validation,
        "grc_sync": grc_sync,
        "documents": document_results,
        "next_steps": "Create mitigation plan for high-priority risks",
    }
