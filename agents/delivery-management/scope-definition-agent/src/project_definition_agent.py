"""
Project Definition & Scope Agent

Purpose:
Establishes foundational artifacts for a project including project charter, scope statement,
work breakdown structure (WBS) and requirements. Guides teams through initiation and planning.

Specification: agents/delivery-management/scope-definition-agent/README.md
"""

import uuid
from pathlib import Path
from typing import Any

from approval_workflow_agent import ApprovalWorkflowAgent
from definition_actions import (
    handle_analyze_stakeholders,
    handle_create_raci_matrix,
    handle_create_traceability_matrix,
    handle_detect_scope_creep,
    handle_generate_charter,
    handle_generate_scope_research,
    handle_generate_wbs,
    handle_get_charter,
    handle_get_requirements,
    handle_get_wbs,
    handle_manage_requirements,
    handle_manage_scope_baseline,
    handle_update_wbs,
)
from definition_actions.baseline_actions import handle_get_baseline
from definition_models import Requirement, TraceabilityEntry, WBSItem
from definition_utils import extract_wbs_item_ids
from definition_utils import generate_traceability_matrix as _generate_traceability_matrix
from scope_research import generate_scope_from_search  # noqa: F401

from agents.common.connector_integration import (
    DatabaseStorageService,
    DocumentManagementService,
    ProjectManagementService,
)
from agents.common.integration_services import LocalEmbeddingService, VectorSearchIndex
from agents.common.web_search import search_web  # noqa: F401
from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore


class ProjectDefinitionAgent(BaseAgent):
    """
    Project Definition & Scope Agent - Creates charters, WBS, and manages requirements.

    Key Capabilities:
    - Project charter generation
    - Scope management with WBS
    - Requirements management and traceability
    - Scope baseline management
    - Stakeholder analysis & RACI matrices
    - Requirements validation & verification
    """

    def __init__(
        self, agent_id: str = "scope-definition-agent", config: dict[str, Any] | None = None
    ):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.template_library = config.get("template_library", {}) if config else {}
        self.priority_thresholds = (
            config.get(
                "priority_thresholds", {"critical": 0.9, "high": 0.7, "medium": 0.4, "low": 0.0}
            )
            if config
            else {"critical": 0.9, "high": 0.7, "medium": 0.4, "low": 0.0}
        )
        self.traceability_threshold = config.get("traceability_threshold", 0.90) if config else 0.90
        self.scope_change_threshold = config.get("scope_change_threshold", 0.10) if config else 0.10
        self.enable_external_research = (
            config.get("enable_external_research", False) if config else False
        )
        self.search_result_limit = int(config.get("search_result_limit", 5)) if config else 5

        charter_store_path = (
            Path(config.get("charter_store_path", "data/project_charters.json"))
            if config
            else Path("data/project_charters.json")
        )
        wbs_store_path = (
            Path(config.get("wbs_store_path", "data/project_wbs.json"))
            if config
            else Path("data/project_wbs.json")
        )
        self.charter_store = TenantStateStore(charter_store_path)
        self.wbs_store = TenantStateStore(wbs_store_path)

        # Data stores (will be replaced with database connections)
        self.charters = {}  # type: ignore
        self.wbs_structures = {}  # type: ignore
        self.requirements = {}  # type: ignore
        self.traceability_matrices = {}  # type: ignore
        self.stakeholder_registers = {}  # type: ignore
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = get_event_bus()
        self.approval_agent = config.get("approval_agent") if config else None
        if self.approval_agent is None:
            approval_config = config.get("approval_agent_config", {}) if config else {}
            self.approval_agent = ApprovalWorkflowAgent(config=approval_config)
        self.db_service = None
        self.document_service = None
        self.project_service = None
        self.openai_client = config.get("openai_client") if config else None
        self.form_recognizer_client = config.get("form_recognizer_client") if config else None
        self.doors_client = config.get("doors_client") if config else None
        self.jama_client = config.get("jama_client") if config else None
        self.graph_client = config.get("graph_client") if config else None
        self.cognitive_search_client = config.get("cognitive_search_client") if config else None
        self.embedding_service = LocalEmbeddingService(
            dimensions=config.get("embedding_dimensions", 128) if config else 128
        )
        self.search_index = VectorSearchIndex(self.embedding_service)
        baseline_store_path = (
            Path(config.get("scope_baseline_store_path", "data/scope_baselines.json"))
            if config
            else Path("data/scope_baselines.json")
        )
        self.scope_baseline_store = TenantStateStore(baseline_store_path)
        self.scope_baselines = {}  # type: ignore

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Project Definition & Scope Agent...")

        self.db_service = self.config.get("db_service") or DatabaseStorageService(
            self.config.get("db_service_config", {})
        )
        self.document_service = self.config.get("document_service") or DocumentManagementService(
            self.config.get("document_service_config", {})
        )
        self.project_service = self.config.get("project_service") or ProjectManagementService(
            self.config.get("project_service_config", {})
        )

        self.logger.info("Project Definition & Scope Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "generate_charter",
            "generate_wbs",
            "update_wbs",
            "manage_requirements",
            "create_traceability_matrix",
            "analyze_stakeholders",
            "create_raci_matrix",
            "manage_scope_baseline",
            "detect_scope_creep",
            "get_baseline",
            "get_charter",
            "get_wbs",
            "get_requirements",
            "generate_scope_research",
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "generate_charter":
            charter_data = input_data.get("charter_data", {})
            required_fields = ["title", "description", "project_type", "methodology"]
            for field in required_fields:
                if field not in charter_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False

        elif action == "generate_wbs":
            if "project_id" not in input_data or "scope_statement" not in input_data:
                self.logger.warning("Missing project_id or scope_statement")
                return False
        elif action == "update_wbs":
            if "project_id" not in input_data:
                self.logger.warning("Missing project_id")
                return False
            if not input_data.get("updates") and not input_data.get("wbs"):
                self.logger.warning("Missing updates or wbs payload")
                return False
        elif action == "generate_scope_research":
            if "project_id" not in input_data or "objective" not in input_data:
                self.logger.warning("Missing project_id or objective")
                return False

        return True

    # ------------------------------------------------------------------
    # Process dispatch
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process project definition and scope management requests.

        Args:
            input_data: {
                "action": "generate_charter" | "generate_wbs" | "update_wbs" | "manage_requirements" |
                          "create_traceability_matrix" | "analyze_stakeholders" |
                          "create_raci_matrix" | "manage_scope_baseline" | "detect_scope_creep" |
                          "get_charter" | "get_wbs" | "get_requirements",
                "charter_data": Charter creation data,
                "project_id": ID of existing project,
                "scope_statement": Scope statement for WBS generation,
                "requirements": Requirements data,
                "stakeholders": Stakeholder information,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - generate_charter: Charter ID, document, sections
            - generate_wbs: WBS ID, hierarchical structure
            - update_wbs: Updated WBS metadata
            - manage_requirements: Requirements repository with traceability
            - create_traceability_matrix: Matrix linking requirements to deliverables
            - analyze_stakeholders: Stakeholder register with influence analysis
            - create_raci_matrix: RACI matrix with responsibilities
            - manage_scope_baseline: Baseline ID, locked scope
            - detect_scope_creep: Detected changes, approval needed
            - get_charter: Full charter document
            - get_wbs: Complete WBS structure
            - get_requirements: Requirements repository
        """
        action = input_data.get("action", "generate_charter")
        context = input_data.get("context", {})
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )

        if action == "generate_charter":
            return await handle_generate_charter(
                self,
                input_data.get("charter_data", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "generate_wbs":
            return await handle_generate_wbs(
                self,
                input_data.get("project_id"),
                input_data.get("scope_statement", {}),  # type: ignore
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                requester=input_data.get("requester", "unknown"),
            )
        elif action == "update_wbs":
            return await handle_update_wbs(
                self,
                input_data.get("project_id"),
                input_data.get("updates", {}),
                wbs_payload=input_data.get("wbs"),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                requester=input_data.get("requester", "unknown"),
            )

        elif action == "manage_requirements":
            return await handle_manage_requirements(
                self,
                input_data.get("project_id"),
                input_data.get("requirements", []),  # type: ignore
            )

        elif action == "create_traceability_matrix":
            return await handle_create_traceability_matrix(self, input_data.get("project_id"))  # type: ignore

        elif action == "analyze_stakeholders":
            return await handle_analyze_stakeholders(
                self,
                input_data.get("project_id"),
                input_data.get("stakeholders", []),  # type: ignore
            )

        elif action == "create_raci_matrix":
            return await handle_create_raci_matrix(
                self,
                input_data.get("project_id"),  # type: ignore
                input_data.get("stakeholders", []),
                input_data.get("deliverables", []),
            )

        elif action == "manage_scope_baseline":
            return await handle_manage_scope_baseline(self, input_data.get("project_id"))  # type: ignore

        elif action == "detect_scope_creep":
            return await handle_detect_scope_creep(
                self,
                input_data.get("project_id"),
                input_data.get("current_scope", {}),  # type: ignore
            )

        elif action == "get_baseline":
            return await handle_get_baseline(input_data.get("baseline_id"))  # type: ignore

        elif action == "get_charter":
            return await handle_get_charter(self, input_data.get("project_id"), tenant_id=tenant_id)  # type: ignore

        elif action == "get_wbs":
            return await handle_get_wbs(self, input_data.get("project_id"), tenant_id=tenant_id)  # type: ignore

        elif action == "get_requirements":
            return await handle_get_requirements(self, input_data.get("project_id"))  # type: ignore

        elif action == "generate_scope_research":
            return await handle_generate_scope_research(
                self,
                input_data.get("project_id"),
                input_data.get("objective", ""),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                requester=input_data.get("requester", "unknown"),
                enable_external_research=input_data.get("enable_external_research"),
                search_result_limit=input_data.get("search_result_limit"),
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Traceability (public API kept on class for backward compatibility)
    # ------------------------------------------------------------------

    def generate_traceability_matrix(
        self, requirements: list[Requirement], wbs: list[WBSItem]
    ) -> list[TraceabilityEntry]:
        """Generate requirement-to-WBS traceability entries with coverage status."""
        return _generate_traceability_matrix(requirements, wbs)

    def _extract_wbs_item_ids(self, wbs_items: list[WBSItem]) -> list[str]:
        return extract_wbs_item_ids(wbs_items)

    # ------------------------------------------------------------------
    # Cleanup & capabilities
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Project Definition & Scope Agent...")
        for client in (
            self.openai_client,
            self.form_recognizer_client,
            self.doors_client,
            self.jama_client,
            self.graph_client,
            self.cognitive_search_client,
        ):
            if hasattr(client, "close"):
                await client.close()
            elif hasattr(client, "aclose"):
                await client.aclose()
        if self.event_bus and hasattr(self.event_bus, "flush"):
            await self.event_bus.flush()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "charter_generation",
            "wbs_generation",
            "requirements_management",
            "traceability_management",
            "stakeholder_analysis",
            "raci_matrix_creation",
            "scope_baseline_management",
            "scope_creep_detection",
            "requirements_validation",
            "requirements_extraction",
        ]
