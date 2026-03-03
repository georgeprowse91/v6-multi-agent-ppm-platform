"""Action handlers: create_contract, sign_contract"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from agents.common.connector_integration import DocumentMetadata

from vendor_utils import (
    extract_contract_clauses,
    generate_contract_id,
    publish_event,
    select_contract_template,
)

if TYPE_CHECKING:
    from vendor_procurement_agent import VendorProcurementAgent


async def handle_create_contract(
    agent: VendorProcurementAgent,
    contract_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Create contract from template.

    Returns contract ID and terms summary.
    """
    agent.logger.info("Creating contract with vendor: %s", contract_data.get("vendor_id"))

    # Generate contract ID
    contract_id = await generate_contract_id()

    # Select contract template
    await select_contract_template(contract_data.get("type", "standard"))

    # Extract key clauses
    key_clauses = await extract_contract_clauses(agent, contract_data)

    # Create contract
    contract = {
        "contract_id": contract_id,
        "vendor_id": contract_data.get("vendor_id"),
        "project_id": contract_data.get("project_id"),
        "type": contract_data.get("type", "standard"),
        "start_date": contract_data.get("start_date"),
        "end_date": contract_data.get("end_date"),
        "value": contract_data.get("value"),
        "currency": contract_data.get("currency", agent.default_currency),
        "terms": contract_data.get("terms", {}),
        "obligations": contract_data.get("obligations", []),
        "slas": contract_data.get("slas", []),
        "renewal_options": contract_data.get("renewal_options"),
        "key_clauses": key_clauses,
        "attachments": contract_data.get("attachments", []),
        "status": "Draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": contract_data.get("created_by", actor_id),
    }

    signature_workflow = {
        "status": "Pending Signatures",
        "method": "manual",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "signatories": contract_data.get("signatories", []),
    }
    contract["signature_workflow"] = signature_workflow

    contract_content = contract_data.get("content") or contract_data.get("document_content")
    if not contract_content:
        contract_content = (
            f"Contract {contract_id} between {contract.get('vendor_id')} "
            f"for {contract.get('project_id')} with value {contract.get('value')} "
            f"{contract.get('currency')} and term {contract.get('start_date')} "
            f"to {contract.get('end_date')}."
        )

    contract_document = None
    if agent.document_service:
        contract_document = await agent.document_service.publish_document(
            document_content=contract_content,
            metadata=DocumentMetadata(
                title=f"Contract {contract_id}",
                description=f"Procurement contract for vendor {contract.get('vendor_id')}",
                tags=["contract", contract.get("type", "standard")],
                owner=contract.get("created_by", ""),
            ),
            folder_path="Procurement/Contracts",
        )
    contract["document"] = contract_document

    # Store contract
    agent.contracts[contract_id] = contract
    agent.contract_store.upsert(tenant_id, contract_id, contract)

    if agent.db_service:
        await agent.db_service.store("contracts", contract_id, contract)
    connector_results = agent.procurement_connector.create_contract(contract)
    await publish_event(
        agent,
        "contract.created",
        payload={"contract": contract, "connector_results": connector_results},
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
        entity_id=contract_id,
    )
    if contract_data.get("status") in {"Signed", "Active"}:
        contract["status"] = "Active"
        await publish_event(
            agent,
            "contract.signed",
            payload={"contract_id": contract_id, "vendor_id": contract.get("vendor_id")},
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
            entity_id=contract_id,
        )

    return {
        "contract_id": contract_id,
        "vendor_id": contract["vendor_id"],
        "type": contract["type"],
        "value": contract["value"],
        "start_date": contract["start_date"],
        "end_date": contract["end_date"],
        "status": "Draft",
        "signature_status": signature_workflow["status"],
        "next_steps": "Collect manual signatures and upload signed contract",
    }


async def handle_sign_contract(
    agent: VendorProcurementAgent,
    contract_id: str,
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    contract = agent.contracts.get(contract_id)
    if not contract:
        raise ValueError(f"Contract not found: {contract_id}")
    contract["status"] = "Active"
    contract["signed_at"] = datetime.now(timezone.utc).isoformat()
    agent.contract_store.upsert(tenant_id, contract_id, contract)
    if agent.db_service:
        await agent.db_service.store("contracts", contract_id, contract)
    await publish_event(
        agent,
        "contract.signed",
        payload={"contract_id": contract_id, "vendor_id": contract.get("vendor_id")},
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
        entity_id=contract_id,
    )
    return {"contract_id": contract_id, "status": contract["status"]}
