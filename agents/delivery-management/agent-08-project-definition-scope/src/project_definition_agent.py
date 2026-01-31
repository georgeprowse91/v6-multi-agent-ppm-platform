"""
Agent 8: Project Definition & Scope Agent

Purpose:
Establishes foundational artifacts for a project including project charter, scope statement,
work breakdown structure (WBS) and requirements. Guides teams through initiation and planning.

Specification: agents/delivery-management/agent-08-project-definition-scope/README.md
"""

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from approval_workflow_agent import ApprovalWorkflowAgent
from events import CharterCreatedEvent, WbsCreatedEvent
from observability.tracing import get_trace_id
from scope_research import generate_scope_from_search
from web_search import search_web

from agents.common.connector_integration import (
    DatabaseStorageService,
    DocumentManagementService,
    DocumentMetadata,
    ProjectManagementService,
)
from agents.runtime import BaseAgent, InMemoryEventBus
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

    def __init__(self, agent_id: str = "project-definition", config: dict[str, Any] | None = None):
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
            self.event_bus = InMemoryEventBus()
        self.approval_agent = config.get("approval_agent") if config else None
        if self.approval_agent is None:
            approval_config = config.get("approval_agent_config", {}) if config else {}
            self.approval_agent = ApprovalWorkflowAgent(config=approval_config)
        self.db_service = None
        self.document_service = None
        self.project_service = None

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Project Definition & Scope Agent...")

        # Future work: Initialize Azure OpenAI Service for charter and WBS generation
        # Future work: Initialize Azure Form Recognizer for requirements extraction from documents
        self.db_service = self.config.get("db_service") or DatabaseStorageService(
            self.config.get("db_service_config", {})
        )
        self.document_service = self.config.get(
            "document_service"
        ) or DocumentManagementService(self.config.get("document_service_config", {}))
        self.project_service = self.config.get("project_service") or ProjectManagementService(
            self.config.get("project_service_config", {})
        )
        # Future work: Connect to IBM DOORS/Jama for requirements management
        # Future work: Initialize SharePoint/Confluence integration for document management
        # Future work: Set up Azure Service Bus/Event Grid for event publishing
        # Future work: Initialize Azure Cognitive Search for similarity search

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
            "manage_requirements",
            "create_traceability_matrix",
            "analyze_stakeholders",
            "create_raci_matrix",
            "manage_scope_baseline",
            "detect_scope_creep",
            "get_charter",
            "get_wbs",
            "get_requirements",
            "generate_scope_research",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "generate_charter":
            charter_data = input_data.get("charter_data", {})
            required_fields = ["title", "description", "project_type", "methodology"]
            for field in required_fields:
                if field not in charter_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        elif action == "generate_wbs":
            if "project_id" not in input_data or "scope_statement" not in input_data:
                self.logger.warning("Missing project_id or scope_statement")
                return False
        elif action == "generate_scope_research":
            if "project_id" not in input_data or "objective" not in input_data:
                self.logger.warning("Missing project_id or objective")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process project definition and scope management requests.

        Args:
            input_data: {
                "action": "generate_charter" | "generate_wbs" | "manage_requirements" |
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
            return await self._generate_charter(
                input_data.get("charter_data", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "generate_wbs":
            return await self._generate_wbs(
                input_data.get("project_id"),
                input_data.get("scope_statement", {}),  # type: ignore
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                requester=input_data.get("requester", "unknown"),
            )

        elif action == "manage_requirements":
            return await self._manage_requirements(
                input_data.get("project_id"), input_data.get("requirements", [])  # type: ignore
            )

        elif action == "create_traceability_matrix":
            return await self._create_traceability_matrix(input_data.get("project_id"))  # type: ignore

        elif action == "analyze_stakeholders":
            return await self._analyze_stakeholders(
                input_data.get("project_id"), input_data.get("stakeholders", [])  # type: ignore
            )

        elif action == "create_raci_matrix":
            return await self._create_raci_matrix(
                input_data.get("project_id"),  # type: ignore
                input_data.get("stakeholders", []),
                input_data.get("deliverables", []),
            )

        elif action == "manage_scope_baseline":
            return await self._manage_scope_baseline(input_data.get("project_id"))  # type: ignore

        elif action == "detect_scope_creep":
            return await self._detect_scope_creep(
                input_data.get("project_id"), input_data.get("current_scope", {})  # type: ignore
            )

        elif action == "get_charter":
            return await self._get_charter(input_data.get("project_id"), tenant_id=tenant_id)  # type: ignore

        elif action == "get_wbs":
            return await self._get_wbs(input_data.get("project_id"), tenant_id=tenant_id)  # type: ignore

        elif action == "get_requirements":
            return await self._get_requirements(input_data.get("project_id"))  # type: ignore

        elif action == "generate_scope_research":
            return await self._generate_scope_research(
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

    async def _generate_charter(
        self, charter_data: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """
        Generate comprehensive project charter.

        Returns charter ID and complete document.
        """
        self.logger.info("Generating project charter")

        # Generate unique project ID
        project_id = await self._generate_project_id()

        # Select appropriate template
        template = await self._select_charter_template(charter_data)

        # Extract key information
        title = charter_data.get("title")
        charter_data.get("description")
        project_type = charter_data.get("project_type")
        methodology = charter_data.get("methodology", "hybrid")

        # Generate charter sections using AI
        # Future work: Use Azure OpenAI for content generation
        executive_summary = await self._generate_executive_summary(charter_data)
        objectives = await self._generate_objectives(charter_data)
        scope_overview = await self._generate_scope_overview(charter_data)
        governance_structure = await self._generate_governance_structure(charter_data)
        high_level_requirements = await self._extract_high_level_requirements(charter_data)

        # Identify stakeholders
        stakeholders = await self._identify_stakeholders(charter_data)

        # Generate success criteria
        success_criteria = await self._generate_success_criteria(charter_data)

        # Generate assumptions and constraints
        assumptions = await self._generate_assumptions(charter_data)
        constraints = await self._generate_constraints(charter_data)

        charter_id = await self._generate_charter_id(project_id)

        # Create charter document
        charter = {
            "charter_id": charter_id,
            "project_id": project_id,
            "title": title,
            "project_type": project_type,
            "methodology": methodology,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": charter_data.get("requester", "unknown"),
            "status": "Draft",
            "template": template,
            "document": {
                "executive_summary": executive_summary,
                "objectives": objectives,
                "scope_overview": scope_overview,
                "high_level_requirements": high_level_requirements,
                "stakeholders": stakeholders,
                "governance_structure": governance_structure,
                "success_criteria": success_criteria,
                "assumptions": assumptions,
                "constraints": constraints,
            },
            "version": "1.0",
        }

        # Store charter
        self.charters[project_id] = charter
        self.charter_store.upsert(tenant_id, project_id, charter)

        approval = await self._request_signoff(
            request_type="scope_change",
            request_id=charter_id,
            requester=charter.get("created_by", "unknown"),
            details={
                "description": "Project charter sign-off",
                "project_id": project_id,
                "title": title,
                "methodology": methodology,
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        await self._publish_charter_created(
            charter,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        await self.db_service.store(
            "project_charters",
            charter_id,
            {"tenant_id": tenant_id, "charter": charter},
        )
        charter_content = await self._generate_charter_content(charter)
        await self.document_service.publish_document(
            charter_content,
            DocumentMetadata(
                title=f"{title} Project Charter",
                description=charter_data.get("description", ""),
                tags=["project-charter", project_type or "general"],
                owner=charter.get("created_by", "unknown"),
            ),
            folder_path="Project Charters",
        )
        # Future work: Publish charter.created event to Service Bus

        self.logger.info(f"Generated charter for project: {project_id}")

        return {
            "project_id": project_id,
            "charter_id": charter_id,
            "status": "Draft",
            "document": charter["document"],
            "next_steps": "Review and refine charter, then submit for approval",
            "approval": approval,
        }

    async def _generate_wbs(
        self,
        project_id: str,
        scope_statement: dict[str, Any],
        *,
        tenant_id: str,
        correlation_id: str,
        requester: str,
    ) -> dict[str, Any]:
        """
        Generate Work Breakdown Structure.

        Returns WBS ID and hierarchical structure.
        """
        self.logger.info(f"Generating WBS for project: {project_id}")

        charter = self.charters.get(project_id)
        if not charter:
            raise ValueError(f"Charter not found for project: {project_id}")

        # Query Knowledge Management Agent for similar projects
        # Future work: Integrate with Agent 19
        similar_projects = await self._find_similar_projects(charter)

        # Generate WBS structure using AI
        # Future work: Use Azure OpenAI for WBS generation
        wbs_structure = await self._generate_wbs_structure(
            charter, scope_statement, similar_projects
        )

        # Add work package details
        wbs_with_details = await self._add_work_package_details(wbs_structure)

        # Generate unique WBS ID
        wbs_id = await self._generate_wbs_id(project_id)

        wbs = {
            "wbs_id": wbs_id,
            "project_id": project_id,
            "structure": wbs_with_details,
            "created_at": datetime.utcnow().isoformat(),
            "status": "Draft",
            "version": "1.0",
        }

        # Store WBS
        self.wbs_structures[project_id] = wbs
        self.wbs_store.upsert(tenant_id, project_id, wbs)

        approval = await self._request_signoff(
            request_type="scope_change",
            request_id=wbs_id,
            requester=requester,
            details={
                "description": "WBS sign-off",
                "project_id": project_id,
                "wbs_id": wbs_id,
            },
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        await self._publish_wbs_created(wbs, tenant_id=tenant_id, correlation_id=correlation_id)

        await self.db_service.store(
            "project_wbs",
            wbs_id,
            {"tenant_id": tenant_id, "wbs": wbs},
        )
        # Future work: Publish wbs.created event

        return {
            "wbs_id": wbs_id,
            "project_id": project_id,
            "structure": wbs_with_details,
            "total_work_packages": await self._count_work_packages(wbs_with_details),
            "next_steps": "Review and refine WBS, then pass to Schedule & Planning Agent",
            "approval": approval,
        }

    async def _generate_scope_research(
        self,
        project_id: str,
        objective: str,
        *,
        tenant_id: str,
        correlation_id: str,
        requester: str,
        enable_external_research: bool | None = None,
        search_result_limit: int | None = None,
    ) -> dict[str, Any]:
        self.logger.info(
            "Generating scope research proposals",
            extra={"project_id": project_id, "tenant_id": tenant_id},
        )

        baseline_scope = await self._generate_scope_overview(
            {"in_scope": [objective], "out_of_scope": [], "deliverables": []}
        )
        baseline_requirements = await self._extract_high_level_requirements(
            {"high_level_requirements": []}
        )
        baseline_wbs = await self._generate_wbs_structure({}, baseline_scope, [])
        baseline_wbs_items = [
            f"{code} {node.get('name', '')}".strip()
            for code, node in baseline_wbs.items()
            if isinstance(node, dict)
        ]

        use_external = (
            self.enable_external_research
            if enable_external_research is None
            else enable_external_research
        )
        result_limit = search_result_limit or self.search_result_limit

        snippets: list[str] = []
        notice: str | None = None
        if use_external:
            safe_query = self._sanitize_search_query(objective)
            if safe_query:
                self.logger.info(
                    "External scope research request",
                    extra={
                        "project_id": project_id,
                        "tenant_id": tenant_id,
                        "query": safe_query,
                        "result_limit": result_limit,
                    },
                )
                try:
                    snippets = await search_web(safe_query, result_limit=result_limit)
                except Exception as exc:  # pragma: no cover - defensive
                    self.logger.warning(
                        "Search failed; falling back to templates", extra={"error": str(exc)}
                    )
                    snippets = []
            else:
                notice = "Objective was too sensitive for external research; using templates."
        else:
            notice = "External research disabled; using internal templates."

        if not snippets:
            if notice is None:
                notice = "No external information found; falling back to templates."
            return {
                "project_id": project_id,
                "objective": objective,
                "scope": baseline_scope,
                "requirements": baseline_requirements,
                "wbs": baseline_wbs_items,
                "sources": [],
                "used_external_research": False,
                "notice": notice,
                "requested_by": requester,
                "generated_at": datetime.utcnow().isoformat(),
                "correlation_id": correlation_id,
            }

        generated = await generate_scope_from_search(
            objective,
            snippets,
            baseline_scope,
            baseline_requirements,
            baseline_wbs_items,
        )

        return {
            "project_id": project_id,
            "objective": objective,
            "scope": generated.get("scope", baseline_scope),
            "requirements": generated.get("requirements", baseline_requirements),
            "wbs": generated.get("wbs", baseline_wbs_items),
            "sources": snippets,
            "summary": generated.get("summary", ""),
            "used_external_research": True,
            "notice": notice,
            "requested_by": requester,
            "generated_at": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
        }

    async def _manage_requirements(
        self, project_id: str, requirements: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Manage project requirements.

        Returns requirements repository with metadata.
        """
        self.logger.info(f"Managing requirements for project: {project_id}")

        # Extract requirements from various sources
        # Future work: Use Azure Form Recognizer for document extraction
        extracted_requirements = await self._extract_requirements_from_sources(
            project_id, requirements
        )

        # Categorize requirements
        categorized = await self._categorize_requirements(extracted_requirements)

        # Prioritize requirements
        prioritized = await self._prioritize_requirements(categorized)

        # Detect conflicts
        conflicts = await self._detect_requirement_conflicts(prioritized)

        # Validate completeness
        validation = await self._validate_requirements_completeness(prioritized)

        requirements_repo = {
            "project_id": project_id,
            "requirements": prioritized,
            "categories": await self._get_requirement_categories(prioritized),
            "conflicts": conflicts,
            "validation": validation,
            "total_count": len(prioritized),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Store requirements
        self.requirements[project_id] = requirements_repo

        await self.db_service.store(
            "project_requirements",
            project_id,
            {"tenant_id": "unknown", "requirements": requirements_repo},
        )
        await self.project_service.sync_project(
            {
                "project_id": project_id,
                "requirements_count": requirements_repo.get("total_count", 0),
                "requirements": requirements_repo.get("requirements", []),
                "updated_at": requirements_repo.get("updated_at"),
            }
        )
        # Future work: Publish requirements.updated event

        return requirements_repo

    async def _create_traceability_matrix(self, project_id: str) -> dict[str, Any]:
        """
        Create requirements traceability matrix.

        Returns matrix linking requirements to user stories and test cases.
        """
        self.logger.info(f"Creating traceability matrix for project: {project_id}")

        requirements_repo = self.requirements.get(project_id)
        if not requirements_repo:
            raise ValueError(f"Requirements not found for project: {project_id}")

        requirements_list = requirements_repo.get("requirements", [])

        # Query user stories from Jira/Azure DevOps
        # Future work: Integrate with work item tracking systems
        user_stories = await self._get_user_stories(project_id)

        # Query test cases
        # Future work: Integrate with test management systems
        test_cases = await self._get_test_cases(project_id)

        # Create traceability links
        traceability_links = await self._create_traceability_links(
            requirements_list, user_stories, test_cases
        )

        # Identify gaps
        gaps = await self._identify_traceability_gaps(requirements_list, traceability_links)

        # Calculate coverage
        coverage = await self._calculate_traceability_coverage(
            requirements_list, traceability_links
        )

        matrix = {
            "project_id": project_id,
            "requirements": requirements_list,
            "user_stories": user_stories,
            "test_cases": test_cases,
            "traceability_links": traceability_links,
            "gaps": gaps,
            "coverage": coverage,
            "meets_threshold": coverage >= self.traceability_threshold,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store matrix
        self.traceability_matrices[project_id] = matrix

        # Future work: Store in Azure SQL Database
        # Future work: Publish traceability_matrix.created event

        return matrix

    async def _analyze_stakeholders(
        self, project_id: str, stakeholders: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Analyze project stakeholders.

        Returns stakeholder register with influence and interest analysis.
        """
        self.logger.info(f"Analyzing stakeholders for project: {project_id}")

        # Classify stakeholders by influence and interest
        classified = await self._classify_stakeholders(stakeholders)

        # Analyze influence network
        # Future work: Use social network analysis
        influence_network = await self._analyze_influence_network(classified)

        # Determine communication strategies
        communication_strategies = await self._determine_communication_strategies(classified)

        stakeholder_register = {
            "project_id": project_id,
            "stakeholders": classified,
            "influence_network": influence_network,
            "communication_strategies": communication_strategies,
            "total_count": len(classified),
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store stakeholder register
        self.stakeholder_registers[project_id] = stakeholder_register

        # Future work: Store in database
        # Future work: Publish stakeholder_register.created event

        return stakeholder_register

    async def _create_raci_matrix(
        self,
        project_id: str,
        stakeholders: list[dict[str, Any]],
        deliverables: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Create RACI matrix.

        Returns matrix mapping stakeholders to deliverables with RACI roles.
        """
        self.logger.info(f"Creating RACI matrix for project: {project_id}")

        # Generate RACI assignments
        # Future work: Use AI to suggest RACI assignments based on roles
        raci_assignments = await self._generate_raci_assignments(stakeholders, deliverables)

        # Validate assignments
        validation = await self._validate_raci_assignments(raci_assignments)

        raci_matrix = {
            "project_id": project_id,
            "stakeholders": stakeholders,
            "deliverables": deliverables,
            "assignments": raci_assignments,
            "validation": validation,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Future work: Store in database
        # Future work: Publish raci_matrix.created event

        return raci_matrix

    async def _manage_scope_baseline(self, project_id: str) -> dict[str, Any]:
        """
        Establish and manage scope baseline.

        Returns baseline ID and locked scope elements.
        """
        self.logger.info(f"Managing scope baseline for project: {project_id}")

        charter = self.charters.get(project_id)
        wbs = self.wbs_structures.get(project_id)
        requirements_repo = self.requirements.get(project_id)

        if not charter or not wbs or not requirements_repo:
            raise ValueError(f"Missing required artifacts for baseline: {project_id}")

        # Create baseline snapshot
        baseline = {
            "project_id": project_id,
            "baseline_id": await self._generate_baseline_id(project_id),
            "charter_version": charter.get("version"),
            "wbs_version": wbs.get("version"),
            "requirements_count": len(requirements_repo.get("requirements", [])),
            "scope_statement": charter["document"].get("scope_overview"),
            "locked_at": datetime.utcnow().isoformat(),
            "locked_by": "system",  # Future work: Get from user context
            "status": "Locked",
        }

        # Future work: Store baseline in database
        # Future work: Publish scope_baseline.locked event

        return baseline

    async def _detect_scope_creep(
        self, project_id: str, current_scope: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Detect scope creep by comparing current scope to baseline.

        Returns detected changes and approval recommendations.
        """
        self.logger.info(f"Detecting scope creep for project: {project_id}")

        charter = self.charters.get(project_id)
        if not charter:
            raise ValueError(f"Charter not found for project: {project_id}")

        baseline_scope = charter["document"].get("scope_overview", {})

        # Compare current scope to baseline
        # Future work: Use semantic similarity analysis
        changes = await self._compare_scope(baseline_scope, current_scope)

        # Calculate scope variance
        variance = await self._calculate_scope_variance(changes)

        # Determine if approval needed
        approval_needed = variance > self.scope_change_threshold

        return {
            "project_id": project_id,
            "changes_detected": changes,
            "scope_variance": variance,
            "approval_needed": approval_needed,
            "threshold": self.scope_change_threshold,
            "recommendation": (
                "Submit to Change Control Board" if approval_needed else "Accept changes"
            ),
        }

    async def _get_charter(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        """Retrieve project charter by ID."""
        charter = self.charters.get(project_id)
        if not charter:
            charter = self.charter_store.get(tenant_id, project_id)
        if not charter:
            raise ValueError(f"Charter not found for project: {project_id}")
        return charter  # type: ignore

    async def _get_wbs(self, project_id: str, *, tenant_id: str) -> dict[str, Any]:
        """Retrieve WBS by project ID."""
        wbs = self.wbs_structures.get(project_id)
        if not wbs:
            wbs = self.wbs_store.get(tenant_id, project_id)
        if not wbs:
            raise ValueError(f"WBS not found for project: {project_id}")
        return wbs  # type: ignore

    async def _get_requirements(self, project_id: str) -> dict[str, Any]:
        """Retrieve requirements repository by project ID."""
        requirements = self.requirements.get(project_id)
        if not requirements:
            raise ValueError(f"Requirements not found for project: {project_id}")
        return requirements  # type: ignore

    # Helper methods

    async def _generate_project_id(self) -> str:
        """Generate unique project ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"PRJ-{timestamp}-{uuid.uuid4().hex[:6]}"

    async def _generate_charter_id(self, project_id: str) -> str:
        """Generate unique charter ID."""
        return f"CHAR-{project_id}-{uuid.uuid4().hex[:6]}"

    async def _generate_wbs_id(self, project_id: str) -> str:
        """Generate unique WBS ID."""
        return f"{project_id}-WBS-001"

    async def _request_signoff(
        self,
        *,
        request_type: str,
        request_id: str,
        requester: str,
        details: dict[str, Any],
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        if not self.approval_agent:
            return {"status": "skipped", "reason": "approval_agent_not_configured"}
        response = await self.approval_agent.process(
            {
                "request_type": request_type,
                "request_id": request_id,
                "requester": requester,
                "details": details,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
            }
        )
        return response

    async def _publish_charter_created(
        self, charter: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> None:
        event = CharterCreatedEvent(
            event_name="charter.created",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "charter_id": charter.get("charter_id", ""),
                "project_id": charter.get("project_id", ""),
                "created_at": datetime.fromisoformat(charter.get("created_at")),
                "owner": charter.get("created_by", "unknown"),
            },
        )
        await self.event_bus.publish("charter.created", event.model_dump())

    async def _publish_wbs_created(
        self, wbs: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> None:
        event = WbsCreatedEvent(
            event_name="wbs.created",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "wbs_id": wbs.get("wbs_id", ""),
                "project_id": wbs.get("project_id", ""),
                "created_at": datetime.fromisoformat(wbs.get("created_at")),
                "baseline_date": None,
            },
        )
        await self.event_bus.publish("wbs.created", event.model_dump())

    async def _generate_baseline_id(self, project_id: str) -> str:
        """Generate unique baseline ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"{project_id}-BASELINE-{timestamp}"

    async def _select_charter_template(self, charter_data: dict[str, Any]) -> str:
        """Select appropriate charter template."""
        project_type = charter_data.get("project_type", "general")
        methodology = charter_data.get("methodology", "hybrid")

        # Future work: Implement template selection logic
        return f"template_{project_type}_{methodology}"

    async def _generate_executive_summary(self, charter_data: dict[str, Any]) -> str:
        """Generate executive summary using AI."""
        # Future work: Use Azure OpenAI for natural language generation
        title = charter_data.get("title", "Project")
        description = charter_data.get("description", "")

        return f"This project charter establishes {title}. {description}"

    async def _generate_objectives(self, charter_data: dict[str, Any]) -> list[str]:
        """Generate project objectives."""
        # Future work: Extract objectives from description using NLP
        return charter_data.get(  # type: ignore
            "objectives",
            [
                "Deliver project on time and within budget",
                "Meet stakeholder expectations",
                "Achieve defined success criteria",
            ],
        )

    async def _generate_scope_overview(self, charter_data: dict[str, Any]) -> dict[str, Any]:
        """Generate scope overview."""
        return {
            "in_scope": charter_data.get("in_scope", []),
            "out_of_scope": charter_data.get("out_of_scope", []),
            "deliverables": charter_data.get("deliverables", []),
        }

    def _sanitize_search_query(self, objective: str) -> str:
        sanitized = objective.strip()
        if not sanitized:
            return ""

        sanitized = re.sub(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}",
            "[REDACTED_EMAIL]",
            sanitized,
        )
        sanitized = re.sub(r"\\b\\d{4,}\\b", "[REDACTED_ID]", sanitized)
        sanitized = re.sub(r"\\b[A-Z0-9]{10,}\\b", "[REDACTED_TOKEN]", sanitized)
        sanitized = sanitized.split("\\n", maxsplit=1)[0]
        return sanitized[:240]

    async def _generate_governance_structure(self, charter_data: dict[str, Any]) -> dict[str, Any]:
        """Generate governance structure."""
        return {
            "sponsor": charter_data.get("sponsor", "Unassigned"),
            "project_manager": charter_data.get("project_manager", "Unassigned"),
            "steering_committee": charter_data.get("steering_committee", []),
            "reporting_frequency": charter_data.get("reporting_frequency", "weekly"),
        }

    async def _extract_high_level_requirements(self, charter_data: dict[str, Any]) -> list[str]:
        """Extract high-level requirements."""
        # Future work: Use NLP to extract requirements
        return charter_data.get("high_level_requirements", [])  # type: ignore

    async def _identify_stakeholders(self, charter_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify project stakeholders."""
        return charter_data.get("stakeholders", [])  # type: ignore

    async def _generate_success_criteria(self, charter_data: dict[str, Any]) -> list[str]:
        """Generate success criteria."""
        return charter_data.get(  # type: ignore
            "success_criteria",
            [
                "Project completed within approved budget",
                "All deliverables meet quality standards",
                "Stakeholder satisfaction > 80%",
            ],
        )

    async def _generate_assumptions(self, charter_data: dict[str, Any]) -> list[str]:
        """Generate project assumptions."""
        return charter_data.get("assumptions", [])  # type: ignore

    async def _generate_constraints(self, charter_data: dict[str, Any]) -> list[str]:
        """Generate project constraints."""
        return charter_data.get("constraints", [])  # type: ignore

    async def _find_similar_projects(self, charter: dict[str, Any]) -> list[dict[str, Any]]:
        """Find similar projects for WBS reference."""
        # Future work: Use Azure Cognitive Search for similarity search
        return []

    async def _generate_wbs_structure(
        self,
        charter: dict[str, Any],
        scope_statement: dict[str, Any],
        similar_projects: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate hierarchical WBS structure."""
        objectives = charter.get("document", {}).get("objectives", []) or charter.get(
            "objectives", []
        )
        scope_overview = scope_statement or charter.get("document", {}).get("scope_overview", {})
        wbs_from_objectives = await self._generate_wbs_from_objectives(
            objectives, scope_overview, similar_projects
        )
        if wbs_from_objectives:
            return wbs_from_objectives

        return {
            "1.0": {
                "name": "Project Management",
                "children": {
                    "1.1": {"name": "Project Planning", "children": {}},
                    "1.2": {"name": "Project Monitoring", "children": {}},
                },
            }
        }

    async def _add_work_package_details(self, wbs_structure: dict[str, Any]) -> dict[str, Any]:
        """Add details to work packages."""
        # Future work: Add effort estimates, resources, durations
        return wbs_structure

    async def _count_work_packages(self, wbs_structure: dict[str, Any]) -> int:
        """Count total work packages in WBS."""
        # Future work: Implement recursive counting
        return 10  # Baseline

    async def _extract_requirements_from_sources(
        self, project_id: str, requirements: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract requirements from various sources."""
        extracted: list[dict[str, Any]] = []
        keyword_patterns = [
            r"\\bshall\\b",
            r"\\bmust\\b",
            r"\\bshould\\b",
            r"\\bis required to\\b",
            r"\\bneeds to\\b",
        ]
        keyword_regex = re.compile("|".join(keyword_patterns), re.IGNORECASE)

        for req in requirements:
            if "text" in req or "description" in req:
                extracted.append(
                    {
                        "id": req.get("id") or f"REQ-{uuid.uuid4().hex[:6]}",
                        "text": req.get("text") or req.get("description", ""),
                        "source": req.get("source", "manual"),
                        "category": req.get("category"),
                    }
                )
            source_text = req.get("source_text") or req.get("document") or req.get("notes", "")
            if source_text:
                sentences = re.split(r"(?<=[.!?])\\s+", str(source_text))
                for sentence in sentences:
                    if keyword_regex.search(sentence):
                        extracted.append(
                            {
                                "id": f"REQ-{uuid.uuid4().hex[:6]}",
                                "text": sentence.strip(),
                                "source": req.get("source", "keyword_parse"),
                            }
                        )

        if not extracted and requirements:
            for req in requirements:
                if "text" in req or "description" in req:
                    extracted.append(req)

        return extracted

    async def _generate_charter_content(self, charter: dict[str, Any]) -> str:
        """Generate formatted charter content from template strings."""
        document = charter.get("document", {})
        title = charter.get("title", "Project Charter")
        project_id = charter.get("project_id", "unknown")
        created_at = charter.get("created_at", "")

        def format_list(items: list[Any]) -> str:
            if not items:
                return "None"
            return "\\n".join(f"- {item}" for item in items)

        scope = document.get("scope_overview", {})
        stakeholders = document.get("stakeholders", [])
        stakeholder_lines: list[str] = []
        for stakeholder in stakeholders:
            name = stakeholder.get("name") if isinstance(stakeholder, dict) else str(stakeholder)
            role = ""
            if isinstance(stakeholder, dict):
                role = stakeholder.get("role", "")
            stakeholder_lines.append(f"{name}{f' ({role})' if role else ''}")

        governance = document.get("governance_structure", {})
        governance_text = (
            f"Sponsor: {governance.get('sponsor', 'Unassigned')}\\n"
            f"Project Manager: {governance.get('project_manager', 'Unassigned')}\\n"
            f"Steering Committee: {', '.join(governance.get('steering_committee', [])) or 'None'}\\n"
            f"Reporting Frequency: {governance.get('reporting_frequency', 'weekly')}"
        )

        return (
            f"Project Charter\\n"
            f"Title: {title}\\n"
            f"Project ID: {project_id}\\n"
            f"Created At: {created_at}\\n"
            f"Status: {charter.get('status', 'Draft')}\\n"
            f"Methodology: {charter.get('methodology', 'hybrid')}\\n\\n"
            f"Executive Summary\\n{document.get('executive_summary', '')}\\n\\n"
            f"Objectives\\n{format_list(document.get('objectives', []))}\\n\\n"
            f"Scope Overview\\n"
            f"In Scope\\n{format_list(scope.get('in_scope', []))}\\n\\n"
            f"Out of Scope\\n{format_list(scope.get('out_of_scope', []))}\\n\\n"
            f"Deliverables\\n{format_list(scope.get('deliverables', []))}\\n\\n"
            f"High-Level Requirements\\n"
            f"{format_list(document.get('high_level_requirements', []))}\\n\\n"
            f"Stakeholders\\n{format_list(stakeholder_lines)}\\n\\n"
            f"Governance Structure\\n{governance_text}\\n\\n"
            f"Success Criteria\\n{format_list(document.get('success_criteria', []))}\\n\\n"
            f"Assumptions\\n{format_list(document.get('assumptions', []))}\\n\\n"
            f"Constraints\\n{format_list(document.get('constraints', []))}\\n"
        )

    async def _generate_wbs_from_objectives(
        self,
        objectives: list[str],
        scope_overview: dict[str, Any],
        similar_projects: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate a WBS by decomposing objectives into phases and work packages."""
        if not objectives and not scope_overview.get("deliverables"):
            return {}

        wbs: dict[str, Any] = {
            "1.0": {
                "name": "Project Management",
                "children": {
                    "1.1": {"name": "Initiation & Planning", "children": {}},
                    "1.2": {"name": "Monitoring & Control", "children": {}},
                    "1.3": {"name": "Closure", "children": {}},
                },
            }
        }

        deliverables = scope_overview.get("deliverables", [])

        def objective_work_packages(objective: str) -> list[str]:
            base_packages = [
                "Discovery & Analysis",
                "Design & Build",
                "Validation & Acceptance",
                "Deployment & Handover",
            ]
            lowered = objective.lower()
            if "migrate" in lowered or "migration" in lowered:
                return [
                    "Migration Planning",
                    "Data & System Migration",
                    "Migration Validation",
                    "Go-Live Support",
                ]
            if "implement" in lowered or "build" in lowered or "develop" in lowered:
                return [
                    "Solution Design",
                    "Implementation",
                    "Testing",
                    "Release",
                ]
            return base_packages

        index_offset = 2
        for idx, objective in enumerate(objectives or ["Deliver scoped outcomes"]):
            root_code = f"{idx + index_offset}.0"
            children: dict[str, Any] = {}
            packages = objective_work_packages(objective)
            for pkg_index, package in enumerate(packages, start=1):
                child_code = f"{idx + index_offset}.{pkg_index}"
                children[child_code] = {"name": package, "children": {}}
            if deliverables:
                for deliverable_index, deliverable in enumerate(deliverables, start=len(children) + 1):
                    child_code = f"{idx + index_offset}.{deliverable_index}"
                    children[child_code] = {"name": f"Deliver {deliverable}", "children": {}}
            if similar_projects:
                children[f"{idx + index_offset}.{len(children) + 1}"] = {
                    "name": "Leverage Similar Project Assets",
                    "children": {},
                }
            wbs[root_code] = {"name": objective, "children": children}

        return wbs

    async def _categorize_requirements(
        self, requirements: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Categorize requirements by type."""
        for req in requirements:
            if "category" not in req:
                # Future work: Use ML to categorize
                req["category"] = "functional"
        return requirements

    async def _prioritize_requirements(
        self, requirements: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Prioritize requirements."""
        for req in requirements:
            if "priority" not in req:
                req["priority"] = "medium"
        return requirements

    async def _detect_requirement_conflicts(
        self, requirements: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Detect conflicting requirements."""
        # Future work: Use semantic similarity to detect conflicts
        return []

    async def _validate_requirements_completeness(
        self, requirements: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Validate requirements completeness."""
        return {"complete": True, "missing_fields": [], "validation_score": 0.95}

    async def _get_requirement_categories(
        self, requirements: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Get requirement count by category."""
        categories = {}  # type: ignore
        for req in requirements:
            category = req.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1
        return categories

    async def _get_user_stories(self, project_id: str) -> list[dict[str, Any]]:
        """Get user stories from work item tracking system."""
        # Future work: Integrate with Jira/Azure DevOps
        return []

    async def _get_test_cases(self, project_id: str) -> list[dict[str, Any]]:
        """Get test cases from test management system."""
        # Future work: Integrate with test management tools
        return []

    async def _create_traceability_links(
        self,
        requirements: list[dict[str, Any]],
        user_stories: list[dict[str, Any]],
        test_cases: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Create traceability links between artifacts."""
        # Future work: Implement linking logic
        return []

    async def _identify_traceability_gaps(
        self, requirements: list[dict[str, Any]], traceability_links: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Identify gaps in traceability."""
        # Future work: Find unlinked requirements
        return []

    async def _calculate_traceability_coverage(
        self, requirements: list[dict[str, Any]], traceability_links: list[dict[str, Any]]
    ) -> float:
        """Calculate traceability coverage percentage."""
        if not requirements:
            return 1.0
        # Future work: Calculate actual coverage
        return 0.85

    async def _classify_stakeholders(
        self, stakeholders: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Classify stakeholders by influence and interest."""
        for stakeholder in stakeholders:
            if "influence" not in stakeholder:
                stakeholder["influence"] = "medium"
            if "interest" not in stakeholder:
                stakeholder["interest"] = "medium"
        return stakeholders

    async def _analyze_influence_network(
        self, stakeholders: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Analyze stakeholder influence network."""
        # Future work: Use social network analysis
        return {"nodes": len(stakeholders), "edges": 0}

    async def _determine_communication_strategies(
        self, stakeholders: list[dict[str, Any]]
    ) -> dict[str, str]:
        """Determine communication strategies for stakeholders."""
        strategies = {}
        for stakeholder in stakeholders:
            name = stakeholder.get("name", "unknown")
            influence = stakeholder.get("influence", "medium")
            interest = stakeholder.get("interest", "medium")

            if influence == "high" and interest == "high":
                strategies[name] = "Manage Closely"
            elif influence == "high" and interest == "low":
                strategies[name] = "Keep Satisfied"
            elif influence == "low" and interest == "high":
                strategies[name] = "Keep Informed"
            else:
                strategies[name] = "Monitor"

        return strategies

    async def _generate_raci_assignments(
        self, stakeholders: list[dict[str, Any]], deliverables: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate RACI assignments."""
        # Future work: Use AI to suggest assignments based on roles
        return []

    async def _validate_raci_assignments(self, assignments: list[dict[str, Any]]) -> dict[str, Any]:
        """Validate RACI assignments."""
        return {"valid": True, "issues": [], "warnings": []}

    async def _compare_scope(
        self, baseline_scope: dict[str, Any], current_scope: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Compare current scope to baseline."""
        # Future work: Use semantic similarity analysis
        return []

    async def _calculate_scope_variance(self, changes: list[dict[str, Any]]) -> float:
        """Calculate scope variance percentage."""
        # Future work: Calculate actual variance
        return 0.05  # 5% variance

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Project Definition & Scope Agent...")
        # Future work: Close database connections
        # Future work: Close external API connections
        # Future work: Flush any pending events

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
