"""
Release & Deployment Agent - Shared utility functions.

Pure helpers that are used across multiple action modules: ID generation,
event publishing, filter matching, deployment-window scoring, environment
reservation / release, pipeline step construction, monitoring helpers, and
tracking-system queries.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from release_models import ReleaseAgentProtocol


# ---------------------------------------------------------------------------
# ID generators
# ---------------------------------------------------------------------------


async def generate_release_id() -> str:
    """Generate unique release ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"REL-{timestamp}"


async def generate_deployment_plan_id() -> str:
    """Generate unique deployment plan ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"DEPLOY-{timestamp}"


async def generate_environment_id() -> str:
    """Generate unique environment ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"ENV-{timestamp}"


async def generate_release_notes_id() -> str:
    """Generate unique release notes ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"NOTES-{timestamp}"


async def generate_readiness_assessment_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"READY-{timestamp}"


# ---------------------------------------------------------------------------
# Event publishing
# ---------------------------------------------------------------------------


async def publish_event(agent: ReleaseAgentProtocol, topic: str, payload: dict[str, Any]) -> None:
    if not agent.event_bus:
        return
    await agent.event_bus.publish(topic, payload)


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------


async def matches_filters(release: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Check if release matches filters."""
    if "status" in filters and release.get("status") != filters["status"]:
        return False
    if "environment" in filters and release.get("target_environment") != filters["environment"]:
        return False
    return True


async def matches_history_filters(record: dict[str, Any], filters: dict[str, Any]) -> bool:
    if "release_id" in filters and record.get("release_id") != filters["release_id"]:
        return False
    if "environment" in filters and record.get("environment") != filters["environment"]:
        return False
    if "status" in filters and record.get("status") != filters["status"]:
        return False
    return True


# ---------------------------------------------------------------------------
# Scheduling conflict detection
# ---------------------------------------------------------------------------


async def detect_scheduling_conflicts(
    agent: ReleaseAgentProtocol, planned_date: str, environment: str
) -> list[dict[str, Any]]:
    """Detect scheduling conflicts."""
    conflicts = []
    for release_id, release in agent.releases.items():
        if (
            release.get("planned_date") == planned_date
            and release.get("target_environment") == environment
            and release.get("status") in ["Planned", "In Progress"]
        ):
            conflicts.append(
                {
                    "release_id": release_id,
                    "release_name": release.get("name"),
                    "planned_date": release.get("planned_date"),
                }
            )
    return conflicts


# ---------------------------------------------------------------------------
# Environment reservation / release
# ---------------------------------------------------------------------------


async def reserve_environment(
    agent: ReleaseAgentProtocol, environment: str, planned_date: str, release_id: str
) -> dict[str, Any] | None:
    """Reserve an environment using reservation system or in-memory tracking."""
    if agent.environment_reservation_client and hasattr(
        agent.environment_reservation_client, "check_availability"
    ):
        availability = await agent.environment_reservation_client.check_availability(
            {"environment": environment, "planned_date": planned_date}
        )
        if not availability.get("available", False):
            return None
        if hasattr(agent.environment_reservation_client, "reserve"):
            reservation = await agent.environment_reservation_client.reserve(
                {
                    "environment": environment,
                    "planned_date": planned_date,
                    "release_id": release_id,
                }
            )
        else:
            reservation = {"reservation_id": str(uuid.uuid4()), "status": "reserved"}
    else:
        for allocation in agent.environment_allocations.values():
            if (
                allocation.get("environment") == environment
                and allocation.get("status") == "reserved"
            ):
                return None
        reservation = {"reservation_id": str(uuid.uuid4()), "status": "reserved"}

    reserved_until = (
        datetime.fromisoformat(planned_date) + timedelta(hours=agent.deployment_window_hours)
    ).isoformat()
    allocation = {
        "allocation_id": reservation.get("reservation_id", str(uuid.uuid4())),
        "environment": environment,
        "release_id": release_id,
        "reserved_at": datetime.now(timezone.utc).isoformat(),
        "reserved_until": reserved_until,
        "status": "reserved",
    }
    agent.environment_allocations[allocation["allocation_id"]] = allocation
    await agent.db_service.store("environment_allocations", allocation["allocation_id"], allocation)
    await publish_event(
        agent,
        "environment.reserved",
        {
            "allocation_id": allocation["allocation_id"],
            "environment": environment,
            "release_id": release_id,
            "reserved_until": reserved_until,
        },
    )
    return allocation


async def check_environment_availability(
    agent: ReleaseAgentProtocol, environment: str, planned_date: str, release_id: str
) -> bool:
    """Check if environment is available and reserve it if possible."""
    allocation = await reserve_environment(agent, environment, planned_date, release_id)
    return allocation is not None


async def ensure_environment_reserved(
    agent: ReleaseAgentProtocol, release_id: str, deployment_plan: dict[str, Any]
) -> None:
    if any(
        allocation.get("release_id") == release_id and allocation.get("status") == "reserved"
        for allocation in agent.environment_allocations.values()
    ):
        return
    planned_date = deployment_plan.get("started_at") or datetime.now(timezone.utc).isoformat()
    environment = deployment_plan.get("environment")
    if environment:
        await reserve_environment(agent, environment, planned_date, release_id)


async def release_environment_allocation(
    agent: ReleaseAgentProtocol, release_id: str, deployment_plan_id: str
) -> None:
    allocation = next(
        (
            allocation
            for allocation in agent.environment_allocations.values()
            if allocation.get("release_id") == release_id and allocation.get("status") == "reserved"
        ),
        None,
    )
    if not allocation:
        return
    allocation["status"] = "released"
    allocation["released_at"] = datetime.now(timezone.utc).isoformat()
    if agent.environment_reservation_client and hasattr(
        agent.environment_reservation_client, "release"
    ):
        await agent.environment_reservation_client.release(allocation)
    await agent.db_service.store("environment_allocations", allocation["allocation_id"], allocation)
    await publish_event(
        agent,
        "environment.released",
        {
            "allocation_id": allocation["allocation_id"],
            "environment": allocation.get("environment"),
            "release_id": release_id,
            "deployment_plan_id": deployment_plan_id,
        },
    )


# ---------------------------------------------------------------------------
# Deployment window scoring & optimization
# ---------------------------------------------------------------------------


async def analyze_usage_patterns(agent: ReleaseAgentProtocol, environment: str) -> dict[str, Any]:
    """Analyze usage patterns."""
    if agent.analytics_client:
        if hasattr(agent.analytics_client, "get_usage_patterns"):
            response = await agent.analytics_client.get_usage_patterns(environment)
            return cast(dict[str, Any], response)
        if hasattr(agent.analytics_client, "process"):
            response = await agent.analytics_client.process(
                {"action": "get_usage_patterns", "environment": environment}
            )
            return cast(dict[str, Any], response)
    return {"peak_hours": [9, 10, 11, 14, 15], "low_usage_hours": [2, 3, 4, 5]}


async def fetch_resource_availability(
    agent: ReleaseAgentProtocol, environment: str
) -> dict[str, Any]:
    if agent.environment_reservation_client and hasattr(
        agent.environment_reservation_client, "get_capacity"
    ):
        response = await agent.environment_reservation_client.get_capacity(
            {"environment": environment}
        )
        return cast(dict[str, Any], response)
    return {"capacity_score": 0.7, "available_slots": 2}


async def fetch_risk_exposure(agent: ReleaseAgentProtocol, environment: str) -> dict[str, Any]:
    if agent.risk_agent:
        response = await agent.risk_agent.process(
            {"action": "get_deployment_risk", "environment": environment}
        )
        return cast(dict[str, Any], response)
    return {"risk_score": 0.3, "risk_level": "low"}


async def fetch_system_health(agent: ReleaseAgentProtocol, environment: str) -> dict[str, Any]:
    if agent.monitoring_client and hasattr(agent.monitoring_client, "get_environment_health"):
        response = await agent.monitoring_client.get_environment_health(environment)
        return cast(dict[str, Any], response)
    return {"health_score": 0.8, "status": "healthy"}


async def fetch_business_calendar(agent: ReleaseAgentProtocol, environment: str) -> dict[str, Any]:
    if agent.configuration_management_client and hasattr(
        agent.configuration_management_client, "get_business_calendar"
    ):
        response = await agent.configuration_management_client.get_business_calendar(environment)
        return cast(dict[str, Any], response)
    return {"blackout": False, "notes": "No blackout window"}


async def score_window(
    window: dict[str, Any],
    *,
    usage_patterns: dict[str, Any],
    resource_availability: dict[str, Any],
    risk_exposure: dict[str, Any],
    system_health: dict[str, Any],
    business_calendar: dict[str, Any],
) -> float:
    start_time = window.get("start_time")
    if not isinstance(start_time, str):
        return 0.0
    hour = datetime.fromisoformat(start_time).hour
    usage_score = 1.0 if hour in usage_patterns.get("low_usage_hours", []) else 0.4
    resource_score = resource_availability.get("capacity_score", 0.5)
    risk_score = max(0.0, 1.0 - risk_exposure.get("risk_score", 0.5))
    health_score = system_health.get("health_score", 0.7)
    calendar_score = 0.2 if business_calendar.get("blackout", False) else 1.0
    weights = {
        "usage": 0.25,
        "resource": 0.2,
        "risk": 0.2,
        "health": 0.2,
        "calendar": 0.15,
    }
    return (
        usage_score * weights["usage"]
        + resource_score * weights["resource"]
        + risk_score * weights["risk"]
        + health_score * weights["health"]
        + calendar_score * weights["calendar"]
    )


async def optimize_deployment_windows(
    agent: ReleaseAgentProtocol,
    *,
    planned_date: str,
    environment: str,
    preferred_window: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    preferred_window = preferred_window or {"start_time": planned_date}
    start_time = datetime.fromisoformat(preferred_window.get("start_time", planned_date))
    candidate_windows: list[dict[str, Any]] = []
    for offset in [-6, -2, 0, 2, 4, 8, 12]:
        window_start = start_time + timedelta(hours=offset)
        candidate_windows.append(
            {
                "start_time": window_start.isoformat(),
                "duration_hours": agent.deployment_window_hours,
                "end_time": (
                    window_start + timedelta(hours=agent.deployment_window_hours)
                ).isoformat(),
            }
        )

    usage_patterns = await analyze_usage_patterns(agent, environment)
    resource_availability = await fetch_resource_availability(agent, environment)
    risk_exp = await fetch_risk_exposure(agent, environment)
    sys_health = await fetch_system_health(agent, environment)
    biz_calendar = await fetch_business_calendar(agent, environment)

    scored_windows = []
    for window in candidate_windows:
        sc = await score_window(
            window,
            usage_patterns=usage_patterns,
            resource_availability=resource_availability,
            risk_exposure=risk_exp,
            system_health=sys_health,
            business_calendar=biz_calendar,
        )
        window["score"] = sc
        scored_windows.append(window)

    scored_windows.sort(key=lambda item: item.get("score", 0), reverse=True)
    return scored_windows[:3]


async def suggest_alternative_windows(
    agent: ReleaseAgentProtocol, planned_date: str, environment: str
) -> list[dict[str, Any]]:
    """Suggest alternative deployment windows."""
    return await optimize_deployment_windows(
        agent, planned_date=planned_date, environment=environment
    )


# ---------------------------------------------------------------------------
# Pipeline step construction
# ---------------------------------------------------------------------------


async def build_pipeline_steps(
    strategy: str, steps: list[dict[str, Any]], deployment_plan: dict[str, Any]
) -> list[dict[str, Any]]:
    if strategy == "blue_green":
        return [
            {"step": 1, "action": "Provision green environment"},
            {"step": 2, "action": "Deploy artifacts to green"},
            {"step": 3, "action": "Run smoke tests on green"},
            {"step": 4, "action": "Switch traffic to green"},
            {"step": 5, "action": "Decommission blue environment"},
        ]
    if strategy == "canary":
        traffic_steps = deployment_plan.get("traffic_steps") or [10, 25, 50, 100]
        pipeline_steps = [
            {"step": 1, "action": "Deploy canary release"},
        ]
        for idx, percentage in enumerate(traffic_steps, start=2):
            pipeline_steps.append(
                {
                    "step": idx,
                    "action": f"Shift {percentage}% traffic to canary",
                    "traffic_percentage": percentage,
                }
            )
        pipeline_steps.append({"step": len(pipeline_steps) + 1, "action": "Promote canary"})
        return pipeline_steps
    return steps


# ---------------------------------------------------------------------------
# Monitoring helpers
# ---------------------------------------------------------------------------


async def fetch_monitoring_metrics(
    agent: ReleaseAgentProtocol, deployment_plan: dict[str, Any]
) -> dict[str, float]:
    if agent.monitoring_client and hasattr(agent.monitoring_client, "get_metrics"):
        response = await agent.monitoring_client.get_metrics(deployment_plan)
        return cast(dict[str, float], response)
    if agent.monitoring_client and hasattr(agent.monitoring_client, "process"):
        response = await agent.monitoring_client.process(
            {"action": "get_metrics", "deployment_plan": deployment_plan}
        )
        return cast(dict[str, float], response)
    return {"response_time_ms": 150.0, "error_rate": 0.001}


async def fetch_baseline_metrics(
    agent: ReleaseAgentProtocol, deployment_plan: dict[str, Any]
) -> dict[str, Any]:
    if agent.monitoring_client and hasattr(agent.monitoring_client, "get_baseline"):
        response = await agent.monitoring_client.get_baseline(deployment_plan)
        return cast(dict[str, Any], response)
    return {
        "response_time_ms": {"mean": 120.0, "std": 20.0},
        "error_rate": {"mean": 0.001, "std": 0.002, "threshold": 0.01},
    }


async def check_application_health(
    agent: ReleaseAgentProtocol, deployment_plan: dict[str, Any]
) -> dict[str, Any]:
    """Check application health."""
    if agent.monitoring_client:
        if hasattr(agent.monitoring_client, "get_health"):
            response = await agent.monitoring_client.get_health(deployment_plan)
            return cast(dict[str, Any], response)
        if hasattr(agent.monitoring_client, "process"):
            response = await agent.monitoring_client.process(
                {"action": "get_health", "deployment_plan": deployment_plan}
            )
            return cast(dict[str, Any], response)
    return {"healthy": True, "response_time_ms": 150, "error_rate": 0.001}


# ---------------------------------------------------------------------------
# Tracking-system queries
# ---------------------------------------------------------------------------


async def query_tracking_systems(
    agent: ReleaseAgentProtocol, release_id: str, *, record_type: str
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for client in agent.tracking_clients:
        if hasattr(client, "get_records"):
            response = await client.get_records(release_id=release_id, record_type=record_type)
            if isinstance(response, list):
                records.extend(response)
        elif hasattr(client, "process"):
            response = await client.process(
                {
                    "action": "get_release_records",
                    "release_id": release_id,
                    "record_type": record_type,
                }
            )
            if isinstance(response, list):
                records.extend(response)
            elif isinstance(response, dict):
                records.extend(response.get("records", []))
    return records


# ---------------------------------------------------------------------------
# Deployment history recording
# ---------------------------------------------------------------------------


async def record_deployment_history(
    agent: ReleaseAgentProtocol,
    deployment_plan: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
    status: str,
) -> None:
    record = {
        "deployment_plan_id": deployment_plan.get("deployment_plan_id"),
        "release_id": deployment_plan.get("release_id"),
        "environment": deployment_plan.get("environment"),
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "correlation_id": correlation_id,
    }
    agent.deployment_history.append(record)
    await agent.db_service.store(
        "deployment_history",
        f"{record['deployment_plan_id']}-{record['timestamp'].replace(':', '-')}",
        record,
    )


# ---------------------------------------------------------------------------
# Rollback helpers
# ---------------------------------------------------------------------------


async def build_rollback_plan(
    agent: ReleaseAgentProtocol,
    deployment_plan: dict[str, Any],
    rollback_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    deployment_plan_id = deployment_plan.get("deployment_plan_id")
    artifacts = agent.deployment_artifacts.get(deployment_plan_id, []) if deployment_plan_id else []
    previous_release = deployment_plan.get("previous_release") or deployment_plan.get(
        "rollback_release"
    )
    rollback_plan = {
        "deployment_plan_id": deployment_plan_id,
        "release_id": deployment_plan.get("release_id"),
        "environment": deployment_plan.get("environment"),
        "steps": rollback_steps,
        "artifacts": artifacts,
        "previous_release": previous_release,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    await agent.db_service.store(
        "rollback_plans", deployment_plan_id or str(uuid.uuid4()), rollback_plan
    )
    return rollback_plan


async def write_rollback_script(agent: ReleaseAgentProtocol, rollback_plan: dict[str, Any]) -> str:
    agent.rollback_scripts_path.mkdir(parents=True, exist_ok=True)
    deployment_plan_id = rollback_plan.get("deployment_plan_id") or str(uuid.uuid4())
    script_path = agent.rollback_scripts_path / f"rollback_{deployment_plan_id}.sh"
    artifact_ids = [artifact.get("artifact_id") for artifact in rollback_plan.get("artifacts", [])]
    script_contents = "\n".join(
        [
            "#!/bin/bash",
            "set -e",
            f"echo 'Starting rollback for {deployment_plan_id}'",
            f"echo 'Artifacts: {json.dumps(artifact_ids)}'",
            "echo 'Stopping services...'",
            "echo 'Restoring artifacts...'",
            "echo 'Running database rollback...'",
            "echo 'Restarting services...'",
        ]
    )
    script_path.write_text(script_contents)
    script_path.chmod(0o750)
    return str(script_path)


async def restore_previous_release(
    agent: ReleaseAgentProtocol, rollback_plan: dict[str, Any]
) -> dict[str, Any]:
    previous_release = rollback_plan.get("previous_release")
    if agent.version_control_client:
        if hasattr(agent.version_control_client, "restore_release"):
            response = await agent.version_control_client.restore_release(previous_release)
            return cast(dict[str, Any], response)
        if hasattr(agent.version_control_client, "checkout"):
            response = await agent.version_control_client.checkout(previous_release)
            return cast(dict[str, Any], response)
    if previous_release:
        return {"success": True, "restored_release": previous_release, "method": "noop"}
    return {"success": False, "error": "No previous release specified"}


async def orchestrate_rollback(rollback_plan: dict[str, Any]) -> dict[str, Any]:
    completed_steps = len(rollback_plan.get("steps", []))
    return {"success": True, "completed_steps": completed_steps}


# ---------------------------------------------------------------------------
# CI/CD pipeline triggers
# ---------------------------------------------------------------------------


async def trigger_azure_devops_pipeline(
    agent: ReleaseAgentProtocol,
    deployment_plan: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Trigger Azure DevOps pipeline deployment."""
    if hasattr(agent.azure_devops_client, "run_pipeline"):
        response = await agent.azure_devops_client.run_pipeline(payload)
        return cast(dict[str, Any], response)
    return {"system": "azure_devops", "status": "queued", "pipeline_id": "ado-mock"}


async def trigger_github_actions_workflow(
    agent: ReleaseAgentProtocol,
    deployment_plan: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Trigger GitHub Actions workflow deployment."""
    if hasattr(agent.github_actions_client, "run_workflow"):
        response = await agent.github_actions_client.run_workflow(payload)
        return cast(dict[str, Any], response)
    return {"system": "github_actions", "status": "queued", "run_id": "gha-mock"}


# ---------------------------------------------------------------------------
# Deployment artifact & log capture
# ---------------------------------------------------------------------------


async def capture_deployment_artifacts(
    agent: ReleaseAgentProtocol,
    deployment_plan: dict[str, Any],
    pipelines: list[dict[str, Any]],
    step_results: dict[str, Any],
) -> None:
    artifacts: list[dict[str, Any]] = []
    for pipeline in pipelines:
        if pipeline.get("artifacts"):
            artifacts.extend(pipeline["artifacts"])
    if step_results.get("artifacts"):
        artifacts.extend(step_results["artifacts"])
    if not artifacts:
        artifacts.append(
            {
                "artifact_id": str(uuid.uuid4()),
                "deployment_plan_id": deployment_plan.get("deployment_plan_id"),
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    deployment_plan_id = deployment_plan.get("deployment_plan_id")
    if deployment_plan_id:
        agent.deployment_artifacts.setdefault(deployment_plan_id, []).extend(artifacts)
        await agent.db_service.store(
            "deployment_artifacts",
            deployment_plan_id,
            {"artifacts": artifacts, "deployment_plan_id": deployment_plan_id},
        )


async def persist_deployment_log(
    agent: ReleaseAgentProtocol, deployment_plan: dict[str, Any], payload: dict[str, Any]
) -> None:
    deployment_plan_id = deployment_plan.get("deployment_plan_id")
    if not deployment_plan_id:
        return
    log_entry = {
        "deployment_plan_id": deployment_plan_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    agent.deployment_logs.setdefault(deployment_plan_id, []).append(log_entry)
    await agent.db_service.store("deployment_logs", deployment_plan_id, log_entry)


# ---------------------------------------------------------------------------
# Azure Policy compliance
# ---------------------------------------------------------------------------


async def check_azure_policy_compliance(
    agent: ReleaseAgentProtocol, environment: dict[str, Any]
) -> dict[str, Any]:
    """Check configuration compliance using Azure Policy."""
    if not agent.azure_policy_client:
        return {"compliance_state": "unknown", "drift_items": []}
    if hasattr(agent.azure_policy_client, "assess_compliance"):
        response = await agent.azure_policy_client.assess_compliance(environment)
        return cast(dict[str, Any], response)
    if hasattr(agent.azure_policy_client, "process"):
        response = await agent.azure_policy_client.process(
            {"action": "check_policy_compliance", "environment": environment}
        )
        return cast(dict[str, Any], response)
    return {"compliance_state": "unknown", "drift_items": []}


# ---------------------------------------------------------------------------
# Readiness blocker collection
# ---------------------------------------------------------------------------


async def collect_readiness_blockers(checks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for name, result in checks.items():
        issues = result.get("issues", [])
        for issue in issues:
            if issue.get("severity") == "critical":
                blockers.append({"category": name, "issue": issue})
        if result.get("critical_blockers"):
            blockers.extend(
                {"category": name, "issue": blocker}
                for blocker in result.get("critical_blockers", [])
            )
        if result.get("compliance_gaps"):
            blockers.extend(
                {"category": name, "issue": gap} for gap in result.get("compliance_gaps", [])
            )
    return blockers
