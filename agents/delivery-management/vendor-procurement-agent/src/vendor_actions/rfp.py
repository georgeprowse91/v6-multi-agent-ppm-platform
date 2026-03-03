"""Action handlers: generate_rfp, submit_proposal, evaluate_proposals, select_vendor"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from agents.common.connector_integration import DocumentMetadata

from vendor_utils import (
    generate_proposal_id,
    generate_rfp_content,
    generate_rfp_id,
    persist_vendor,
    publish_event,
    score_proposal,
    select_rfp_template,
    select_vendors_to_invite,
)

if TYPE_CHECKING:
    from vendor_procurement_agent import VendorProcurementAgent


async def handle_generate_rfp(
    agent: VendorProcurementAgent,
    request_id: str,
    rfp_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Generate RFP from procurement request.

    Returns RFP ID and invitation details.
    """
    agent.logger.info("Generating RFP for request: %s", request_id)

    request = agent.procurement_requests.get(request_id)
    if not request:
        raise ValueError(f"Procurement request not found: {request_id}")

    # Generate RFP ID
    rfp_id = await generate_rfp_id()

    # Select RFP template based on category
    template = await select_rfp_template(
        agent,
        request.get("category"),
        template_id=rfp_data.get("template_id"),
    )

    # Generate RFP content
    rfp_content = await generate_rfp_content(agent, request, template, rfp_data)

    # Select vendors to invite
    invited_vendors = await select_vendors_to_invite(
        agent,
        request.get("category"),
        request.get("suggested_vendors", []),
        rfp_data.get("vendor_ids", []),
    )

    # Create RFP
    rfp = {
        "rfp_id": rfp_id,
        "request_id": request_id,
        "title": rfp_data.get("title", request.get("description")),
        "content": rfp_content,
        "requirements": rfp_data.get("requirements", []),
        "evaluation_criteria": rfp_data.get("evaluation_criteria", {}),
        "submission_deadline": rfp_data.get("submission_deadline"),
        "invited_vendors": invited_vendors,
        "proposals_received": [],
        "status": "Published",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    rfp_document = None
    if agent.document_service:
        rfp_document = await agent.document_service.publish_document(
            document_content=rfp_content,
            metadata=DocumentMetadata(
                title=f"RFP {rfp_id}: {rfp['title']}",
                description=f"RFP for procurement request {request_id}",
                tags=["rfp", request.get("category", "general")],
                owner=request.get("requester", ""),
            ),
            folder_path="Procurement/RFPs",
        )
    rfp["document"] = rfp_document

    # Store RFP
    agent.rfps[rfp_id] = rfp

    if agent.db_service:
        await agent.db_service.store("rfps", rfp_id, rfp)
    connector_results = agent.procurement_connector.publish_rfp(rfp)
    await publish_event(
        agent,
        "rfp.published",
        payload={
            "rfp": rfp,
            "connector_results": connector_results,
            "request_id": request_id,
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
        entity_id=rfp_id,
    )

    return {
        "rfp_id": rfp_id,
        "request_id": request_id,
        "title": rfp["title"],
        "submission_deadline": rfp["submission_deadline"],
        "invited_vendors": len(invited_vendors),
        "vendor_list": invited_vendors,
        "next_steps": "Wait for vendor proposals by submission deadline",
    }


async def handle_submit_proposal(
    agent: VendorProcurementAgent,
    rfp_id: str,
    vendor_id: str,
    proposal_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Submit vendor proposal for RFP.

    Returns proposal ID and submission confirmation.
    """
    agent.logger.info("Submitting proposal from vendor %s for RFP %s", vendor_id, rfp_id)

    rfp = agent.rfps.get(rfp_id)
    if not rfp:
        raise ValueError(f"RFP not found: {rfp_id}")

    # Generate proposal ID
    proposal_id = await generate_proposal_id()

    # Validate submission deadline
    deadline = datetime.fromisoformat(rfp.get("submission_deadline"))
    if datetime.now(timezone.utc) > deadline:
        raise ValueError("Submission deadline has passed")

    # Create proposal
    proposal = {
        "proposal_id": proposal_id,
        "rfp_id": rfp_id,
        "vendor_id": vendor_id,
        "pricing": proposal_data.get("pricing", {}),
        "delivery_schedule": proposal_data.get("delivery_schedule"),
        "terms": proposal_data.get("terms", {}),
        "technical_response": proposal_data.get("technical_response"),
        "attachments": proposal_data.get("attachments", []),
        "evaluation_score": None,  # Calculated during evaluation
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "Submitted",
    }

    # Store proposal
    agent.proposals[proposal_id] = proposal

    # Update RFP
    rfp["proposals_received"].append(proposal_id)

    if agent.db_service:
        await agent.db_service.store("proposals", proposal_id, proposal)
    connector_results = agent.procurement_connector.submit_proposal(proposal)
    await publish_event(
        agent,
        "proposal.submitted",
        payload={"proposal": proposal, "connector_results": connector_results},
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
        entity_id=proposal_id,
    )

    return {
        "proposal_id": proposal_id,
        "rfp_id": rfp_id,
        "vendor_id": vendor_id,
        "submitted_at": proposal["submitted_at"],
        "status": "Submitted",
        "next_steps": "Proposal will be evaluated after submission deadline",
    }


async def handle_evaluate_proposals(
    agent: VendorProcurementAgent,
    rfp_id: str,
    criteria: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate all proposals for an RFP.

    Returns evaluation results and vendor rankings.
    """
    agent.logger.info("Evaluating proposals for RFP: %s", rfp_id)

    rfp = agent.rfps.get(rfp_id)
    if not rfp:
        raise ValueError(f"RFP not found: {rfp_id}")

    proposal_ids = rfp.get("proposals_received", [])
    if len(proposal_ids) < agent.min_vendor_proposals:
        agent.logger.warning(
            "Only %s proposals received, minimum is %s",
            len(proposal_ids),
            agent.min_vendor_proposals,
        )

    # Get evaluation criteria with weights
    eval_criteria = criteria or rfp.get(
        "evaluation_criteria",
        {"cost": 0.40, "quality": 0.30, "delivery": 0.15, "risk": 0.10, "diversity": 0.05},
    )

    # Evaluate each proposal
    evaluated_proposals = []
    for proposal_id in proposal_ids:
        proposal = agent.proposals.get(proposal_id)
        if not proposal:
            continue

        # Calculate scores for each criterion
        scores = await score_proposal(agent, proposal, eval_criteria)

        # Calculate weighted total score
        total_score = sum(
            scores.get(criterion, 0) * weight for criterion, weight in eval_criteria.items()
        )

        # Update proposal with evaluation
        proposal["evaluation_score"] = total_score
        proposal["criterion_scores"] = scores

        evaluated_proposals.append(
            {
                "proposal_id": proposal_id,
                "vendor_id": proposal.get("vendor_id"),
                "total_score": total_score,
                "scores": scores,
                "pricing": proposal.get("pricing"),
            }
        )

    # Rank proposals by score
    ranked_proposals = sorted(evaluated_proposals, key=lambda x: x["total_score"], reverse=True)

    if agent.db_service:
        await agent.db_service.store(
            "rfp_evaluations",
            rfp_id,
            {
                "rfp_id": rfp_id,
                "criteria": eval_criteria,
                "rankings": ranked_proposals,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    return {
        "rfp_id": rfp_id,
        "proposals_evaluated": len(evaluated_proposals),
        "evaluation_criteria": eval_criteria,
        "rankings": ranked_proposals,
        "recommended_vendor": ranked_proposals[0] if ranked_proposals else None,
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
    }


async def handle_select_vendor(
    agent: VendorProcurementAgent,
    rfp_id: str,
    vendor_id: str,
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """
    Select vendor and finalize procurement.

    Returns selection confirmation and next steps.
    """
    agent.logger.info("Selecting vendor %s for RFP %s", vendor_id, rfp_id)

    rfp = agent.rfps.get(rfp_id)
    if not rfp:
        raise ValueError(f"RFP not found: {rfp_id}")

    # Find selected proposal
    selected_proposal = None
    for proposal_id in rfp.get("proposals_received", []):
        proposal = agent.proposals.get(proposal_id)
        if proposal and proposal.get("vendor_id") == vendor_id:
            selected_proposal = proposal
            break

    if not selected_proposal:
        raise ValueError(f"No proposal found from vendor {vendor_id}")

    # Document selection rationale

    # Update RFP and proposal status
    rfp["status"] = "Vendor Selected"
    rfp["selected_vendor_id"] = vendor_id
    rfp["selected_proposal_id"] = selected_proposal.get("proposal_id")
    selected_proposal["status"] = "Accepted"

    if agent.db_service:
        await agent.db_service.store(
            "vendor_selections",
            f"{rfp_id}:{vendor_id}",
            {
                "rfp_id": rfp_id,
                "vendor_id": vendor_id,
                "proposal_id": selected_proposal.get("proposal_id"),
                "selected_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    connector_results = agent.procurement_connector.select_vendor(
        {
            "rfp_id": rfp_id,
            "vendor_id": vendor_id,
            "proposal_id": selected_proposal.get("proposal_id"),
        }
    )
    vendor = agent.vendors.get(vendor_id)
    if vendor:
        vendor["last_selected_at"] = datetime.now(timezone.utc).isoformat()
        vendor["last_selected_rfp"] = rfp_id
        await persist_vendor(agent, vendor, tenant_id=tenant_id)
    await publish_event(
        agent,
        "vendor.selected",
        payload={
            "rfp_id": rfp_id,
            "vendor_id": vendor_id,
            "proposal_id": selected_proposal.get("proposal_id"),
            "connector_results": connector_results,
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
        entity_id=vendor_id,
    )

    return {
        "rfp_id": rfp_id,
        "selected_vendor_id": vendor_id,
        "proposal_id": selected_proposal.get("proposal_id"),
        "pricing": selected_proposal.get("pricing"),
        "evaluation_score": selected_proposal.get("evaluation_score"),
        "next_steps": "Generate contract from approved templates",
    }
