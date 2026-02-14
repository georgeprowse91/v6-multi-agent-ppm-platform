"""
Agent 14: Quality Management Agent

Purpose:
Ensures deliverables meet defined quality standards and satisfy stakeholder expectations.
Provides tools for planning quality activities, defining metrics, managing test cases and defects,
performing reviews and audits, and continuously improving processes.

Specification: agents/delivery-management/agent-14-quality-management/README.md
"""

import json
import math
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from events import EventEnvelope
from observability.tracing import get_trace_id

from agents.common.connector_integration import (
    CalendarIntegrationService,
    DatabaseStorageService,
    DocumentManagementService,
    DocumentMetadata,
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

    def __init__(self, agent_id: str = "agent_014", config: dict[str, Any] | None = None):
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
        self.calendar_service = CalendarIntegrationService(
            (config or {}).get("calendar")
        )
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

    async def initialize(self) -> None:
        """Initialize database connections, test tool integrations, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Quality Management Agent...")

        self.db_service = DatabaseStorageService(self.config.get("database"))
        self.document_service = DocumentManagementService(self.config.get("document_service"))
        self.defect_classifier = self._build_defect_classifier()
        self.defect_ml_model = await self._train_defect_classification_model()
        self.defect_cluster_model = await self._train_defect_cluster_model()
        # Integration configuration is captured in self.integration_config.
        # Each integration currently uses lightweight mocks that simulate
        # expected behaviors for orchestration, testing, and reporting.

        self.logger.info("Quality Management Agent initialized")

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
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "create_quality_plan":
            plan_data = input_data.get("plan", {})
            required_fields = ["project_id", "objectives"]
            for field in required_fields:
                if field not in plan_data:
                    self.logger.warning(f"Missing required field: {field}")
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
                    self.logger.warning(f"Missing required field: {field}")
                    return False
        elif action == "link_test_case_requirements":
            link_data = input_data.get("link", {})
            required_fields = ["test_case_id", "requirement_ids"]
            for field in required_fields:
                if field not in link_data:
                    self.logger.warning(f"Missing required field: {field}")
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

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process quality management requests.

        Args:
            input_data: {
                "action": "create_quality_plan" | "define_metrics" | "create_test_case" |
                          "create_test_suite" | "execute_tests" | "log_defect" |
                          "update_defect" | "schedule_review" | "conduct_audit" |
                          "calculate_metrics" | "analyze_defect_trends" |
                          "perform_root_cause_analysis" | "get_quality_dashboard" |
                          "generate_quality_report",
                "plan": Quality plan data,
                "metrics": Metric definitions,
                "test_case": Test case data,
                "test_suite": Test suite data,
                "test_execution": Test execution details,
                "defect": Defect information,
                "review": Review details,
                "audit": Audit information,
                "project_id": Project identifier,
                "defect_id": Defect ID,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - create_quality_plan: Plan ID and objectives
            - define_metrics: Metric IDs and thresholds
            - create_test_case: Test case ID and details
            - create_test_suite: Suite ID and test count
            - execute_tests: Execution results and coverage
            - log_defect: Defect ID and workflow status
            - update_defect: Updated defect status
            - schedule_review: Review ID and participants
            - conduct_audit: Audit findings and scores
            - calculate_metrics: Quality metrics and trends
            - analyze_defect_trends: Trend analysis and patterns
            - perform_root_cause_analysis: RCA results and recommendations
            - get_quality_dashboard: Dashboard data and visualizations
            - generate_quality_report: Report data
        """
        action = input_data.get("action", "get_quality_dashboard")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        if action == "create_quality_plan":
            return await self._create_quality_plan(
                input_data.get("plan", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "approve_quality_plan":
            return await self._approve_quality_plan(
                input_data.get("plan_id"),
                approver=input_data.get("approver", "unknown"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "define_metrics":
            return await self._define_metrics(
                input_data.get("project_id"), input_data.get("metrics", [])  # type: ignore
            )

        elif action == "create_test_case":
            return await self._create_test_case(
                input_data.get("test_case", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "create_test_suite":
            return await self._create_test_suite(input_data.get("test_suite", {}))

        elif action == "execute_tests":
            return await self._execute_tests(
                input_data.get("test_execution", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "log_defect":
            return await self._log_defect(
                input_data.get("defect", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "update_defect":
            return await self._update_defect(
                input_data.get("defect_id"), input_data.get("updates", {})  # type: ignore
            )

        elif action == "schedule_review":
            return await self._schedule_review(input_data.get("review", {}))

        elif action == "conduct_audit":
            return await self._conduct_audit(
                input_data.get("audit", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "calculate_metrics":
            return await self._calculate_metrics(input_data.get("project_id"))  # type: ignore

        elif action == "analyze_defect_trends":
            return await self._analyze_defect_trends(input_data.get("project_id"))  # type: ignore

        elif action == "perform_root_cause_analysis":
            return await self._perform_root_cause_analysis(input_data.get("defect_ids", []))

        elif action == "link_test_case_requirements":
            return await self._link_test_case_requirements(
                input_data.get("link", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "update_test_case_links":
            return await self._update_test_case_links(
                input_data.get("link_id"), input_data.get("updates", {})  # type: ignore
            )

        elif action == "get_requirement_links":
            return await self._get_requirement_links(
                input_data.get("filters", {}), tenant_id=tenant_id
            )

        elif action == "sync_defect_tickets":
            return await self._sync_defect_tickets(
                input_data.get("defect_ids", []),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "get_quality_dashboard":
            return await self._get_quality_dashboard(
                input_data.get("project_id"), input_data.get("filters", {})
            )

        elif action == "generate_quality_report":
            return await self._generate_quality_report(
                input_data.get("report_type", "summary"), input_data.get("filters", {})
            )
        elif action == "query_quality_artifacts":
            return await self._query_quality_artifacts(
                input_data.get("filters", {}),
                tenant_id=tenant_id,
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _create_quality_plan(
        self,
        plan_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Create quality plan with objectives and metrics.

        Returns plan ID and objectives.
        """
        self.logger.info(f"Creating quality plan for project: {plan_data.get('project_id')}")

        # Generate plan ID
        plan_id = await self._generate_plan_id()

        # Recommend metrics based on project type
        recommended_metrics = await self._recommend_quality_metrics(plan_data)

        # Create quality plan
        quality_plan = {
            "plan_id": plan_id,
            "project_id": plan_data.get("project_id"),
            "methodology": plan_data.get("methodology", "predictive"),
            "objectives": plan_data.get("objectives", []),
            "metrics": plan_data.get("metrics", recommended_metrics),
            "acceptance_criteria": plan_data.get("acceptance_criteria", []),
            "test_strategy": plan_data.get("test_strategy", {}),
            "review_schedule": plan_data.get("review_schedule", []),
            "responsible_roles": plan_data.get("responsible_roles", {}),
            "standards": plan_data.get("standards", self.quality_standards),
            "status": "Draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": plan_data.get("owner", "unknown"),
        }

        # Store plan
        self.quality_plans[plan_id] = quality_plan
        self.quality_plan_store.upsert(tenant_id, plan_id, quality_plan)
        await self._publish_quality_event(
            "quality.plan.created",
            payload={
                "plan_id": plan_id,
                "project_id": quality_plan.get("project_id"),
                "created_at": quality_plan.get("created_at"),
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        await self._store_record("quality_plans", plan_id, quality_plan)
        approval_response = await self._request_quality_plan_approval(
            plan_id,
            quality_plan,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        if approval_response:
            quality_plan = await self._apply_quality_plan_approval(
                quality_plan,
                approval_response,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
            await self._store_record("quality_plans", plan_id, quality_plan)

        return {
            "plan_id": plan_id,
            "project_id": quality_plan["project_id"],
            "objectives": quality_plan["objectives"],
            "metrics": quality_plan["metrics"],
            "recommended_metrics": recommended_metrics,
            "status": quality_plan["status"],
            "approval": approval_response,
            "next_steps": (
                "Await approval decision"
                if approval_response
                else "Review plan and submit for approval"
            ),
        }

    async def _approve_quality_plan(
        self,
        plan_id: str | None,
        *,
        approver: str,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Approve a quality plan and publish an approval event."""
        if not plan_id:
            raise ValueError("plan_id is required for approval")
        plan = self.quality_plans.get(plan_id)
        if not plan:
            stored_plan = self.quality_plan_store.get(tenant_id, plan_id)
            if not stored_plan:
                raise ValueError(f"Quality plan not found: {plan_id}")
            plan = stored_plan
            self.quality_plans[plan_id] = plan

        plan["status"] = "Approved"
        plan["approved_by"] = approver
        plan["approved_at"] = datetime.now(timezone.utc).isoformat()
        self.quality_plan_store.upsert(tenant_id, plan_id, plan)

        await self._publish_quality_event(
            "quality.plan.approved",
            payload={
                "plan_id": plan_id,
                "project_id": plan.get("project_id"),
                "approved_by": approver,
                "approved_at": plan.get("approved_at"),
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        await self._store_record("quality_plans", plan_id, plan)

        return {
            "plan_id": plan_id,
            "status": plan["status"],
            "approved_by": approver,
            "approved_at": plan.get("approved_at"),
        }

    async def _define_metrics(
        self, project_id: str, metrics: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Define quality metrics for project.

        Returns metric IDs and thresholds.
        """
        self.logger.info(f"Defining quality metrics for project: {project_id}")

        defined_metrics = []

        for metric_def in metrics:
            metric_id = await self._generate_metric_id()

            metric = {
                "metric_id": metric_id,
                "project_id": project_id,
                "name": metric_def.get("name"),
                "description": metric_def.get("description"),
                "type": metric_def.get("type"),  # defect_density, test_coverage, etc.
                "threshold": metric_def.get("threshold"),
                "target": metric_def.get("target"),
                "unit": metric_def.get("unit"),
                "collection_frequency": metric_def.get("collection_frequency", "daily"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            if project_id not in self.quality_metrics:
                self.quality_metrics[project_id] = []

            self.quality_metrics[project_id].append(metric)
            defined_metrics.append(metric)

            await self._store_record("quality_metric_definitions", metric_id, metric)

        return {
            "project_id": project_id,
            "metrics_defined": len(defined_metrics),
            "metrics": defined_metrics,
        }

    async def _create_test_case(
        self,
        test_case_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Create test case.

        Returns test case ID and details.
        """
        self.logger.info(f"Creating test case: {test_case_data.get('name')}")

        # Generate test case ID
        test_case_id = await self._generate_test_case_id()

        # Link to requirements
        requirements = await self._link_to_requirements(
            test_case_data.get("requirement_ids", []),
            project_id=test_case_data.get("project_id"),
        )
        if requirements:
            await self._link_test_case_requirements(
                {
                    "project_id": test_case_data.get("project_id"),
                    "test_case_id": test_case_id,
                    "requirement_ids": [req.get("requirement_id") for req in requirements],
                },
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        # Create test case
        test_case = {
            "test_case_id": test_case_id,
            "project_id": test_case_data.get("project_id"),
            "name": test_case_data.get("name"),
            "description": test_case_data.get("description"),
            "type": test_case_data.get("type", "functional"),  # functional, integration, etc.
            "priority": test_case_data.get("priority", "medium"),
            "steps": test_case_data.get("steps", []),
            "expected_results": test_case_data.get("expected_results"),
            "preconditions": test_case_data.get("preconditions", []),
            "requirements": requirements,
            "automation_status": test_case_data.get("automation_status", "manual"),
            "status": "Active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store test case
        self.test_cases[test_case_id] = test_case
        self.test_case_store.upsert(tenant_id, test_case_id, test_case)
        sync_status = await self._sync_test_management_assets("test_case", test_case)
        if sync_status.get("external_refs"):
            test_case["external_refs"] = sync_status["external_refs"]
        await self._publish_quality_event(
            "quality.test_case.created",
            payload={
                "test_case_id": test_case_id,
                "name": test_case.get("name"),
                "sync_status": sync_status,
                "created_at": test_case.get("created_at"),
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        await self._store_record("quality_test_cases", test_case_id, test_case)

        return {
            "test_case_id": test_case_id,
            "name": test_case["name"],
            "type": test_case["type"],
            "priority": test_case["priority"],
            "automation_status": test_case["automation_status"],
            "requirements_linked": len(requirements),
            "sync_status": sync_status,
        }

    async def _create_test_suite(self, suite_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create test suite from test cases.

        Returns suite ID and test count.
        """
        self.logger.info(f"Creating test suite: {suite_data.get('name')}")

        # Generate suite ID
        suite_id = await self._generate_suite_id()

        # Validate test case IDs
        test_case_ids = suite_data.get("test_case_ids", [])
        valid_test_cases = [tc_id for tc_id in test_case_ids if tc_id in self.test_cases]

        # Create test suite
        test_suite = {
            "suite_id": suite_id,
            "project_id": suite_data.get("project_id"),
            "name": suite_data.get("name"),
            "description": suite_data.get("description"),
            "test_case_ids": valid_test_cases,
            "test_environment": suite_data.get("test_environment"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store suite
        self.test_suites[suite_id] = test_suite

        await self._store_record("quality_test_suites", suite_id, test_suite)
        sync_status = await self._sync_test_management_assets("test_suite", test_suite)
        if sync_status.get("external_refs"):
            test_suite["external_refs"] = sync_status["external_refs"]

        return {
            "suite_id": suite_id,
            "name": test_suite["name"],
            "test_case_count": len(valid_test_cases),
            "test_environment": test_suite["test_environment"],
            "sync_status": sync_status,
        }

    async def _execute_tests(
        self,
        execution_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Execute tests and record results.

        Returns execution results and coverage.
        """
        self.logger.info(f"Executing test suite: {execution_data.get('suite_id')}")

        suite_id = execution_data.get("suite_id")
        test_suite = self.test_suites.get(suite_id)  # type: ignore

        if not test_suite:
            raise ValueError(f"Test suite not found: {suite_id}")

        # Generate execution ID
        execution_id = await self._generate_execution_id()

        # Execute tests by importing JSON results if provided
        test_results = await self._import_test_results(execution_data)
        execution_mode = execution_data.get("execution_mode", "manual")
        if not test_results:
            if execution_mode == "ci":
                test_results = await self._fetch_ci_test_results(execution_data)
            elif execution_mode == "playwright":
                test_results = await self._run_playwright_tests(
                    test_suite, execution_data.get("playwright_config", {})
                )
            else:
                test_results = await self._run_test_suite(test_suite, execution_mode)

        # Calculate pass rate
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.get("result") == "pass")
        failed_tests = sum(1 for r in test_results if r.get("result") == "fail")
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0

        # Calculate code coverage
        code_coverage = await self._calculate_code_coverage(execution_data.get("project_id"))  # type: ignore
        coverage_snapshot = await self._record_coverage_snapshot(
            execution_data.get("project_id"), code_coverage
        )

        # Create execution record
        artifact_blob = await self._store_test_results_in_blob(
            suite_id, execution_id, test_results, execution_data
        )
        sync_status = await self._sync_test_execution_results(
            execution_id, test_results, execution_data
        )
        await self._update_quality_kpis_from_execution(
            execution_data.get("project_id"),
            test_results,
            code_coverage,
            sync_status,
        )
        execution = {
            "execution_id": execution_id,
            "suite_id": suite_id,
            "project_id": execution_data.get("project_id"),
            "execution_mode": execution_data.get("execution_mode", "manual"),
            "executed_by": execution_data.get("executed_by", "system"),
            "test_results": test_results,
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "pass_rate": pass_rate,
            "code_coverage": code_coverage,
            "coverage_snapshot": coverage_snapshot,
            "artifact_blob": artifact_blob,
            "sync_status": sync_status,
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store execution
        self.test_executions[execution_id] = execution

        # Auto-log defects for failed tests
        defects_logged = []
        if execution_data.get("auto_log_defects", True):
            for result in test_results:
                if result.get("result") == "fail":
                    defect = await self._auto_log_defect_from_test(
                        result,
                        tenant_id=tenant_id,
                        correlation_id=correlation_id,
                    )
                    defects_logged.append(defect.get("defect_id"))

        await self._store_record("quality_test_executions", execution_id, execution)
        await self._publish_quality_event(
            "quality.test_execution.completed",
            payload={
                "execution_id": execution_id,
                "suite_id": suite_id,
                "project_id": execution_data.get("project_id"),
                "pass_rate": pass_rate,
                "code_coverage": code_coverage,
                "artifact_blob": artifact_blob,
                "sync_status": sync_status,
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        return {
            "execution_id": execution_id,
            "suite_id": suite_id,
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "pass_rate": pass_rate,
            "code_coverage": code_coverage,
            "coverage_threshold_met": code_coverage >= self.min_test_coverage,
            "defects_logged": len(defects_logged),
            "defect_ids": defects_logged,
            "artifact_blob": artifact_blob,
            "sync_status": sync_status,
            "coverage_snapshot": coverage_snapshot,
        }

    async def _log_defect(
        self,
        defect_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Log a defect.

        Returns defect ID and workflow status.
        """
        self.logger.info(f"Logging defect: {defect_data.get('summary')}")

        # Generate defect ID
        defect_id = await self._generate_defect_id()

        # Auto-classify severity and root cause
        auto_classification = await self._auto_classify_defect(defect_data)

        # Create defect
        defect = {
            "defect_id": defect_id,
            "project_id": defect_data.get("project_id"),
            "summary": defect_data.get("summary"),
            "description": defect_data.get("description"),
            "severity": defect_data.get("severity", auto_classification.get("severity")),
            "priority": defect_data.get("priority", auto_classification.get("priority")),
            "category": auto_classification.get("category"),
            "component": defect_data.get("component"),
            "test_case_id": defect_data.get("test_case_id"),
            "steps_to_reproduce": defect_data.get("steps_to_reproduce", []),
            "expected_behavior": defect_data.get("expected_behavior"),
            "actual_behavior": defect_data.get("actual_behavior"),
            "environment": defect_data.get("environment"),
            "attachments": defect_data.get("attachments", []),
            "assigned_to": None,
            "root_cause": auto_classification.get("root_cause"),
            "status": "Open",
            "resolution": None,
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "logged_by": defect_data.get("logged_by", "unknown"),
            "status_history": [{"status": "Open", "timestamp": datetime.now(timezone.utc).isoformat()}],
        }

        # Store defect
        self.defects[defect_id] = defect
        self.defect_store.upsert(tenant_id, defect_id, defect)
        self.defect_ml_model = await self._train_defect_classification_model()
        self.defect_cluster_model = await self._train_defect_cluster_model()
        await self._publish_quality_event(
            "quality.defect.logged",
            payload={
                "defect_id": defect_id,
                "severity": defect.get("severity"),
                "status": defect.get("status"),
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        # Assign owner based on component
        assigned_owner = await self._assign_defect_owner(defect)
        defect["assigned_to"] = assigned_owner
        defect["external_sync"] = await self._sync_defect_ticket(
            defect, action="create", tenant_id=tenant_id, correlation_id=correlation_id
        )

        await self._store_record("quality_defects", defect_id, defect)

        return {
            "defect_id": defect_id,
            "summary": defect["summary"],
            "severity": defect["severity"],
            "priority": defect["priority"],
            "assigned_to": defect["assigned_to"],
            "status": "Open",
            "auto_classification": auto_classification,
        }

    async def _update_defect(self, defect_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """
        Update defect status and details.

        Returns updated defect status.
        """
        self.logger.info(f"Updating defect: {defect_id}")

        defect = self.defects.get(defect_id)
        if not defect:
            raise ValueError(f"Defect not found: {defect_id}")

        # Track status changes
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
            await self._apply_external_defect_updates(defect, external_updates)

        # Apply updates
        for key, value in updates.items():
            if key in defect and key != "status_history":
                defect[key] = value

        defect["last_updated"] = datetime.now(timezone.utc).isoformat()

        # Calculate resolution time if resolved
        if defect.get("status") in ["Resolved", "Closed", "Verified"]:
            resolution_time = await self._calculate_resolution_time(defect)
            defect["resolution_time_hours"] = resolution_time

        defect["external_sync"] = await self._sync_defect_ticket(
            defect,
            action="update",
            tenant_id=defect.get("project_id", "unknown"),
            correlation_id=str(uuid.uuid4()),
        )

        await self._store_record("quality_defects", defect_id, defect)

        return {
            "defect_id": defect_id,
            "status": defect["status"],
            "resolution": defect.get("resolution"),
            "resolution_time_hours": defect.get("resolution_time_hours"),
            "last_updated": defect["last_updated"],
        }

    async def _schedule_review(self, review_data: dict[str, Any]) -> dict[str, Any]:
        """
        Schedule quality review or audit.

        Returns review ID and participants.
        """
        self.logger.info(f"Scheduling review: {review_data.get('title')}")

        # Generate review ID
        review_id = await self._generate_review_id()

        # Create review
        review = {
            "review_id": review_id,
            "project_id": review_data.get("project_id"),
            "type": review_data.get(
                "type", "peer_review"
            ),  # peer_review, code_review, design_review
            "title": review_data.get("title"),
            "scope": review_data.get("scope"),
            "participants": review_data.get("participants", []),
            "scheduled_date": review_data.get("scheduled_date"),
            "agenda": review_data.get("agenda", []),
            "artifacts": review_data.get("artifacts", []),
            "findings": [],
            "action_items": [],
            "status": "Scheduled",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store review
        self.reviews[review_id] = review

        calendar_event = await self._schedule_calendar_event(review)
        if calendar_event:
            review["calendar_event"] = calendar_event
        await self._store_record("quality_reviews", review_id, review)
        await self._publish_quality_event(
            "quality.review.scheduled",
            payload={
                "review_id": review_id,
                "project_id": review.get("project_id"),
                "scheduled_date": review.get("scheduled_date"),
                "calendar_event": calendar_event,
            },
            tenant_id=review.get("project_id") or "unknown",
            correlation_id=str(uuid.uuid4()),
        )

        return {
            "review_id": review_id,
            "title": review["title"],
            "type": review["type"],
            "scheduled_date": review["scheduled_date"],
            "participants": review["participants"],
            "participant_count": len(review["participants"]),
            "calendar_event": calendar_event,
        }

    async def _conduct_audit(
        self,
        audit_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """
        Conduct quality audit.

        Returns audit findings and scores.
        """
        self.logger.info(f"Conducting audit: {audit_data.get('title')}")

        # Generate audit ID
        audit_id = await self._generate_audit_id()

        # Perform audit checks
        audit_checks = await self._perform_audit_checks(
            audit_data.get("project_id"), audit_data.get("checklist", [])  # type: ignore
        )

        # Calculate audit score
        audit_score = await self._calculate_audit_score(audit_checks)

        # Create audit record
        audit = {
            "audit_id": audit_id,
            "project_id": audit_data.get("project_id"),
            "title": audit_data.get("title"),
            "type": audit_data.get("type", "process_audit"),
            "auditor": audit_data.get("auditor"),
            "audit_date": datetime.now(timezone.utc).isoformat(),
            "checklist": audit_data.get("checklist", []),
            "checks_performed": audit_checks,
            "audit_score": audit_score,
            "findings": await self._extract_audit_findings(audit_checks),
            "recommendations": await self._generate_audit_recommendations(audit_checks),
            "status": "Completed",
            "report": audit_data.get("report"),
        }

        # Store audit
        self.audits[audit_id] = audit
        self.audit_store.upsert(tenant_id, audit_id, audit)
        await self._publish_quality_event(
            "quality.audit.completed",
            payload={
                "audit_id": audit_id,
                "project_id": audit.get("project_id"),
                "score": audit.get("audit_score"),
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        audit_document = await self._publish_audit_document(audit, audit_data)
        if audit_document:
            audit["document"] = audit_document
        await self._store_record("quality_audits", audit_id, audit)

        return {
            "audit_id": audit_id,
            "project_id": audit["project_id"],
            "audit_score": audit_score,
            "total_checks": len(audit_checks),
            "passed_checks": sum(1 for c in audit_checks if c.get("result") == "pass"),
            "findings": audit["findings"],
            "recommendations": audit["recommendations"],
        }

    async def _calculate_metrics(self, project_id: str) -> dict[str, Any]:
        """
        Calculate quality metrics for project.

        Returns quality metrics and trends.
        """
        self.logger.info(f"Calculating quality metrics for project: {project_id}")

        # Get project defects
        project_defects = [d for d in self.defects.values() if d.get("project_id") == project_id]

        # Calculate defect metrics
        total_defects = len(project_defects)
        open_defects = len([d for d in project_defects if d.get("status") == "Open"])
        critical_defects = len([d for d in project_defects if d.get("severity") == "critical"])

        # Calculate defect density
        defect_density = await self._calculate_defect_density(project_id, total_defects)
        code_size = await self._get_code_size_metrics(project_id)
        defect_density_per_fp = await self._calculate_defect_density_per_fp(
            project_id, total_defects
        )

        # Get test coverage
        test_coverage = await self._get_latest_test_coverage(project_id)
        coverage_snapshot = await self._fetch_coverage_metrics(project_id)
        if coverage_snapshot:
            self.coverage_snapshots[project_id] = coverage_snapshot
            test_coverage = float(coverage_snapshot.get("coverage_pct", test_coverage))

        # Calculate mean time to resolution
        mttr = await self._calculate_mttr(project_defects)

        # Get pass rate
        pass_rate = await self._calculate_pass_rate(project_id)

        # Calculate quality score
        quality_score = await self._calculate_quality_score(
            defect_density, test_coverage, pass_rate
        )
        coverage_trend = await self._calculate_coverage_trend(project_id)

        model_summary = await self._train_defect_prediction_model(project_id)
        subsystem_model = await self._train_defect_subsystem_model(project_id, project_defects)
        improvement_recommendations = await self._generate_quality_improvement_recommendations(
            project_id,
            project_defects,
            test_coverage,
            pass_rate,
            coverage_snapshot,
        )
        metrics = {
            "project_id": project_id,
            "total_defects": total_defects,
            "open_defects": open_defects,
            "critical_defects": critical_defects,
            "defect_density": defect_density,
            "defect_density_per_function_point": defect_density_per_fp,
            "code_size_metrics": code_size,
            "test_coverage_pct": test_coverage,
            "coverage_snapshot": coverage_snapshot,
            "coverage_trend": coverage_trend,
            "pass_rate_pct": pass_rate,
            "mean_time_to_resolution_hours": mttr,
            "quality_score": quality_score,
            "defect_prediction_model": model_summary,
            "defect_subsystem_model": subsystem_model,
            "improvement_recommendations": improvement_recommendations,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

        history = self.defect_density_history.setdefault(project_id, [])
        history.append(
            {"defect_density": defect_density, "timestamp": metrics["calculated_at"]}
        )
        metrics_record_id = f"QMET-{project_id}-{metrics['calculated_at']}"
        await self._store_record("quality_metrics", metrics_record_id, metrics)
        await self._publish_quality_event(
            "quality.metrics.calculated",
            payload={
                "project_id": project_id,
                "defect_density": defect_density,
                "test_coverage_pct": test_coverage,
                "quality_score": quality_score,
                "model_version": model_summary.get("model_version"),
            },
            tenant_id=project_id,
            correlation_id=str(uuid.uuid4()),
        )
        await self._publish_improvement_recommendations(
            project_id,
            improvement_recommendations,
        )

        return metrics

    async def _analyze_defect_trends(self, project_id: str) -> dict[str, Any]:
        """
        Analyze defect trends and patterns.

        Returns trend analysis and patterns.
        """
        self.logger.info(f"Analyzing defect trends for project: {project_id}")

        # Get project defects
        project_defects = [d for d in self.defects.values() if d.get("project_id") == project_id]

        # Analyze trends over time
        trends = await self._calculate_defect_trends_over_time(project_defects)

        # Identify patterns
        patterns = await self._identify_defect_patterns(project_defects)

        # Detect anomalies
        anomalies = await self._detect_defect_anomalies(project_defects)
        defect_density_prediction = await self._predict_defect_density(project_id)

        return {
            "project_id": project_id,
            "trends": trends,
            "patterns": patterns,
            "anomalies": anomalies,
            "defect_density_prediction": defect_density_prediction,
            "total_defects_analyzed": len(project_defects),
            "cluster_insights": await self._summarize_defect_clusters(project_defects),
        }

    async def _perform_root_cause_analysis(self, defect_ids: list[str]) -> dict[str, Any]:
        """
        Perform root cause analysis on defects.

        Returns RCA results and recommendations.
        """
        self.logger.info(f"Performing RCA on {len(defect_ids)} defects")

        # Get defects
        defects_to_analyze = [
            self.defects.get(defect_id) for defect_id in defect_ids if defect_id in self.defects
        ]

        # Identify common root causes
        root_causes = await self._identify_root_causes(defects_to_analyze)  # type: ignore

        # Perform Pareto analysis
        pareto_analysis = await self._perform_pareto_analysis(root_causes)

        # Generate recommendations
        recommendations = await self._generate_improvement_recommendations(
            root_causes, pareto_analysis
        )
        subsystem_recommendations = await self._recommend_refactoring_targets(defects_to_analyze)

        return {
            "defects_analyzed": len(defects_to_analyze),
            "root_causes": root_causes,
            "pareto_analysis": pareto_analysis,
            "recommendations": recommendations,
            "refactoring_recommendations": subsystem_recommendations,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _get_quality_dashboard(
        self, project_id: str | None, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Get quality dashboard data.

        Returns dashboard data and visualizations.
        """
        self.logger.info(f"Getting quality dashboard for project: {project_id}")

        # Calculate current metrics
        metrics = await self._calculate_metrics(project_id) if project_id else {}

        # Get defect statistics
        defect_stats = await self._get_defect_statistics(project_id, filters)

        # Get test execution summary
        test_summary = await self._get_test_execution_summary(project_id, filters)

        # Get recent audits
        recent_audits = await self._get_recent_audits(project_id, filters)

        return {
            "project_id": project_id,
            "metrics": metrics,
            "defect_statistics": defect_stats,
            "test_summary": test_summary,
            "recent_audits": recent_audits,
            "recommendations": metrics.get("improvement_recommendations", [])
            if isinstance(metrics, dict)
            else [],
            "dashboard_generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _generate_quality_report(
        self, report_type: str, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generate quality report.

        Returns report data.
        """
        self.logger.info(f"Generating {report_type} quality report")

        if report_type == "summary":
            report = await self._generate_summary_report(filters)
        elif report_type == "defect_analysis":
            report = await self._generate_defect_analysis_report(filters)
        elif report_type == "test_coverage":
            report = await self._generate_test_coverage_report(filters)
        elif report_type == "audit_summary":
            report = await self._generate_audit_summary_report(filters)
        elif report_type == "release_notes":
            report = await self._generate_release_notes_report(filters)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

        await self._publish_quality_event(
            "quality.report.published",
            payload={"report_type": report_type, "filters": filters},
            tenant_id=filters.get("tenant_id", "unknown"),
            correlation_id=str(uuid.uuid4()),
        )
        return report

    # Helper methods

    async def _generate_plan_id(self) -> str:
        """Generate unique quality plan ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"QP-{timestamp}"

    async def _generate_metric_id(self) -> str:
        """Generate unique metric ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"QM-{timestamp}"

    async def _generate_test_case_id(self) -> str:
        """Generate unique test case ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"TC-{timestamp}"

    async def _generate_suite_id(self) -> str:
        """Generate unique test suite ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"TS-{timestamp}"

    async def _generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"EX-{timestamp}"

    async def _generate_defect_id(self) -> str:
        """Generate unique defect ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"DEF-{timestamp}"

    async def _generate_review_id(self) -> str:
        """Generate unique review ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"REV-{timestamp}"

    async def _generate_audit_id(self) -> str:
        """Generate unique audit ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"AUD-{timestamp}"

    async def _link_test_case_requirements(
        self,
        link_data: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Create a requirement linkage record for a test case."""
        link_id = f"TRL-{uuid.uuid4().hex[:8]}"
        requirement_ids = list(
            {str(req) for req in link_data.get("requirement_ids", []) if req}
        )
        requirements = await self._link_to_requirements(
            requirement_ids, project_id=link_data.get("project_id")
        )
        link_record = {
            "link_id": link_id,
            "project_id": link_data.get("project_id"),
            "test_case_id": link_data.get("test_case_id"),
            "requirements": requirements,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "status": "linked",
        }
        self.requirement_links[link_id] = link_record
        self.requirement_link_store.upsert(tenant_id, link_id, link_record)
        await self._store_record("quality_requirement_links", link_id, link_record)
        await self._publish_quality_event(
            "quality.requirements.linked",
            payload={
                "link_id": link_id,
                "project_id": link_record.get("project_id"),
                "test_case_id": link_record.get("test_case_id"),
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        return link_record

    async def _update_test_case_links(self, link_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update a requirement linkage record."""
        link_record = self.requirement_links.get(link_id)
        if not link_record:
            raise ValueError(f"Requirement link not found: {link_id}")
        if "requirement_ids" in updates:
            requirement_ids = list({str(req) for req in updates.get("requirement_ids", []) if req})
            link_record["requirements"] = await self._link_to_requirements(
                requirement_ids, project_id=link_record.get("project_id")
            )
        if "status" in updates:
            link_record["status"] = updates.get("status")
        link_record["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.requirement_links[link_id] = link_record
        await self._store_record("quality_requirement_links", link_id, link_record)
        return link_record

    async def _get_requirement_links(
        self, filters: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """Query requirement linkage records by filters."""
        project_id = filters.get("project_id")
        test_case_id = filters.get("test_case_id")
        requirement_id = filters.get("requirement_id")
        link_records = list(self.requirement_links.values())
        if not link_records and tenant_id:
            link_records = self.requirement_link_store.list(tenant_id)
        filtered = []
        for record in link_records:
            if project_id and record.get("project_id") != project_id:
                continue
            if test_case_id and record.get("test_case_id") != test_case_id:
                continue
            if requirement_id:
                requirements = record.get("requirements", [])
                if not any(req.get("requirement_id") == requirement_id for req in requirements):
                    continue
            filtered.append(record)
        return {"count": len(filtered), "links": filtered}

    async def _recommend_quality_metrics(self, plan_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Recommend quality metrics based on project type."""
        baseline = [
            {
                "name": "defect_density",
                "threshold": self.defect_density_threshold,
                "unit": "defects/kloc",
            },
            {"name": "test_coverage", "threshold": self.min_test_coverage, "unit": "percentage"},
            {"name": "pass_rate", "threshold": 0.95, "unit": "percentage"},
            {"name": "mean_time_to_resolution", "threshold": 48, "unit": "hours"},
        ]
        project_type = str(plan_data.get("project_type", "")).lower()
        if project_type in {"compliance", "regulated"}:
            baseline.append(
                {"name": "audit_score", "threshold": 0.9, "unit": "percentage"}
            )
        return baseline

    async def _link_to_requirements(
        self, requirement_ids: list[str], project_id: str | None
    ) -> list[dict[str, Any]]:
        """Link test case to requirements."""
        if not requirement_ids:
            return []
        requirements = await self._fetch_project_requirements(project_id)
        requirement_lookup = {
            str(req.get("requirement_id") or req.get("id")): req for req in requirements
        }
        linked = []
        for req_id in requirement_ids:
            req_record = requirement_lookup.get(str(req_id))
            linked.append(
                {
                    "requirement_id": req_id,
                    "title": req_record.get("title") if req_record else None,
                    "status": "validated" if req_record else "unverified",
                }
            )
        return linked

    async def _fetch_project_requirements(self, project_id: str | None) -> list[dict[str, Any]]:
        if not project_id:
            return []
        project_definition_client = (self.config or {}).get("project_definition_client")
        if project_definition_client and hasattr(project_definition_client, "get_requirements"):
            response = project_definition_client.get_requirements(project_id)
            if hasattr(response, "__await__"):
                response = await response
            requirements = response.get("requirements", []) if isinstance(response, dict) else []
            return requirements
        requirements_config = self.integration_config.get("project_definition", {}).get(
            "requirements_by_project", {}
        )
        return requirements_config.get(project_id, [])

    async def _run_test_suite(
        self, test_suite: dict[str, Any], execution_mode: str
    ) -> list[dict[str, Any]]:
        """Execute test suite."""
        results: list[dict[str, Any]] = []
        for test_case_id in test_suite.get("test_case_ids", []):
            test_case = self.test_cases.get(test_case_id)
            if test_case:
                # Simulate test execution
                results.append(
                    {
                        "test_case_id": test_case_id,
                        "name": test_case.get("name"),
                        "result": "pass",  # Baseline
                        "execution_time_ms": 1000,
                    }
                )
        return results

    async def _calculate_code_coverage(self, project_id: str) -> float:
        """Calculate code coverage percentage."""
        ci_coverage = await self._fetch_ci_coverage_report(project_id)
        if ci_coverage:
            self.coverage_snapshots[project_id] = ci_coverage
            return float(ci_coverage.get("coverage_pct", 0.0))
        coverage_snapshot = await self._fetch_coverage_metrics(project_id)
        if coverage_snapshot:
            self.coverage_snapshots[project_id] = coverage_snapshot
            return float(coverage_snapshot.get("coverage_pct", 0.0))
        return 85.0  # Baseline

    async def _record_coverage_snapshot(
        self, project_id: str | None, coverage_pct: float
    ) -> dict[str, Any] | None:
        if not project_id:
            return None
        snapshot = {
            "project_id": project_id,
            "coverage_pct": coverage_pct,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        history = self.coverage_trends.setdefault(project_id, [])
        history.append(snapshot)
        self.coverage_trend_store.upsert(project_id, snapshot["captured_at"], snapshot)
        await self._store_record("quality_coverage_trends", snapshot["captured_at"], snapshot)
        await self._publish_quality_event(
            "quality.coverage.trend.updated",
            payload=snapshot,
            tenant_id=project_id,
            correlation_id=str(uuid.uuid4()),
        )
        return snapshot

    async def _auto_log_defect_from_test(
        self,
        test_result: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Automatically log defect from failed test."""
        defect_data = {
            "project_id": test_result.get("project_id"),
            "summary": f"Test failure: {test_result.get('name')}",
            "description": f"Test {test_result.get('test_case_id')} failed",
            "severity": "medium",
            "component": "unknown",
            "test_case_id": test_result.get("test_case_id"),
            "logged_by": "system",
        }
        return await self._log_defect(
            defect_data,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

    async def _auto_classify_defect(self, defect_data: dict[str, Any]) -> dict[str, Any]:
        """Auto-classify defect severity and root cause using AI."""
        classification = await self._classify_defect(defect_data)
        category = classification.get("category", "code_defect")
        severity = defect_data.get("severity") or classification.get(
            "severity", self._severity_from_category(category)
        )
        priority = defect_data.get("priority") or classification.get(
            "priority", "high" if severity in {"critical", "high"} else "medium"
        )
        return {
            "severity": severity,
            "priority": priority,
            "root_cause": self._root_cause_from_category(category),
            "category": category,
            "classification_confidence": classification.get("probabilities", {}),
            "model": classification.get("model", "statistical"),
        }

    async def _classify_defect(self, defect_data: dict[str, Any]) -> dict[str, Any]:
        """Classify defect category using learned text/statistical models."""
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
        if not self.defect_ml_model or not self.defect_ml_model.get("label_tokens"):
            self.defect_ml_model = await self._train_defect_classification_model()
        model = self.defect_ml_model or {}
        label_scores = self._score_labels(content, model.get("label_tokens", {}))
        if not label_scores:
            classifier = self._get_defect_classifier()
            category, probabilities = classifier.predict(content)
            return {
                "category": category,
                "probabilities": probabilities,
                "model": "naive_bayes_fallback",
            }
        category = max(label_scores, key=label_scores.get)
        probabilities = self._normalize_scores(label_scores)
        severity_scores = self._score_labels(content, model.get("severity_tokens", {}))
        severity = max(severity_scores, key=severity_scores.get) if severity_scores else None
        return {
            "category": category,
            "probabilities": probabilities,
            "severity": severity,
            "model": "token_frequency",
        }

    async def _assign_defect_owner(self, defect: dict[str, Any]) -> str:
        """Assign defect owner based on component."""
        resource_client = (self.config or {}).get("resource_capacity_client")
        required_skills = self._derive_required_skills(defect)
        if resource_client:
            if hasattr(resource_client, "match_skills"):
                results = resource_client.match_skills(required_skills)
                if results:
                    return results[0].get("resource_id", "unassigned")
            if hasattr(resource_client, "search_resources"):
                results = resource_client.search_resources({"skills": required_skills})
                if results:
                    return results[0].get("resource_id", "unassigned")
        candidates = self.integration_config.get("resource_capacity", {}).get("candidates", [])
        if not candidates:
            return "unassigned"
        scored = sorted(
            (
                (self._score_resource_candidate(candidate, required_skills), candidate)
                for candidate in candidates
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        return scored[0][1].get("resource_id", "unassigned") if scored else "unassigned"

    def _derive_required_skills(self, defect: dict[str, Any]) -> list[str]:
        component = defect.get("component")
        category = defect.get("root_cause")
        required_skills = [skill for skill in [component, category] if skill]
        if defect.get("severity") == "critical":
            required_skills.append("incident_response")
        return required_skills

    def _score_resource_candidate(self, candidate: dict[str, Any], skills: list[str]) -> float:
        candidate_skills = set(candidate.get("skills", []))
        skill_match = sum(1 for skill in skills if skill in candidate_skills)
        availability = float(candidate.get("availability", 0.0))
        return skill_match * 0.7 + availability * 0.3

    async def _calculate_resolution_time(self, defect: dict[str, Any]) -> float:
        """Calculate defect resolution time in hours."""
        logged_at = datetime.fromisoformat(defect.get("logged_at"))  # type: ignore
        resolved_at = datetime.now(timezone.utc)

        if defect.get("status_history"):
            for entry in reversed(defect["status_history"]):
                if entry.get("status") in ["Resolved", "Closed"]:
                    resolved_at = datetime.fromisoformat(entry["timestamp"])
                    break

        delta = resolved_at - logged_at
        return delta.total_seconds() / 3600

    async def _perform_audit_checks(
        self, project_id: str, checklist: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Perform audit checks."""
        checks = []
        static_analysis = self.integration_config.get("qa_tools", {}).get("static_analysis", {})
        lint_issues = static_analysis.get("issues", [])
        lint_result = "fail" if lint_issues else "pass"
        checks.append(
            {
                "check": "static_analysis",
                "result": lint_result,
                "notes": "Issues detected" if lint_issues else "No issues detected",
                "issues": lint_issues,
            }
        )
        coverage_snapshot = await self._fetch_coverage_metrics(project_id)
        coverage_pct = float(coverage_snapshot.get("coverage_pct", 0.0)) if coverage_snapshot else 0.0
        coverage_result = "pass" if coverage_pct >= self.min_test_coverage * 100 else "fail"
        checks.append(
            {
                "check": "coverage_threshold",
                "result": coverage_result,
                "notes": f"Coverage {coverage_pct:.1f}%",
            }
        )
        for item in checklist:
            checks.append(
                {
                    "check": item.get("check"),
                    "result": item.get("result", "pass"),
                    "notes": item.get("notes", ""),
                }
            )
        return checks

    async def _calculate_audit_score(self, checks: list[dict[str, Any]]) -> float:
        """Calculate audit score."""
        if not checks:
            return 0.0

        passed = sum(1 for c in checks if c.get("result") == "pass")
        return (passed / len(checks)) * 100

    async def _extract_audit_findings(self, checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract audit findings from checks."""
        findings = []
        for check in checks:
            if check.get("result") == "fail":
                findings.append(
                    {
                        "check": check.get("check"),
                        "severity": "high",
                        "description": check.get("notes", "Failed audit check"),
                    }
                )
        return findings

    async def _generate_audit_recommendations(self, checks: list[dict[str, Any]]) -> list[str]:
        """Generate audit recommendations."""
        recommendations = []
        failed_checks = [c for c in checks if c.get("result") == "fail"]

        if failed_checks:
            recommendations.append("Address failed audit checks immediately")
            recommendations.append("Implement corrective action plan")

        return recommendations

    async def _calculate_defect_density(self, project_id: str, total_defects: int) -> float:
        """Calculate defect density (defects per KLOC)."""
        code_size = await self._get_code_size_metrics(project_id)
        loc = code_size.get("loc")
        kloc = code_size.get("kloc", (float(loc) / 1000.0) if loc else 10.0)
        return total_defects / kloc if kloc > 0 else 0

    async def _calculate_defect_density_per_fp(
        self, project_id: str, total_defects: int
    ) -> float | None:
        code_size = await self._get_code_size_metrics(project_id)
        function_points = code_size.get("function_points")
        if not function_points:
            return None
        return total_defects / float(function_points) if function_points > 0 else None

    async def _get_latest_test_coverage(self, project_id: str) -> float:
        """Get latest test coverage for project."""
        executions = []
        for execution in self.test_executions.values():
            if execution.get("project_id") != project_id:
                continue
            if not execution.get("executed_at"):
                continue
            executions.append(execution)
        if not executions:
            return 0.0
        latest = max(
            executions,
            key=lambda item: datetime.fromisoformat(item.get("executed_at")),
        )
        return float(latest.get("code_coverage", 0.0))

    async def _calculate_mttr(self, defects: list[dict[str, Any]]) -> float:
        """Calculate mean time to resolution."""
        resolved_defects = [
            d for d in defects if d.get("status") in ["Resolved", "Closed", "Verified"]
        ]

        if not resolved_defects:
            return 0.0

        total_time = 0.0
        for defect in resolved_defects:
            resolution_time = await self._calculate_resolution_time(defect)
            total_time += resolution_time

        return total_time / len(resolved_defects)

    async def _calculate_pass_rate(self, project_id: str) -> float:
        """Calculate test pass rate."""
        executions = [
            execution
            for execution in self.test_executions.values()
            if execution.get("project_id") == project_id
        ]
        if not executions:
            return 0.0
        total_tests = sum(execution.get("total_tests", 0) for execution in executions)
        passed_tests = sum(execution.get("passed", 0) for execution in executions)
        return (passed_tests / total_tests) * 100 if total_tests > 0 else 0.0

    async def _calculate_quality_score(
        self, defect_density: float, test_coverage: float, pass_rate: float
    ) -> float:
        """Calculate overall quality score."""
        # Weighted score
        score = (
            (1 - min(defect_density / self.defect_density_threshold, 1.0)) * 30
            + (test_coverage / 100) * 40
            + (pass_rate / 100) * 30
        )
        return min(100, max(0, score))

    async def _calculate_defect_trends_over_time(
        self, defects: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate defect trends over time."""
        if not defects:
            return {"trend": "stable", "weekly_average": 0, "peak_week": None}
        weekly_counts: dict[int, int] = {}
        for defect in defects:
            logged_at = defect.get("logged_at")
            if not logged_at:
                continue
            week_num = datetime.fromisoformat(logged_at).isocalendar()[1]
            weekly_counts[week_num] = weekly_counts.get(week_num, 0) + 1
        if not weekly_counts:
            return {"trend": "stable", "weekly_average": 0, "peak_week": None}
        sorted_weeks = sorted(weekly_counts)
        counts = [weekly_counts[week] for week in sorted_weeks]
        trend = (
            "increasing"
            if counts[-1] > counts[0]
            else "decreasing" if counts[-1] < counts[0] else "stable"
        )
        return {
            "trend": trend,
            "weekly_average": sum(counts) / len(counts),
            "peak_week": max(weekly_counts, key=weekly_counts.get),
        }

    async def _identify_defect_patterns(
        self, defects: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Identify patterns in defects."""
        if not defects:
            return []
        component_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        for defect in defects:
            component = defect.get("component", "unknown")
            category = defect.get("root_cause", "unknown")
            component_counts[component] = component_counts.get(component, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
        patterns = [
            {"pattern": f"Defects clustered in component '{component}'", "count": count}
            for component, count in sorted(
                component_counts.items(), key=lambda item: item[1], reverse=True
            )
        ]
        patterns.extend(
            {
                "pattern": f"Root cause '{category}' appears frequently",
                "count": count,
            }
            for category, count in sorted(
                category_counts.items(), key=lambda item: item[1], reverse=True
            )
        )
        cluster_patterns = await self._summarize_defect_clusters(defects)
        patterns.extend(cluster_patterns)
        return patterns[:5]

    async def _detect_defect_anomalies(self, defects: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect anomalies in defect data."""
        if not defects:
            return []
        weekly_counts: dict[int, int] = {}
        for defect in defects:
            logged_at = defect.get("logged_at")
            if not logged_at:
                continue
            week_num = datetime.fromisoformat(logged_at).isocalendar()[1]
            weekly_counts[week_num] = weekly_counts.get(week_num, 0) + 1
        if len(weekly_counts) < 2:
            return []
        counts = list(weekly_counts.values())
        mean = sum(counts) / len(counts)
        variance = sum((count - mean) ** 2 for count in counts) / len(counts)
        std_dev = math.sqrt(variance)
        threshold = mean + 2 * std_dev
        anomalies = [
            {
                "week": week,
                "count": count,
                "reason": "defect_spike",
            }
            for week, count in weekly_counts.items()
            if count > threshold
        ]
        return anomalies

    async def _train_defect_subsystem_model(
        self, project_id: str, defects: list[dict[str, Any]]
    ) -> dict[str, Any]:
        subsystem_map: dict[str, int] = {}
        for defect in defects:
            component = defect.get("component", "unknown")
            subsystem_map[component] = subsystem_map.get(component, 0) + 1
        model_version = datetime.now(timezone.utc).strftime("subsystem-%Y%m%d%H%M%S")
        model_info = {
            "project_id": project_id,
            "model_version": model_version,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "subsystem_distribution": subsystem_map,
        }
        self.defect_subsystem_models[project_id] = model_info
        await self._store_record(
            "quality_defect_subsystem_models", f"{project_id}-{model_version}", model_info
        )
        return model_info

    async def _recommend_refactoring_targets(self, defects: list[dict[str, Any]]) -> list[str]:
        if not defects:
            return []
        component_counts: dict[str, int] = {}
        for defect in defects:
            component = defect.get("component", "unknown")
            component_counts[component] = component_counts.get(component, 0) + 1
        sorted_components = sorted(component_counts.items(), key=lambda item: item[1], reverse=True)
        return [
            f"Prioritize refactoring in {component} (defects: {count})"
            for component, count in sorted_components[:3]
        ]

    async def _generate_quality_improvement_recommendations(
        self,
        project_id: str,
        defects: list[dict[str, Any]],
        coverage_pct: float,
        pass_rate: float,
        coverage_snapshot: dict[str, Any] | None,
    ) -> list[str]:
        recommendations = []
        if coverage_pct < self.min_test_coverage:
            recommendations.append(
                f"Increase automated test coverage to at least {self.min_test_coverage:.0%}."
            )
        if pass_rate < 90:
            recommendations.append("Stabilize flaky tests and improve pass rate above 90%.")
        if defects:
            top_components = await self._recommend_refactoring_targets(defects)
            recommendations.extend(top_components)
        cluster_insights = await self._summarize_defect_clusters(defects)
        if cluster_insights:
            recommendations.extend(
                [insight.get("pattern") for insight in cluster_insights if insight.get("pattern")]
            )
        if coverage_snapshot and coverage_snapshot.get("source") == "ci":
            recommendations.append("Review CI coverage configuration for gaps.")
        return recommendations

    async def _publish_improvement_recommendations(
        self, project_id: str, recommendations: list[str]
    ) -> None:
        if not recommendations:
            return
        await self._publish_quality_event(
            "quality.improvement.recommendations",
            payload={"project_id": project_id, "recommendations": recommendations},
            tenant_id=project_id,
            correlation_id=str(uuid.uuid4()),
        )
        stakeholder_client = (self.config or {}).get("stakeholder_communications_client")
        if stakeholder_client:
            if hasattr(stakeholder_client, "publish_update"):
                stakeholder_client.publish_update(
                    {
                        "project_id": project_id,
                        "recommendations": recommendations,
                        "type": "quality_improvement",
                    }
                )
            elif hasattr(stakeholder_client, "send_update"):
                stakeholder_client.send_update(project_id, recommendations)

    async def _sync_defect_tickets(
        self, defect_ids: list[str], *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        sync_results = []
        for defect_id in defect_ids:
            defect = self.defects.get(defect_id)
            if not defect:
                continue
            sync_results.append(
                await self._sync_defect_ticket(
                    defect, action="update", tenant_id=tenant_id, correlation_id=correlation_id
                )
            )
        return {"synced": len(sync_results), "results": sync_results}

    async def _sync_defect_ticket(
        self, defect: dict[str, Any], *, action: str, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        jira_enabled = self.integration_config.get("jira", {}).get("enabled", True)
        azure_enabled = self.integration_config.get("azure_devops", {}).get("enabled", True)
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
        await self._publish_quality_event(
            "quality.defect.synced",
            payload=sync_record,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        await self._store_record("quality_defect_sync", defect.get("defect_id", ""), sync_record)
        return sync_record

    async def _apply_external_defect_updates(
        self, defect: dict[str, Any], external_updates: dict[str, Any]
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

    async def _fetch_ci_test_results(self, execution_data: dict[str, Any]) -> list[dict[str, Any]]:
        pipeline_id = execution_data.get("ci_pipeline_id")
        provider = execution_data.get("ci_provider") or execution_data.get("pipeline_provider")
        pipelines_config = self.integration_config.get("ci_pipelines", {})
        if provider:
            provider_config = pipelines_config.get(provider, {})
            pipelines = provider_config.get("pipelines", {})
        else:
            pipelines = pipelines_config.get("pipelines", {})
        pipeline = pipelines.get(pipeline_id, {})
        results = pipeline.get("test_results", []) or pipeline.get("results", [])
        return [
            {
                **result,
                "result": result.get("result", "pass"),
                "project_id": execution_data.get("project_id"),
            }
            for result in results
        ]

    async def _fetch_ci_coverage_report(self, project_id: str) -> dict[str, Any] | None:
        pipeline_config = self.integration_config.get("ci_pipelines", {})
        coverage = pipeline_config.get("coverage_by_project", {}).get(project_id)
        if not coverage:
            for provider in ("github_actions", "azure_devops"):
                provider_config = pipeline_config.get(provider, {})
                coverage = provider_config.get("coverage_by_project", {}).get(project_id)
                if coverage:
                    coverage = {**coverage, "provider": provider}
                    break
        if coverage:
            return {
                "coverage_pct": coverage.get("coverage_pct", 0.0),
                "source": "ci",
                "provider": coverage.get("provider"),
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }
        return None

    async def _identify_root_causes(self, defects: list[dict[str, Any]]) -> dict[str, int]:
        """Identify root causes from defects."""
        root_causes = {}  # type: ignore
        for defect in defects:
            cause = defect.get("root_cause", "unknown")
            root_causes[cause] = root_causes.get(cause, 0) + 1
        return root_causes

    async def _perform_pareto_analysis(self, root_causes: dict[str, int]) -> dict[str, Any]:
        """Perform Pareto analysis on root causes."""
        total = sum(root_causes.values())
        sorted_causes = sorted(root_causes.items(), key=lambda x: x[1], reverse=True)

        pareto = []
        cumulative_pct = 0.0

        for cause, count in sorted_causes:
            pct = (count / total) * 100 if total > 0 else 0
            cumulative_pct += pct
            pareto.append(
                {
                    "root_cause": cause,
                    "count": count,
                    "percentage": pct,
                    "cumulative_percentage": cumulative_pct,
                }
            )

        return {
            "pareto_chart": pareto,
            "vital_few": [p for p in pareto if p["cumulative_percentage"] <= 80],  # type: ignore
        }

    async def _generate_improvement_recommendations(
        self, root_causes: dict[str, int], pareto_analysis: dict[str, Any]
    ) -> list[str]:
        """Generate improvement recommendations."""
        recommendations = []
        vital_few = pareto_analysis.get("vital_few", [])

        for item in vital_few:
            recommendations.append(
                f"Focus on addressing {item['root_cause']} (accounts for {item['percentage']:.1f}% of defects)"
            )

        return recommendations

    async def _get_defect_statistics(
        self, project_id: str | None, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Get defect statistics."""
        defects = [
            defect
            for defect in self.defects.values()
            if not project_id or defect.get("project_id") == project_id
        ]
        severity_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        for defect in defects:
            severity = defect.get("severity", "unknown")
            status = defect.get("status", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1
        return {"total": len(defects), "by_severity": severity_counts, "by_status": status_counts}

    async def _get_test_execution_summary(
        self, project_id: str | None, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Get test execution summary."""
        executions = [
            execution
            for execution in self.test_executions.values()
            if not project_id or execution.get("project_id") == project_id
        ]
        if not executions:
            return {"total_executions": 0, "pass_rate": 0, "coverage": 0}
        total_tests = sum(execution.get("total_tests", 0) for execution in executions)
        passed_tests = sum(execution.get("passed", 0) for execution in executions)
        avg_pass_rate = (passed_tests / total_tests) * 100 if total_tests else 0.0
        latest_execution = max(
            executions,
            key=lambda item: datetime.fromisoformat(item.get("executed_at"))
            if item.get("executed_at")
            else datetime.min,
        )
        return {
            "total_executions": len(executions),
            "pass_rate": avg_pass_rate,
            "coverage": latest_execution.get("code_coverage", 0),
        }

    async def _get_recent_audits(
        self, project_id: str | None, filters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get recent audits."""
        audits = [
            audit
            for audit in self.audits.values()
            if not project_id or audit.get("project_id") == project_id
        ]
        audits.sort(
            key=lambda item: datetime.fromisoformat(item.get("audit_date"))
            if item.get("audit_date")
            else datetime.min,
            reverse=True,
        )
        return audits[:5]

    async def _generate_summary_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate summary quality report."""
        narrative = await self._generate_openai_narrative(
            "summary", filters, default_prompt="Summarize overall quality health."
        )
        report = {
            "report_type": "summary",
            "data": {"narrative": narrative},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.quality_reports[str(uuid.uuid4())] = report
        return report

    async def _generate_defect_analysis_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate defect analysis report."""
        narrative = await self._generate_openai_narrative(
            "defect_analysis", filters, default_prompt="Analyze defect trends and root causes."
        )
        report = {
            "report_type": "defect_analysis",
            "data": {"narrative": narrative},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.quality_reports[str(uuid.uuid4())] = report
        return report

    async def _generate_test_coverage_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate test coverage report."""
        narrative = await self._generate_openai_narrative(
            "test_coverage", filters, default_prompt="Summarize coverage and automation gaps."
        )
        report = {
            "report_type": "test_coverage",
            "data": {"narrative": narrative},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.quality_reports[str(uuid.uuid4())] = report
        return report

    async def _generate_audit_summary_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate audit summary report."""
        narrative = await self._generate_openai_narrative(
            "audit_summary", filters, default_prompt="Summarize recent audit outcomes."
        )
        report = {
            "report_type": "audit_summary",
            "data": {"narrative": narrative},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.quality_reports[str(uuid.uuid4())] = report
        return report

    async def _generate_release_notes_report(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Generate release notes using Azure OpenAI prompt templates."""
        narrative = await self._generate_openai_narrative(
            "release_notes",
            filters,
            default_prompt="Draft release notes from test executions, defects, and audits.",
        )
        report = {
            "report_type": "release_notes",
            "data": {"narrative": narrative},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.quality_reports[str(uuid.uuid4())] = report
        return report

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

    def _build_defect_classifier(self) -> NaiveBayesTextClassifier:
        classifier = NaiveBayesTextClassifier(
            labels=[
                "ui_defect",
                "performance_issue",
                "security_gap",
                "integration_failure",
                "configuration_error",
                "data_issue",
                "requirements_gap",
                "code_defect",
            ]
        )
        classifier.fit(
            [
                ("button alignment layout css styling", "ui_defect"),
                ("page rendering broken ui glitch", "ui_defect"),
                ("slow response timeout latency", "performance_issue"),
                ("memory spike cpu overload", "performance_issue"),
                ("authentication bypass vulnerability", "security_gap"),
                ("permission escalation access control", "security_gap"),
                ("api integration failed endpoint", "integration_failure"),
                ("third party service error response", "integration_failure"),
                ("misconfigured feature flag config", "configuration_error"),
                ("environment variable missing configuration", "configuration_error"),
                ("data corruption incorrect dataset", "data_issue"),
                ("migration lost records data sync", "data_issue"),
                ("missing requirement incorrect expectation", "requirements_gap"),
                ("user story misunderstood acceptance criteria", "requirements_gap"),
                ("null pointer exception crash", "code_defect"),
                ("logic bug incorrect calculation", "code_defect"),
            ]
        )
        return classifier

    def _get_defect_classifier(self) -> NaiveBayesTextClassifier:
        if self.defect_classifier is None:
            self.defect_classifier = self._build_defect_classifier()
        return self.defect_classifier

    def _severity_from_category(self, category: str) -> str:
        if category in {"security_gap", "data_issue"}:
            return "critical"
        if category in {"performance_issue", "integration_failure"}:
            return "high"
        return "medium"

    def _root_cause_from_category(self, category: str) -> str:
        root_cause_map = {
            "ui_defect": "ux_issue",
            "performance_issue": "performance_regression",
            "security_gap": "security_gap",
            "integration_failure": "integration_issue",
            "configuration_error": "configuration_issue",
            "data_issue": "data_quality",
            "requirements_gap": "requirements_gap",
            "code_defect": "code_defect",
        }
        return root_cause_map.get(category, "code_defect")

    async def _store_record(
        self, collection: str, record_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        if self.db_service is None:
            self.db_service = DatabaseStorageService(self.config.get("database"))
        return await self.db_service.store(collection, record_id, data)

    async def _import_test_results(
        self, execution_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        raw_results = execution_data.get("test_results")
        if isinstance(raw_results, list):
            results = raw_results
        else:
            raw_json = execution_data.get("test_results_json")
            results = []
            if raw_json:
                data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
                results = data.get("results", data) if isinstance(data, dict) else data
            else:
                results_path = execution_data.get("test_results_path")
                if results_path:
                    content = Path(results_path).read_text()
                    data = json.loads(content)
                    results = data.get("results", data) if isinstance(data, dict) else data
        if not results or not isinstance(results, list):
            return []
        normalized: list[dict[str, Any]] = []
        project_id = execution_data.get("project_id")
        for result in results:
            status = result.get("result") or result.get("status") or result.get("outcome")
            normalized_status = str(status or "pass").lower()
            if normalized_status in {"passed", "success"}:
                normalized_status = "pass"
            elif normalized_status in {"failed", "error"}:
                normalized_status = "fail"
            normalized.append(
                {
                    **result,
                    "project_id": result.get("project_id", project_id),
                    "result": normalized_status,
                }
            )
        return normalized

    async def _publish_audit_document(
        self, audit: dict[str, Any], audit_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        report_content = audit_data.get("report")
        if not report_content:
            return None
        if self.document_service is None:
            self.document_service = DocumentManagementService(self.config.get("document_service"))
        metadata = DocumentMetadata(
            title=audit.get("title") or f"Quality Audit {audit.get('audit_id')}",
            description=f"Quality audit report for project {audit.get('project_id')}",
            classification=audit_data.get("classification", "internal"),
            tags=["quality", "audit", audit.get("type", "process_audit")],
            owner=audit_data.get("auditor", ""),
        )
        return await self.document_service.publish_document(
            document_content=report_content,
            metadata=metadata,
            folder_path="Quality/Audits",
        )

    async def _sync_test_management_assets(
        self, asset_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Sync test assets with Azure DevOps Test Plans, Jira Xray, and TestRail."""
        sync_targets = {
            "azure_devops": self.integration_config.get("azure_devops", {}).get("enabled", True),
            "jira_xray": self.integration_config.get("jira_xray", {}).get("enabled", True),
            "testrail": self.integration_config.get("testrail", {}).get("enabled", True),
        }
        synced = {name: "queued" if enabled else "disabled" for name, enabled in sync_targets.items()}
        external_refs: dict[str, Any] = {}
        if sync_targets.get("azure_devops"):
            external_refs["azure_devops"] = await self._create_azure_devops_test_asset(
                asset_type, payload
            )
        return {
            "asset_type": asset_type,
            "asset_id": payload.get("test_case_id") or payload.get("suite_id"),
            "sync_targets": synced,
            "external_refs": external_refs,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _sync_test_execution_results(
        self, execution_id: str, test_results: list[dict[str, Any]], execution_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Sync test execution results to external test management systems."""
        summary = {
            "execution_id": execution_id,
            "results": len(test_results),
            "project_id": execution_data.get("project_id"),
        }
        targets = {
            "azure_devops": self.integration_config.get("azure_devops", {}).get("enabled", True),
            "jira_xray": self.integration_config.get("jira_xray", {}).get("enabled", True),
            "testrail": self.integration_config.get("testrail", {}).get("enabled", True),
        }
        azure_run = None
        if targets.get("azure_devops"):
            azure_run = await self._create_azure_devops_test_run(execution_id, test_results)
        return {
            "summary": summary,
            "targets": {
                name: "submitted" if enabled else "disabled" for name, enabled in targets.items()
            },
            "external_refs": {"azure_devops": azure_run} if azure_run else {},
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _run_playwright_tests(
        self, test_suite: dict[str, Any], config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Simulate Playwright test execution."""
        results = []
        for idx, test_case_id in enumerate(test_suite.get("test_case_ids", [])):
            test_case = self.test_cases.get(test_case_id)
            if not test_case:
                continue
            status = "pass" if idx % 5 != 0 else "fail"
            results.append(
                {
                    "test_case_id": test_case_id,
                    "name": test_case.get("name"),
                    "result": status,
                    "runner": "playwright",
                    "browser": config.get("browser", "chromium"),
                    "duration_ms": 1200,
                    "artifact": f"{test_case_id}.zip",
                }
            )
        return results

    async def _create_azure_devops_test_asset(
        self, asset_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        config = self.integration_config.get("azure_devops", {})
        plan_id = config.get("plan_id", "plan-1")
        project = config.get("project", payload.get("project_id", "project"))
        asset_id = payload.get("test_case_id") or payload.get("suite_id") or "asset"
        external_id = f"ado-{asset_type}-{asset_id}"
        record = {
            "project": project,
            "plan_id": plan_id,
            "external_id": external_id,
            "asset_type": asset_type,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._store_record("quality_devops_assets", external_id, record)
        return record

    async def _create_azure_devops_test_run(
        self, execution_id: str, test_results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        config = self.integration_config.get("azure_devops", {})
        run_id = f"ado-run-{execution_id}"
        passed = sum(1 for result in test_results if result.get("result") == "pass")
        failed = sum(1 for result in test_results if result.get("result") == "fail")
        record = {
            "run_id": run_id,
            "plan_id": config.get("plan_id", "plan-1"),
            "suite_id": config.get("suite_id", "suite-1"),
            "passed": passed,
            "failed": failed,
            "total": len(test_results),
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._store_record("quality_devops_test_runs", run_id, record)
        return record

    async def _store_test_results_in_blob(
        self,
        suite_id: str,
        execution_id: str,
        test_results: list[dict[str, Any]],
        execution_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Store test results in blob storage (simulated)."""
        container = self.integration_config.get("blob_storage", {}).get("container", "quality-tests")
        blob_name = f"{suite_id}/{execution_id}/results.json"
        payload = {
            "execution_id": execution_id,
            "suite_id": suite_id,
            "project_id": execution_data.get("project_id"),
            "results": test_results,
        }
        if self.db_service is None:
            self.db_service = DatabaseStorageService(self.config.get("database"))
        await self.db_service.store("quality_test_artifacts", execution_id, payload)
        return {
            "container": container,
            "blob_name": blob_name,
            "uri": f"https://blob.local/{container}/{blob_name}",
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _train_defect_prediction_model(self, project_id: str) -> dict[str, Any]:
        """Train or refresh a defect prediction model using Azure ML (simulated)."""
        model_version = datetime.now(timezone.utc).strftime("v%Y%m%d%H%M%S")
        model_info = {
            "project_id": project_id,
            "model_version": model_version,
            "training_status": "completed",
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "features": ["defect_density", "coverage_pct", "pass_rate"],
        }
        self.defect_prediction_models[project_id] = model_info
        await self._store_record("quality_defect_models", f"{project_id}-{model_version}", model_info)
        return model_info

    async def _fetch_coverage_metrics(self, project_id: str) -> dict[str, Any]:
        """Pull coverage metrics from code repositories (simulated)."""
        repo_config = self.integration_config.get("code_repos", {})
        coverage_data = repo_config.get("coverage_by_project", {}).get(project_id)
        if coverage_data:
            return coverage_data
        return {"coverage_pct": 85.0, "source": "mock", "captured_at": datetime.now(timezone.utc).isoformat()}

    async def _get_code_size_metrics(self, project_id: str) -> dict[str, Any]:
        repo_config = self.integration_config.get("code_repos", {})
        size_data = repo_config.get("size_by_project", {}).get(project_id)
        if size_data:
            return size_data
        return {"kloc": 10.0, "source": "mock"}

    async def _generate_openai_narrative(
        self, report_type: str, filters: dict[str, Any], default_prompt: str
    ) -> str:
        """Generate narrative text using Azure OpenAI (simulated)."""
        prompt_prefix = self.integration_config.get("azure_openai", {}).get("prompt_prefix", "")
        context = {
            "filters": filters,
            "report_type": report_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        summary = f"{default_prompt} Context: {json.dumps(context)}"
        if prompt_prefix:
            summary = f"{prompt_prefix}\n{summary}"
        return summary

    async def _predict_defect_density(self, project_id: str) -> dict[str, Any]:
        history = self.defect_density_history.get(project_id, [])
        if not history:
            return {"predicted_defect_density": 0.0, "trend": "unknown", "data_points": 0}
        densities = [entry["defect_density"] for entry in history]
        if len(densities) == 1:
            return {
                "predicted_defect_density": densities[0],
                "trend": "stable",
                "data_points": 1,
            }
        slope = (densities[-1] - densities[0]) / max(len(densities) - 1, 1)
        prediction = max(densities[-1] + slope, 0.0)
        trend = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
        return {
            "predicted_defect_density": prediction,
            "trend": trend,
            "data_points": len(densities),
        }

    async def _request_quality_plan_approval(
        self,
        plan_id: str,
        quality_plan: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any] | None:
        if not self.approval_agent_enabled:
            return None
        if not self.approval_agent:
            try:
                from approval_workflow_agent import ApprovalWorkflowAgent
            except ImportError:
                return None
            self.approval_agent = ApprovalWorkflowAgent(config=self.approval_agent_config)
        response = await self.approval_agent.process(
            {
                "request_type": "quality_plan_approval",
                "request_id": plan_id,
                "requester": quality_plan.get("created_by", "unknown"),
                "details": {
                    "project_id": quality_plan.get("project_id"),
                    "objectives": quality_plan.get("objectives"),
                    "metrics": quality_plan.get("metrics"),
                },
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
            }
        )
        await self._publish_quality_event(
            "quality.plan.approval.requested",
            payload={"plan_id": plan_id, "approval": response},
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        return response

    async def _apply_quality_plan_approval(
        self,
        quality_plan: dict[str, Any],
        approval_response: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        status = approval_response.get("status", "pending")
        normalized = status.lower()
        if normalized in {"approved", "approve"}:
            quality_plan["status"] = "Approved"
        elif normalized in {"rejected", "denied"}:
            quality_plan["status"] = "Rejected"
        else:
            quality_plan["status"] = "Pending Approval"
        quality_plan["approval"] = approval_response
        self.quality_plan_store.upsert(tenant_id, quality_plan["plan_id"], quality_plan)
        await self._store_record("quality_plan_approvals", quality_plan["plan_id"], approval_response)
        if quality_plan["status"] == "Approved":
            await self._publish_quality_event(
                "quality.plan.approved",
                payload={
                    "plan_id": quality_plan.get("plan_id"),
                    "project_id": quality_plan.get("project_id"),
                    "approved_by": approval_response.get("approver", "workflow"),
                    "approved_at": datetime.now(timezone.utc).isoformat(),
                },
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
        return quality_plan

    async def _schedule_calendar_event(self, review: dict[str, Any]) -> dict[str, Any] | None:
        if self.calendar_client and hasattr(self.calendar_client, "create_event"):
            response = self.calendar_client.create_event(review)
            if hasattr(response, "__await__"):
                return await response
            return response
        if self.calendar_service:
            response = self.calendar_service.create_event(
                {
                    "title": review.get("title") or review.get("review_id"),
                    "summary": review.get("title") or review.get("review_id"),
                    "scheduled_time": review.get("scheduled_date"),
                    "description": review.get("description"),
                }
            )
            return response
        comms_client = (self.config or {}).get("stakeholder_communications_client")
        if comms_client and hasattr(comms_client, "create_calendar_event"):
            response = comms_client.create_calendar_event(review)
            if hasattr(response, "__await__"):
                return await response
            return response
        calendar_config = self.integration_config.get("calendar", {})
        provider = calendar_config.get("provider")
        if provider in {"outlook", "google"}:
            return {
                "provider": provider,
                "event_id": f"cal-{review['review_id']}",
                "status": "scheduled",
            }
        return None

    async def _query_quality_artifacts(
        self, filters: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        artifact_type = filters.get("type")
        records: list[dict[str, Any]] = []
        store_map = {
            "plans": self.quality_plan_store,
            "test_cases": self.test_case_store,
            "defects": self.defect_store,
            "audits": self.audit_store,
            "requirement_links": self.requirement_link_store,
            "coverage_trends": self.coverage_trend_store,
        }
        if artifact_type in store_map:
            records = store_map[artifact_type].list(tenant_id)
        else:
            records = (
                self.quality_plan_store.list(tenant_id)
                + self.test_case_store.list(tenant_id)
                + self.defect_store.list(tenant_id)
                + self.audit_store.list(tenant_id)
            )
        return {"count": len(records), "artifacts": records}

    async def _update_quality_kpis_from_execution(
        self,
        project_id: str | None,
        test_results: list[dict[str, Any]],
        coverage_pct: float,
        sync_status: dict[str, Any],
    ) -> None:
        if not project_id:
            return
        pass_rate = (
            sum(1 for result in test_results if result.get("result") == "pass")
            / max(len(test_results), 1)
        ) * 100
        await self._store_record(
            "quality_execution_kpis",
            f"{project_id}-{datetime.now(timezone.utc).isoformat()}",
            {
                "project_id": project_id,
                "pass_rate_pct": pass_rate,
                "coverage_pct": coverage_pct,
                "synced_at": sync_status.get("synced_at"),
            },
        )

    def _tokenize_text(self, text: str) -> list[str]:
        tokens = [
            "".join(ch for ch in token.lower() if ch.isalnum())
            for token in text.split()
        ]
        return [token for token in tokens if token]

    def _score_labels(self, content: str, label_tokens: dict[str, list[str]]) -> dict[str, float]:
        if not label_tokens:
            return {}
        tokens = self._tokenize_text(content)
        scores: dict[str, float] = {}
        for label, vocab in label_tokens.items():
            if not vocab:
                continue
            vocab_set = set(vocab)
            overlap = sum(1 for token in tokens if token in vocab_set)
            scores[label] = overlap / len(vocab_set)
        return scores

    def _normalize_scores(self, scores: dict[str, float]) -> dict[str, float]:
        total = sum(scores.values())
        if total <= 0:
            return {label: 0.0 for label in scores}
        return {label: value / total for label, value in scores.items()}

    async def _train_defect_classification_model(self) -> dict[str, Any]:
        if not self.defects:
            return {"label_tokens": {}, "severity_tokens": {}, "trained_at": None}
        label_tokens: dict[str, list[str]] = {}
        severity_tokens: dict[str, list[str]] = {}
        for defect in self.defects.values():
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
            tokens = self._tokenize_text(content)
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
        await self._store_record(
            "quality_defect_models", f"classifier-{uuid.uuid4().hex[:6]}", model
        )
        return model

    async def _train_defect_cluster_model(self) -> dict[str, Any]:
        defects = list(self.defects.values())
        if len(defects) < 2:
            return {"clusters": [], "trained_at": None}
        vectors, vocab = self._vectorize_defects(defects)
        k = min(3, len(vectors))
        clusters = self._kmeans(vectors, k)
        model = {
            "clusters": clusters,
            "vocab": vocab,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._store_record(
            "quality_defect_cluster_models", f"cluster-{uuid.uuid4().hex[:6]}", model
        )
        return model

    def _vectorize_defects(self, defects: list[dict[str, Any]]) -> tuple[list[list[float]], list[str]]:
        texts = []
        for defect in defects:
            text = " ".join(
                value
                for value in [
                    defect.get("summary"),
                    defect.get("description"),
                    defect.get("component"),
                    defect.get("root_cause"),
                ]
                if value
            )
            texts.append(text)
        vocab = sorted({token for text in texts for token in self._tokenize_text(text)})
        vectors = []
        for text in texts:
            tokens = self._tokenize_text(text)
            vector = [tokens.count(term) for term in vocab]
            vectors.append(vector)
        return vectors, vocab

    def _kmeans(self, vectors: list[list[float]], k: int) -> list[dict[str, Any]]:
        if not vectors:
            return []
        centroids = random.sample(vectors, k=k)
        assignments = [0 for _ in vectors]
        for _ in range(5):
            for idx, vector in enumerate(vectors):
                distances = [self._euclidean_distance(vector, centroid) for centroid in centroids]
                assignments[idx] = distances.index(min(distances))
            new_centroids = [[0.0 for _ in vectors[0]] for _ in range(k)]
            counts = [0 for _ in range(k)]
            for vector, cluster_id in zip(vectors, assignments):
                counts[cluster_id] += 1
                for i, value in enumerate(vector):
                    new_centroids[cluster_id][i] += value
            for cluster_id in range(k):
                if counts[cluster_id] == 0:
                    continue
                new_centroids[cluster_id] = [
                    value / counts[cluster_id] for value in new_centroids[cluster_id]
                ]
            centroids = new_centroids
        clusters = []
        for cluster_id in range(k):
            clusters.append(
                {
                    "cluster_id": cluster_id,
                    "count": assignments.count(cluster_id),
                }
            )
        return clusters

    def _euclidean_distance(self, vector: list[float], centroid: list[float]) -> float:
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(vector, centroid)))

    async def _summarize_defect_clusters(
        self, defects: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not defects:
            return []
        if not self.defect_cluster_model or not self.defect_cluster_model.get("clusters"):
            self.defect_cluster_model = await self._train_defect_cluster_model()
        clusters = (self.defect_cluster_model or {}).get("clusters", [])
        insights = []
        for cluster in clusters:
            if cluster.get("count", 0) < 2:
                continue
            insights.append(
                {
                    "pattern": f"Cluster {cluster['cluster_id']} contains {cluster['count']} recurring defects",
                    "count": cluster.get("count", 0),
                }
            )
        return insights

    async def _calculate_coverage_trend(self, project_id: str) -> dict[str, Any]:
        history = self.coverage_trends.get(project_id, [])
        if len(history) < 2:
            return {"trend": "stable", "data_points": len(history)}
        points = [entry.get("coverage_pct", 0.0) for entry in history]
        slope = (points[-1] - points[0]) / max(len(points) - 1, 1)
        trend = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
        return {"trend": trend, "data_points": len(points), "latest": points[-1]}
