"""
Risk Management Agent

Purpose:
Proactively identifies, assesses and monitors risks across projects, programs and portfolios.
Maintains a central risk register, quantifies probability and impact, recommends mitigation
strategies and continuously tracks risk status.

Specification: agents/delivery-management/risk-management-agent/README.md
"""

import os
import uuid
from typing import Any

from tools.runtime_paths import bootstrap_runtime_paths

bootstrap_runtime_paths()

from agents.common.web_search import search_web, summarize_snippets  # noqa: E402, F401
from analytics_insights_agent import DataLakeManager, SynapseManager  # noqa: E402
from llm.client import LLMGateway  # noqa: E402

# Action handlers ---------------------------------------------------------
from risk_actions import (  # noqa: E402
    assess_risk,
    create_mitigation_plan,
    generate_risk_matrix,
    generate_risk_report,
    get_risk_dashboard,
    get_top_risks,
    identify_risk,
    monitor_triggers,
    perform_sensitivity_analysis,
    prioritize_risks,
    research_risks_action,
    research_risks_public,
    run_monte_carlo,
    update_risk_status,
)

# Re-export models so that existing imports keep working.
from risk_models import (  # noqa: E402, F401
    CognitiveSearchService,
    KnowledgeBaseQueryService,
    RiskNLPExtractor,
)
from risk_utils import (  # noqa: E402
    apply_config,
    calculate_quantitative_impact,
    handle_cost_overrun_event,
    handle_financial_update_event,
    handle_milestone_missed_event,
    handle_quality_event,
    handle_resource_utilization_event,
    handle_schedule_baseline_event,
    handle_schedule_delay_event,
    initialize_project_management_services,
    perform_monte_carlo_simulation,
    prime_risk_extractor,
)

from agents.common.connector_integration import (  # noqa: E402
    DatabaseStorageService,
    DocumentationPublishingService,
    DocumentManagementService,
    GRCIntegrationService,
    MLPredictionService,
)
from agents.runtime import BaseAgent, get_event_bus  # noqa: E402
from agents.runtime.src.audit import build_audit_event, emit_audit_event  # noqa: E402
from agents.runtime.src.policy import evaluate_compliance_controls  # noqa: E402


class RiskManagementAgent(BaseAgent):
    """
    Risk Management Agent - Identifies, assesses and monitors risks.

    Key Capabilities:
    - Risk identification and capture
    - Risk classification and scoring
    - Risk prioritization and ranking
    - Mitigation and response planning
    - Trigger and threshold monitoring
    - Risk reporting and dashboards
    - Integration with other disciplines
    - Monte Carlo simulation
    """

    def __init__(self, agent_id: str = "risk-management-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)
        apply_config(self, config)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize database connections, analytics tools, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Risk Management Agent...")

        self.db_service = DatabaseStorageService(self.config)
        self.grc_service = GRCIntegrationService(self.config)
        self.document_service = DocumentManagementService(self.config)
        self.documentation_service = DocumentationPublishingService(self.config)
        self.ml_service = self.config.get("ml_service") or MLPredictionService(self.config)
        self.cognitive_search_service = self.config.get(
            "cognitive_search_service"
        ) or CognitiveSearchService(
            endpoint=self.config.get("cognitive_search_endpoint")
            or os.getenv("AZURE_COG_SEARCH_ENDPOINT"),
            api_key=self.config.get("cognitive_search_key")
            or os.getenv("AZURE_COG_SEARCH_API_KEY"),
            index_name=self.config.get("cognitive_search_index")
            or os.getenv("AZURE_COG_SEARCH_INDEX"),
        )
        self.knowledge_base_service = self.config.get(
            "knowledge_base_service"
        ) or KnowledgeBaseQueryService(
            self.document_service,
            self.documentation_service,
        )
        self.project_management_services = initialize_project_management_services(self.config)
        self.data_lake_manager = self.config.get("data_lake_manager") or DataLakeManager(
            file_system_name=self.config.get("data_lake_file_system")
            or os.getenv("AZURE_DATA_LAKE_FILE_SYSTEM"),
            service_client=self.config.get("data_lake_client"),
        )
        self.synapse_manager = self.config.get("synapse_manager") or SynapseManager(
            workspace_name=self.config.get("synapse_workspace")
            or os.getenv("AZURE_SYNAPSE_WORKSPACE"),
            sql_pool_name=self.config.get("synapse_sql_pool")
            or os.getenv("AZURE_SYNAPSE_SQL_POOL"),
            spark_pool_name=self.config.get("synapse_spark_pool")
            or os.getenv("AZURE_SYNAPSE_SPARK_POOL"),
            synapse_client=self.config.get("synapse_client"),
        )
        self.event_bus = self.config.get("event_bus")
        if not self.event_bus:
            try:
                self.event_bus = get_event_bus()
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ):
                self.event_bus = None
        if self.event_bus and hasattr(self.event_bus, "subscribe"):
            self.event_bus.subscribe(
                "schedule.baseline.locked", self._handle_schedule_baseline_event
            )
            self.event_bus.subscribe("schedule.delay", self._handle_schedule_delay_event)
            self.event_bus.subscribe(
                "financial.budget.updated", self._handle_financial_update_event
            )
            self.event_bus.subscribe("financial.cost_overrun", self._handle_cost_overrun_event)
            self.event_bus.subscribe(
                "schedule.milestone.missed", self._handle_milestone_missed_event
            )
            self.event_bus.subscribe("quality.defect_rate", self._handle_quality_event)
            self.event_bus.subscribe(
                "resource.utilization", self._handle_resource_utilization_event
            )

        if self.synapse_manager:
            self.synapse_manager.ensure_pools()

        await prime_risk_extractor(self)

        self.logger.info("Risk Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "identify_risk",
            "assess_risk",
            "prioritize_risks",
            "create_mitigation_plan",
            "monitor_triggers",
            "update_risk_status",
            "run_monte_carlo",
            "generate_risk_matrix",
            "get_risk_dashboard",
            "generate_risk_report",
            "perform_sensitivity_analysis",
            "get_top_risks",
            "research_risks",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "identify_risk":
            risk_data = input_data.get("risk", {})
            required_fields = ["title", "description", "category"]
            for field in required_fields:
                if field not in risk_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False
        elif action == "research_risks":
            if not input_data.get("domain"):
                self.logger.warning("Missing required field: domain")
                return False

        return True

    # ------------------------------------------------------------------
    # Compliance gate
    # ------------------------------------------------------------------

    def _check_compliance(
        self,
        input_data: dict[str, Any],
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any] | None:
        """Run compliance controls; return denial payload or ``None`` to proceed."""
        compliance_decision = evaluate_compliance_controls(
            {
                "personal_data": input_data.get("personal_data", {}),
                "consent": input_data.get("consent", {}),
            }
        )
        resource_id = input_data.get("project_id") or "unknown"
        if compliance_decision.decision == "deny":
            emit_audit_event(
                build_audit_event(
                    tenant_id=tenant_id,
                    action="risk.data_processing.denied",
                    outcome="denied",
                    actor_id=self.agent_id,
                    actor_type="service",
                    actor_roles=[],
                    resource_id=resource_id,
                    resource_type="risk_processing",
                    metadata={"reasons": list(compliance_decision.reasons)},
                    legal_basis="consent",
                    retention_period="P1Y",
                    correlation_id=correlation_id,
                )
            )
            return {
                "status": "error",
                "error": "Consent is required before processing personal data.",
                "reasons": list(compliance_decision.reasons),
            }

        input_data["personal_data"] = compliance_decision.sanitized_payload.get(
            "personal_data", {}
        )
        emit_audit_event(
            build_audit_event(
                tenant_id=tenant_id,
                action="risk.data_processing.allowed",
                outcome="success",
                actor_id=self.agent_id,
                actor_type="service",
                actor_roles=[],
                resource_id=resource_id,
                resource_type="risk_processing",
                metadata={
                    "masked_fields": list(compliance_decision.masked_fields),
                    "reasons": list(compliance_decision.reasons),
                },
                legal_basis="consent",
                retention_period="P1Y",
                correlation_id=correlation_id,
            )
        )
        return None

    # ------------------------------------------------------------------
    # Main dispatch
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process risk management requests and dispatch to the appropriate action handler."""
        action = input_data.get("action", "get_risk_dashboard")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        denial = self._check_compliance(input_data, tenant_id, correlation_id)
        if denial is not None:
            return denial

        if action == "identify_risk":
            return await identify_risk(
                self,
                input_data.get("risk", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "assess_risk":
            return await assess_risk(self, input_data.get("risk_id"))  # type: ignore

        elif action == "prioritize_risks":
            return await prioritize_risks(
                self, input_data.get("project_id"), input_data.get("portfolio_id")
            )

        elif action == "create_mitigation_plan":
            return await create_mitigation_plan(
                self, input_data.get("risk_id"), input_data.get("mitigation", {})  # type: ignore
            )

        elif action == "monitor_triggers":
            return await monitor_triggers(self, input_data.get("risk_id"))

        elif action == "update_risk_status":
            return await update_risk_status(
                self,
                input_data.get("risk_id"),  # type: ignore
                input_data.get("updates", {}),
                tenant_id=tenant_id,
            )

        elif action == "run_monte_carlo":
            return await run_monte_carlo(
                self, input_data.get("project_id"), input_data.get("iterations", 10000)  # type: ignore
            )

        elif action == "generate_risk_matrix":
            return await generate_risk_matrix(
                self, input_data.get("project_id"), input_data.get("portfolio_id")
            )

        elif action == "get_risk_dashboard":
            return await get_risk_dashboard(
                self,
                input_data.get("project_id"),
                input_data.get("portfolio_id"),
                tenant_id=tenant_id,
                external_context=input_data.get("external_context"),
            )

        elif action == "generate_risk_report":
            return await generate_risk_report(
                self, input_data.get("report_type", "summary"), input_data.get("filters", {})
            )

        elif action == "perform_sensitivity_analysis":
            return await perform_sensitivity_analysis(self, input_data.get("project_id"))  # type: ignore

        elif action == "get_top_risks":
            return await get_top_risks(  # type: ignore
                self, input_data.get("project_id"), input_data.get("limit", 10)
            )

        elif action == "research_risks":
            return await research_risks_action(
                self,
                project_id=input_data.get("project_id"),
                domain=input_data.get("domain", ""),
                region=input_data.get("region"),
                categories=input_data.get("categories", []),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Public research method (preserves original API)
    # ------------------------------------------------------------------

    async def research_risks(
        self,
        domain: str,
        region: str | None,
        categories: list[str] | None,
        *,
        llm_client: LLMGateway | None = None,
        result_limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Research emerging risks using external sources."""
        return await research_risks_public(
            self,
            domain,
            region,
            categories,
            llm_client=llm_client,
            result_limit=result_limit,
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Risk Management Agent...")
        if self.event_bus and hasattr(self.event_bus, "stop"):
            await self.event_bus.stop()
        if self.data_lake_manager and hasattr(self.data_lake_manager, "service_client"):
            service_client = getattr(self.data_lake_manager, "service_client")
            if service_client and hasattr(service_client, "close"):
                service_client.close()
        if self.synapse_manager and hasattr(self.synapse_manager, "synapse_client"):
            synapse_client = getattr(self.synapse_manager, "synapse_client")
            if synapse_client and hasattr(synapse_client, "close"):
                synapse_client.close()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "risk_identification",
            "risk_extraction_from_documents",
            "risk_classification",
            "risk_scoring",
            "risk_prioritization",
            "predictive_risk_modeling",
            "mitigation_planning",
            "mitigation_strategy_recommendation",
            "trigger_monitoring",
            "monte_carlo_simulation",
            "sensitivity_analysis",
            "correlation_analysis",
            "risk_matrix_generation",
            "risk_dashboards",
            "risk_reporting",
            "quantitative_risk_analysis",
            "external_risk_research",
            "risk_event_publishing",
            "knowledge_base_guidance",
            "pm_connector_risk_signals",
        ]

    # ------------------------------------------------------------------
    # Private-method delegates (preserve API used by existing tests)
    # ------------------------------------------------------------------

    async def _perform_monte_carlo_simulation(
        self,
        project_id: str,
        risks: list[dict[str, Any]],
        iterations: int,
        schedule_distribution: dict[str, Any] | None = None,
        financial_distribution: dict[str, Any] | None = None,
    ) -> dict[str, list[float]]:
        return await perform_monte_carlo_simulation(
            project_id, risks, iterations,
            schedule_distribution=schedule_distribution,
            financial_distribution=financial_distribution,
        )

    async def _calculate_quantitative_impact(self, risk: dict[str, Any]) -> dict[str, Any]:
        return await calculate_quantitative_impact(self, risk)

    async def _run_monte_carlo(
        self, project_id: str, iterations: int = 10000
    ) -> dict[str, Any]:
        return await run_monte_carlo(self, project_id, iterations)

    async def _create_mitigation_plan(
        self, risk_id: str, mitigation_data: dict[str, Any]
    ) -> dict[str, Any]:
        return await create_mitigation_plan(self, risk_id, mitigation_data)

    async def _identify_risk(
        self,
        risk_data: dict[str, Any],
        *,
        tenant_id: str = "unknown",
        correlation_id: str = "",
    ) -> dict[str, Any]:
        return await identify_risk(
            self, risk_data, tenant_id=tenant_id, correlation_id=correlation_id
        )

    # ------------------------------------------------------------------
    # Event handler delegates (thin wrappers to preserve bound-method API)
    # ------------------------------------------------------------------

    async def _handle_schedule_baseline_event(self, payload: dict[str, Any]) -> None:
        await handle_schedule_baseline_event(self, payload)

    async def _handle_schedule_delay_event(self, payload: dict[str, Any]) -> None:
        await handle_schedule_delay_event(self, payload)

    async def _handle_financial_update_event(self, payload: dict[str, Any]) -> None:
        await handle_financial_update_event(self, payload)

    async def _handle_cost_overrun_event(self, payload: dict[str, Any]) -> None:
        await handle_cost_overrun_event(self, payload)

    async def _handle_milestone_missed_event(self, payload: dict[str, Any]) -> None:
        await handle_milestone_missed_event(self, payload)

    async def _handle_quality_event(self, payload: dict[str, Any]) -> None:
        await handle_quality_event(self, payload)

    async def _handle_resource_utilization_event(self, payload: dict[str, Any]) -> None:
        await handle_resource_utilization_event(self, payload)
