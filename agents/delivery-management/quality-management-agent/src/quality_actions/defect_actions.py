"""Action handlers for defect logging, updating, classification, and syncing."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from quality_models import build_defect
from quality_utils import (
    calculate_resolution_time,
    derive_required_skills,
    generate_defect_id,
    normalize_scores,
    root_cause_from_category,
    score_labels,
    score_resource_candidate,
    severity_from_category,
    tokenize_text,
)

if TYPE_CHECKING:
    from quality_management_agent import QualityManagementAgent


async def log_defect(
    agent: QualityManagementAgent,
    defect_data: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Log a defect.  Returns defect ID and workflow status."""
    agent.logger.info("Logging defect: %s", defect_data.get("summary"))

    defect_id = await generate_defect_id()
    auto_classification = await _auto_classify_defect(agent, defect_data)
    defect = build_defect(defect_id, defect_data, auto_classification)

    agent.defects[defect_id] = defect
    agent.defect_store.upsert(tenant_id, defect_id, defect)
    agent.defect_ml_model = await _train_defect_classification_model(agent)
    agent.defect_cluster_model = await _train_defect_cluster_model(agent)
    await agent._publish_quality_event(
        "quality.defect.logged",
        payload={
            "defect_id": defect_id,
            "severity": defect.get("severity"),
            "status": defect.get("status"),
        },
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    assigned_owner = await _assign_defect_owner(agent, defect)
    defect["assigned_to"] = assigned_owner
    defect["external_sync"] = await _sync_defect_ticket(
        agent, defect, action="create", tenant_id=tenant_id, correlation_id=correlation_id
    )

    await agent._store_record("quality_defects", defect_id, defect)

    return {
        "defect_id": defect_id,
        "summary": defect["summary"],
        "severity": defect["severity"],
        "priority": defect["priority"],
        "assigned_to": defect["assigned_to"],
        "status": "Open",
        "auto_classification": auto_classification,
    }


async def update_defect(
    agent: QualityManagementAgent,
    defect_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Update defect status and details.  Returns updated defect status."""
    agent.logger.info("Updating defect: %s", defect_id)

    defect = agent.defects.get(defect_id)
    if not defect:
        raise ValueError(f"Defect not found: {defect_id}")

    if "status" in updates and updates["status"] != defect.get("status"):
        defect["status_history"].append(
            {
                "status": updates["status"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "updated_by": updates.get("updated_by", "unknown"),
            }
        )

    external_updates = updates.pop("external_updates", None)
    if external_updates:
        await _apply_external_defect_updates(defect, external_updates)

    for key, value in updates.items():
        if key in defect and key != "status_history":
            defect[key] = value

    defect["last_updated"] = datetime.now(timezone.utc).isoformat()

    if defect.get("status") in ["Resolved", "Closed", "Verified"]:
        resolution_time = await calculate_resolution_time(defect)
        defect["resolution_time_hours"] = resolution_time

    defect["external_sync"] = await _sync_defect_ticket(
        agent,
        defect,
        action="update",
        tenant_id=defect.get("project_id", "unknown"),
        correlation_id=str(uuid.uuid4()),
    )

    await agent._store_record("quality_defects", defect_id, defect)

    return {
        "defect_id": defect_id,
        "status": defect["status"],
        "resolution": defect.get("resolution"),
        "resolution_time_hours": defect.get("resolution_time_hours"),
        "last_updated": defect["last_updated"],
    }


async def sync_defect_tickets(
    agent: QualityManagementAgent,
    defect_ids: list[str],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    sync_results = []
    for defect_id in defect_ids:
        defect = agent.defects.get(defect_id)
        if not defect:
            continue
        sync_results.append(
            await _sync_defect_ticket(
                agent, defect, action="update", tenant_id=tenant_id, correlation_id=correlation_id
            )
        )
    return {"synced": len(sync_results), "results": sync_results}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _auto_classify_defect(
    agent: QualityManagementAgent, defect_data: dict[str, Any]
) -> dict[str, Any]:
    classification = await _classify_defect(agent, defect_data)
    category = classification.get("category", "code_defect")
    severity = defect_data.get("severity") or classification.get(
        "severity", severity_from_category(category)
    )
    priority = defect_data.get("priority") or classification.get(
        "priority", "high" if severity in {"critical", "high"} else "medium"
    )
    return {
        "severity": severity,
        "priority": priority,
        "root_cause": root_cause_from_category(category),
        "category": category,
        "classification_confidence": classification.get("probabilities", {}),
        "model": classification.get("model", "statistical"),
    }


async def _classify_defect(
    agent: QualityManagementAgent, defect_data: dict[str, Any]
) -> dict[str, Any]:
    content = " ".join(
        value
        for value in [
            defect_data.get("summary"),
            defect_data.get("description"),
            defect_data.get("component"),
            defect_data.get("expected_behavior"),
            defect_data.get("actual_behavior"),
        ]
        if value
    ).strip()
    if not content:
        return {"category": "code_defect", "probabilities": {}, "model": "fallback"}
    if not agent.defect_ml_model or not agent.defect_ml_model.get("label_tokens"):
        agent.defect_ml_model = await _train_defect_classification_model(agent)
    model = agent.defect_ml_model or {}
    label_scores = score_labels(content, model.get("label_tokens", {}))
    if not label_scores:
        classifier = _get_defect_classifier(agent)
        category, probabilities = classifier.predict(content)
        return {
            "category": category,
            "probabilities": probabilities,
            "model": "naive_bayes_fallback",
        }
    category = max(label_scores, key=label_scores.get)
    probabilities = normalize_scores(label_scores)
    severity_scores = score_labels(content, model.get("severity_tokens", {}))
    severity = max(severity_scores, key=severity_scores.get) if severity_scores else None
    return {
        "category": category,
        "probabilities": probabilities,
        "severity": severity,
        "model": "token_frequency",
    }


def _get_defect_classifier(agent: QualityManagementAgent):
    from quality_utils import build_defect_classifier

    if agent.defect_classifier is None:
        agent.defect_classifier = build_defect_classifier()
    return agent.defect_classifier


async def _assign_defect_owner(agent: QualityManagementAgent, defect: dict[str, Any]) -> str:
    resource_client = (agent.config or {}).get("resource_capacity_client")
    required_skills = derive_required_skills(defect)
    if resource_client:
        if hasattr(resource_client, "match_skills"):
            results = resource_client.match_skills(required_skills)
            if results:
                return results[0].get("resource_id", "unassigned")
        if hasattr(resource_client, "search_resources"):
            results = resource_client.search_resources({"skills": required_skills})
            if results:
                return results[0].get("resource_id", "unassigned")
    candidates = agent.integration_config.get("resource_capacity", {}).get("candidates", [])
    if not candidates:
        return "unassigned"
    scored = sorted(
        (
            (score_resource_candidate(candidate, required_skills), candidate)
            for candidate in candidates
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    return scored[0][1].get("resource_id", "unassigned") if scored else "unassigned"


async def _sync_defect_ticket(
    agent: QualityManagementAgent,
    defect: dict[str, Any],
    *,
    action: str,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    jira_enabled = agent.integration_config.get("jira", {}).get("enabled", True)
    azure_enabled = agent.integration_config.get("azure_devops", {}).get("enabled", True)
    jira_key = defect.get("external", {}).get("jira_key") if defect.get("external") else None
    azure_id = defect.get("external", {}).get("azure_work_item") if defect.get("external") else None
    if action == "create":
        jira_key = jira_key or f"JIRA-{defect.get('defect_id')}"
        azure_id = azure_id or f"ADO-{defect.get('defect_id')}"
    sync_record = {
        "defect_id": defect.get("defect_id"),
        "action": action,
        "jira": {"status": "queued" if jira_enabled else "disabled", "key": jira_key},
        "azure_devops": {
            "status": "queued" if azure_enabled else "disabled",
            "work_item": azure_id,
        },
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }
    defect["external"] = {"jira_key": jira_key, "azure_work_item": azure_id}
    await agent._publish_quality_event(
        "quality.defect.synced",
        payload=sync_record,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )
    await agent._store_record("quality_defect_sync", defect.get("defect_id", ""), sync_record)
    return sync_record


async def _apply_external_defect_updates(
    defect: dict[str, Any], external_updates: dict[str, Any]
) -> None:
    jira_update = external_updates.get("jira")
    azure_update = external_updates.get("azure_devops")
    for update in [jira_update, azure_update]:
        if not update:
            continue
        status = update.get("status")
        if status:
            defect["status"] = status
        resolution = update.get("resolution")
        if resolution:
            defect["resolution"] = resolution


async def _train_defect_classification_model(
    agent: QualityManagementAgent,
) -> dict[str, Any]:
    if not agent.defects:
        return {"label_tokens": {}, "severity_tokens": {}, "trained_at": None}
    label_tokens: dict[str, list[str]] = {}
    severity_tokens: dict[str, list[str]] = {}
    for defect in agent.defects.values():
        content = " ".join(
            value
            for value in [
                defect.get("summary"),
                defect.get("description"),
                defect.get("component"),
                defect.get("category"),
            ]
            if value
        )
        tokens = tokenize_text(content)
        category = defect.get("category", "code_defect")
        label_tokens.setdefault(category, []).extend(tokens)
        severity = defect.get("severity")
        if severity:
            severity_tokens.setdefault(severity, []).extend(tokens)
    model = {
        "label_tokens": label_tokens,
        "severity_tokens": severity_tokens,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    await agent._store_record("quality_defect_models", f"classifier-{uuid.uuid4().hex[:6]}", model)
    return model


async def _train_defect_cluster_model(
    agent: QualityManagementAgent,
) -> dict[str, Any]:
    from quality_utils import kmeans, vectorize_defects

    defects = list(agent.defects.values())
    if len(defects) < 2:
        return {"clusters": [], "trained_at": None}
    vectors, vocab = vectorize_defects(defects)
    k = min(3, len(vectors))
    clusters = kmeans(vectors, k)
    model = {
        "clusters": clusters,
        "vocab": vocab,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    await agent._store_record(
        "quality_defect_cluster_models", f"cluster-{uuid.uuid4().hex[:6]}", model
    )
    return model
