"""Action handlers: upload_evidence, list_evidence, get_evidence"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from agents.common.connector_integration import DocumentMetadata

from compliance_utils import generate_evidence_id

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


async def handle_upload_evidence(
    agent: ComplianceRegulatoryAgent,
    control_id: str,
    evidence_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """
    Upload evidence for control.

    Returns evidence ID and confirmation.
    """
    agent.logger.info("Uploading evidence for control: %s", control_id)

    control = agent.control_registry.get(control_id)
    if not control:
        raise ValueError(f"Control not found: {control_id}")

    # Generate evidence ID
    evidence_id = await generate_evidence_id()

    # Create evidence record
    evidence_record = {
        "evidence_id": evidence_id,
        "control_id": control_id,
        "file_name": evidence_data.get("file_name"),
        "file_type": evidence_data.get("file_type"),
        "file_url": evidence_data.get("file_url"),
        "description": evidence_data.get("description"),
        "uploaded_by": evidence_data.get("uploaded_by", "unknown"),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "classification": evidence_data.get("classification", "confidential"),
    }

    # Store evidence
    if control_id not in agent.evidence:
        agent.evidence[control_id] = []
    agent.evidence[control_id].append(evidence_record)
    agent.evidence_store.upsert(tenant_id, evidence_id, evidence_record)

    # Update project mapping
    for project_id, mapping in agent.compliance_mappings.items():
        if control_id in mapping.get("control_status", {}):
            mapping["control_status"][control_id]["evidence_uploaded"] = True

    # Persist to database
    await agent.db_service.store("evidence", evidence_id, evidence_record)

    # Upload evidence document to SharePoint with security classification
    evidence_content = evidence_data.get("content", f"Evidence for control {control_id}")
    doc_metadata = DocumentMetadata(
        title=evidence_record["file_name"] or f"Evidence-{evidence_id}",
        description=evidence_record.get("description", ""),
        classification=evidence_record.get("classification", "confidential"),
        tags=["evidence", control_id, evidence_id],
        owner=evidence_record.get("uploaded_by", "compliance"),
        retention_days=2555,  # 7 years retention for compliance evidence
    )
    publish_result = await agent.document_service.publish_document(
        document_content=evidence_content,
        metadata=doc_metadata,
        folder_path=f"Compliance Evidence/{control_id}",
    )
    evidence_record["storage_url"] = publish_result.get("url")
    evidence_record["document_id"] = publish_result.get("document_id")

    return {
        "evidence_id": evidence_id,
        "control_id": control_id,
        "file_name": evidence_record["file_name"],
        "uploaded_at": evidence_record["uploaded_at"],
        "storage_url": evidence_record["file_url"],
    }


async def handle_list_evidence(
    agent: ComplianceRegulatoryAgent, filters: dict[str, Any]
) -> dict[str, Any]:
    records = await agent.db_service.query("evidence", filters=filters, limit=200)
    return {"count": len(records), "evidence": records}


async def handle_get_evidence(
    agent: ComplianceRegulatoryAgent, evidence_id: str | None
) -> dict[str, Any]:
    if not evidence_id:
        raise ValueError("evidence_id is required")
    record = await agent.db_service.retrieve("evidence", evidence_id)
    return {"evidence": record}
