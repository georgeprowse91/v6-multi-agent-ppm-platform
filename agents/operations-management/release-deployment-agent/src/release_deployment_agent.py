"""
Release & Deployment Agent

Purpose:
Manages the planning, coordination and execution of software and project deliverable releases
across environments. Ensures controlled deployments with minimal risk and downtime.

Specification: agents/operations-management/release-deployment-agent/README.md
"""

import uuid
from pathlib import Path
from typing import Any

# -- action handlers (each lives in its own module under release_actions/) --
from release_actions import (
    assess_readiness,
    check_configuration_drift,
    create_deployment_plan,
    execute_deployment,
    generate_release_notes,
    get_deployment_history,
    get_deployment_status,
    get_release_calendar,
    get_release_status,
    manage_environment,
    plan_release,
    rollback_deployment,
    schedule_deployment_window,
    track_deployment_metrics,
    verify_post_deployment,
)
from release_actions.verify_post_deployment import (
    _detect_post_deployment_anomalies as _detect_pd_anomalies,
)

# -- shared utilities used by event handlers and backward-compat stubs --
from release_utils import (
    publish_event,
)
from release_utils import (
    release_environment_allocation as _release_env_alloc,
)
from release_utils import (
    reserve_environment as _reserve_env,
)
from release_utils import (
    suggest_alternative_windows as _suggest_alt_windows,
)

from agents.common.connector_integration import (
    CalendarIntegrationService,
    DatabaseStorageService,
    DocumentationPublishingService,
)
from agents.runtime import BaseAgent, get_event_bus
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

    def __init__(
        self, agent_id: str = "release-deployment-agent", config: dict[str, Any] | None = None
    ):
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
        self.calendar_service = CalendarIntegrationService((config or {}).get("calendar"))

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
        self.configuration_management_client = (
            config.get("configuration_management_client") if config else None
        )
        self.tracking_clients = config.get("tracking_clients", []) if config else []
        self.version_control_client = config.get("version_control_client") if config else None
        self.monitoring_client = config.get("monitoring_client") if config else None
        self.analytics_client = config.get("analytics_client") if config else None
        self.event_bus = config.get("event_bus") if config else None
        self.rollback_scripts_path = (
            Path(config.get("rollback_scripts_path", "data/rollback_scripts"))
            if config
            else Path("data/rollback_scripts")
        )
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
        self.readiness_assessments: dict[str, dict[str, Any]] = {}
        self.deployment_history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

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

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Release & Deployment Agent...")
        # Integration services use connection pooling and don't require explicit cleanup
        self.logger.info("Release & Deployment Agent cleanup complete")

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = {
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
            "get_deployment_status",
            "get_deployment_history",
            "trigger_deployment",
        }

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
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
        elif action == "get_deployment_status":
            if "deployment_plan_id" not in input_data:
                self.logger.warning("Missing deployment_plan_id")
                return False

        return True

    # ------------------------------------------------------------------
    # Action router
    # ------------------------------------------------------------------

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
            return await plan_release(
                self,
                input_data.get("release", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "assess_readiness":
            release_id = input_data.get("release_id")
            assert isinstance(release_id, str), "release_id must be a string"
            return await assess_readiness(self, release_id)

        elif action == "create_deployment_plan":
            release_id = input_data.get("release_id")
            assert isinstance(release_id, str), "release_id must be a string"
            return await create_deployment_plan(
                self,
                release_id,
                input_data.get("deployment_plan", {}),
                tenant_id=tenant_id,
            )

        elif action == "execute_deployment":
            deployment_plan_id = input_data.get("deployment_plan_id")
            assert isinstance(deployment_plan_id, str), "deployment_plan_id must be a string"
            return await execute_deployment(
                self,
                deployment_plan_id,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
        elif action == "trigger_deployment":
            deployment_plan_id = input_data.get("deployment_plan_id")
            assert isinstance(deployment_plan_id, str), "deployment_plan_id must be a string"
            return await execute_deployment(
                self,
                deployment_plan_id,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "rollback_deployment":
            deployment_plan_id = input_data.get("deployment_plan_id")
            assert isinstance(deployment_plan_id, str), "deployment_plan_id must be a string"
            return await rollback_deployment(self, deployment_plan_id)

        elif action == "manage_environment":
            return await manage_environment(self, input_data.get("environment", {}))

        elif action == "check_configuration_drift":
            environment_id = input_data.get("environment_id")
            assert isinstance(environment_id, str), "environment_id must be a string"
            return await check_configuration_drift(self, environment_id)

        elif action == "generate_release_notes":
            release_id = input_data.get("release_id")
            assert isinstance(release_id, str), "release_id must be a string"
            return await generate_release_notes(self, release_id)

        elif action == "track_deployment_metrics":
            release_id = input_data.get("release_id")
            assert isinstance(release_id, str), "release_id must be a string"
            return await track_deployment_metrics(self, release_id)

        elif action == "schedule_deployment_window":
            release_id = input_data.get("release_id")
            assert isinstance(release_id, str), "release_id must be a string"
            return await schedule_deployment_window(
                self, release_id, input_data.get("preferred_window", {})
            )

        elif action == "verify_post_deployment":
            deployment_plan_id = input_data.get("deployment_plan_id")
            assert isinstance(deployment_plan_id, str), "deployment_plan_id must be a string"
            return await verify_post_deployment(
                self, deployment_plan_id, input_data.get("verification_params", {})
            )

        elif action == "get_release_calendar":
            return await get_release_calendar(self, input_data.get("filters", {}))

        elif action == "get_release_status":
            release_id = input_data.get("release_id")
            assert isinstance(release_id, str), "release_id must be a string"
            return await get_release_status(self, release_id)

        elif action == "get_deployment_status":
            deployment_plan_id = input_data.get("deployment_plan_id")
            assert isinstance(deployment_plan_id, str), "deployment_plan_id must be a string"
            return await get_deployment_status(self, deployment_plan_id)

        elif action == "get_deployment_history":
            return await get_deployment_history(
                self,
                filters=input_data.get("filters", {}),
                limit=input_data.get("limit", 50),
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Event handlers (kept on the class -- they mutate agent state)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Backward-compatible private method stubs -- delegate to modules
    # ------------------------------------------------------------------

    async def _plan_release(self, release_data, *, tenant_id, correlation_id, actor_id):
        return await plan_release(
            self,
            release_data,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            actor_id=actor_id,
        )

    async def _assess_readiness(self, release_id):
        return await assess_readiness(self, release_id)

    async def _create_deployment_plan(self, release_id, plan_data, *, tenant_id):
        return await create_deployment_plan(self, release_id, plan_data, tenant_id=tenant_id)

    async def _execute_deployment(self, deployment_plan_id, *, tenant_id, correlation_id):
        return await execute_deployment(
            self, deployment_plan_id, tenant_id=tenant_id, correlation_id=correlation_id
        )

    async def _rollback_deployment(self, deployment_plan_id):
        return await rollback_deployment(self, deployment_plan_id)

    async def _manage_environment(self, environment_data):
        return await manage_environment(self, environment_data)

    async def _check_configuration_drift(self, environment_id):
        return await check_configuration_drift(self, environment_id)

    async def _generate_release_notes(self, release_id):
        return await generate_release_notes(self, release_id)

    async def _track_deployment_metrics(self, release_id):
        return await track_deployment_metrics(self, release_id)

    async def _schedule_deployment_window(self, release_id, preferred_window):
        return await schedule_deployment_window(self, release_id, preferred_window)

    async def _verify_post_deployment(self, deployment_plan_id, verification_params):
        return await verify_post_deployment(self, deployment_plan_id, verification_params)

    async def _get_release_calendar(self, filters):
        return await get_release_calendar(self, filters)

    async def _get_release_status(self, release_id):
        return await get_release_status(self, release_id)

    async def _get_deployment_status(self, deployment_plan_id):
        return await get_deployment_status(self, deployment_plan_id)

    async def _get_deployment_history(self, *, filters, limit):
        return await get_deployment_history(self, filters=filters, limit=limit)

    async def _publish_event(self, topic, payload):
        return await publish_event(self, topic, payload)

    async def _suggest_alternative_windows(self, planned_date, environment):
        return await _suggest_alt_windows(self, planned_date, environment)

    async def _reserve_environment(self, environment, planned_date, release_id):
        return await _reserve_env(self, environment, planned_date, release_id)

    async def _release_environment_allocation(self, release_id, deployment_plan_id):
        return await _release_env_alloc(self, release_id, deployment_plan_id)

    async def _detect_post_deployment_anomalies(self, deployment_plan):
        return await _detect_pd_anomalies(self, deployment_plan)
