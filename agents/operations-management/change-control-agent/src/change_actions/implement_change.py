"""Action handlers for implementing, updating, and rolling back changes."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib import request

from change_actions.submit_change import notify_stakeholders, publish_event, record_change_audit

if TYPE_CHECKING:
    from change_configuration_agent import ChangeConfigurationAgent


async def implement_change(
    agent: ChangeConfigurationAgent,
    change_id: str | None,
    implementation: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """Implement change with staging validation, deployment coordination, and monitoring."""
    if not change_id:
        raise ValueError("change_id is required")
    change = agent.change_requests.get(change_id)
    if not change:
        raise ValueError(f"Change request not found: {change_id}")
    if change.get("approval_status") != "Approved":
        return {"change_id": change_id, "status": "blocked", "reason": "not_approved"}

    automated_tests = await run_automated_tests(agent, change, implementation)
    if automated_tests.get("status") == "failed":
        rollback = await rollback_change(agent, change_id, reason="automated_tests_failed")
        return {
            "change_id": change_id,
            "status": "rolled_back",
            "automated_tests": automated_tests,
            "rollback": rollback,
        }
    if automated_tests.get("status") == "skipped" and agent.require_automated_tests:
        return {
            "change_id": change_id,
            "status": "blocked",
            "reason": "automated_tests_required",
        }

    validation = await run_staging_validation(agent, change, implementation)
    if validation.get("status") == "failed":
        rollback = await rollback_change(agent, change_id, reason="staging_validation_failed")
        return {
            "change_id": change_id,
            "status": "rolled_back",
            "validation": validation,
            "rollback": rollback,
        }
    if validation.get("status") == "skipped" and agent.require_staging_tests:
        return {
            "change_id": change_id,
            "status": "blocked",
            "reason": "staging_validation_required",
        }

    change["status"] = "In Progress"
    change["implementation_plan"] = implementation
    change["implementation_started_at"] = datetime.now(timezone.utc).isoformat()
    await agent.db_service.store("change_requests", change_id, change)
    await record_change_audit(
        agent,
        change_id,
        "implementation_started",
        actor_id=actor_id,
        details={"validation": validation, "automated_tests": automated_tests},
    )

    coordination = await coordinate_release_and_governance(agent, change, tenant_id, correlation_id)
    if coordination.get("deployment_status") == "scheduled":
        change["status"] = "Scheduled"
    await agent.db_service.store("change_requests", change_id, change)
    await publish_event(
        agent,
        "change.implementation.started",
        {
            "event_id": f"change.implementation.started:{change_id}",
            "change_id": change_id,
            "coordination": coordination,
        },
    )
    return {
        "change_id": change_id,
        "status": change["status"],
        "validation": validation,
        "coordination": coordination,
    }


async def update_change_request(
    agent: ChangeConfigurationAgent,
    change_id: str | None,
    updates: dict[str, Any],
    *,
    tenant_id: str,
    actor_id: str,
) -> dict[str, Any]:
    if not change_id:
        raise ValueError("change_id is required")
    change = agent.change_requests.get(change_id)
    if not change:
        raise ValueError(f"Change request not found: {change_id}")
    change.update(updates)
    change["version"] = int(change.get("version", 1)) + 1
    change["last_modified"] = datetime.now(timezone.utc).isoformat()
    agent.change_store.upsert(tenant_id, change_id, change)
    await agent.db_service.store("change_requests", change_id, change)
    await record_change_audit(
        agent,
        change_id,
        "updated",
        actor_id=actor_id,
        details={"fields": list(updates.keys())},
    )
    return {"change_id": change_id, "version": change["version"], "status": "updated"}


async def rollback_change(
    agent: ChangeConfigurationAgent, change_id: str, reason: str
) -> dict[str, Any]:
    """Rollback change and publish event."""
    change = agent.change_requests.get(change_id)
    if not change:
        raise ValueError(f"Change request not found: {change_id}")
    change["status"] = "Rolled Back"
    change["rollback_reason"] = reason
    change["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
    await agent.db_service.store("change_requests", change_id, change)
    await record_change_audit(
        agent,
        change_id,
        "rolled_back",
        actor_id=change.get("actor_id", "system"),
        details={"reason": reason},
    )
    await publish_event(
        agent,
        "change.rolled_back",
        {
            "event_id": f"change.rolled_back:{change_id}",
            "change_id": change_id,
            "status": change["status"],
            "reason": reason,
        },
    )
    await notify_stakeholders(
        agent,
        change,
        event_type="change.rolled_back",
        tenant_id=change.get("tenant_id", "unknown"),
        correlation_id=change.get("correlation_id", str(uuid.uuid4())),
    )
    return {"change_id": change_id, "status": change["status"], "reason": reason}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def run_staging_validation(
    agent: ChangeConfigurationAgent,
    change: dict[str, Any],
    implementation: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "change_id": change.get("change_id"),
        "title": change.get("title"),
        "implementation": implementation,
        "impacted_cis": change.get("impacted_cis", []),
    }
    if not agent.staging_validation_endpoint:
        return {"status": "skipped", "reason": "no_validation_endpoint"}
    try:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(agent.staging_validation_endpoint, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with request.urlopen(req, timeout=20) as response:
            response_body = response.read().decode("utf-8")
            return {"status": "passed", "details": response_body}
    except OSError as exc:
        return {"status": "failed", "error": str(exc)}


async def run_automated_tests(
    agent: ChangeConfigurationAgent,
    change: dict[str, Any],
    implementation: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "change_id": change.get("change_id"),
        "title": change.get("title"),
        "implementation": implementation,
        "impacted_cis": change.get("impacted_cis", []),
    }
    if not agent.automated_test_endpoint:
        return {"status": "skipped", "reason": "no_automated_test_endpoint"}
    try:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(agent.automated_test_endpoint, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with request.urlopen(req, timeout=20) as response:
            response_body = response.read().decode("utf-8")
            return {"status": "passed", "details": response_body}
    except OSError as exc:
        return {"status": "failed", "error": str(exc)}


async def coordinate_release_and_governance(
    agent: ChangeConfigurationAgent,
    change: dict[str, Any],
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    coordination = {"deployment_status": "unconfigured", "governance_status": "unconfigured"}
    deployment_payload = {
        "change_id": change.get("change_id"),
        "title": change.get("title"),
        "priority": change.get("priority"),
        "tenant_id": tenant_id,
        "correlation_id": correlation_id,
    }
    if agent.release_deployment_endpoint:
        try:
            body = json.dumps(deployment_payload).encode("utf-8")
            req = request.Request(agent.release_deployment_endpoint, data=body, method="POST")
            req.add_header("Content-Type", "application/json")
            with request.urlopen(req, timeout=10) as response:
                coordination["deployment_status"] = response.read().decode("utf-8") or "scheduled"
        except OSError as exc:
            coordination["deployment_status"] = f"error:{exc}"
    else:
        coordination["deployment_status"] = "scheduled"
    governance_payload = {
        "change_id": change.get("change_id"),
        "status": change.get("status"),
        "classification": change.get("classification"),
        "tenant_id": tenant_id,
        "correlation_id": correlation_id,
    }
    if agent.lifecycle_governance_endpoint:
        try:
            body = json.dumps(governance_payload).encode("utf-8")
            req = request.Request(agent.lifecycle_governance_endpoint, data=body, method="POST")
            req.add_header("Content-Type", "application/json")
            with request.urlopen(req, timeout=10) as response:
                coordination["governance_status"] = response.read().decode("utf-8") or "checked"
        except OSError as exc:
            coordination["governance_status"] = f"error:{exc}"
    else:
        coordination["governance_status"] = "checked"
    return coordination
