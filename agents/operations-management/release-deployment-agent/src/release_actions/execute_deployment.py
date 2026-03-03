"""Action handler: execute_deployment."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from release_utils import (
    build_pipeline_steps,
    capture_deployment_artifacts,
    ensure_environment_reserved,
    persist_deployment_log,
    publish_event,
    record_deployment_history,
    release_environment_allocation,
    trigger_azure_devops_pipeline,
    trigger_github_actions_workflow,
)

if TYPE_CHECKING:
    from release_models import ReleaseAgentProtocol


async def execute_deployment(
    agent: ReleaseAgentProtocol,
    deployment_plan_id: str,
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """
    Execute deployment workflow.

    Returns deployment status and progress.
    """
    agent.logger.info("Executing deployment: %s", deployment_plan_id)

    deployment_plan = agent.deployment_plans.get(deployment_plan_id)
    if not deployment_plan:
        raise ValueError(f"Deployment plan not found: {deployment_plan_id}")

    assert deployment_plan is not None and isinstance(deployment_plan, dict)

    release_id = deployment_plan.get("release_id")
    release = agent.releases.get(release_id)
    assert release is not None and isinstance(release, dict), "Release not found"

    if agent.enforce_readiness_gates:
        # Import here to avoid circular dependency at module level
        from release_actions.assess_readiness import assess_readiness

        readiness = await assess_readiness(agent, release_id)
        if readiness.get("recommendation") != "GO":
            if release.get("approval_required"):
                return {
                    "deployment_plan_id": deployment_plan_id,
                    "release_id": release_id,
                    "status": "Pending Approval",
                    "readiness": readiness,
                    "next_steps": "Await release approval before deployment.",
                }
            return {
                "deployment_plan_id": deployment_plan_id,
                "release_id": release_id,
                "status": "Blocked",
                "readiness": readiness,
                "next_steps": "Resolve readiness gate failures before deployment.",
            }

    if release.get("approval_required"):
        approval = release.get("approval")
        if approval is None:
            if not agent.approval_agent:
                return {
                    "deployment_plan_id": deployment_plan_id,
                    "release_id": release_id,
                    "status": "Blocked",
                    "error": "Approval agent not configured",
                    "next_steps": "Configure approval workflow before deployment.",
                }
            approval = await agent.approval_agent.process(
                {
                    "request_type": "phase_gate",
                    "request_id": release_id,
                    "requester": release.get("created_by", "unknown"),
                    "details": {
                        "description": release.get("description"),
                        "environment": release.get("target_environment"),
                        "planned_date": release.get("planned_date"),
                        "urgency": "medium",
                    },
                    "tenant_id": tenant_id,
                    "correlation_id": correlation_id,
                }
            )
            release["approval"] = approval
            release["approval_status"] = approval.get("status")
            agent.release_store.upsert(tenant_id, release_id, release)

        if release.get("approval_status") != "approved":
            return {
                "deployment_plan_id": deployment_plan_id,
                "release_id": release_id,
                "status": "Pending Approval",
                "approval": release.get("approval"),
                "next_steps": "Await release approval before deployment.",
            }

    # Update status
    deployment_plan["status"] = "In Progress"
    deployment_plan["started_at"] = datetime.now(timezone.utc).isoformat()
    await ensure_environment_reserved(agent, release_id, deployment_plan)
    await publish_event(
        agent,
        "deployment.started",
        {
            "deployment_plan_id": deployment_plan_id,
            "release_id": release_id,
            "environment": deployment_plan.get("environment"),
            "strategy": deployment_plan.get("strategy"),
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "status": deployment_plan["status"],
        },
    )

    # Execute pre-deployment tasks
    pre_deployment_results = await _execute_pre_deployment_tasks(
        agent,
        deployment_plan.get("pre_deployment_tasks", []),
        deployment_plan_id=deployment_plan_id,
    )

    if not pre_deployment_results.get("success"):
        deployment_plan["status"] = "Failed"
        await publish_event(
            agent,
            "deployment.failed",
            {
                "deployment_plan_id": deployment_plan_id,
                "release_id": release_id,
                "environment": deployment_plan.get("environment"),
                "strategy": deployment_plan.get("strategy"),
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "status": deployment_plan["status"],
                "error": "Pre-deployment tasks failed",
            },
        )
        await release_environment_allocation(agent, release_id, deployment_plan_id)
        return {
            "deployment_plan_id": deployment_plan_id,
            "status": "Failed",
            "error": "Pre-deployment tasks failed",
            "details": pre_deployment_results,
        }

    deployment_results = await _orchestrate_deployment(
        agent, deployment_plan, tenant_id=tenant_id, correlation_id=correlation_id
    )

    if not deployment_results.get("success"):
        # Check if auto-rollback is needed
        if await _should_auto_rollback(agent, deployment_results):
            agent.logger.warning("Auto-rollback triggered")
            from actions.rollback_deployment import rollback_deployment

            await rollback_deployment(agent, deployment_plan_id)

        deployment_plan["status"] = "Failed"
        await publish_event(
            agent,
            "deployment.failed",
            {
                "deployment_plan_id": deployment_plan_id,
                "release_id": release_id,
                "environment": deployment_plan.get("environment"),
                "strategy": deployment_plan.get("strategy"),
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "status": deployment_plan["status"],
                "error": "Deployment steps failed",
            },
        )
        await release_environment_allocation(agent, release_id, deployment_plan_id)
        return {
            "deployment_plan_id": deployment_plan_id,
            "status": "Failed",
            "error": "Deployment steps failed",
            "details": deployment_results,
            "rollback_triggered": True,
        }

    # Execute post-deployment verification
    verification_results = await _execute_post_deployment_verification(
        agent,
        deployment_plan.get("post_deployment_verification", []),
        deployment_plan_id=deployment_plan_id,
    )

    if not verification_results.get("success") and agent.auto_rollback_on_anomaly:
        agent.logger.warning("Post-deployment verification failed; triggering rollback")
        from actions.rollback_deployment import rollback_deployment

        await rollback_deployment(agent, deployment_plan_id)

    # Update deployment plan and release
    deployment_plan["status"] = "Completed" if verification_results.get("success") else "Failed"
    deployment_plan["completed_at"] = datetime.now(timezone.utc).isoformat()

    if verification_results.get("success"):
        release["status"] = "Deployed"
        release["actual_date"] = datetime.now(timezone.utc).isoformat()

    # Persist updates to database
    await agent.db_service.store("deployment_plans", deployment_plan_id, deployment_plan)
    await agent.db_service.store("releases", release_id, release)
    await release_environment_allocation(agent, release_id, deployment_plan_id)

    await record_deployment_history(
        agent,
        deployment_plan,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        status=deployment_plan["status"],
    )

    await publish_event(
        agent,
        "deployment.succeeded" if verification_results.get("success") else "deployment.failed",
        {
            "deployment_plan_id": deployment_plan_id,
            "release_id": release_id,
            "environment": deployment_plan.get("environment"),
            "strategy": deployment_plan.get("strategy"),
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "status": deployment_plan["status"],
            "completed_at": deployment_plan.get("completed_at"),
        },
    )

    return {
        "deployment_plan_id": deployment_plan_id,
        "release_id": release_id,
        "status": deployment_plan["status"],
        "started_at": deployment_plan["started_at"],
        "completed_at": deployment_plan.get("completed_at"),
        "pre_deployment": pre_deployment_results,
        "deployment": deployment_results,
        "verification": verification_results,
        "next_steps": "Monitor application health and generate release notes",
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _execute_pre_deployment_tasks(
    agent: ReleaseAgentProtocol,
    tasks: list[dict[str, Any]],
    *,
    deployment_plan_id: str,
) -> dict[str, Any]:
    """Execute pre-deployment tasks."""
    completed = 0
    for task in tasks:
        await publish_event(
            agent,
            "deployment.progress",
            {
                "deployment_plan_id": deployment_plan_id,
                "phase": "pre_deployment",
                "task": task.get("task"),
                "status": "started",
            },
        )
        if task.get("should_fail"):
            await publish_event(
                agent,
                "deployment.progress",
                {
                    "deployment_plan_id": deployment_plan_id,
                    "phase": "pre_deployment",
                    "task": task.get("task"),
                    "status": "failed",
                },
            )
            return {"success": False, "completed_tasks": completed, "failed_task": task}
        completed += 1
        await publish_event(
            agent,
            "deployment.progress",
            {
                "deployment_plan_id": deployment_plan_id,
                "phase": "pre_deployment",
                "task": task.get("task"),
                "status": "completed",
            },
        )
    return {"success": True, "completed_tasks": completed}


async def _execute_deployment_steps(
    agent: ReleaseAgentProtocol,
    steps: list[dict[str, Any]],
    *,
    deployment_plan: dict[str, Any],
) -> dict[str, Any]:
    """Execute deployment steps."""
    strategy = deployment_plan.get("strategy", "rolling")
    pipeline_steps = await build_pipeline_steps(strategy, steps, deployment_plan)
    completed_steps: list[dict[str, Any]] = []
    failure_step = None
    for step in pipeline_steps:
        await publish_event(
            agent,
            "deployment.progress",
            {
                "deployment_plan_id": deployment_plan.get("deployment_plan_id"),
                "phase": "deployment",
                "strategy": strategy,
                "step": step.get("action") or step.get("step"),
                "status": "started",
            },
        )
        if step.get("should_fail"):
            failure_step = step
            await publish_event(
                agent,
                "deployment.progress",
                {
                    "deployment_plan_id": deployment_plan.get("deployment_plan_id"),
                    "phase": "deployment",
                    "strategy": strategy,
                    "step": step.get("action") or step.get("step"),
                    "status": "failed",
                },
            )
            break
        completed_steps.append(step)
        await publish_event(
            agent,
            "deployment.progress",
            {
                "deployment_plan_id": deployment_plan.get("deployment_plan_id"),
                "phase": "deployment",
                "strategy": strategy,
                "step": step.get("action") or step.get("step"),
                "status": "completed",
            },
        )
    success = failure_step is None
    failure_rate = 0.0 if success else 1.0
    return {
        "success": success,
        "completed_steps": len(completed_steps),
        "steps": completed_steps,
        "failure_step": failure_step,
        "failure_rate": failure_rate,
        "strategy": strategy,
    }


async def _execute_post_deployment_verification(
    agent: ReleaseAgentProtocol,
    checks: list[dict[str, Any]],
    *,
    deployment_plan_id: str,
) -> dict[str, Any]:
    """Execute post-deployment verification."""
    passed = 0
    for check in checks:
        await publish_event(
            agent,
            "deployment.progress",
            {
                "deployment_plan_id": deployment_plan_id,
                "phase": "post_deployment",
                "check": check.get("check"),
                "status": "started",
            },
        )
        if check.get("should_fail"):
            await publish_event(
                agent,
                "deployment.progress",
                {
                    "deployment_plan_id": deployment_plan_id,
                    "phase": "post_deployment",
                    "check": check.get("check"),
                    "status": "failed",
                },
            )
            return {"success": False, "passed_checks": passed, "failed_check": check}
        passed += 1
        await publish_event(
            agent,
            "deployment.progress",
            {
                "deployment_plan_id": deployment_plan_id,
                "phase": "post_deployment",
                "check": check.get("check"),
                "status": "completed",
            },
        )
    return {"success": True, "passed_checks": passed}


async def _should_auto_rollback(
    agent: ReleaseAgentProtocol, deployment_results: dict[str, Any]
) -> bool:
    """Determine if auto-rollback should be triggered."""
    failure_rate = float(deployment_results.get("failure_rate", 0))
    return cast(bool, failure_rate > agent.auto_rollback_threshold)  # type: ignore


async def _orchestrate_deployment(
    agent: ReleaseAgentProtocol,
    deployment_plan: dict[str, Any],
    *,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Orchestrate deployment via Durable Functions and CI/CD pipelines."""
    steps = deployment_plan.get("deployment_steps", [])
    orchestrator_payload = {
        "deployment_plan_id": deployment_plan.get("deployment_plan_id"),
        "steps": steps,
        "tenant_id": tenant_id,
        "correlation_id": correlation_id,
    }

    pipeline_results = []
    if agent.azure_devops_client:
        pipeline_results.append(
            await trigger_azure_devops_pipeline(agent, deployment_plan, orchestrator_payload)
        )
    if agent.github_actions_client:
        pipeline_results.append(
            await trigger_github_actions_workflow(agent, deployment_plan, orchestrator_payload)
        )

    if agent.durable_functions_client and hasattr(agent.durable_functions_client, "orchestrate"):
        orchestration = await agent.durable_functions_client.orchestrate(orchestrator_payload)
    else:
        orchestration = {"orchestration_id": str(uuid.uuid4()), "status": "completed"}

    step_results = await _execute_deployment_steps(agent, steps, deployment_plan=deployment_plan)
    await capture_deployment_artifacts(agent, deployment_plan, pipeline_results, step_results)
    await persist_deployment_log(
        agent,
        deployment_plan,
        {
            "pipelines": pipeline_results,
            "steps": step_results.get("steps"),
            "orchestration": orchestration,
        },
    )
    success = step_results.get("success", False) and all(
        result.get("status") in {"queued", "success", "completed"}
        for result in pipeline_results
    )
    return {
        "success": success,
        "completed_steps": step_results.get("completed_steps", 0),
        "pipelines": pipeline_results,
        "durable_functions": orchestration,
    }
