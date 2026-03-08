"""
Change & Configuration Management Agent

Purpose:
Governs controlled introduction of changes to projects, programs and configuration items.
Ensures changes are assessed, approved, implemented and documented to minimize disruption
and preserve integrity. Maintains CMDB for project artifacts and infrastructure.

Specification: agents/operations-management/change-control-agent/README.md
"""

import importlib.util
import os
import uuid
from pathlib import Path
from typing import Any

# Action handlers ----------------------------------------------------------
from change_actions import (
    approve_change,
    assess_impact,
    audit_changes,
    classify_change,
    create_baseline,
    generate_change_report,
    get_change_dashboard,
    get_change_metrics,
    handle_cicd_webhook,
    identify_impacted_cis,
    implement_change,
    matches_filters,
    monitor_change,
    predict_impact,
    publish_event,
    query_impacted_cis,
    record_change_audit,
    register_ci,
    review_change,
    rollback_change,
    run_automated_tests,
    run_staging_validation,
    submit_change_request,
    subscribe_cicd_webhooks,
    track_change_implementation,
    update_change_request,
    visualize_dependencies,
)
from change_actions.classify_and_assess import (
    assess_compliance_impact,
    recommend_mitigation,
)

# Re-export models so that ``from change_configuration_agent import X`` keeps working.
from change_models import (  # noqa: F401
    ChangeImpactModel,
    ImpactTrainingSample,
    PullRequestSummary,
    RepositoryReference,
)
from change_utils import (  # noqa: F401
    ApprovalFallbackAgent,
    ChangeEventPublisher,
    ChangeRequestClassifier,
    ChangeWorkflowOrchestrator,
    DependencyGraphService,
    IaCChangeParser,
    RepositoryIntegrationService,
)

from agents.common.connector_integration import (
    DatabaseStorageService,
    DocumentManagementService,
    ITSMIntegrationService,
)
from agents.runtime import BaseAgent
from agents.runtime.src.state_store import TenantStateStore


class ChangeConfigurationAgent(BaseAgent):
    """
    Change & Configuration Management Agent - Manages changes and configuration items.

    Key Capabilities:
    - Change request intake and classification
    - Impact assessment and risk evaluation
    - Approval workflow orchestration
    - Configuration management database (CMDB)
    - Baseline and version control
    - Change implementation tracking
    - Change audit and history
    - Configuration visualization and dependency mapping
    """

    def __init__(
        self, agent_id: str = "change-control-agent", config: dict[str, Any] | None = None
    ):
        super().__init__(agent_id, config)
        cfg = config or {}
        self.change_types = cfg.get("change_types", ["normal", "standard", "emergency"])
        self.priority_levels = cfg.get("priority_levels", ["critical", "high", "medium", "low"])
        self.baseline_threshold = cfg.get("baseline_threshold", 0.10)
        self.approval_priority_thresholds = cfg.get(
            "approval_priority_thresholds", ["critical", "high"]
        )
        self.approval_change_types = cfg.get("approval_change_types", ["normal", "emergency"])
        change_store_path = Path(cfg.get("change_store_path", "data/change_requests.json"))
        cmdb_store_path = Path(cfg.get("cmdb_store_path", "data/cmdb.json"))
        self.change_store = TenantStateStore(change_store_path)
        self.cmdb_store = TenantStateStore(cmdb_store_path)

        # Data stores
        self.change_requests: dict[str, Any] = {}
        self.cmdb: dict[str, Any] = {}
        self.baselines: dict[str, Any] = {}
        self.change_history: dict[str, Any] = {}
        self.cab_meetings: dict[str, Any] = {}
        self.approval_agent = cfg.get("approval_agent")
        if self.approval_agent is None:
            if importlib.util.find_spec("msal"):
                from approval_workflow_agent import ApprovalWorkflowAgent

                self.approval_agent = ApprovalWorkflowAgent(
                    config=cfg.get("approval_agent_config", {})
                )
            else:
                self.approval_agent = ApprovalFallbackAgent()

        self.event_publisher = cfg.get("event_publisher")
        self.dependency_graph = cfg.get("dependency_graph")
        self.schedule_agent = cfg.get("schedule_agent")
        self.resource_agent = cfg.get("resource_agent")
        self.financial_agent = cfg.get("financial_agent")
        self.risk_agent = cfg.get("risk_agent")
        self.task_management_client = cfg.get("task_management_client")
        self.document_service = None
        self.repo_service = None
        self.iac_parser = None
        self.workflow_orchestrator = None
        self.impact_model = None
        self.text_classifier = None
        self.cicd_subscriptions: list[dict[str, Any]] = []
        self.release_deployment_endpoint = cfg.get("release_deployment_endpoint") or os.getenv(
            "RELEASE_DEPLOYMENT_ENDPOINT"
        )
        self.lifecycle_governance_endpoint = cfg.get("lifecycle_governance_endpoint") or os.getenv(
            "LIFECYCLE_GOVERNANCE_ENDPOINT"
        )
        self.stakeholder_comms_endpoint = cfg.get("stakeholder_comms_endpoint") or os.getenv(
            "STAKEHOLDER_COMMS_ENDPOINT"
        )
        self.require_staging_tests = bool(
            cfg.get("require_staging_tests")
            or os.getenv("REQUIRE_STAGING_TESTS", "false").lower() == "true"
        )
        self.require_automated_tests = bool(
            cfg.get("require_automated_tests")
            or os.getenv("REQUIRE_AUTOMATED_TESTS", "false").lower() == "true"
        )
        self.staging_validation_endpoint = cfg.get("staging_validation_endpoint") or os.getenv(
            "STAGING_VALIDATION_ENDPOINT"
        )
        self.automated_test_endpoint = cfg.get("automated_test_endpoint") or os.getenv(
            "CHANGE_TEST_ENDPOINT"
        )
        self.monitoring_endpoint = cfg.get("monitoring_endpoint") or os.getenv(
            "CHANGE_MONITORING_ENDPOINT"
        )
        self.metrics_endpoint = cfg.get("metrics_endpoint") or os.getenv("CHANGE_METRICS_ENDPOINT")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize database connections, ITSM integrations, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Change & Configuration Management Agent...")
        cfg = self.config or {}

        self.db_service = DatabaseStorageService(cfg.get("database_storage", {}))
        self.itsm_service = ITSMIntegrationService(cfg.get("itsm_integration", {}))

        # Change classification model
        self.text_classifier = ChangeRequestClassifier(labels=self.change_types)
        training_samples = cfg.get("change_classification_samples", []) or [
            ("emergency fix for production outage", "emergency"),
            ("critical security patch rollout", "emergency"),
            ("routine maintenance window update", "standard"),
            ("standard patching for monthly updates", "standard"),
            ("feature enhancement request", "normal"),
            ("configuration change for new capability", "normal"),
        ]
        self.text_classifier.train(training_samples)

        self.repo_service = RepositoryIntegrationService(self.logger)
        self.iac_parser = IaCChangeParser(self.logger)
        orchestrator = cfg.get("workflow_orchestrator", "durable_functions")
        self.workflow_orchestrator = ChangeWorkflowOrchestrator(
            self.db_service, orchestrator, cfg.get("workflow_config", {})
        )

        # Impact prediction model
        impact_samples = cfg.get("impact_model_samples", []) or [
            ImpactTrainingSample(2.0, 0.1, 3, "medium", 0.85),
            ImpactTrainingSample(4.0, 0.3, 8, "high", 0.6),
            ImpactTrainingSample(1.0, 0.05, 1, "low", 0.92),
        ]
        normalized_samples: list[ImpactTrainingSample] = []
        for sample in impact_samples:
            if isinstance(sample, ImpactTrainingSample):
                normalized_samples.append(sample)
            elif isinstance(sample, dict):
                normalized_samples.append(
                    ImpactTrainingSample(
                        sample.get("complexity", 1.0),
                        sample.get("historical_failure_rate", 0.1),
                        sample.get("affected_services", 1),
                        sample.get("risk_category", "medium"),
                        sample.get("success_probability", 0.8),
                    )
                )
        self.impact_model = ChangeImpactModel()
        self.impact_model.train(normalized_samples)

        if not self.document_service:
            self.document_service = DocumentManagementService(cfg.get("document_management", {}))
        if not self.event_publisher:
            self.event_publisher = ChangeEventPublisher(cfg.get("event_bus", {}), self.logger)
        if not self.dependency_graph:
            self.dependency_graph = DependencyGraphService(self.logger, cfg.get("graph", {}))
        self.dependency_graph.load_cmdb(self.cmdb)

        self.cicd_subscriptions = await subscribe_cicd_webhooks(
            self, cfg.get("cicd_subscriptions", [])
        )
        self.logger.info("Change & Configuration Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "submit_change_request",
            "classify_change",
            "assess_impact",
            "predict_impact",
            "approve_change",
            "review_change",
            "implement_change",
            "update_change_request",
            "rollback_change",
            "register_ci",
            "create_baseline",
            "track_change_implementation",
            "audit_changes",
            "visualize_dependencies",
            "query_impacted_cis",
            "get_change_dashboard",
            "generate_change_report",
            "get_change_metrics",
            "cicd_webhook",
            "monitor_change",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "submit_change_request":
            change_data = input_data.get("change", {})
            required_fields = ["title", "description", "requester"]
            for field in required_fields:
                if field not in change_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False

        return True

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process change and configuration management requests.

        Args:
            input_data: {
                "action": "submit_change_request" | "classify_change" | "assess_impact" |
                          "approve_change" | "register_ci" | "create_baseline" |
                          "track_change_implementation" | "audit_changes" |
                          "visualize_dependencies" | "get_change_dashboard" |
                          "generate_change_report",
                "change": Change request data,
                "ci": Configuration item data,
                "baseline": Baseline data,
                "change_id": Change request ID,
                "ci_id": Configuration item ID,
                "filters": Query filters
            }

        Returns:
            Response based on action
        """
        action = input_data.get("action", "get_change_dashboard")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        actor_id = context.get("user_id") or input_data.get("actor_id") or "system"

        if action == "submit_change_request":
            return await submit_change_request(
                self,
                input_data.get("change", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "classify_change":
            return await classify_change(self, input_data.get("change_id"))  # type: ignore

        elif action == "assess_impact":
            return await assess_impact(self, input_data.get("change_id"))  # type: ignore

        elif action == "predict_impact":
            return await predict_impact(self, input_data.get("change", {}))

        elif action == "approve_change":
            return await approve_change(
                self, input_data.get("change_id"), input_data.get("approval", {})  # type: ignore
            )

        elif action == "review_change":
            return await review_change(
                self, input_data.get("change_id"), input_data.get("review", {})  # type: ignore
            )

        elif action == "implement_change":
            return await implement_change(
                self,
                input_data.get("change_id"),
                input_data.get("implementation", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                actor_id=actor_id,
            )

        elif action == "update_change_request":
            return await update_change_request(
                self,
                input_data.get("change_id"),
                input_data.get("updates", {}),
                tenant_id=tenant_id,
                actor_id=actor_id,
            )

        elif action == "rollback_change":
            return await rollback_change(
                self, input_data.get("change_id"), input_data.get("reason", "")  # type: ignore
            )

        elif action == "register_ci":
            return await register_ci(
                self,
                input_data.get("ci", {}),
                tenant_id=tenant_id,
            )

        elif action == "create_baseline":
            return await create_baseline(self, input_data.get("baseline", {}))

        elif action == "track_change_implementation":
            return await track_change_implementation(self, input_data.get("change_id"))  # type: ignore

        elif action == "audit_changes":
            return await audit_changes(self, input_data.get("filters", {}))

        elif action == "visualize_dependencies":
            return await visualize_dependencies(self, input_data.get("ci_id"))

        elif action == "get_change_dashboard":
            return await get_change_dashboard(self, input_data.get("filters", {}))

        elif action == "generate_change_report":
            return await generate_change_report(
                self, input_data.get("report_type", "summary"), input_data.get("filters", {})
            )

        elif action == "get_change_metrics":
            return await get_change_metrics(self, input_data.get("filters", {}))

        elif action == "cicd_webhook":
            return await handle_cicd_webhook(self, input_data.get("payload", {}))

        elif action == "query_impacted_cis":
            return await query_impacted_cis(self, input_data.get("ci_ids", []))

        elif action == "monitor_change":
            return await monitor_change(
                self, input_data.get("change_id"), input_data.get("window_minutes", 60)  # type: ignore
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    # -- Thin delegating methods (backward compat for direct calls) -----

    async def _submit_change_request(self, cd, *, tenant_id, correlation_id, actor_id):
        return await submit_change_request(
            self, cd, tenant_id=tenant_id, correlation_id=correlation_id, actor_id=actor_id
        )

    async def _classify_change(self, cid):
        return await classify_change(self, cid)

    async def _assess_impact(self, cid):
        return await assess_impact(self, cid)

    async def _predict_impact(self, cd):
        return await predict_impact(self, cd)

    async def _approve_change(self, cid, ad):
        return await approve_change(self, cid, ad)

    async def _review_change(self, cid, rd):
        return await review_change(self, cid, rd)

    async def _implement_change(self, cid, imp, *, tenant_id, correlation_id, actor_id):
        return await implement_change(
            self, cid, imp, tenant_id=tenant_id, correlation_id=correlation_id, actor_id=actor_id
        )

    async def _update_change_request(self, cid, upd, *, tenant_id, actor_id):
        return await update_change_request(self, cid, upd, tenant_id=tenant_id, actor_id=actor_id)

    async def _rollback_change(self, cid, reason):
        return await rollback_change(self, cid, reason)

    async def _register_ci(self, ci_data, *, tenant_id):
        return await register_ci(self, ci_data, tenant_id=tenant_id)

    async def _create_baseline(self, bd):
        return await create_baseline(self, bd)

    async def _track_change_implementation(self, cid):
        return await track_change_implementation(self, cid)

    async def _audit_changes(self, f):
        return await audit_changes(self, f)

    async def _visualize_dependencies(self, ci_id):
        return await visualize_dependencies(self, ci_id)

    async def _get_change_dashboard(self, f):
        return await get_change_dashboard(self, f)

    async def _generate_change_report(self, rt, f):
        return await generate_change_report(self, rt, f)

    async def _get_change_metrics(self, f):
        return await get_change_metrics(self, f)

    async def _handle_cicd_webhook(self, p):
        return await handle_cicd_webhook(self, p)

    async def _query_impacted_cis(self, ci_ids):
        return await query_impacted_cis(self, ci_ids)

    async def _monitor_change(self, cid, wm):
        return await monitor_change(self, cid, wm)

    async def _identify_impacted_cis(self, cd):
        return await identify_impacted_cis(self, cd)

    async def _assess_compliance_impact(self, c):
        return await assess_compliance_impact(self, c)

    async def _publish_event(self, topic, payload):
        return await publish_event(self, topic, payload)

    async def _record_change_audit(self, cid, action, *, actor_id, details=None):
        return await record_change_audit(self, cid, action, actor_id=actor_id, details=details)

    async def _matches_filters(self, change, filters):
        return await matches_filters(change, filters)

    async def _run_automated_tests(self, change, implementation):
        return await run_automated_tests(self, change, implementation)

    async def _run_staging_validation(self, change, implementation):
        return await run_staging_validation(self, change, implementation)

    async def _recommend_mitigation(self, prediction):
        return await recommend_mitigation(prediction)

    # ------------------------------------------------------------------
    # Cleanup & capabilities
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Change & Configuration Management Agent...")
        if hasattr(self.db_service, "close"):
            await self.db_service.close()
        if hasattr(self.itsm_service, "close"):
            await self.itsm_service.close()
        if isinstance(self.event_publisher, ChangeEventPublisher):
            await self.event_publisher.stop()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "change_request_intake",
            "change_classification",
            "change_impact_prediction",
            "impact_assessment",
            "risk_evaluation",
            "approval_workflow_orchestration",
            "change_review",
            "change_implementation",
            "change_update_versioning",
            "repository_integration",
            "iac_change_analysis",
            "cicd_webhook_tracking",
            "document_context_enrichment",
            "service_bus_eventing",
            "graph_dependency_analysis",
            "cmdb_management",
            "ci_registration",
            "baseline_management",
            "version_control",
            "change_implementation_tracking",
            "staging_validation",
            "automated_rollback",
            "change_audit",
            "dependency_mapping",
            "configuration_visualization",
            "change_dashboards",
            "change_reporting",
            "change_metrics",
            "post_change_monitoring",
        ]
