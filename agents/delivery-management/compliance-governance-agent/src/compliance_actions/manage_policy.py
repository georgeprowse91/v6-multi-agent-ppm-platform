"""Action handler: manage_policy"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from agents.common.connector_integration import DocumentMetadata

from compliance_utils import generate_policy_id

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


async def handle_manage_policy(
    agent: ComplianceRegulatoryAgent, policy_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Manage policy document.

    Returns policy ID and version.
    """
    agent.logger.info("Managing policy: %s", policy_data.get("title"))

    # Generate policy ID
    policy_id = policy_data.get("policy_id") or await generate_policy_id()

    # Check if update to existing policy
    existing_policy = agent.policies.get(policy_id)

    if existing_policy:
        # Create new version
        version = existing_policy.get("version", 1.0) + 0.1
    else:
        version = 1.0

    # Create/update policy
    policy = {
        "policy_id": policy_id,
        "title": policy_data.get("title"),
        "description": policy_data.get("description"),
        "version": version,
        "effective_date": policy_data.get("effective_date"),
        "owner": policy_data.get("owner"),
        "approval_status": "Draft",
        "document_url": policy_data.get("document_url"),
        "related_regulations": policy_data.get("related_regulations", []),
        "version_history": (
            existing_policy.get("version_history", []) if existing_policy else []
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Add to version history
    if existing_policy:
        policy["version_history"].append(
            {
                "version": existing_policy["version"],
                "effective_date": existing_policy["effective_date"],
                "archived_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    # Store policy
    agent.policies[policy_id] = policy

    # Persist to database
    await agent.db_service.store("policies", policy_id, policy)

    # Publish policy document to SharePoint
    policy_content = f"""# {policy['title']}

**Version:** {policy['version']}
**Effective Date:** {policy.get('effective_date', 'unknown')}
**Owner:** {policy.get('owner', 'Unassigned')}

## Description
{policy.get('description', 'No description provided.')}

## Related Regulations
{', '.join(policy.get('related_regulations', [])) or 'None specified'}
"""
    doc_metadata = DocumentMetadata(
        title=f"Policy - {policy['title']} v{policy['version']}",
        description=policy.get("description", ""),
        classification="confidential",
        tags=["policy", policy_id] + policy.get("related_regulations", []),
        owner=policy.get("owner", "compliance"),
    )
    publish_result = await agent.document_service.publish_document(
        document_content=policy_content,
        metadata=doc_metadata,
        folder_path="Policies",
    )
    policy["document_url"] = publish_result.get("url")

    return {
        "policy_id": policy_id,
        "title": policy["title"],
        "version": policy["version"],
        "status": policy["approval_status"],
        "next_steps": "Submit policy for approval and publication",
    }
