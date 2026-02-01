"""
Agent 18: Release & Deployment Agent

Purpose:
Manages the planning, coordination and execution of software and project deliverable releases
across environments. Ensures controlled deployments with minimal risk and downtime.

Specification: agents/operations-management/agent-18-release-deployment/README.md
"""

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from agents.common.connector_integration import (
    DatabaseStorageService,
    DocumentationPublishingService,
)
from agents.runtime import BaseAgent
from agents.runtime import get_event_bus
from agents.runtime.src.state_store import TenantStateStore


class ReleaseDeploymentAgent(BaseAgent):
    """
    Release & Deployment Agent - Orchestrates release planning and deployment workflows.

    Key Capabilities:
    - Release planning and scheduling
    - Release readiness assessment and go/no-go checks
    - Deployment orchestration across environments
    - Environment management and configuration tracking
    - Release approvals and gating
    - Change and incident coordination
    - Release documentation and communication
    - Deployment metrics and reporting
    """

    def __init__(self, agent_id: str = "agent_018", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.environments = (
            config.get("environments", ["development", "test", "staging", "production"])
            if config
            else ["development", "test", "staging", "production"]
        )

        self.auto_rollback_threshold = (
            config.get("auto_rollback_threshold", 0.05) if config else 0.05
        )
        self.deployment_window_hours = config.get("deployment_window_hours", 4) if config else 4
        self.approval_environments = (
            config.get("approval_environments", ["production"]) if config else ["production"]
        )

        release_store_path = (
            Path(config.get("release_store_path", "data/release_calendar.json"))
            if config
            else Path("data/release_calendar.json")
        )
        deployment_plan_store_path = (
            Path(config.get("deployment_plan_store_path", "data/deployment_plans.json"))
            if config
            else Path("data/deployment_plans.json")
        )
        self.release_store = TenantStateStore(release_store_path)
        self.deployment_plan_store = TenantStateStore(deployment_plan_store_path)

        # Data stores (will be replaced with database)
        self.releases: dict[str, Any] = {}
        self.deployment_plans: dict[str, Any] = {}
        self.environments_inventory: dict[str, Any] = {}
        self.release_notes: dict[str, Any] = {}
        self.deployment_metrics: dict[str, Any] = {}
        self.enforce_readiness_gates = (
            config.get("enforce_readiness_gates", True) if config else True
        )
        self.auto_rollback_on_anomaly = (
            config.get("auto_rollback_on_anomaly", True) if config else True
        )

        self.quality_agent = config.get("quality_agent") if config else None
        self.change_agent = config.get("change_agent") if config else None
        self.risk_agent = config.get("risk_agent") if config else None
        self.compliance_agent = config.get("compliance_agent") if config else None
        self.schedule_agent = config.get("schedule_agent") if config else None
        self.schedule_agent_action = (
            config.get("schedule_agent_action", "suggest_deployment_window") if config else None
        )

        self.azure_devops_client = config.get("azure_devops_client") if config else None
        self.github_actions_client = config.get("github_actions_client") if config else None
        self.durable_functions_client = config.get("durable_functions_client") if config else None
        self.azure_policy_client = config.get("azure_policy_client") if config else None
        self.openai_client = config.get("openai_client") if config else None
        self.environment_reservation_client = (
            config.get("environment_reservation_client") if config else None
        )
        self.monitoring_client = config.get("monitoring_client") if config else None
        self.analytics_client = config.get("analytics_client") if config else None
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            try:
                self.event_bus = get_event_bus()
            except ValueError:
                self.event_bus = None
        self.approval_agent = config.get("approval_agent") if config else None
        if self.approval_agent is None:
            approval_config = config.get("approval_agent_config") if config else None
            if approval_config:
                from approval_workflow_agent import ApprovalWorkflowAgent

                self.approval_agent = ApprovalWorkflowAgent(config=approval_config)

        self.environment_allocations: dict[str, dict[str, Any]] = {}
        self.deployment_logs: dict[str, list[dict[str, Any]]] = {}
        self.deployment_artifacts: dict[str, list[dict[str, Any]]] = {}

    async def initialize(self) -> None:
        """Initialize deployment orchestration, CI/CD integrations, and monitoring."""
        await super().initialize()
        self.logger.info("Initializing Release & Deployment Agent...")

        # Initialize Documentation Publishing Service (Confluence, SharePoint)
        doc_config = self.config.get("documentation_publishing", {}) if self.config else {}
        self.doc_publishing_service = DocumentationPublishingService(doc_config)
        self.logger.info("Documentation Publishing Service initialized")

        # Initialize Database Storage Service (Azure SQL, Cosmos DB, or JSON fallback)
        db_config = self.config.get("database_storage", {}) if self.config else {}
        self.db_service = DatabaseStorageService(db_config)
        self.logger.info("Database Storage Service initialized")

        if self.event_bus and hasattr(self.event_bus, "subscribe"):
            self.event_bus.subscribe("system.health.updated", self._handle_system_health_event)
            self.event_bus.subscribe("analytics.deployment.metrics", self._handle_analytics_event)

        self.logger.info("Release & Deployment Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "plan_release",
            "assess_readiness",
            "create_deployment_plan",
            "execute_deployment",
            "rollback_deployment",
            "manage_environment",
            "check_configuration_drift",
            "generate_release_notes",
            "track_deployment_metrics",
            "schedule_deployment_window",
            "verify_post_deployment",
            "get_release_calendar",
            "get_release_status",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "plan_release":
            release_data = input_data.get("release", {})
            if not release_data.get("name") or not release_data.get("target_environment"):
                self.logger.warning("Missing required release fields")
                return False

        elif action == "execute_deployment":
            if "deployment_plan_id" not in input_data:
                self.logger.warning("Missing deployment_plan_id")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process release and deployment management requests.

        Args:
            input_data: {
                "action": "plan_release" | "assess_readiness" | "create_deployment_plan" |
                          "execute_deployment" | "rollback_deployment" | "manage_environment" |
                          "check_configuration_drift" | "generate_release_notes" |
                          "track_deployment_metrics" | "schedule_deployment_window" |
                          "verify_post_deployment" | "get_release_calendar" | "get_release_status",
                "release": Release data for planning,
                "release_id": Release identifier,
                "deployment_plan": Deployment plan details,
                "deployment_plan_id": Deployment plan ID,
                "environment": Environment details,
                "environment_id": Environment identifier,
                "verification_params": Post-deployment verification parameters,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - plan_release: Release ID, schedule, and calendar entry
            - assess_readiness: Readiness status and go/no-go assessment
            - create_deployment_plan: Deployment plan ID and workflow steps
            - execute_deployment: Deployment status and progress
            - rollback_deployment: Rollback status and restored state
            - manage_environment: Environment ID and configuration
            - check_configuration_drift: Drift detection results
            - generate_release_notes: Generated release notes
            - track_deployment_metrics: Deployment metrics and KPIs
            - schedule_deployment_window: Scheduled window and conflicts
            - verify_post_deployment: Verification results
            - get_release_calendar: Release calendar view
            - get_release_status: Detailed release status
        """
        action = input_data.get("action", "get_release_calendar")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        actor_id = context.get("user_id") or input_data.get("actor_id") or "system"

        if action == "plan_release":
            return await self._plan_release(
                input_data.get("release", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "assess_readiness":
            release_id = input_data.get("release_id")
            assert isinstance(release_id, str), "release_id must be a string"
            return await self._assess_readiness(release_id)

        elif action == "create_deployment_plan":
            release_id = input_data.get("release_id")
            assert isinstance(release_id, str), "release_id must be a string"
            return await self._create_deployment_plan(
                release_id,
                input_data.get("deployment_plan", {}),
                tenant_id=tenant_id,
            )

        elif action == "execute_deployment":
            deployment_plan_id = input_data.get("deployment_plan_id")
            assert isinstance(deployment_plan_id, str), "deployment_plan_id must be a string"
            return await self._execute_deployment(
                deployment_plan_id,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "rollback_deployment":
            deployment_plan_id = input_data.get("deployment_plan_id")
            assert isinstance(deployment_plan_id, str), "deployment_plan_id must be a string"
            return await self._rollback_deployment(deployment_plan_id)

        elif action == "manage_environment":
            return await self._manage_environment(input_data.get("environment", {}))

        elif action == "check_configuration_drift":
            environment_id = input_data.get("environment_id")
            assert isinstance(environment_id, str), "environment_id must be a string"
            return await self._check_configuration_drift(environment_id)

        elif action == "generate_release_notes":
            release_id = input_data.get("release_id")
            assert isinstance(release_id, str), "release_id must be a string"
            return await self._generate_release_notes(release_id)

        elif action == "track_deployment_metrics":
            release_id = input_data.get("release_id")
            assert isinstance(release_id, str), "release_id must be a string"
            return await self._track_deployment_metrics(release_id)

        elif action == "schedule_deployment_window":
            release_id = input_data.get("release_id")
            assert isinstance(release_id, str), "release_id must be a string"
            return await self._schedule_deployment_window(
                release_id, input_data.get("preferred_window", {})
            )

        elif action == "verify_post_deployment":
            deployment_plan_id = input_data.get("deployment_plan_id")
            assert isinstance(deployment_plan_id, str), "deployment_plan_id must be a string"
            return await self._verify_post_deployment(
                deployment_plan_id, input_data.get("verification_params", {})
            )

        elif action == "get_release_calendar":
            return await self._get_release_calendar(input_data.get("filters", {}))

        elif action == "get_release_status":
            release_id = input_data.get("release_id")
            assert isinstance(release_id, str), "release_id must be a string"
            return await self._get_release_status(release_id)

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _plan_release(
        self,
        release_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Plan a new release and add to calendar.

        Returns release ID and schedule.
        """
        self.logger.info(f"Planning release: {release_data.get('name')}")

        # Generate release ID
        release_id = await self._generate_release_id()

        target_environment = release_data.get("target_environment")
        planned_date = release_data.get("planned_date")
        assert isinstance(target_environment, str), "target_environment must be a string"
        assert isinstance(planned_date, str), "planned_date must be a string"

        # Check for environment availability
        env_availability = await self._check_environment_availability(
            target_environment, planned_date, release_id
        )

        # Detect scheduling conflicts
        conflicts = await self._detect_scheduling_conflicts(planned_date, target_environment)

        # Suggest alternative windows if conflicts exist
        alternative_windows: list[dict[str, Any]] = []
        if conflicts:
            alternative_windows = await self._suggest_alternative_windows(
                planned_date, target_environment
            )

        approval_required = target_environment in self.approval_environments
        approval_payload = None
        if approval_required:
            if self.approval_agent:
                approval_payload = await self.approval_agent.process(
                    {
                        "request_type": "phase_gate",
                        "request_id": release_id,
                        "requester": release_data.get("requester", actor_id),
                        "details": {
                            "description": release_data.get("description"),
                            "environment": target_environment,
                            "planned_date": planned_date,
                            "urgency": release_data.get("urgency", "medium"),
                        },
                        "tenant_id": tenant_id,
                        "correlation_id": correlation_id,
                    }
                )

        # Create release record
        release = {
            "release_id": release_id,
            "name": release_data.get("name"),
            "description": release_data.get("description"),
            "target_environment": release_data.get("target_environment"),
            "planned_date": release_data.get("planned_date"),
            "actual_date": None,
            "project_ids": release_data.get("project_ids", []),
            "change_requests": release_data.get("change_requests", []),
            "status": "Planned",
            "approval_required": approval_required,
            "approval": approval_payload,
            "approval_status": (
                approval_payload.get("status")
                if approval_payload
                else ("not_required" if not approval_required else "not_configured")
            ),
            "environment_available": env_availability,
            "conflicts": conflicts,
            "alternative_windows": alternative_windows,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": release_data.get("requester", "unknown"),
        }

        # Store release
        self.releases[release_id] = release
        self.release_store.upsert(tenant_id, release_id, release)

        # Persist to database
        await self.db_service.store("releases", release_id, release)

        return {
            "release_id": release_id,
            "name": release["name"],
            "planned_date": release["planned_date"],
            "target_environment": release["target_environment"],
            "environment_available": env_availability,
            "conflicts": conflicts,
            "alternative_windows": alternative_windows,
            "approval_required": approval_required,
            "approval": approval_payload,
            "next_steps": "Create deployment plan and assess readiness",
        }

    async def _assess_readiness(self, release_id: str) -> dict[str, Any]:
        """
        Assess release readiness with go/no-go criteria.

        Returns readiness assessment and recommendations.
        """
        self.logger.info(f"Assessing readiness for release: {release_id}")

        release = self.releases.get(release_id)
        if not release:
            raise ValueError(f"Release not found: {release_id}")

        quality_check = await self._check_quality_criteria(release_id)
        approval_check = await self._check_approval_status(release_id)
        change_check = await self._check_change_approvals(release_id)
        risk_check = await self._check_risk_level(release_id)
        compliance_check = await self._check_compliance_requirements(release_id)

        critical_blockers = await self._collect_readiness_blockers(
            {
                "quality": quality_check,
                "approval": approval_check,
                "change": change_check,
                "risk": risk_check,
                "compliance": compliance_check,
            }
        )

        # Calculate overall readiness score
        readiness_criteria = {
            "quality_passed": quality_check.get("passed", False),
            "approvals_complete": approval_check.get("complete", False),
            "changes_approved": change_check.get("approved", False),
            "risk_acceptable": risk_check.get("acceptable", False),
            "compliance_met": compliance_check.get("met", False),
        }

        all_passed = all(readiness_criteria.values()) and not critical_blockers
        readiness_score = sum(1 for v in readiness_criteria.values() if v) / len(readiness_criteria)

        # Generate go/no-go recommendation
        recommendation = "GO" if all_passed else "NO-GO"

        # Future work: Store assessment results

        return {
            "release_id": release_id,
            "readiness_score": readiness_score,
            "recommendation": recommendation,
            "criteria": readiness_criteria,
            "quality_details": quality_check,
            "approval_details": approval_check,
            "change_details": change_check,
            "risk_details": risk_check,
            "compliance_details": compliance_check,
            "critical_blockers": critical_blockers,
            "next_steps": "Proceed with deployment" if all_passed else "Address failing criteria",
        }

    async def _create_deployment_plan(
        self,
        release_id: str,
        plan_data: dict[str, Any],
        *,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        Create detailed deployment plan with workflow steps.

        Returns deployment plan ID and workflow.
        """
        self.logger.info(f"Creating deployment plan for release: {release_id}")

        release = self.releases.get(release_id)
        if not release:
            raise ValueError(f"Release not found: {release_id}")

        # Generate deployment plan ID
        plan_id = await self._generate_deployment_plan_id()

        # Define deployment steps
        deployment_steps = await self._define_deployment_steps(
            release, plan_data.get("custom_steps", [])
        )

        # Define pre-deployment tasks
        pre_deployment = await self._define_pre_deployment_tasks(release)

        # Define post-deployment verification
        post_deployment = await self._define_post_deployment_verification(release)

        # Define rollback procedures
        rollback_steps = await self._define_rollback_procedures(release)

        # Create deployment plan
        deployment_plan = {
            "deployment_plan_id": plan_id,
            "release_id": release_id,
            "environment": release.get("target_environment"),
            "strategy": plan_data.get("strategy") or release.get("deployment_strategy", "rolling"),
            "traffic_steps": plan_data.get("traffic_steps"),
            "pre_deployment_tasks": pre_deployment,
            "deployment_steps": deployment_steps,
            "post_deployment_verification": post_deployment,
            "rollback_procedures": rollback_steps,
            "estimated_duration_minutes": await self._estimate_deployment_duration(
                deployment_steps
            ),
            "responsible_owner": plan_data.get("owner"),
            "status": "Draft",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store deployment plan
        self.deployment_plans[plan_id] = deployment_plan
        self.deployment_plan_store.upsert(tenant_id, plan_id, deployment_plan)

        # Persist to database
        await self.db_service.store("deployment_plans", plan_id, deployment_plan)

        return {
            "deployment_plan_id": plan_id,
            "release_id": release_id,
            "environment": deployment_plan["environment"],
            "strategy": deployment_plan["strategy"],
            "total_steps": len(deployment_steps),
            "estimated_duration_minutes": deployment_plan["estimated_duration_minutes"],
            "pre_deployment_tasks": len(pre_deployment),
            "post_deployment_checks": len(post_deployment),
            "next_steps": "Review and execute deployment plan",
        }

    async def _execute_deployment(
        self,
        deployment_plan_id: str,
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Execute deployment workflow.

        Returns deployment status and progress.
        """
        self.logger.info(f"Executing deployment: {deployment_plan_id}")

        deployment_plan = self.deployment_plans.get(deployment_plan_id)
        if not deployment_plan:
            raise ValueError(f"Deployment plan not found: {deployment_plan_id}")

        assert deployment_plan is not None and isinstance(deployment_plan, dict)

        release_id = deployment_plan.get("release_id")
        release = self.releases.get(release_id)
        assert release is not None and isinstance(release, dict), "Release not found"

        if self.enforce_readiness_gates:
            readiness = await self._assess_readiness(release_id)
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
                if not self.approval_agent:
                    return {
                        "deployment_plan_id": deployment_plan_id,
                        "release_id": release_id,
                        "status": "Blocked",
                        "error": "Approval agent not configured",
                        "next_steps": "Configure approval workflow before deployment.",
                    }
                approval = await self.approval_agent.process(
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
                self.release_store.upsert(tenant_id, release_id, release)

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
        deployment_plan["started_at"] = datetime.utcnow().isoformat()
        await self._publish_event(
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
        pre_deployment_results = await self._execute_pre_deployment_tasks(
            deployment_plan.get("pre_deployment_tasks", []),
            deployment_plan_id=deployment_plan_id,
        )

        if not pre_deployment_results.get("success"):
            deployment_plan["status"] = "Failed"
            await self._publish_event(
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
            await self._release_environment_allocation(release_id, deployment_plan_id)
            return {
                "deployment_plan_id": deployment_plan_id,
                "status": "Failed",
                "error": "Pre-deployment tasks failed",
                "details": pre_deployment_results,
            }

        deployment_results = await self._orchestrate_deployment(
            deployment_plan, tenant_id=tenant_id, correlation_id=correlation_id
        )

        if not deployment_results.get("success"):
            # Check if auto-rollback is needed
            if await self._should_auto_rollback(deployment_results):
                self.logger.warning("Auto-rollback triggered")
                await self._rollback_deployment(deployment_plan_id)

            deployment_plan["status"] = "Failed"
            await self._publish_event(
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
            await self._release_environment_allocation(release_id, deployment_plan_id)
            return {
                "deployment_plan_id": deployment_plan_id,
                "status": "Failed",
                "error": "Deployment steps failed",
                "details": deployment_results,
                "rollback_triggered": True,
            }

        # Execute post-deployment verification
        verification_results = await self._execute_post_deployment_verification(
            deployment_plan.get("post_deployment_verification", []),
            deployment_plan_id=deployment_plan_id,
        )

        if not verification_results.get("success") and self.auto_rollback_on_anomaly:
            self.logger.warning("Post-deployment verification failed; triggering rollback")
            await self._rollback_deployment(deployment_plan_id)

        # Update deployment plan and release
        deployment_plan["status"] = "Completed" if verification_results.get("success") else "Failed"
        deployment_plan["completed_at"] = datetime.utcnow().isoformat()

        if verification_results.get("success"):
            release["status"] = "Deployed"
            release["actual_date"] = datetime.utcnow().isoformat()

        # Persist updates to database
        await self.db_service.store("deployment_plans", deployment_plan_id, deployment_plan)
        await self.db_service.store("releases", release_id, release)
        await self._release_environment_allocation(release_id, deployment_plan_id)

        await self._publish_event(
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

    async def _rollback_deployment(self, deployment_plan_id: str) -> dict[str, Any]:
        """
        Execute rollback procedures.

        Returns rollback status.
        """
        self.logger.info(f"Rolling back deployment: {deployment_plan_id}")

        deployment_plan = self.deployment_plans.get(deployment_plan_id)
        if not deployment_plan:
            raise ValueError(f"Deployment plan not found: {deployment_plan_id}")

        # Execute rollback steps
        rollback_steps = deployment_plan.get("rollback_procedures", [])
        rollback_results = await self._execute_rollback_steps(rollback_steps)

        # Update status
        deployment_plan["rollback_executed"] = True
        deployment_plan["rollback_at"] = datetime.utcnow().isoformat()
        deployment_plan["status"] = "Rolled Back"

        # Persist to database
        await self.db_service.store("deployment_plans", deployment_plan_id, deployment_plan)

        await self._publish_event(
            "deployment.failed",
            {
                "deployment_plan_id": deployment_plan_id,
                "release_id": deployment_plan.get("release_id"),
                "environment": deployment_plan.get("environment"),
                "strategy": deployment_plan.get("strategy"),
                "status": deployment_plan["status"],
                "rollback_executed": rollback_results.get("success", False),
            },
        )

        return {
            "deployment_plan_id": deployment_plan_id,
            "rollback_status": "Success" if rollback_results.get("success") else "Failed",
            "rollback_results": rollback_results,
            "next_steps": "Investigate root cause and plan remediation",
        }

    async def _manage_environment(self, environment_data: dict[str, Any]) -> dict[str, Any]:
        """
        Manage environment configuration and status.

        Returns environment ID and details.
        """
        self.logger.info(f"Managing environment: {environment_data.get('name')}")

        # Generate environment ID
        env_id = await self._generate_environment_id()

        # Create environment record
        environment = {
            "environment_id": env_id,
            "name": environment_data.get("name"),
            "type": environment_data.get("type"),
            "configuration": environment_data.get("configuration", {}),
            "version": environment_data.get("version"),
            "status": environment_data.get("status", "Available"),
            "owner": environment_data.get("owner"),
            "reserved_by": None,
            "reserved_until": None,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store environment
        self.environments_inventory[env_id] = environment

        # Persist to database
        await self.db_service.store("environments", env_id, environment)

        return {
            "environment_id": env_id,
            "name": environment["name"],
            "type": environment["type"],
            "status": environment["status"],
            "configuration": environment["configuration"],
        }

    async def _check_configuration_drift(self, environment_id: str) -> dict[str, Any]:
        """
        Detect configuration drift between environments.

        Returns drift analysis.
        """
        self.logger.info(f"Checking configuration drift for environment: {environment_id}")

        environment = self.environments_inventory.get(environment_id)
        if not environment:
            raise ValueError(f"Environment not found: {environment_id}")

        # Get baseline configuration
        baseline_config = await self._get_baseline_configuration(environment.get("type"))

        policy_results = await self._check_azure_policy_compliance(environment)
        drift_items = await self._compare_configurations(
            environment.get("configuration", {}), baseline_config
        )
        policy_drift_items = policy_results.get("drift_items", [])

        combined_drift = drift_items + policy_drift_items
        drift_detected = len(combined_drift) > 0

        return {
            "environment_id": environment_id,
            "drift_detected": drift_detected,
            "drift_items": combined_drift,
            "drift_count": len(combined_drift),
            "baseline_version": baseline_config.get("version"),
            "policy_compliance": policy_results.get("compliance_state"),
            "recommendations": await self._generate_drift_recommendations(combined_drift),
        }

    async def _generate_release_notes(self, release_id: str) -> dict[str, Any]:
        """
        Generate release notes using NLG.

        Returns formatted release notes.
        """
        self.logger.info(f"Generating release notes for: {release_id}")

        release = self.releases.get(release_id)
        if not release:
            raise ValueError(f"Release not found: {release_id}")

        # Gather release information
        changes = await self._gather_release_changes(release_id)
        features = await self._gather_release_features(release_id)
        bug_fixes = await self._gather_release_bug_fixes(release_id)
        known_issues = await self._gather_known_issues(release_id)

        # Generate notes using AI
        release_notes_content = await self._generate_notes_content(
            release, changes, features, bug_fixes, known_issues
        )

        # Create release notes record
        notes_id = await self._generate_release_notes_id()
        release_notes = {
            "notes_id": notes_id,
            "release_id": release_id,
            "content": release_notes_content,
            "features": features,
            "bug_fixes": bug_fixes,
            "known_issues": known_issues,
            "related_tickets": changes,
            "generated_at": datetime.utcnow().isoformat(),
        }

        self.release_notes[notes_id] = release_notes

        # Persist to database
        await self.db_service.store("release_notes", notes_id, release_notes)

        # Publish to documentation repository (Confluence or SharePoint)
        publish_result = await self.doc_publishing_service.publish_release_notes(
            release_id=release_id,
            release_name=release.get("name", release_id),
            content=release_notes_content,
            metadata={
                "environment": release.get("target_environment"),
                "tags": ["release-notes", release.get("target_environment", "")],
            },
        )
        release_notes["published_url"] = publish_result.get("url")
        release_notes["published_platform"] = publish_result.get("platform")

        return {
            "notes_id": notes_id,
            "release_id": release_id,
            "content": release_notes_content,
            "features_count": len(features),
            "bug_fixes_count": len(bug_fixes),
            "known_issues_count": len(known_issues),
            "published_url": publish_result.get("url"),
            "published_platform": publish_result.get("platform"),
        }

    async def _track_deployment_metrics(self, release_id: str) -> dict[str, Any]:
        """
        Track and analyze deployment metrics.

        Returns deployment KPIs.
        """
        self.logger.info(f"Tracking deployment metrics for release: {release_id}")

        # Calculate deployment metrics
        metrics = {
            "deployment_frequency": await self._calculate_deployment_frequency(),
            "lead_time_for_changes": await self._calculate_lead_time(release_id),
            "mean_time_to_deploy": await self._calculate_mean_time_to_deploy(release_id),
            "mean_time_to_restore": await self._calculate_mttr(),
            "deployment_success_rate": await self._calculate_success_rate(),
            "rollback_rate": await self._calculate_rollback_rate(),
            "change_failure_rate": await self._calculate_change_failure_rate(),
            "environment_utilization": await self._calculate_environment_utilization(),
        }
        anomalies = await self._detect_metric_anomalies(metrics)

        # Store metrics
        metrics_record = {
            "release_id": release_id,
            "metrics": metrics,
            "anomalies": anomalies,
            "calculated_at": datetime.utcnow().isoformat(),
        }
        self.deployment_metrics[release_id] = metrics_record

        # Persist to database
        await self.db_service.store("deployment_metrics", f"metrics-{release_id}", metrics_record)
        await self._publish_event(
            "analytics.deployment.metrics",
            {
                "release_id": release_id,
                "metrics": metrics,
                "anomalies": anomalies,
                "calculated_at": metrics_record["calculated_at"],
            },
        )

        return {
            "release_id": release_id,
            "metrics": metrics,
            "anomalies": anomalies,
            "recommendations": await self._generate_deployment_recommendations(metrics),
        }

    async def _schedule_deployment_window(
        self, release_id: str, preferred_window: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Schedule optimal deployment window.

        Returns scheduled window and conflicts.
        """
        self.logger.info(f"Scheduling deployment window for release: {release_id}")

        release = self.releases.get(release_id)
        if not release:
            raise ValueError(f"Release not found: {release_id}")

        optimal_window = None
        usage_patterns = await self._analyze_usage_patterns(release.get("target_environment"))

        if self.schedule_agent and self.schedule_agent_action:
            response = await self.schedule_agent.process(
                {
                    "action": self.schedule_agent_action,
                    "release_id": release_id,
                    "preferred_window": preferred_window,
                    "environment": release.get("target_environment"),
                }
            )
            optimal_window = response.get("scheduled_window") or response.get("window")

        if not optimal_window:
            optimal_window = await self._find_optimal_deployment_window(
                preferred_window, usage_patterns, release.get("target_environment")
            )

        # Check for conflicts
        start_time = optimal_window.get("start_time")
        target_env = release.get("target_environment")
        assert isinstance(start_time, str), "start_time must be a string"
        assert isinstance(target_env, str), "target_environment must be a string"
        conflicts = await self._detect_scheduling_conflicts(start_time, target_env)

        return {
            "release_id": release_id,
            "scheduled_window": optimal_window,
            "conflicts": conflicts,
            "usage_impact": await self._calculate_usage_impact(optimal_window, usage_patterns),
        }

    async def _verify_post_deployment(
        self, deployment_plan_id: str, verification_params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Verify application health post-deployment.

        Returns verification results.
        """
        self.logger.info(f"Verifying post-deployment for: {deployment_plan_id}")

        deployment_plan = self.deployment_plans.get(deployment_plan_id)
        if not deployment_plan:
            raise ValueError(f"Deployment plan not found: {deployment_plan_id}")

        health_check = await self._check_application_health(deployment_plan)

        metrics_comparison = await self._compare_metrics_to_baseline(deployment_plan)
        anomalies = await self._detect_post_deployment_anomalies(deployment_plan)

        verification_passed = (
            health_check.get("healthy", False)
            and metrics_comparison.get("acceptable", False)
            and len(anomalies) == 0
        )

        return {
            "deployment_plan_id": deployment_plan_id,
            "verification_passed": verification_passed,
            "health_check": health_check,
            "metrics_comparison": metrics_comparison,
            "anomalies": anomalies,
            "recommendations": (
                "Deployment successful" if verification_passed else "Investigate anomalies"
            ),
        }

    async def _get_release_calendar(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Get release calendar view.

        Returns scheduled releases.
        """
        self.logger.info("Retrieving release calendar")

        # Filter releases
        filtered_releases = []
        for release_id, release in self.releases.items():
            if await self._matches_filters(release, filters):
                filtered_releases.append(
                    {
                        "release_id": release_id,
                        "name": release.get("name"),
                        "planned_date": release.get("planned_date"),
                        "actual_date": release.get("actual_date"),
                        "target_environment": release.get("target_environment"),
                        "status": release.get("status"),
                    }
                )

        # Sort by planned date
        filtered_releases.sort(key=lambda x: x.get("planned_date", ""))

        return {
            "total_releases": len(filtered_releases),
            "releases": filtered_releases,
            "filters": filters,
        }

    async def _get_release_status(self, release_id: str) -> dict[str, Any]:
        """
        Get detailed release status.

        Returns comprehensive status information.
        """
        self.logger.info(f"Getting release status: {release_id}")

        release = self.releases.get(release_id)
        if not release:
            raise ValueError(f"Release not found: {release_id}")

        # Find associated deployment plan
        deployment_plan = None
        for plan_id, plan in self.deployment_plans.items():
            if plan.get("release_id") == release_id:
                deployment_plan = plan
                break

        return {
            "release_id": release_id,
            "name": release.get("name"),
            "status": release.get("status"),
            "planned_date": release.get("planned_date"),
            "actual_date": release.get("actual_date"),
            "target_environment": release.get("target_environment"),
            "deployment_plan": (
                deployment_plan.get("deployment_plan_id") if deployment_plan else None
            ),
            "deployment_status": deployment_plan.get("status") if deployment_plan else None,
        }

    # Helper methods

    async def _generate_release_id(self) -> str:
        """Generate unique release ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"REL-{timestamp}"

    async def _generate_deployment_plan_id(self) -> str:
        """Generate unique deployment plan ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"DEPLOY-{timestamp}"

    async def _generate_environment_id(self) -> str:
        """Generate unique environment ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"ENV-{timestamp}"

    async def _generate_release_notes_id(self) -> str:
        """Generate unique release notes ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"NOTES-{timestamp}"

    async def _check_environment_availability(
        self, environment: str, planned_date: str, release_id: str
    ) -> bool:
        """Check if environment is available and reserve it if possible."""
        allocation = await self._reserve_environment(environment, planned_date, release_id)
        return allocation is not None

    async def _detect_scheduling_conflicts(
        self, planned_date: str, environment: str
    ) -> list[dict[str, Any]]:
        """Detect scheduling conflicts."""
        conflicts = []
        for release_id, release in self.releases.items():
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

    async def _suggest_alternative_windows(
        self, planned_date: str, environment: str
    ) -> list[dict[str, Any]]:
        """Suggest alternative deployment windows."""
        # Future work: Use optimization algorithm
        return [
            {
                "start_time": (
                    datetime.fromisoformat(planned_date) + timedelta(hours=4)
                ).isoformat(),
                "reason": "Low usage period",
            }
        ]

    async def _check_quality_criteria(self, release_id: str) -> dict[str, Any]:
        """Check quality criteria."""
        if self.quality_agent:
            return await self.quality_agent.process(
                {"action": "assess_release_quality", "release_id": release_id}
            )
        return {"passed": True, "test_pass_rate": 100.0}

    async def _check_approval_status(self, release_id: str) -> dict[str, Any]:
        """Check approval status."""
        if self.approval_agent:
            response = await self.approval_agent.process(
                {
                    "request_type": "release_readiness",
                    "request_id": release_id,
                }
            )
            if isinstance(response, dict) and "complete" not in response:
                status = response.get("status")
                response["complete"] = status == "approved"
            return response
        return {"complete": True, "approvals": []}

    async def _check_change_approvals(self, release_id: str) -> dict[str, Any]:
        """Check change approvals."""
        if self.change_agent:
            return await self.change_agent.process(
                {"action": "check_release_changes", "release_id": release_id}
            )
        return {"approved": True, "change_requests": []}

    async def _check_risk_level(self, release_id: str) -> dict[str, Any]:
        """Check risk level."""
        if self.risk_agent:
            return await self.risk_agent.process(
                {"action": "assess_release_risk", "release_id": release_id}
            )
        return {"acceptable": True, "risk_score": 0.2}

    async def _check_compliance_requirements(self, release_id: str) -> dict[str, Any]:
        """Check compliance requirements."""
        if self.compliance_agent:
            return await self.compliance_agent.process(
                {"action": "verify_release_compliance", "release_id": release_id}
            )
        return {"met": True, "requirements": []}

    async def _define_deployment_steps(
        self, release: dict[str, Any], custom_steps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Define deployment steps."""
        if custom_steps:
            return custom_steps

        # Default deployment steps
        return [
            {"step": 1, "action": "Backup database", "estimated_minutes": 15},
            {"step": 2, "action": "Stop application", "estimated_minutes": 5},
            {"step": 3, "action": "Deploy artifacts", "estimated_minutes": 20},
            {"step": 4, "action": "Run database migrations", "estimated_minutes": 10},
            {"step": 5, "action": "Start application", "estimated_minutes": 5},
            {"step": 6, "action": "Verify deployment", "estimated_minutes": 10},
        ]

    async def _define_pre_deployment_tasks(self, release: dict[str, Any]) -> list[dict[str, Any]]:
        """Define pre-deployment tasks."""
        return [
            {"task": "Backup production database"},
            {"task": "Create configuration snapshot"},
            {"task": "Notify stakeholders"},
        ]

    async def _define_post_deployment_verification(
        self, release: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Define post-deployment verification steps."""
        return [
            {"check": "Application health check"},
            {"check": "Database connectivity"},
            {"check": "API endpoints responding"},
            {"check": "Performance metrics within baseline"},
        ]

    async def _define_rollback_procedures(self, release: dict[str, Any]) -> list[dict[str, Any]]:
        """Define rollback procedures."""
        return [
            {"step": 1, "action": "Stop current application"},
            {"step": 2, "action": "Restore previous artifacts"},
            {"step": 3, "action": "Rollback database"},
            {"step": 4, "action": "Start previous version"},
            {"step": 5, "action": "Verify rollback"},
        ]

    async def _estimate_deployment_duration(self, deployment_steps: list[dict[str, Any]]) -> int:
        """Estimate total deployment duration."""
        total_minutes = sum(int(step.get("estimated_minutes", 5)) for step in deployment_steps)
        return cast(int, total_minutes)  # type: ignore

    async def _execute_pre_deployment_tasks(
        self, tasks: list[dict[str, Any]], *, deployment_plan_id: str
    ) -> dict[str, Any]:
        """Execute pre-deployment tasks."""
        completed = 0
        for task in tasks:
            await self._publish_event(
                "deployment.progress",
                {
                    "deployment_plan_id": deployment_plan_id,
                    "phase": "pre_deployment",
                    "task": task.get("task"),
                    "status": "started",
                },
            )
            if task.get("should_fail"):
                await self._publish_event(
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
            await self._publish_event(
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
        self, steps: list[dict[str, Any]], *, deployment_plan: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute deployment steps."""
        strategy = deployment_plan.get("strategy", "rolling")
        pipeline_steps = await self._build_pipeline_steps(strategy, steps, deployment_plan)
        completed_steps: list[dict[str, Any]] = []
        failure_step = None
        for step in pipeline_steps:
            await self._publish_event(
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
                await self._publish_event(
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
            await self._publish_event(
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
        self, checks: list[dict[str, Any]], *, deployment_plan_id: str
    ) -> dict[str, Any]:
        """Execute post-deployment verification."""
        passed = 0
        for check in checks:
            await self._publish_event(
                "deployment.progress",
                {
                    "deployment_plan_id": deployment_plan_id,
                    "phase": "post_deployment",
                    "check": check.get("check"),
                    "status": "started",
                },
            )
            if check.get("should_fail"):
                await self._publish_event(
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
            await self._publish_event(
                "deployment.progress",
                {
                    "deployment_plan_id": deployment_plan_id,
                    "phase": "post_deployment",
                    "check": check.get("check"),
                    "status": "completed",
                },
            )
        return {"success": True, "passed_checks": passed}

    async def _should_auto_rollback(self, deployment_results: dict[str, Any]) -> bool:
        """Determine if auto-rollback should be triggered."""
        failure_rate = float(deployment_results.get("failure_rate", 0))
        return cast(bool, failure_rate > self.auto_rollback_threshold)  # type: ignore

    async def _execute_rollback_steps(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        """Execute rollback steps."""
        # Future work: Execute actual rollback
        return {"success": True, "completed_steps": len(steps)}

    async def _get_baseline_configuration(self, env_type: str) -> dict[str, Any]:
        """Get baseline configuration for environment type."""
        # Future work: Load from configuration management
        return {"version": "1.0", "settings": {}}

    async def _compare_configurations(
        self, current_config: dict[str, Any], baseline_config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Compare configurations to detect drift."""
        drift = []
        baseline_settings = baseline_config.get("settings", {})
        for key, baseline_value in baseline_settings.items():
            current_value = current_config.get(key)
            if current_value != baseline_value:
                drift.append(
                    {
                        "setting": key,
                        "expected": baseline_value,
                        "actual": current_value,
                    }
                )
        return drift

    async def _generate_drift_recommendations(self, drift_items: list[dict[str, Any]]) -> list[str]:
        """Generate recommendations for drift remediation."""
        if not drift_items:
            return ["No drift detected - configuration is compliant"]
        return ["Review and align configuration with baseline"]

    async def _gather_release_changes(self, release_id: str) -> list[dict[str, Any]]:
        """Gather release changes."""
        # Future work: Query change management system
        return []

    async def _gather_release_features(self, release_id: str) -> list[dict[str, Any]]:
        """Gather release features."""
        # Future work: Query feature tracking system
        return []

    async def _gather_release_bug_fixes(self, release_id: str) -> list[dict[str, Any]]:
        """Gather release bug fixes."""
        # Future work: Query bug tracking system
        return []

    async def _gather_known_issues(self, release_id: str) -> list[dict[str, Any]]:
        """Gather known issues."""
        # Future work: Query issue tracking system
        return []

    async def _generate_notes_content(
        self,
        release: dict[str, Any],
        changes: list[dict[str, Any]],
        features: list[dict[str, Any]],
        bug_fixes: list[dict[str, Any]],
        known_issues: list[dict[str, Any]],
    ) -> str:
        """Generate release notes content using NLG."""
        if self.openai_client:
            prompt = await self._build_release_notes_prompt(
                release, changes, features, bug_fixes, known_issues
            )
            if hasattr(self.openai_client, "generate"):
                response = await self.openai_client.generate(prompt)
                return cast(str, response)
            if hasattr(self.openai_client, "complete"):
                response = await self.openai_client.complete(prompt)
                return cast(str, response)
        return f"""Release Notes: {release.get('name')}

Date: {release.get('actual_date', release.get('planned_date'))}
Environment: {release.get('target_environment')}

Features:
{chr(10).join(f"- {f.get('description', 'Feature')}" for f in features)}

Bug Fixes:
{chr(10).join(f"- {b.get('description', 'Fix')}" for b in bug_fixes)}

Known Issues:
{chr(10).join(f"- {i.get('description', 'Issue')}" for i in known_issues)}
"""

    async def _build_release_notes_prompt(
        self,
        release: dict[str, Any],
        changes: list[dict[str, Any]],
        features: list[dict[str, Any]],
        bug_fixes: list[dict[str, Any]],
        known_issues: list[dict[str, Any]],
    ) -> str:
        """Build prompt for release notes generation."""
        change_list = "\n".join(f"- {item.get('description', 'Change')}" for item in changes)
        feature_list = "\n".join(f"- {item.get('description', 'Feature')}" for item in features)
        bug_list = "\n".join(f"- {item.get('description', 'Fix')}" for item in bug_fixes)
        issue_list = "\n".join(f"- {item.get('description', 'Issue')}" for item in known_issues)
        return (
            "Create release notes with sections for Changes, Features, Bug Fixes, and Known Issues.\n"
            f"Release: {release.get('name')}\n"
            f"Environment: {release.get('target_environment')}\n"
            f"Planned Date: {release.get('planned_date')}\n"
            f"Changes:\n{change_list}\n"
            f"Features:\n{feature_list}\n"
            f"Bug Fixes:\n{bug_list}\n"
            f"Known Issues:\n{issue_list}\n"
        )

    async def _calculate_deployment_frequency(self) -> float:
        """Calculate deployment frequency."""
        now = datetime.utcnow()
        window_start = now - timedelta(days=30)
        completed = [
            plan
            for plan in self.deployment_plans.values()
            if plan.get("completed_at")
            and datetime.fromisoformat(plan["completed_at"]) >= window_start
        ]
        return len(completed) / 1.0  # per 30 days

    async def _calculate_lead_time(self, release_id: str) -> float:
        """Calculate lead time for changes."""
        release = self.releases.get(release_id)
        if not release:
            return 0.0
        created_at = release.get("created_at")
        actual_date = release.get("actual_date")
        if not created_at or not actual_date:
            return 0.0
        start = datetime.fromisoformat(created_at)
        end = datetime.fromisoformat(actual_date)
        return max((end - start).total_seconds() / 86400, 0.0)

    async def _calculate_mean_time_to_deploy(self, release_id: str) -> float:
        """Calculate mean time to deploy."""
        durations = []
        for plan in self.deployment_plans.values():
            if plan.get("release_id") != release_id:
                continue
            started = plan.get("started_at")
            completed = plan.get("completed_at")
            if started and completed:
                start = datetime.fromisoformat(started)
                end = datetime.fromisoformat(completed)
                durations.append((end - start).total_seconds() / 60)
        return sum(durations) / len(durations) if durations else 0.0

    async def _calculate_success_rate(self) -> float:
        """Calculate deployment success rate."""
        if not self.deployment_plans:
            return 1.0
        total = len(self.deployment_plans)
        success = sum(1 for plan in self.deployment_plans.values() if plan.get("status") == "Completed")
        return success / total if total else 0.0

    async def _calculate_rollback_rate(self) -> float:
        """Calculate rollback rate."""
        if not self.deployment_plans:
            return 0.0
        total = len(self.deployment_plans)
        rolled_back = sum(
            1 for plan in self.deployment_plans.values() if plan.get("status") == "Rolled Back"
        )
        return rolled_back / total if total else 0.0

    async def _calculate_environment_utilization(self) -> dict[str, float]:
        """Calculate environment utilization."""
        utilization: dict[str, float] = {env: 0.0 for env in self.environments}
        if not self.environment_allocations:
            return utilization
        total_allocations = len(self.environment_allocations)
        for allocation in self.environment_allocations.values():
            env = allocation.get("environment")
            if env in utilization:
                utilization[env] += 1 / total_allocations
        return utilization

    async def _calculate_mttr(self) -> float:
        """Calculate mean time to restore service."""
        restore_times = []
        for plan in self.deployment_plans.values():
            if plan.get("status") != "Rolled Back":
                continue
            rollback_at = plan.get("rollback_at")
            started_at = plan.get("started_at")
            if rollback_at and started_at:
                start = datetime.fromisoformat(started_at)
                end = datetime.fromisoformat(rollback_at)
                restore_times.append((end - start).total_seconds() / 60)
        return sum(restore_times) / len(restore_times) if restore_times else 0.0

    async def _calculate_change_failure_rate(self) -> float:
        """Calculate change failure rate."""
        if not self.deployment_plans:
            return 0.0
        failed = sum(
            1
            for plan in self.deployment_plans.values()
            if plan.get("status") in {"Failed", "Rolled Back"}
        )
        return failed / len(self.deployment_plans)

    async def _generate_deployment_recommendations(self, metrics: dict[str, Any]) -> list[str]:
        """Generate recommendations based on metrics."""
        recommendations = []

        if metrics.get("deployment_success_rate", 1.0) < 0.90:
            recommendations.append("Improve deployment success rate through better testing")

        if metrics.get("rollback_rate", 0) > 0.05:
            recommendations.append("Reduce rollback rate by enhancing pre-deployment validation")

        if not recommendations:
            recommendations.append("Deployment metrics are healthy - continue current practices")

        return recommendations

    async def _analyze_usage_patterns(self, environment: str) -> dict[str, Any]:
        """Analyze usage patterns."""
        # Future work: Analyze actual usage data
        return {"peak_hours": [9, 10, 11, 14, 15], "low_usage_hours": [2, 3, 4, 5]}

    async def _find_optimal_deployment_window(
        self, preferred_window: dict[str, Any], usage_patterns: dict[str, Any], environment: str
    ) -> dict[str, Any]:
        """Find optimal deployment window."""
        # Future work: Use optimization algorithm
        start_time_str = preferred_window.get("start_time")
        assert isinstance(start_time_str, str), "start_time must be a string"

        return {
            "start_time": start_time_str,
            "duration_hours": self.deployment_window_hours,
            "end_time": (
                datetime.fromisoformat(start_time_str)
                + timedelta(hours=self.deployment_window_hours)
            ).isoformat(),
        }

    async def _calculate_usage_impact(
        self, window: dict[str, Any], usage_patterns: dict[str, Any]
    ) -> str:
        """Calculate usage impact."""
        # Future work: Calculate actual impact
        return "Low impact - deployment during low usage period"

    async def _check_application_health(self, deployment_plan: dict[str, Any]) -> dict[str, Any]:
        """Check application health."""
        if self.monitoring_client:
            if hasattr(self.monitoring_client, "get_health"):
                response = await self.monitoring_client.get_health(deployment_plan)
                return cast(dict[str, Any], response)
            if hasattr(self.monitoring_client, "process"):
                response = await self.monitoring_client.process(
                    {"action": "get_health", "deployment_plan": deployment_plan}
                )
                return cast(dict[str, Any], response)
        return {"healthy": True, "response_time_ms": 150, "error_rate": 0.001}

    async def _compare_metrics_to_baseline(self, deployment_plan: dict[str, Any]) -> dict[str, Any]:
        """Compare metrics to baseline."""
        metrics = await self._fetch_monitoring_metrics(deployment_plan)
        baseline = await self._fetch_baseline_metrics(deployment_plan)
        if not baseline:
            return {"acceptable": True, "variance": 0.0, "metrics": metrics}
        variance = {}
        acceptable = True
        for metric, value in metrics.items():
            base = baseline.get(metric, {})
            baseline_value = base.get("mean", base.get("value"))
            if baseline_value is None:
                continue
            diff = value - baseline_value
            variance[metric] = diff
            if abs(diff) > base.get("threshold", baseline_value * 0.2):
                acceptable = False
        return {"acceptable": acceptable, "variance": variance, "metrics": metrics}

    async def _detect_post_deployment_anomalies(
        self, deployment_plan: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect post-deployment anomalies."""
        metrics = await self._fetch_monitoring_metrics(deployment_plan)
        baseline = await self._fetch_baseline_metrics(deployment_plan)
        anomalies = []
        for metric, value in metrics.items():
            base = baseline.get(metric, {}) if baseline else {}
            mean = base.get("mean", base.get("value"))
            std = base.get("std", 0.0)
            threshold = base.get("threshold")
            if mean is None:
                continue
            if threshold is None:
                threshold = mean + (2 * std)
            if value > threshold:
                anomalies.append(
                    {
                        "metric": metric,
                        "value": value,
                        "baseline_mean": mean,
                        "threshold": threshold,
                        "severity": "high" if value > threshold * 1.2 else "medium",
                    }
                )
        if metrics.get("error_rate", 0) > 0.02:
            anomalies.append(
                {
                    "metric": "error_rate",
                    "value": metrics.get("error_rate"),
                    "threshold": 0.02,
                    "severity": "high",
                }
            )
        return anomalies

    async def _detect_metric_anomalies(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect anomalies in deployment metrics."""
        anomalies = []
        if metrics.get("deployment_success_rate", 1.0) < 0.9:
            anomalies.append(
                {
                    "metric": "deployment_success_rate",
                    "severity": "high",
                    "value": metrics.get("deployment_success_rate"),
                }
            )
        if metrics.get("rollback_rate", 0.0) > 0.05:
            anomalies.append(
                {
                    "metric": "rollback_rate",
                    "severity": "medium",
                    "value": metrics.get("rollback_rate"),
                }
            )
        return anomalies

    async def _check_azure_policy_compliance(self, environment: dict[str, Any]) -> dict[str, Any]:
        """Check configuration compliance using Azure Policy."""
        if not self.azure_policy_client:
            return {"compliance_state": "unknown", "drift_items": []}
        if hasattr(self.azure_policy_client, "assess_compliance"):
            response = await self.azure_policy_client.assess_compliance(environment)
            return cast(dict[str, Any], response)
        if hasattr(self.azure_policy_client, "process"):
            response = await self.azure_policy_client.process(
                {"action": "check_policy_compliance", "environment": environment}
            )
            return cast(dict[str, Any], response)
        return {"compliance_state": "unknown", "drift_items": []}

    async def _orchestrate_deployment(
        self,
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
        if self.azure_devops_client:
            pipeline_results.append(
                await self._trigger_azure_devops_pipeline(deployment_plan, orchestrator_payload)
            )
        if self.github_actions_client:
            pipeline_results.append(
                await self._trigger_github_actions_workflow(deployment_plan, orchestrator_payload)
            )

        if self.durable_functions_client and hasattr(self.durable_functions_client, "orchestrate"):
            orchestration = await self.durable_functions_client.orchestrate(orchestrator_payload)
        else:
            orchestration = {"orchestration_id": str(uuid.uuid4()), "status": "completed"}

        step_results = await self._execute_deployment_steps(steps, deployment_plan=deployment_plan)
        await self._capture_deployment_artifacts(deployment_plan, pipeline_results, step_results)
        await self._persist_deployment_log(
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

    async def _trigger_azure_devops_pipeline(
        self, deployment_plan: dict[str, Any], payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Trigger Azure DevOps pipeline deployment."""
        if hasattr(self.azure_devops_client, "run_pipeline"):
            response = await self.azure_devops_client.run_pipeline(payload)
            return cast(dict[str, Any], response)
        return {"system": "azure_devops", "status": "queued", "pipeline_id": "ado-mock"}

    async def _trigger_github_actions_workflow(
        self, deployment_plan: dict[str, Any], payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Trigger GitHub Actions workflow deployment."""
        if hasattr(self.github_actions_client, "run_workflow"):
            response = await self.github_actions_client.run_workflow(payload)
            return cast(dict[str, Any], response)
        return {"system": "github_actions", "status": "queued", "run_id": "gha-mock"}

    async def _reserve_environment(
        self, environment: str, planned_date: str, release_id: str
    ) -> dict[str, Any] | None:
        """Reserve an environment using reservation system or in-memory tracking."""
        if self.environment_reservation_client and hasattr(
            self.environment_reservation_client, "check_availability"
        ):
            availability = await self.environment_reservation_client.check_availability(
                {"environment": environment, "planned_date": planned_date}
            )
            if not availability.get("available", False):
                return None
            if hasattr(self.environment_reservation_client, "reserve"):
                reservation = await self.environment_reservation_client.reserve(
                    {
                        "environment": environment,
                        "planned_date": planned_date,
                        "release_id": release_id,
                    }
                )
            else:
                reservation = {"reservation_id": str(uuid.uuid4()), "status": "reserved"}
        else:
            for allocation in self.environment_allocations.values():
                if allocation.get("environment") == environment and allocation.get("status") == "reserved":
                    return None
            reservation = {"reservation_id": str(uuid.uuid4()), "status": "reserved"}

        reserved_until = (
            datetime.fromisoformat(planned_date) + timedelta(hours=self.deployment_window_hours)
        ).isoformat()
        allocation = {
            "allocation_id": reservation.get("reservation_id", str(uuid.uuid4())),
            "environment": environment,
            "release_id": release_id,
            "reserved_at": datetime.utcnow().isoformat(),
            "reserved_until": reserved_until,
            "status": "reserved",
        }
        self.environment_allocations[allocation["allocation_id"]] = allocation
        await self.db_service.store("environment_allocations", allocation["allocation_id"], allocation)
        await self._publish_event(
            "environment.reserved",
            {
                "allocation_id": allocation["allocation_id"],
                "environment": environment,
                "release_id": release_id,
                "reserved_until": reserved_until,
            },
        )
        return allocation

    async def _release_environment_allocation(
        self, release_id: str, deployment_plan_id: str
    ) -> None:
        allocation = next(
            (
                allocation
                for allocation in self.environment_allocations.values()
                if allocation.get("release_id") == release_id
                and allocation.get("status") == "reserved"
            ),
            None,
        )
        if not allocation:
            return
        allocation["status"] = "released"
        allocation["released_at"] = datetime.utcnow().isoformat()
        if self.environment_reservation_client and hasattr(
            self.environment_reservation_client, "release"
        ):
            await self.environment_reservation_client.release(allocation)
        await self.db_service.store("environment_allocations", allocation["allocation_id"], allocation)
        await self._publish_event(
            "environment.released",
            {
                "allocation_id": allocation["allocation_id"],
                "environment": allocation.get("environment"),
                "release_id": release_id,
                "deployment_plan_id": deployment_plan_id,
            },
        )

    async def _build_pipeline_steps(
        self, strategy: str, steps: list[dict[str, Any]], deployment_plan: dict[str, Any]
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

    async def _fetch_monitoring_metrics(self, deployment_plan: dict[str, Any]) -> dict[str, float]:
        if self.monitoring_client and hasattr(self.monitoring_client, "get_metrics"):
            response = await self.monitoring_client.get_metrics(deployment_plan)
            return cast(dict[str, float], response)
        if self.monitoring_client and hasattr(self.monitoring_client, "process"):
            response = await self.monitoring_client.process(
                {"action": "get_metrics", "deployment_plan": deployment_plan}
            )
            return cast(dict[str, float], response)
        return {"response_time_ms": 150.0, "error_rate": 0.001}

    async def _fetch_baseline_metrics(self, deployment_plan: dict[str, Any]) -> dict[str, Any]:
        if self.monitoring_client and hasattr(self.monitoring_client, "get_baseline"):
            response = await self.monitoring_client.get_baseline(deployment_plan)
            return cast(dict[str, Any], response)
        return {
            "response_time_ms": {"mean": 120.0, "std": 20.0},
            "error_rate": {"mean": 0.001, "std": 0.002, "threshold": 0.01},
        }

    async def _capture_deployment_artifacts(
        self,
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
                    "captured_at": datetime.utcnow().isoformat(),
                }
            )
        deployment_plan_id = deployment_plan.get("deployment_plan_id")
        if deployment_plan_id:
            self.deployment_artifacts.setdefault(deployment_plan_id, []).extend(artifacts)
            await self.db_service.store(
                "deployment_artifacts",
                deployment_plan_id,
                {"artifacts": artifacts, "deployment_plan_id": deployment_plan_id},
            )

    async def _persist_deployment_log(
        self, deployment_plan: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        deployment_plan_id = deployment_plan.get("deployment_plan_id")
        if not deployment_plan_id:
            return
        log_entry = {
            "deployment_plan_id": deployment_plan_id,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        }
        self.deployment_logs.setdefault(deployment_plan_id, []).append(log_entry)
        await self.db_service.store("deployment_logs", deployment_plan_id, log_entry)

    async def _collect_readiness_blockers(
        self, checks: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
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

    async def _publish_event(self, topic: str, payload: dict[str, Any]) -> None:
        if not self.event_bus:
            return
        await self.event_bus.publish(topic, payload)

    async def _handle_system_health_event(self, payload: dict[str, Any]) -> None:
        deployment_plan_id = payload.get("deployment_plan_id")
        if not deployment_plan_id:
            return
        deployment_plan = self.deployment_plans.get(deployment_plan_id)
        if not deployment_plan:
            return
        deployment_plan["health_status"] = payload.get("status") or payload.get("health_status")
        await self.db_service.store("deployment_plans", deployment_plan_id, deployment_plan)

    async def _handle_analytics_event(self, payload: dict[str, Any]) -> None:
        deployment_plan_id = payload.get("deployment_plan_id")
        if not deployment_plan_id:
            return
        deployment_plan = self.deployment_plans.get(deployment_plan_id)
        if not deployment_plan:
            return
        deployment_plan["analytics"] = payload
        await self.db_service.store("deployment_plans", deployment_plan_id, deployment_plan)

    async def _matches_filters(self, release: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if release matches filters."""
        if "status" in filters and release.get("status") != filters["status"]:
            return False

        if "environment" in filters and release.get("target_environment") != filters["environment"]:
            return False

        return True

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Release & Deployment Agent...")
        # Integration services use connection pooling and don't require explicit cleanup
        self.logger.info("Release & Deployment Agent cleanup complete")

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "release_planning",
            "release_scheduling",
            "release_readiness_assessment",
            "deployment_orchestration",
            "environment_management",
            "configuration_drift_detection",
            "release_approvals",
            "deployment_automation",
            "rollback_procedures",
            "release_notes_generation",
            "deployment_metrics",
            "deployment_window_optimization",
            "post_deployment_verification",
            "ci_cd_integration",
            "monitoring_integration",
        ]
