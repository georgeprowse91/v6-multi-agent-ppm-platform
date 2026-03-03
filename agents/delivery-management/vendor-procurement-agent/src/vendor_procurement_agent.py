"""
Vendor & Procurement Management Agent

Purpose:
Streamlines end-to-end procurement lifecycle from vendor onboarding and contract management
to purchase order processing and invoice reconciliation. Ensures external spending aligns
with organizational policies and supports vendor performance monitoring.

Specification: agents/delivery-management/vendor-procurement-agent/README.md
"""

import importlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.runtime_paths import bootstrap_runtime_paths

bootstrap_runtime_paths()

from llm.client import LLMGateway, LLMProviderError  # noqa: E402

from agents.common.connector_integration import (  # noqa: E402
    DatabaseStorageService,
    DocumentManagementService,
)
from agents.common.web_search import (  # noqa: E402
    build_search_query,
    search_web,
    summarize_snippets,
)
from agents.runtime import BaseAgent  # noqa: E402
from agents.runtime.src.state_store import TenantStateStore  # noqa: E402

# Re-export models so existing imports keep working
from vendor_models import (  # noqa: E402
    CommunicationsClient,
    ConnectorStatus,
    EventBusClient,
    FinancialManagementClient,
    FormRecognizerClient,
    LocalApprovalAgent,
    PerformanceAnalyticsClient,
    ProcurementClassifier,
    ProcurementConnectorService,
    ProcurementEventPublisher,
    RiskDatabaseClient,
    TaskManagementClient,
    VendorMLService,
)

# Action handlers
from vendor_actions import (  # noqa: E402
    handle_create_contract,
    handle_create_procurement_request,
    handle_create_purchase_order,
    handle_evaluate_proposals,
    handle_generate_rfp,
    handle_get_procurement_status,
    handle_get_vendor_profile,
    handle_get_vendor_scorecard,
    handle_list_vendor_profiles,
    handle_onboard_vendor,
    handle_reconcile_invoice,
    handle_research_vendor,
    handle_search_vendors,
    handle_select_vendor,
    handle_sign_contract,
    handle_submit_invoice,
    handle_submit_proposal,
    handle_track_vendor_performance,
    handle_update_vendor_profile,
)
from vendor_actions.event_handlers import register_event_handlers  # noqa: E402

# Utilities used directly by the agent class
from vendor_utils import (  # noqa: E402
    extract_sources as _extract_sources,
    extract_vendor_insights as _extract_vendor_insights,
    score_vendor_research as _score_vendor_research,
)

class VendorProcurementAgent(BaseAgent):
    """
    Vendor & Procurement Management Agent - Manages procurement lifecycle and vendor relationships.

    Key Capabilities:
    - Vendor registry and onboarding
    - Procurement request intake and processing
    - RFP/RFQ generation and quote management
    - Vendor selection and scoring
    - Contract and agreement management
    - Purchase order creation and approval
    - Invoice receipt and reconciliation
    - Vendor performance monitoring
    - Compliance and audit support
    """

    DEFAULT_RFP_TEMPLATES = {
        "software": {
            "template_id": "rfp_software_v1",
            "sections": [
                "Executive Summary",
                "Scope of Work",
                "Technical Requirements",
                "Security & Compliance",
                "Pricing",
                "Implementation Timeline",
            ],
        },
        "services": {
            "template_id": "rfp_services_v1",
            "sections": [
                "Background",
                "Service Requirements",
                "Staffing & Credentials",
                "SLA Expectations",
                "Pricing & Payment Terms",
            ],
        },
        "consulting": {
            "template_id": "rfp_consulting_v1",
            "sections": [
                "Problem Statement",
                "Proposed Approach",
                "Team Experience",
                "Deliverables",
                "Commercials",
            ],
        },
        "cloud": {
            "template_id": "rfp_cloud_v1",
            "sections": [
                "Cloud Architecture Needs",
                "Migration Approach",
                "Security & Compliance",
                "Service Levels",
                "Pricing Model",
            ],
        },
    }

    def __init__(self, agent_id: str = "vendor-procurement-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)
        _c = (config or {}).get  # shorthand for safe config access

        # Scalar configuration
        self.default_currency = _c("default_currency", "AUD")
        self.procurement_threshold = _c("procurement_threshold", 10000)
        self.min_vendor_proposals = _c("min_vendor_proposals", 3)
        self.invoice_tolerance_pct = _c("invoice_tolerance_pct", 0.05)
        self.vendor_schema_path = Path(_c("vendor_schema_path", "data/schemas/vendor.schema.json"))
        self.enable_openai_rfp = _c("enable_openai_rfp", False)
        self.enable_ai_scoring = _c("enable_ai_scoring", False)
        self.enable_ai_vendor_ranking = _c("enable_ai_vendor_ranking", False)
        self.enable_ml_recommendations = _c("enable_ml_recommendations", True)
        self.enable_vendor_research = _c("enable_vendor_research", False)
        self.vendor_search_result_limit = int(_c("vendor_search_result_limit", 5))
        self.compliance_policy = _c(
            "compliance_policy",
            {"block_on_fail": True, "flag_on_watchlist": True, "risk_threshold": 75},
        )
        self.vendor_categories = _c(
            "vendor_categories",
            ["software", "hardware", "consulting", "materials", "services", "cloud"],
        )
        self.vendor_search_keywords = _c(
            "vendor_search_keywords",
            ["financial health", "performance issues", "contract dispute",
             "credit rating", "supplier review"],
        )

        # Tenant state stores
        self.vendor_store = TenantStateStore(Path(_c("vendor_store_path", "data/vendors.json")))
        self.contract_store = TenantStateStore(Path(_c("contract_store_path", "data/vendor_contracts.json")))
        self.invoice_store = TenantStateStore(Path(_c("invoice_store_path", "data/vendor_invoices.json")))
        self.vendor_performance_store = TenantStateStore(Path(_c("vendor_performance_store_path", "data/vendor_performance.json")))
        self.event_store = TenantStateStore(Path(_c("event_store_path", "data/vendor_procurement_events.json")))

        # External service clients
        self.db_service: DatabaseStorageService | None = None
        self.document_service: DocumentManagementService | None = None
        self.risk_client = RiskDatabaseClient(_c("risk_config"))
        self.event_bus = EventBusClient(_c("event_bus"))
        self.procurement_connector = ProcurementConnectorService(_c("procurement_connectors"))
        self.erp_ap_connector = ProcurementConnectorService(_c("erp_ap_connectors"))
        self.event_publisher = ProcurementEventPublisher(_c("event_publisher"), event_bus=self.event_bus)
        self.ml_config = _c("ml_config")
        self.ml_service = VendorMLService(self.ml_config)
        self.vendor_scoring_weights = (self.ml_config or {}).get("scoring_weights", {})
        self.form_recognizer = FormRecognizerClient(_c("form_recognizer"))
        self.request_classifier = ProcurementClassifier(_c("classification_config"))
        self.financial_client = FinancialManagementClient(_c("financial_config"))
        self.analytics_client = PerformanceAnalyticsClient(_c("analytics_config"))

        # Task & communications clients (injectable)
        self.task_client = _c("task_client") or TaskManagementClient(_c("task_management"))
        self.communications_client = _c("communications_client") or CommunicationsClient(_c("communications_config"))

        # In-memory data stores
        self.vendors: dict[str, Any] = {}
        self.procurement_requests: dict[str, Any] = {}
        self.rfps: dict[str, Any] = {}
        self.proposals: dict[str, Any] = {}
        self.contracts: dict[str, Any] = {}
        self.purchase_orders: dict[str, Any] = {}
        self.invoices: dict[str, Any] = {}
        self.vendor_performance: dict[str, Any] = {}

        # Approval agent
        self.approval_agent = _c("approval_agent")
        self.use_external_approval_agent = _c("use_external_approval_agent", False)
        if self.approval_agent is None:
            approval_config = _c("approval_agent_config", {})
            if self.use_external_approval_agent:
                self.approval_agent = self._resolve_approval_agent()(config=approval_config)
            else:
                self.approval_agent = LocalApprovalAgent(config=approval_config)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize database connections, ERP integrations, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Vendor & Procurement Management Agent...")

        self.db_service = DatabaseStorageService(self.config.get("database_config"))
        self.document_service = DocumentManagementService(self.config.get("document_config"))

        connector_statuses = self.procurement_connector.initialize()
        erp_statuses = self.erp_ap_connector.initialize()
        if connector_statuses or erp_statuses:
            self.logger.info(
                "Connector status",
                extra={
                    "procurement_connectors": [status.__dict__ for status in connector_statuses],
                    "erp_connectors": [status.__dict__ for status in erp_statuses],
                },
            )

        await self._load_vendor_cache()
        await self.ml_service.train_models(list(self.vendors.values()))
        self._register_event_handlers()

        if self.form_recognizer.is_configured():
            self.logger.info("Form Recognizer configured for contract clause extraction.")
        else:
            self.logger.info("Form Recognizer not configured; falling back to regex extraction.")

        self.logger.info("Vendor & Procurement Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "onboard_vendor",
            "create_procurement_request",
            "generate_rfp",
            "submit_proposal",
            "evaluate_proposals",
            "select_vendor",
            "create_contract",
            "create_purchase_order",
            "submit_invoice",
            "reconcile_invoice",
            "track_vendor_performance",
            "get_vendor_scorecard",
            "search_vendors",
            "get_procurement_status",
            "research_vendor",
            "get_vendor_profile",
            "update_vendor_profile",
            "list_vendor_profiles",
            "sign_contract",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "onboard_vendor":
            vendor_data = input_data.get("vendor", {})
            required_fields = ["legal_name", "contact_email", "category"]
            for field in required_fields:
                if field not in vendor_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False

        elif action == "create_procurement_request":
            request_data = input_data.get("request", {})
            required_fields = ["requester", "description", "estimated_cost"]
            for field in required_fields:
                if field not in request_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False
        elif action == "research_vendor":
            if not input_data.get("vendor_id") and not input_data.get("vendor_name"):
                self.logger.warning("Missing required field: vendor_id or vendor_name")
                return False
        elif action == "update_vendor_profile":
            if not input_data.get("vendor_id"):
                self.logger.warning("Missing required field: vendor_id")
                return False
            if not input_data.get("updates"):
                self.logger.warning("Missing required field: updates")
                return False

        return True

    # ------------------------------------------------------------------
    # Process routing
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Route incoming requests to the appropriate action handler."""
        action = input_data.get("action", "search_vendors")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        actor_id = context.get("user_id") or input_data.get("actor_id") or "system"

        # Shorthand for common keyword args
        ctx = dict(tenant_id=tenant_id, correlation_id=correlation_id, actor_id=actor_id)
        g = input_data.get

        if action == "onboard_vendor":
            return await handle_onboard_vendor(self, g("vendor", {}), **ctx)
        if action == "create_procurement_request":
            return await handle_create_procurement_request(self, g("request", {}), **ctx)
        if action == "generate_rfp":
            return await handle_generate_rfp(self, g("request_id"), g("rfp", {}), **ctx)  # type: ignore
        if action == "submit_proposal":
            return await handle_submit_proposal(self, g("rfp_id"), g("vendor_id"), g("proposal", {}), **ctx)  # type: ignore
        if action == "evaluate_proposals":
            return await handle_evaluate_proposals(self, g("rfp_id"), g("criteria", {}))  # type: ignore
        if action == "select_vendor":
            return await handle_select_vendor(self, g("rfp_id"), g("vendor_id"), **ctx)  # type: ignore
        if action == "create_contract":
            return await handle_create_contract(self, g("contract", {}), **ctx)
        if action == "create_purchase_order":
            return await handle_create_purchase_order(self, g("purchase_order", {}), **ctx)
        if action == "submit_invoice":
            return await handle_submit_invoice(self, g("invoice", {}), **ctx)
        if action == "reconcile_invoice":
            return await handle_reconcile_invoice(self, g("invoice_id"), **ctx)  # type: ignore
        if action == "track_vendor_performance":
            return await handle_track_vendor_performance(self, g("vendor_id"), **ctx)  # type: ignore
        if action == "get_vendor_scorecard":
            return await handle_get_vendor_scorecard(self, g("vendor_id"), **ctx)  # type: ignore
        if action == "research_vendor":
            return await handle_research_vendor(
                self, vendor_id=g("vendor_id"), vendor_name=g("vendor_name"),
                domain=g("domain"), tenant_id=tenant_id, correlation_id=correlation_id,
            )
        if action == "get_vendor_profile":
            return await handle_get_vendor_profile(self, g("vendor_id"), tenant_id=tenant_id, correlation_id=correlation_id)  # type: ignore
        if action == "update_vendor_profile":
            return await handle_update_vendor_profile(self, g("vendor_id"), g("updates", {}), **ctx)  # type: ignore
        if action == "list_vendor_profiles":
            return await handle_list_vendor_profiles(self, g("criteria", {}), tenant_id=tenant_id)
        if action == "sign_contract":
            return await handle_sign_contract(self, g("contract_id"), **ctx)  # type: ignore
        if action == "search_vendors":
            return await handle_search_vendors(self, g("criteria", {}))
        if action == "get_procurement_status":
            return await handle_get_procurement_status(self, g("request_id"))  # type: ignore
        raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Public research method (kept on class for backward compat)
    # ------------------------------------------------------------------

    async def research_vendor(
        self,
        vendor_name: str,
        domain: str,
        *,
        llm_client: LLMGateway | None = None,
        result_limit: int | None = None,
    ) -> dict[str, Any]:
        """Research external signals about a vendor using public sources."""
        if not self.enable_vendor_research:
            return {"summary": "", "insights": [], "sources": [], "used_external_research": False}

        context = f"{vendor_name} {domain}".strip()
        query = build_search_query(
            context,
            "vendor",
            extra_keywords=self.vendor_search_keywords,
        )

        # NOTE: Only high-level vendor context should be sent to the search API.
        snippets = await search_web(
            query, result_limit=result_limit or self.vendor_search_result_limit
        )
        if not snippets:
            return {"summary": "", "insights": [], "sources": [], "used_external_research": False}

        summary = await summarize_snippets(snippets, llm_client=llm_client, purpose="vendor")
        insights = await _extract_vendor_insights(self, summary, snippets, llm_client=llm_client)
        sources = _extract_sources(snippets)
        return {
            "summary": summary,
            "insights": insights,
            "sources": sources,
            "used_external_research": True,
        }

    # ------------------------------------------------------------------
    # Event handler registration (handlers live in actions/event_handlers.py)
    # ------------------------------------------------------------------

    def _register_event_handlers(self) -> None:
        register_event_handlers(self)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_approval_agent(self) -> type:
        module = importlib.import_module("approval_workflow_agent")
        return getattr(module, "ApprovalWorkflowAgent")

    async def _load_vendor_cache(self) -> None:
        for tenant_id in self.vendor_store.tenants():
            for vendor in self.vendor_store.list(tenant_id):
                vendor_id = vendor.get("vendor_id")
                if vendor_id:
                    self.vendors[vendor_id] = vendor

    def _extract_sources(self, snippets: list[str]) -> list[dict[str, str]]:
        return _extract_sources(snippets)

    def _score_vendor_research(self, research: dict[str, Any]) -> dict[str, Any]:
        return _score_vendor_research(research)

    # ------------------------------------------------------------------
    # Cleanup & capabilities
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Vendor & Procurement Management Agent...")

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "vendor_registry",
            "vendor_onboarding",
            "vendor_risk_scoring",
            "procurement_request_intake",
            "rfp_generation",
            "rfp_quote_management",
            "vendor_selection",
            "vendor_scoring",
            "contract_management",
            "purchase_order_creation",
            "purchase_order_approval",
            "invoice_receipt",
            "invoice_reconciliation",
            "three_way_matching",
            "vendor_performance_monitoring",
            "vendor_scorecard_generation",
            "compliance_enforcement",
            "vendor_profile_management",
            "risk_mitigation_workflows",
            "event_bus_integration",
            "audit_trail_management",
            "spend_analysis",
            "external_vendor_research",
        ]
