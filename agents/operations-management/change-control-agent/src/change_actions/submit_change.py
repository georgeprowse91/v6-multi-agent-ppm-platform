"""Action handler for submitting change requests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from change_models import RepositoryReference

if TYPE_CHECKING:
    from change_configuration_agent import ChangeConfigurationAgent


async def submit_change_request(
    agent: ChangeConfigurationAgent,
    change_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """Submit change request."""
    agent.logger.info("Submitting change request: %s", change_data.get("title"))

    # Generate change ID
    change_id = await generate_change_id()

    # Auto-classify change type
    change_type = await auto_classify_change_type(agent, change_data)

    iac_changes = await analyze_iac_changes(agent, change_data)

    # Identify impacted CIs
    impacted_cis = await identify_impacted_cis(agent, change_data)

    classification = await classify_change_category(agent, change_type, change_data)
    approval_required = await requires_approval(agent, change_type, change_data)
    approval_payload = None
    if approval_required:
        approval_payload = await agent.approval_agent.process(
            {
                "request_type": "scope_change",
                "request_id": change_id,
                "requester": change_data.get("requester", actor_id),
                "details": {
                    "description": change_data.get("description"),
                    "urgency": change_data.get("priority", "medium"),
                    "impact": change_data.get("impact", "medium"),
                },
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
            }
        )

    repo_context = await retrieve_repo_context(agent, change_data)
    knowledge_context = await retrieve_context_documents(agent, change_data)
    workflow = await agent.workflow_orchestrator.create_workflow(change_id, tenant_id)

    # Create change request
    change = {
        "change_id": change_id,
        "title": change_data.get("title"),
        "description": change_data.get("description"),
        "type": change_type,
        "classification": classification,
        "priority": change_data.get("priority", "medium"),
        "requester": change_data.get("requester"),
        "project_id": change_data.get("project_id"),
        "tenant_id": tenant_id,
        "correlation_id": correlation_id,
        "actor_id": actor_id,
        "impacted_cis": impacted_cis,
        "impact_assessment": None,
        "risk_assessment": None,
        "approval_status": "Pending" if approval_required else "Approved",
        "approval": approval_payload,
        "status": "Submitted",
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repository_context": repo_context,
        "iac_changes": iac_changes,
        "knowledge_context": knowledge_context,
        "workflow": workflow,
    }

    # Store change
    agent.change_requests[change_id] = change
    agent.change_store.upsert(tenant_id, change_id, change)

    itsm_payload = {
        "title": change.get("title"),
        "description": change.get("description"),
        "priority": change.get("priority"),
        "requester": change.get("requester"),
        "status": change.get("status"),
    }
    change["itsm_record"] = await agent.itsm_service.create_change_request(itsm_payload)
    await agent.db_service.store("change_requests", change_id, change)
    await record_change_audit(
        agent,
        change_id,
        "submitted",
        actor_id=actor_id,
        details={"approval_required": approval_required, "classification": classification},
    )
    await notify_stakeholders(
        agent,
        change,
        event_type="change.submitted",
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    await publish_event(
        agent,
        "change.created",
        {
            "event_id": f"change.created:{change_id}",
            "change_id": change_id,
            "tenant_id": tenant_id,
            "status": change["status"],
        },
    )

    return {
        "change_id": change_id,
        "type": change_type,
        "status": "Submitted",
        "impacted_cis": len(impacted_cis),
        "approval_required": approval_required,
        "approval": approval_payload,
        "next_steps": "Impact assessment will be performed",
    }


# ---------------------------------------------------------------------------
# Helpers used by submit (and potentially other actions)
# ---------------------------------------------------------------------------


async def generate_change_id() -> str:
    """Generate unique change ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"CHG-{timestamp}"


async def auto_classify_change_type(
    agent: ChangeConfigurationAgent, change_data: dict[str, Any]
) -> str:
    """Auto-classify change type using NLP."""
    description = f"{change_data.get('title', '')} {change_data.get('description', '')}".strip()
    classification, _ = agent.text_classifier.predict(description)
    return classification


async def identify_impacted_cis(
    agent: ChangeConfigurationAgent, change_data: dict[str, Any]
) -> list[str]:
    """Identify impacted configuration items."""
    ci_ids = set(change_data.get("ci_ids", []))
    impacted_resources = change_data.get("impacted_resources", [])
    for ci_id, ci in agent.cmdb.items():
        attributes = ci.get("attributes", {})
        resource_type = attributes.get("resource_type")
        resource_name = attributes.get("resource_name")
        for resource in impacted_resources:
            if resource_type == resource.get("resource_type") and resource_name == resource.get(
                "resource_name"
            ):
                ci_ids.add(ci_id)
    if agent.dependency_graph:
        impacted = agent.dependency_graph.get_impacted(ci_ids)
        ci_ids.update(impacted)
    return sorted(ci_ids)


async def classify_change_category(
    agent: ChangeConfigurationAgent, change_type: str, change_data: dict[str, Any]
) -> dict[str, Any]:
    priority = change_data.get("priority", "medium")
    impacted_count = len(change_data.get("ci_ids", []))
    risk_category = change_data.get("risk_category", "medium")
    if change_type == "emergency" or priority in {"critical", "high"}:
        category = "urgent"
    elif impacted_count > 5 or risk_category in {"high", "critical"}:
        category = "major"
    else:
        category = "routine"
    return {
        "category": category,
        "priority": priority,
        "risk_category": risk_category,
        "impacted_ci_count": impacted_count,
    }


async def requires_approval(
    agent: ChangeConfigurationAgent, change_type: str, change_data: dict[str, Any]
) -> bool:
    priority = change_data.get("priority", "medium")
    return (
        change_type in agent.approval_change_types or priority in agent.approval_priority_thresholds
    )


async def retrieve_repo_context(
    agent: ChangeConfigurationAgent, change_data: dict[str, Any]
) -> dict[str, Any]:
    repo_provider = change_data.get("repo_provider")
    repo_slug = change_data.get("repo_slug")
    if not repo_provider or not repo_slug or not agent.repo_service:
        return {"status": "unavailable"}
    reference = RepositoryReference(
        provider=repo_provider,
        repo=repo_slug,
        pull_request_id=change_data.get("pull_request_id"),
        commit_id=change_data.get("commit_id"),
    )
    return {
        "repository": agent.repo_service.fetch_repository_data(reference),
        "pull_request": agent.repo_service.fetch_pull_request_status(reference),
        "pull_request_list": agent.repo_service.list_pull_requests(reference).__dict__,
        "pull_request_diff": agent.repo_service.fetch_pull_request_diff(reference),
        "commit_diff": agent.repo_service.fetch_commit_diff(reference),
    }


async def analyze_iac_changes(
    agent: ChangeConfigurationAgent, change_data: dict[str, Any]
) -> dict[str, Any]:
    file_paths = [Path(path) for path in change_data.get("iac_files", [])]
    repo_root = Path(change_data["iac_repo_path"]) if change_data.get("iac_repo_path") else None
    if not agent.iac_parser or (not file_paths and not repo_root):
        return {"resources": [], "status": "no_iac"}
    resources = agent.iac_parser.parse_files(file_paths)
    if repo_root:
        resources.extend(agent.iac_parser.parse_repository(repo_root))
    change_data["impacted_resources"] = resources
    return {"resources": resources, "resource_count": len(resources)}


async def retrieve_context_documents(
    agent: ChangeConfigurationAgent, change_data: dict[str, Any]
) -> dict[str, Any]:
    if not agent.document_service:
        return {"documents": [], "status": "unavailable"}
    query = change_data.get("knowledge_query") or change_data.get("title")
    if not query:
        return {"documents": [], "status": "no_query"}
    documents = await agent.document_service.list_documents(limit=25)
    filtered = [doc for doc in documents if query.lower() in str(doc.get("title", "")).lower()]
    return {"documents": filtered, "status": "ok"}


async def record_change_audit(
    agent: ChangeConfigurationAgent,
    change_id: str,
    action: str,
    *,
    actor_id: str,
    details: dict[str, Any] | None = None,
) -> None:
    entry = {
        "change_id": change_id,
        "action": action,
        "actor_id": actor_id,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    agent.change_history.setdefault(change_id, []).append(entry)
    await agent.db_service.store(
        "change_audit", f"{change_id}-{entry['timestamp'].replace(':', '-')}", entry
    )


async def publish_event(
    agent: ChangeConfigurationAgent, topic: str, payload: dict[str, Any]
) -> None:
    if not agent.event_publisher:
        return
    await agent.event_publisher.publish_event(topic, payload)


async def notify_stakeholders(
    agent: ChangeConfigurationAgent,
    change: dict[str, Any],
    *,
    event_type: str,
    tenant_id: str,
    correlation_id: str,
) -> None:
    import json
    from urllib import request

    payload = {
        "change_id": change.get("change_id"),
        "event_type": event_type,
        "title": change.get("title"),
        "status": change.get("status"),
        "priority": change.get("priority"),
        "approval_status": change.get("approval_status"),
        "tenant_id": tenant_id,
        "correlation_id": correlation_id,
    }
    if agent.stakeholder_comms_endpoint:
        body = json.dumps(payload).encode("utf-8")
        try:
            req = request.Request(agent.stakeholder_comms_endpoint, data=body, method="POST")
            req.add_header("Content-Type", "application/json")
            request.urlopen(req, timeout=10)
        except OSError as exc:
            agent.logger.warning("Stakeholder comms notify failed: %s", exc)
            await publish_event(
                agent,
                "stakeholder.comms.failed",
                {
                    "event_id": f"stakeholder.comms.failed:{change.get('change_id')}",
                    "error": str(exc),
                },
            )
    else:
        await publish_event(
            agent,
            "stakeholder.comms.requested",
            {"event_id": f"stakeholder.comms.requested:{change.get('change_id')}", **payload},
        )
