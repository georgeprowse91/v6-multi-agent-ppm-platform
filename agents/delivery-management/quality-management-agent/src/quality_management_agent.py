"""
Quality Management Agent

Purpose:
Ensures deliverables meet defined quality standards and satisfy stakeholder expectations.
Provides tools for planning quality activities, defining metrics, managing test cases and defects,
performing reviews and audits, and continuously improving processes.

Specification: agents/delivery-management/quality-management-agent/README.md
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from events import EventEnvelope
except Exception:
    from packages.contracts.src.events import EventEnvelope
from observability.tracing import get_trace_id

# Action handlers  ----------------------------------------------------------
from quality_actions import (
    analysis_actions,
    audit_actions,
    defect_actions,
    metric_actions,
    plan_actions,
    reporting_actions,
    requirement_actions,
    review_actions,
    test_actions,
)
from quality_utils import build_defect_classifier

from agents.common.connector_integration import (
    CalendarIntegrationService,
    DatabaseStorageService,
    DocumentManagementService,
)
from agents.common.integration_services import NaiveBayesTextClassifier
from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore


class QualityManagementAgent(BaseAgent):
    """
    Quality Management Agent - Ensures quality standards across projects and portfolios.

    Key Capabilities:
    - Quality planning and metric definition
    - Test management and execution
    - Defect and issue tracking
    - Review and audit management
    - Quality dashboards and reporting
    - Continuous improvement and root cause analysis
    - Compliance and standards management
    """

    def __init__(
        self, agent_id: str = "quality-management-agent", config: dict[str, Any] | None = None
    ):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.defect_severity_levels = (
            config.get("defect_severity_levels", ["critical", "high", "medium", "low"])
            if config
            else ["critical", "high", "medium", "low"]
        )

        self.quality_standards = (
            config.get("quality_standards", ["ISO 9001", "CMMI", "IEEE 829"])
            if config
            else ["ISO 9001", "CMMI", "IEEE 829"]
        )

        self.min_test_coverage = config.get("min_test_coverage", 0.80) if config else 0.80
        self.defect_density_threshold = (
            config.get("defect_density_threshold", 0.05) if config else 0.05
        )

        quality_plan_store_path = (
            Path(config.get("quality_plan_store_path", "data/quality_plans.json"))
            if config
            else Path("data/quality_plans.json")
        )
        test_case_store_path = (
            Path(config.get("test_case_store_path", "data/quality_test_cases.json"))
            if config
            else Path("data/quality_test_cases.json")
        )
        defect_store_path = (
            Path(config.get("defect_store_path", "data/quality_defects.json"))
            if config
            else Path("data/quality_defects.json")
        )
        audit_store_path = (
            Path(config.get("audit_store_path", "data/quality_audits.json"))
            if config
            else Path("data/quality_audits.json")
        )
        requirement_link_store_path = (
            Path(config.get("requirement_link_store_path", "data/quality_requirement_links.json"))
            if config
            else Path("data/quality_requirement_links.json")
        )
        coverage_trend_store_path = (
            Path(config.get("coverage_trend_store_path", "data/quality_coverage_trends.json"))
            if config
            else Path("data/quality_coverage_trends.json")
        )
        self.quality_plan_store = TenantStateStore(quality_plan_store_path)
        self.test_case_store = TenantStateStore(test_case_store_path)
        self.defect_store = TenantStateStore(defect_store_path)
        self.audit_store = TenantStateStore(audit_store_path)
        self.requirement_link_store = TenantStateStore(requirement_link_store_path)
        self.coverage_trend_store = TenantStateStore(coverage_trend_store_path)

        # Data stores (will be replaced with database)
        self.quality_plans: dict[str, Any] = {}
        self.test_cases: dict[str, Any] = {}
        self.test_suites: dict[str, Any] = {}
        self.test_executions: dict[str, Any] = {}
        self.defects: dict[str, Any] = {}
        self.reviews: dict[str, Any] = {}
        self.audits: dict[str, Any] = {}
        self.quality_metrics: dict[str, Any] = {}
        self.defect_density_history: dict[str, list[dict[str, Any]]] = {}
        self.defect_prediction_models: dict[str, dict[str, Any]] = {}
        self.defect_subsystem_models: dict[str, dict[str, Any]] = {}
        self.coverage_snapshots: dict[str, dict[str, Any]] = {}
        self.coverage_trends: dict[str, list[dict[str, Any]]] = {}
        self.quality_reports: dict[str, dict[str, Any]] = {}
        self.requirement_links: dict[str, dict[str, Any]] = {}
        self.db_service: DatabaseStorageService | None = None
        self.document_service: DocumentManagementService | None = None
        self.defect_classifier: NaiveBayesTextClassifier | None = None
        self.defect_ml_model: dict[str, Any] | None = None
        self.defect_cluster_model: dict[str, Any] | None = None
        self.calendar_client = (config or {}).get("calendar_client")
        self.calendar_service = CalendarIntegrationService((config or {}).get("calendar"))
        self.approval_agent = (config or {}).get("approval_agent")
        self.approval_agent_config = (config or {}).get("approval_agent_config", {})
        self.approval_agent_enabled = (
            (config or {}).get("approval_agent_enabled", True) if config is not None else True
        )
        self.integration_config = {
            "azure_devops": (config or {}).get("azure_devops", {}),
            "jira_xray": (config or {}).get("jira_xray", {}),
            "testrail": (config or {}).get("testrail", {}),
            "playwright": (config or {}).get("playwright", {}),
            "blob_storage": (config or {}).get("blob_storage", {}),
            "azure_ml": (config or {}).get("azure_ml", {}),
            "code_repos": (config or {}).get("code_repos", {}),
            "azure_openai": (config or {}).get("azure_openai", {}),
            "project_definition": (config or {}).get("project_definition", {}),
            "resource_capacity": (config or {}).get("resource_capacity", {}),
            "jira": (config or {}).get("jira", {}),
            "ci_pipelines": (config or {}).get("ci_pipelines", {}),
            "analytics": (config or {}).get("analytics", {}),
            "stakeholder_comms": (config or {}).get("stakeholder_comms", {}),
            "calendar": (config or {}).get("calendar", {}),
            "qa_tools": (config or {}).get("qa_tools", {}),
        }
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = get_event_bus()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize database connections, test tool integrations, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Quality Management Agent...")

        self.db_service = DatabaseStorageService(self.config.get("database"))
        self.document_service = DocumentManagementService(self.config.get("document_service"))
        self.defect_classifier = build_defect_classifier()
        self.defect_ml_model = await self._train_defect_classification_model()
        self.defect_cluster_model = await self._train_defect_cluster_model()

        self.logger.info("Quality Management Agent initialized")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Quality Management Agent...")
        if self.db_service and hasattr(self.db_service, "close"):
            await self.db_service.close()
        if self.event_bus and hasattr(self.event_bus, "stop"):
            await self.event_bus.stop()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "quality_planning",
            "metric_definition",
            "test_case_management",
            "test_suite_creation",
            "test_execution",
            "defect_tracking",
            "defect_prediction",
            "defect_classification",
            "review_scheduling",
            "audit_management",
            "quality_metrics_calculation",
            "defect_trend_analysis",
            "root_cause_analysis",
            "continuous_improvement",
            "quality_dashboards",
            "quality_reporting",
            "standards_compliance",
        ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "approve_quality_plan",
            "create_quality_plan",
            "define_metrics",
            "create_test_case",
            "create_test_suite",
            "execute_tests",
            "log_defect",
            "update_defect",
            "schedule_review",
            "conduct_audit",
            "calculate_metrics",
            "analyze_defect_trends",
            "perform_root_cause_analysis",
            "link_test_case_requirements",
            "update_test_case_links",
            "get_requirement_links",
            "sync_defect_tickets",
            "get_quality_dashboard",
            "generate_quality_report",
            "query_quality_artifacts",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "create_quality_plan":
            plan_data = input_data.get("plan", {})
            required_fields = ["project_id", "objectives"]
            for field in required_fields:
                if field not in plan_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False
        elif action == "approve_quality_plan":
            if not input_data.get("plan_id"):
                self.logger.warning("Missing required field: plan_id")
                return False

        elif action == "log_defect":
            defect_data = input_data.get("defect", {})
            required_fields = ["summary", "severity", "component"]
            for field in required_fields:
                if field not in defect_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False
        elif action == "link_test_case_requirements":
            link_data = input_data.get("link", {})
            required_fields = ["test_case_id", "requirement_ids"]
            for field in required_fields:
                if field not in link_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False
        elif action == "update_test_case_links":
            if not input_data.get("link_id"):
                self.logger.warning("Missing required field: link_id")
                return False
        elif action == "sync_defect_tickets":
            if not input_data.get("defect_ids"):
                self.logger.warning("Missing required field: defect_ids")
                return False

        return True

    # ------------------------------------------------------------------
    # Process (dispatch)
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process quality management requests.

        Dispatches to the appropriate action handler module based on
        the ``action`` field in *input_data*.
        """
        action = input_data.get("action", "get_quality_dashboard")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        if action == "create_quality_plan":
            return await plan_actions.create_quality_plan(
                self,
                input_data.get("plan", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "approve_quality_plan":
            return await plan_actions.approve_quality_plan(
                self,
                input_data.get("plan_id"),
                approver=input_data.get("approver", "unknown"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "define_metrics":
            return await metric_actions.define_metrics(
                self, input_data.get("project_id"), input_data.get("metrics", [])  # type: ignore
            )

        elif action == "create_test_case":
            return await test_actions.create_test_case(
                self,
                input_data.get("test_case", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "create_test_suite":
            return await test_actions.create_test_suite(self, input_data.get("test_suite", {}))

        elif action == "execute_tests":
            return await test_actions.execute_tests(
                self,
                input_data.get("test_execution", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "log_defect":
            return await defect_actions.log_defect(
                self,
                input_data.get("defect", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "update_defect":
            return await defect_actions.update_defect(
                self, input_data.get("defect_id"), input_data.get("updates", {})  # type: ignore
            )

        elif action == "schedule_review":
            return await review_actions.schedule_review(self, input_data.get("review", {}))

        elif action == "conduct_audit":
            return await audit_actions.conduct_audit(
                self,
                input_data.get("audit", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "calculate_metrics":
            return await metric_actions.calculate_metrics(self, input_data.get("project_id"))  # type: ignore

        elif action == "analyze_defect_trends":
            return await analysis_actions.analyze_defect_trends(self, input_data.get("project_id"))  # type: ignore

        elif action == "perform_root_cause_analysis":
            return await analysis_actions.perform_root_cause_analysis(
                self, input_data.get("defect_ids", [])
            )

        elif action == "link_test_case_requirements":
            return await requirement_actions.link_test_case_requirements(
                self,
                input_data.get("link", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "update_test_case_links":
            return await requirement_actions.update_test_case_links(
                self, input_data.get("link_id"), input_data.get("updates", {})  # type: ignore
            )

        elif action == "get_requirement_links":
            return await requirement_actions.get_requirement_links(
                self, input_data.get("filters", {}), tenant_id=tenant_id
            )

        elif action == "sync_defect_tickets":
            return await defect_actions.sync_defect_tickets(
                self,
                input_data.get("defect_ids", []),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "get_quality_dashboard":
            return await reporting_actions.get_quality_dashboard(
                self, input_data.get("project_id"), input_data.get("filters", {})
            )

        elif action == "generate_quality_report":
            return await reporting_actions.generate_quality_report(
                self, input_data.get("report_type", "summary"), input_data.get("filters", {})
            )

        elif action == "query_quality_artifacts":
            return await reporting_actions.query_quality_artifacts(
                self,
                input_data.get("filters", {}),
                tenant_id=tenant_id,
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Shared infrastructure helpers (used by action modules)
    # ------------------------------------------------------------------

    async def _publish_quality_event(
        self,
        event_name: str,
        *,
        payload: dict[str, Any],
        tenant_id: str,
        correlation_id: str,
    ) -> None:
        event = EventEnvelope(
            event_name=event_name,
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload=payload,
        )
        await self.event_bus.publish(event_name, event.model_dump(mode="json"))

    async def _store_record(
        self, collection: str, record_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        if self.db_service is None:
            self.db_service = DatabaseStorageService(self.config.get("database"))
        return await self.db_service.store(collection, record_id, data)

    # ------------------------------------------------------------------
    # ML model training helpers (delegated from action modules)
    # ------------------------------------------------------------------

    async def _train_defect_classification_model(self) -> dict[str, Any]:
        return await defect_actions._train_defect_classification_model(self)

    async def _train_defect_cluster_model(self) -> dict[str, Any]:
        return await defect_actions._train_defect_cluster_model(self)
