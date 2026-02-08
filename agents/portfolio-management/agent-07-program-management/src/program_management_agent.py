"""
Agent 7: Program Management Agent

Purpose:
Coordinates groups of related projects (programs) to achieve shared strategic objectives
and realize synergies. Manages inter-project dependencies, plans integrated roadmaps
and monitors program health.

Specification: agents/portfolio-management/agent-07-program-management/README.md
"""

import asyncio
import json
import os
import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

from events import ProgramCreatedEvent, ProgramRoadmapUpdatedEvent
from llm.client import LLMClient
from observability.tracing import get_trace_id

from agents.common.connector_integration import DatabaseStorageService
from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore


class ProgramManagementAgent(BaseAgent):
    """
    Program Management Agent - Coordinates programs and manages inter-project dependencies.

    Key Capabilities:
    - Program definition & roadmap planning
    - Inter-project dependency tracking
    - Benefits aggregation across projects
    - Cross-project resource coordination
    - Synergy identification and optimization
    - Program-level change impact analysis
    - Program governance & reporting
    """

    def __init__(self, agent_id: str = "program-management", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.dependency_types = (
            config.get(
                "dependency_types",
                [
                    "finish_to_start",
                    "start_to_start",
                    "finish_to_finish",
                    "start_to_finish",
                    "shared_resource",
                    "technical_dependency",
                    "deliverable_dependency",
                ],
            )
            if config
            else [
                "finish_to_start",
                "start_to_start",
                "finish_to_finish",
                "start_to_finish",
                "shared_resource",
                "technical_dependency",
                "deliverable_dependency",
            ]
        )

        self.synergy_detection_threshold = (
            config.get("synergy_detection_threshold", 0.75) if config else 0.75
        )
        self.health_score_weights = (
            config.get(
                "health_score_weights",
                {"schedule": 0.25, "budget": 0.25, "risk": 0.20, "quality": 0.15, "resource": 0.15},
            )
            if config
            else {"schedule": 0.25, "budget": 0.25, "risk": 0.20, "quality": 0.15, "resource": 0.15}
        )
        self.optimization_objectives = (
            config.get(
                "optimization_objectives",
                {
                    "utilization": 0.3,
                    "cost": 0.2,
                    "risk": 0.2,
                    "schedule": 0.15,
                    "alignment": 0.1,
                    "synergy": 0.05,
                },
            )
            if config
            else {
                "utilization": 0.3,
                "cost": 0.2,
                "risk": 0.2,
                "schedule": 0.15,
                "alignment": 0.1,
                "synergy": 0.05,
            }
        )

        program_store_path = (
            Path(config.get("program_store_path", "data/program_store.json"))
            if config
            else Path("data/program_store.json")
        )
        roadmap_store_path = (
            Path(config.get("program_roadmap_store_path", "data/program_roadmap_store.json"))
            if config
            else Path("data/program_roadmap_store.json")
        )
        dependency_store_path = (
            Path(config.get("program_dependency_store_path", "data/program_dependency_store.json"))
            if config
            else Path("data/program_dependency_store.json")
        )
        self.program_store = TenantStateStore(program_store_path)
        self.roadmap_store = TenantStateStore(roadmap_store_path)
        self.dependency_store = TenantStateStore(dependency_store_path)
        self.synergies = {}  # type: ignore
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = get_event_bus()
        self.db_service: DatabaseStorageService | None = None
        self.schedule_agent = config.get("schedule_agent") if config else None
        self.business_case_agent = config.get("business_case_agent") if config else None
        self.resource_agent = config.get("resource_agent") if config else None
        self.project_definition_agent = config.get("project_definition_agent") if config else None
        self.lifecycle_agent = config.get("lifecycle_agent") if config else None
        self.financial_agent = config.get("financial_agent") if config else None
        self.risk_agent = config.get("risk_agent") if config else None
        self.quality_agent = config.get("quality_agent") if config else None
        self.approval_agent = config.get("approval_agent") if config else None
        self.approval_agent_config = config.get("approval_agent_config", {}) if config else {}
        self.approval_agent_enabled = (
            config.get("approval_agent_enabled", True) if config else True
        )
        self.schedule_ids = config.get("schedule_ids", {}) if config else {}
        self.business_case_ids = config.get("business_case_ids", {}) if config else {}
        self.health_actions = config.get("health_actions", {}) if config else {}
        self.cosmos_client = config.get("cosmos_client") if config else None
        self.cosmos_database = config.get("cosmos_database") if config else None
        self.dependency_container = config.get("dependency_container") if config else None
        self.mapping_container = config.get("mapping_container") if config else None
        self.service_bus_client = config.get("service_bus_client") if config else None
        self.service_bus_receiver = None
        self.service_bus_task: asyncio.Task | None = None
        self.ml_workspace = config.get("ml_workspace") if config else None
        self.health_model = config.get("ml_model") if config else None
        self.synapse_client = config.get("synapse_client") if config else None
        self.text_analytics_client = config.get("text_analytics_client") if config else None
        self.llm_client = config.get("llm_client") if config else None
        self.planview_connector = config.get("planview_connector") if config else None
        self.clarity_connector = config.get("clarity_connector") if config else None
        self.jira_base_url = config.get("jira_base_url") if config else None
        self.jira_api_token = config.get("jira_api_token") if config else None
        self.azure_devops_org_url = config.get("azure_devops_org_url") if config else None
        self.azure_devops_pat = config.get("azure_devops_pat") if config else None

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Program Management Agent...")

        db_config = self.config.get("database_storage", {}) if self.config else {}
        self.db_service = DatabaseStorageService(db_config)
        self.logger.info("Database Storage Service initialized")

        await self._initialize_cosmos()
        await self._initialize_ml()
        await self._initialize_llm()
        await self._initialize_integrations()
        await self._subscribe_to_program_events()

        self.logger.info("Program Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "create_program",
            "generate_roadmap",
            "track_dependencies",
            "aggregate_benefits",
            "coordinate_resources",
            "identify_synergies",
            "analyze_change_impact",
            "get_program_health",
            "optimize_program",
            "submit_program_for_approval",
            "record_program_decision",
            "get_program",
            "list_dependency_graphs",
            "get_dependency_graph",
            "delete_dependency_graph",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "create_program":
            program_data = input_data.get("program", {})
            required_fields = [
                "name",
                "description",
                "strategic_objectives",
                "constituent_projects",
            ]
            for field in required_fields:
                if field not in program_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        elif action in [
            "track_dependencies",
            "analyze_change_impact",
            "get_dependency_graph",
            "delete_dependency_graph",
            "optimize_program",
            "submit_program_for_approval",
            "record_program_decision",
        ]:
            if "program_id" not in input_data:
                self.logger.warning("Missing program_id")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process program management requests.

        Args:
            input_data: {
                "action": "create_program" | "generate_roadmap" | "track_dependencies" |
                          "aggregate_benefits" | "coordinate_resources" | "identify_synergies" |
                          "analyze_change_impact" | "get_program_health" | "get_program",
                "program": Program definition data,
                "program_id": ID of existing program,
                "change": Change details for impact analysis,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - create_program: Program ID, structure, initial roadmap
            - generate_roadmap: Integrated roadmap with milestones and dependencies
            - track_dependencies: Dependency graph and critical paths
            - aggregate_benefits: Consolidated benefits across projects
            - coordinate_resources: Resource allocation recommendations
            - identify_synergies: Synergy opportunities with cost savings
            - analyze_change_impact: Impact assessment across program
            - get_program_health: Composite health score and metrics
            - get_program: Full program details
        """
        action = input_data.get("action", "create_program")
        context = input_data.get("context", {})
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"

        if action == "create_program":
            return await self._create_program(
                input_data.get("program", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "generate_roadmap":
            return await self._generate_roadmap(
                input_data.get("program_id"),  # type: ignore
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "track_dependencies":
            return await self._track_dependencies(
                input_data.get("program_id"),  # type: ignore
                tenant_id=tenant_id,
            )

        elif action == "aggregate_benefits":
            return await self._aggregate_benefits(
                input_data.get("program_id"),  # type: ignore
                tenant_id=tenant_id,
            )

        elif action == "coordinate_resources":
            return await self._coordinate_resources(
                input_data.get("program_id"),  # type: ignore
                tenant_id=tenant_id,
            )

        elif action == "identify_synergies":
            return await self._identify_synergies(
                input_data.get("program_id"),  # type: ignore
                tenant_id=tenant_id,
            )

        elif action == "analyze_change_impact":
            return await self._analyze_change_impact(
                input_data.get("program_id"),
                input_data.get("change", {}),  # type: ignore
                tenant_id=tenant_id,
            )

        elif action == "get_program_health":
            return await self._get_program_health(
                input_data.get("program_id"),  # type: ignore
                tenant_id=tenant_id,
            )
        elif action == "optimize_program":
            return await self._optimize_program_schedule(
                input_data.get("program_id"),  # type: ignore
                objectives=input_data.get("objectives"),
                constraints=input_data.get("constraints", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
        elif action == "submit_program_for_approval":
            return await self._submit_program_for_approval(
                input_data.get("program_id"),  # type: ignore
                decision_payload=input_data.get("decision_payload", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
        elif action == "record_program_decision":
            return await self._record_program_decision(
                input_data.get("program_id"),  # type: ignore
                decision=input_data.get("decision", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )

        elif action == "get_program":
            return await self._get_program(
                input_data.get("program_id"),  # type: ignore
                tenant_id=tenant_id,
            )
        elif action == "list_dependency_graphs":
            return {
                "dependency_graphs": await self._list_dependency_graphs(),
            }
        elif action == "get_dependency_graph":
            return await self._read_dependency_graph(input_data.get("program_id"))  # type: ignore
        elif action == "delete_dependency_graph":
            await self._delete_dependency_graph(input_data.get("program_id"))  # type: ignore
            return {"status": "deleted", "program_id": input_data.get("program_id")}

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _create_program(
        self, program_data: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """
        Create a new program structure.

        Returns program ID and initial structure.
        """
        self.logger.info("Creating new program")

        # Generate unique program ID
        program_id = await self._generate_program_id()

        # Extract program details
        name = program_data.get("name")
        description = program_data.get("description")
        strategic_objectives = program_data.get("strategic_objectives", [])
        constituent_projects = program_data.get("constituent_projects", [])
        methodology = program_data.get("methodology", "hybrid")

        # Create program structure
        program = {
            "program_id": program_id,
            "name": name,
            "description": description,
            "strategic_objectives": strategic_objectives,
            "constituent_projects": constituent_projects,
            "methodology": methodology,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": program_data.get("created_by", "unknown"),
            "status": "Planning",
            "portfolio_id": program_data.get("portfolio_id", "unknown"),
            "metadata": {
                "project_count": len(constituent_projects),
                "dependencies_identified": 0,
                "synergies_found": 0,
            },
        }

        self.program_store.upsert(tenant_id, program_id, program)
        if self.db_service:
            await self.db_service.store("programs", program_id, program)
        await self._sync_work_management_mappings(program_id, program)

        self.logger.info(f"Created program: {program_id}")

        await self._publish_program_created(
            program,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        return {
            "program_id": program_id,
            "name": name,
            "status": "Planning",
            "constituent_projects": constituent_projects,
            "next_steps": "Generate roadmap and identify dependencies",
        }

    async def _generate_roadmap(
        self, program_id: str, *, tenant_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """
        Generate integrated program roadmap.

        Returns roadmap with milestones, dependencies, and timelines.
        """
        self.logger.info(f"Generating roadmap for program: {program_id}")

        program = self.program_store.get(tenant_id, program_id)
        if not program:
            raise ValueError(f"Program not found: {program_id}")

        constituent_projects = program.get("constituent_projects", [])

        # Query project schedules from Schedule & Planning Agent
        project_schedules = await self._get_project_schedules(constituent_projects)

        # Query resource allocations for overlap detection
        resource_allocations = await self._get_resource_allocations(constituent_projects)

        # Identify inter-project dependencies
        dependencies = await self._identify_dependencies(
            constituent_projects,
            schedules=project_schedules,
            resource_allocations=resource_allocations,
        )

        # Calculate critical path across program
        critical_path = await self._calculate_program_critical_path(project_schedules, dependencies)

        # Generate milestone timeline
        milestones = await self._generate_program_milestones(project_schedules, dependencies)

        # Create roadmap visualization data
        roadmap = {
            "program_id": program_id,
            "milestones": milestones,
            "dependencies": dependencies,
            "critical_path": critical_path,
            "project_timelines": project_schedules,
            "resource_allocations": resource_allocations,
            "start_date": await self._calculate_program_start(project_schedules),
            "end_date": await self._calculate_program_end(project_schedules),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        self.roadmap_store.upsert(tenant_id, program_id, roadmap)
        self.dependency_store.upsert(
            tenant_id, program_id, {"program_id": program_id, "dependencies": dependencies}
        )
        await self._create_dependency_graph(program_id, dependencies, tenant_id=tenant_id)
        if self.db_service:
            await self.db_service.store("program_roadmaps", program_id, roadmap)
            await self.db_service.store(
                "program_dependencies",
                program_id,
                {"program_id": program_id, "dependencies": dependencies},
            )

        await self._publish_program_roadmap_updated(
            roadmap,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        return roadmap

    async def _track_dependencies(self, program_id: str, *, tenant_id: str) -> dict[str, Any]:
        """
        Track and analyze inter-project dependencies.

        Returns dependency graph and critical paths.
        """
        self.logger.info(f"Tracking dependencies for program: {program_id}")

        program = self.program_store.get(tenant_id, program_id)
        if not program:
            raise ValueError(f"Program not found: {program_id}")

        constituent_projects = program.get("constituent_projects", [])

        # Identify all dependencies
        project_schedules = await self._get_project_schedules(constituent_projects)
        resource_allocations = await self._get_resource_allocations(constituent_projects)
        dependencies = await self._identify_dependencies(
            constituent_projects,
            schedules=project_schedules,
            resource_allocations=resource_allocations,
        )
        self.dependency_store.upsert(
            tenant_id, program_id, {"program_id": program_id, "dependencies": dependencies}
        )
        await self._update_dependency_graph(program_id, dependencies, tenant_id=tenant_id)
        if self.db_service:
            await self.db_service.store(
                "program_dependencies",
                program_id,
                {"program_id": program_id, "dependencies": dependencies},
            )

        # Analyze dependency graph
        graph_analysis = await self._analyze_dependency_graph(dependencies)

        # Identify critical dependencies
        critical_dependencies = await self._identify_critical_dependencies(
            dependencies, graph_analysis
        )

        # Detect circular dependencies
        circular_deps = await self._detect_circular_dependencies(dependencies)
        optimization = await self._optimize_dependency_graph(
            dependencies, graph_analysis, circular_deps
        )

        return {
            "program_id": program_id,
            "dependencies": dependencies,
            "dependency_count": len(dependencies),
            "critical_dependencies": critical_dependencies,
            "circular_dependencies": circular_deps,
            "graph_analysis": graph_analysis,
            "recommendations": await self._generate_dependency_recommendations(
                dependencies, circular_deps
            ),
            "optimization": optimization,
        }

    async def _aggregate_benefits(self, program_id: str, *, tenant_id: str) -> dict[str, Any]:
        """
        Aggregate benefits across program projects.

        Returns consolidated benefits and realized value.
        """
        self.logger.info(f"Aggregating benefits for program: {program_id}")

        program = self.program_store.get(tenant_id, program_id)
        if not program:
            raise ValueError(f"Program not found: {program_id}")

        constituent_projects = program.get("constituent_projects", [])

        # Query benefits from each project
        project_benefits = await self._get_project_benefits(constituent_projects)

        # Aggregate financial benefits
        total_benefits = sum(pb.get("total_benefits", 0) for pb in project_benefits.values())

        total_costs = sum(pb.get("total_costs", 0) for pb in project_benefits.values())

        # Calculate program-level ROI
        program_roi = (total_benefits - total_costs) / total_costs if total_costs > 0 else 0

        # Identify overlapping benefits (to avoid double-counting)
        adjusted_benefits = await self._adjust_for_overlaps(project_benefits)
        if self.db_service:
            await self.db_service.store(
                "program_benefits",
                program_id,
                {
                    "program_id": program_id,
                    "total_benefits": total_benefits,
                    "adjusted_benefits": adjusted_benefits,
                    "total_costs": total_costs,
                    "program_roi": program_roi,
                    "project_benefits": project_benefits,
                },
            )

        return {
            "program_id": program_id,
            "total_benefits": total_benefits,
            "adjusted_benefits": adjusted_benefits,
            "total_costs": total_costs,
            "program_roi": program_roi,
            "project_benefits": project_benefits,
            "benefit_categories": await self._categorize_benefits(project_benefits),
            "realization_timeline": await self._generate_benefit_timeline(project_benefits),
        }

    async def _coordinate_resources(self, program_id: str, *, tenant_id: str) -> dict[str, Any]:
        """
        Coordinate resource allocation across projects.

        Returns resource allocation recommendations and conflict resolution.
        """
        self.logger.info(f"Coordinating resources for program: {program_id}")

        program = self.program_store.get(tenant_id, program_id)
        if not program:
            raise ValueError(f"Program not found: {program_id}")

        constituent_projects = program.get("constituent_projects", [])

        # Query resource allocations from Resource Management Agent
        resource_allocations = await self._get_resource_allocations(constituent_projects)

        # Identify resource conflicts
        conflicts = await self._identify_resource_conflicts(resource_allocations)

        # Generate optimization recommendations
        recommendations = await self._optimize_resource_allocation(resource_allocations, conflicts)

        # Calculate utilization across program
        utilization = await self._calculate_program_utilization(resource_allocations)

        return {
            "program_id": program_id,
            "resource_allocations": resource_allocations,
            "conflicts": conflicts,
            "recommendations": recommendations,
            "utilization": utilization,
            "shared_resources": await self._identify_shared_resources(resource_allocations),
        }

    async def _identify_synergies(self, program_id: str, *, tenant_id: str) -> dict[str, Any]:
        """
        Identify synergy opportunities across projects.

        Returns synergies with potential cost savings and efficiency gains.
        """
        self.logger.info(f"Identifying synergies for program: {program_id}")

        program = self.program_store.get(tenant_id, program_id)
        if not program:
            raise ValueError(f"Program not found: {program_id}")

        constituent_projects = program.get("constituent_projects", [])

        # Analyze project scopes and technologies
        project_details = await self._get_project_details(constituent_projects)
        synergy_analysis = await self.analyze_synergies(project_details)

        shared_components = synergy_analysis.get("shared_components", [])
        vendor_synergies = synergy_analysis.get("vendor_consolidation", [])
        infrastructure_synergies = synergy_analysis.get("infrastructure_synergies", [])

        # Calculate potential savings
        project_costs = await self._estimate_project_costs(constituent_projects, tenant_id=tenant_id)
        cost_savings = await self._calculate_synergy_savings(
            shared_components, vendor_synergies, infrastructure_synergies, project_costs
        )
        optimization = await self._optimize_synergy_portfolio(
            shared_components, vendor_synergies, infrastructure_synergies
        )
        mitigations = await self._propose_synergy_mitigations(optimization)

        synergies = {
            "shared_components": shared_components,
            "vendor_consolidation": vendor_synergies,
            "infrastructure_sharing": infrastructure_synergies,
            "estimated_savings": cost_savings,
            "optimization": optimization,
            "mitigations": mitigations,
        }

        # Store synergies
        self.synergies[program_id] = synergies
        if self.db_service:
            await self.db_service.store(
                "program_synergies",
                program_id,
                {"program_id": program_id, "synergies": synergies},
            )
            await self.db_service.store(
                "program_analytics",
                program_id,
                {"program_id": program_id, "synergy_savings": cost_savings},
            )

        await self.event_bus.publish(
            "program.synergy.identified",
            {
                "program_id": program_id,
                "tenant_id": tenant_id,
                "synergies": synergies,
                "estimated_savings": cost_savings,
            },
        )

        return {
            "program_id": program_id,
            "synergies": synergies,
            "total_savings": cost_savings.get("total", 0),
            "recommendations": await self._generate_synergy_recommendations(synergies),
        }

    async def _analyze_change_impact(
        self, program_id: str, change: dict[str, Any], *, tenant_id: str
    ) -> dict[str, Any]:
        """
        Analyze impact of changes across the program.

        Returns impact assessment and mitigation options.
        """
        self.logger.info(f"Analyzing change impact for program: {program_id}")

        program = self.program_store.get(tenant_id, program_id)
        if not program:
            raise ValueError(f"Program not found: {program_id}")

        change_type = change.get("type", "scope")
        affected_project = change.get("project_id")
        change_details = change.get("details", {})

        # Get dependencies for affected project
        dependencies = await self._get_project_dependencies(program_id, affected_project)  # type: ignore

        # Analyze cascading effects
        cascading_effects = await self._analyze_cascading_effects(
            affected_project, dependencies, change_details  # type: ignore
        )

        # Calculate schedule impact
        schedule_impact = await self._calculate_schedule_impact(cascading_effects, change_details)

        # Calculate cost impact
        cost_impact = await self._calculate_cost_impact(cascading_effects, change_details)

        # Generate mitigation options
        mitigation_options = await self._generate_mitigation_options(
            cascading_effects, schedule_impact, cost_impact
        )

        return {
            "program_id": program_id,
            "change_type": change_type,
            "affected_project": affected_project,
            "cascading_effects": cascading_effects,
            "schedule_impact": schedule_impact,
            "cost_impact": cost_impact,
            "mitigation_options": mitigation_options,
            "recommendation": await self._select_best_mitigation(mitigation_options),
        }

    async def _get_program_health(self, program_id: str, *, tenant_id: str) -> dict[str, Any]:
        """
        Calculate composite program health score.

        Returns health metrics and recommendations.
        """
        self.logger.info(f"Calculating program health for: {program_id}")

        program = self.program_store.get(tenant_id, program_id)
        if not program:
            raise ValueError(f"Program not found: {program_id}")

        constituent_projects = program.get("constituent_projects", [])

        # Gather health metrics from domain agents
        schedule_health = await self._get_schedule_health(constituent_projects)
        budget_health = await self._get_budget_health(constituent_projects)
        risk_health = await self._get_risk_health(constituent_projects)
        quality_health = await self._get_quality_health(constituent_projects)
        resource_health = await self._get_resource_health(constituent_projects)

        # Calculate weighted composite score
        composite_score = (
            schedule_health * self.health_score_weights["schedule"]
            + budget_health * self.health_score_weights["budget"]
            + risk_health * self.health_score_weights["risk"]
            + quality_health * self.health_score_weights["quality"]
            + resource_health * self.health_score_weights["resource"]
        )

        benefit_metrics = await self._compute_benefit_realization_metrics(
            program_id, constituent_projects
        )
        external_signals = await self._collect_external_health_signals(
            program_id, constituent_projects
        )
        predicted = await self._predict_program_health(
            {
                "schedule_variance": 1 - schedule_health,
                "cost_variance": 1 - budget_health,
                "risk_indicator": 1 - risk_health,
                "benefit_realization": benefit_metrics.get("realization_rate", 0),
                "external_health": external_signals.get("health_index", 0.0),
                "dependency_load": external_signals.get("dependency_load", 0.0),
            }
        )
        if predicted.get("score") is not None:
            composite_score = float(predicted["score"])

        # Determine health status
        health_status = await self._determine_health_status(composite_score)

        # Identify primary concerns
        concerns = await self._identify_health_concerns(
            schedule_health, budget_health, risk_health, quality_health, resource_health
        )

        health_payload = {
            "program_id": program_id,
            "composite_score": composite_score,
            "health_status": health_status,
            "metrics": {
                "schedule": schedule_health,
                "budget": budget_health,
                "risk": risk_health,
                "quality": quality_health,
                "resource": resource_health,
            },
            "benefit_metrics": benefit_metrics,
            "prediction": predicted,
            "external_signals": external_signals,
            "concerns": concerns,
            "recommendations": await self._generate_health_recommendations(
                composite_score, concerns
            ),
            "narrative": await self._generate_program_narrative(
                program,
                schedule_health=schedule_health,
                budget_health=budget_health,
                risk_health=risk_health,
                quality_health=quality_health,
                resource_health=resource_health,
                benefit_metrics=benefit_metrics,
            ),
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.db_service:
            await self.db_service.store("program_health", program_id, health_payload)
            await self.db_service.store(
                "program_analytics",
                program_id,
                {
                    "program_id": program_id,
                    "health_status": health_status,
                    "composite_score": composite_score,
                },
            )

        await self.event_bus.publish(
            "program.health.updated",
            {
                "program_id": program_id,
                "tenant_id": tenant_id,
                "health": health_payload,
            },
        )

        await self._publish_program_status_update(
            program_id,
            tenant_id=tenant_id,
            correlation_id=str(uuid.uuid4()),
            status_type="health",
            payload={
                "health_score": composite_score,
                "health_status": health_status,
                "concerns": concerns,
            },
        )

        return health_payload

    async def _get_program(self, program_id: str, *, tenant_id: str) -> dict[str, Any]:
        """Retrieve a program by ID."""
        program = self.program_store.get(tenant_id, program_id)
        if not program:
            raise ValueError(f"Program not found: {program_id}")
        return program  # type: ignore

    # Helper methods

    async def _generate_program_id(self) -> str:
        """Generate unique program ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"PROG-{timestamp}"

    async def _publish_program_created(
        self, program: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> None:
        event = ProgramCreatedEvent(
            event_name="program.created",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "program_id": program.get("program_id", ""),
                "name": program.get("name", ""),
                "portfolio_id": program.get("portfolio_id", "unknown"),
                "created_at": datetime.fromisoformat(program.get("created_at")),
                "owner": program.get("created_by", "unknown"),
            },
        )
        await self.event_bus.publish("program.created", event.model_dump())

    async def _publish_program_roadmap_updated(
        self, roadmap: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> None:
        event = ProgramRoadmapUpdatedEvent(
            event_name="program.roadmap.updated",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "program_id": roadmap.get("program_id", ""),
                "roadmap_id": roadmap.get("program_id", ""),
                "updated_at": datetime.fromisoformat(roadmap.get("generated_at")),
                "milestone_count": len(roadmap.get("milestones", [])),
            },
        )
        await self.event_bus.publish("program.roadmap.updated", event.model_dump())

    async def _publish_program_status_update(
        self,
        program_id: str,
        *,
        tenant_id: str,
        correlation_id: str,
        status_type: str,
        payload: dict[str, Any],
    ) -> None:
        status_payload = {
            "program_id": program_id,
            "status_type": status_type,
            "payload": payload,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.db_service:
            await self.db_service.store(
                "program_status_updates",
                f"{program_id}:{status_type}:{uuid.uuid4().hex}",
                status_payload,
            )
        await self.event_bus.publish(
            "program.status.updated",
            {
                "program_id": program_id,
                "tenant_id": tenant_id,
                "status": status_payload,
                "correlation_id": correlation_id,
            },
        )

    async def _get_project_schedules(self, project_ids: list[str]) -> dict[str, Any]:
        """Query project schedules from Schedule & Planning Agent."""
        if self.schedule_agent and project_ids:
            schedules = {}
            for project_id in project_ids:
                schedule_id = self.schedule_ids.get(project_id)
                if schedule_id:
                    response = await self.schedule_agent.process(
                        {"action": "get_schedule", "schedule_id": schedule_id}
                    )
                    schedules[project_id] = {
                        "start": response.get("start_date") or response.get("start"),
                        "end": response.get("end_date") or response.get("end"),
                        "schedule_id": schedule_id,
                    }
            if schedules:
                return schedules
        return {pid: {"start": "2026-01-01", "end": "2026-12-31"} for pid in project_ids}

    async def _identify_dependencies(
        self,
        project_ids: list[str],
        *,
        schedules: dict[str, Any] | None = None,
        resource_allocations: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Identify inter-project dependencies and overlaps."""
        dependencies: list[dict[str, Any]] = []
        schedules = schedules or {}
        resource_allocations = resource_allocations or {}

        schedule_overlaps = self._detect_schedule_overlaps(project_ids, schedules)
        resource_overlaps = self._detect_resource_overlaps(project_ids, resource_allocations)
        overlap_pairs = {(item["project_a"], item["project_b"]) for item in schedule_overlaps}
        resource_overlap_map = {
            (item["project_a"], item["project_b"]): item for item in resource_overlaps
        }

        for overlap in schedule_overlaps:
            dependencies.append(
                {
                    "predecessor": overlap["project_a"],
                    "successor": overlap["project_b"],
                    "type": "schedule_overlap",
                    "overlap_days": overlap["overlap_days"],
                    "overlap_window": overlap["overlap_window"],
                }
            )

        for overlap in resource_overlaps:
            dependencies.append(
                {
                    "predecessor": overlap["project_a"],
                    "successor": overlap["project_b"],
                    "type": "shared_resource",
                    "shared_resources": overlap["shared_resources"],
                    "overlap_score": overlap["overlap_score"],
                }
            )

        for project_a, project_b in combinations(project_ids, 2):
            if (project_a, project_b) not in overlap_pairs and (project_b, project_a) not in overlap_pairs:
                continue
            resource_overlap = (
                resource_overlap_map.get((project_a, project_b))
                or resource_overlap_map.get((project_b, project_a))
            )
            if not resource_overlap:
                continue
            schedule_a = schedules.get(project_a, {})
            schedule_b = schedules.get(project_b, {})
            start_a = self._parse_date(schedule_a.get("start"))
            end_a = self._parse_date(schedule_a.get("end"))
            start_b = self._parse_date(schedule_b.get("start"))
            end_b = self._parse_date(schedule_b.get("end"))
            if not (start_a and end_a and start_b and end_b):
                continue
            if start_a <= end_b and start_b <= end_a:
                dependencies.append(
                    {
                        "predecessor": project_a,
                        "successor": project_b,
                        "type": "resource_contention",
                        "shared_resources": resource_overlap.get("shared_resources", []),
                        "overlap_window": {
                            "start": max(start_a, start_b).date().isoformat(),
                            "end": min(end_a, end_b).date().isoformat(),
                        },
                    }
                )
            else:
                if end_a < start_b:
                    dependencies.append(
                        {
                            "predecessor": project_a,
                            "successor": project_b,
                            "type": "resource_sequence",
                            "lag_days": (start_b - end_a).days,
                            "shared_resources": resource_overlap.get("shared_resources", []),
                        }
                    )
                elif end_b < start_a:
                    dependencies.append(
                        {
                            "predecessor": project_b,
                            "successor": project_a,
                            "type": "resource_sequence",
                            "lag_days": (start_a - end_b).days,
                            "shared_resources": resource_overlap.get("shared_resources", []),
                        }
                    )

        for idx in range(len(project_ids) - 1):
            predecessor = project_ids[idx]
            successor = project_ids[idx + 1]
            dependencies.append(
                {
                    "predecessor": predecessor,
                    "successor": successor,
                    "type": self.dependency_types[idx % len(self.dependency_types)],
                }
            )

        return dependencies

    async def _calculate_program_critical_path(
        self, schedules: dict[str, Any], dependencies: list[dict[str, Any]]
    ) -> list[str]:
        """Calculate critical path across the program."""
        return self._calculate_critical_path(schedules, dependencies)

    async def _generate_program_milestones(
        self, schedules: dict[str, Any], dependencies: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate program-level milestones."""
        milestones = []
        for project_id, schedule in schedules.items():
            start = schedule.get("start")
            end = schedule.get("end")
            if start:
                milestones.append(
                    {"project_id": project_id, "milestone": "Start", "date": start}
                )
            if end:
                milestones.append(
                    {"project_id": project_id, "milestone": "Finish", "date": end}
                )
        return milestones

    async def _calculate_program_start(self, schedules: dict[str, Any]) -> str:
        """Calculate program start date."""
        # Baseline
        return datetime.now(timezone.utc).isoformat()

    async def _calculate_program_end(self, schedules: dict[str, Any]) -> str:
        """Calculate program end date."""
        # Baseline
        return datetime.now(timezone.utc).isoformat()

    def _parse_date(self, date_value: str | None) -> datetime | None:
        if not date_value:
            return None
        try:
            return datetime.fromisoformat(date_value)
        except ValueError:
            try:
                return datetime.strptime(date_value, "%Y-%m-%d")
            except ValueError:
                return None

    def _detect_schedule_overlaps(
        self, project_ids: list[str], schedules: dict[str, Any]
    ) -> list[dict[str, Any]]:
        overlaps: list[dict[str, Any]] = []
        for project_a, project_b in combinations(project_ids, 2):
            schedule_a = schedules.get(project_a, {})
            schedule_b = schedules.get(project_b, {})
            start_a = self._parse_date(schedule_a.get("start"))
            end_a = self._parse_date(schedule_a.get("end"))
            start_b = self._parse_date(schedule_b.get("start"))
            end_b = self._parse_date(schedule_b.get("end"))
            if not (start_a and end_a and start_b and end_b):
                continue
            latest_start = max(start_a, start_b)
            earliest_end = min(end_a, end_b)
            if latest_start <= earliest_end:
                overlap_days = (earliest_end - latest_start).days + 1
                overlaps.append(
                    {
                        "project_a": project_a,
                        "project_b": project_b,
                        "overlap_days": overlap_days,
                        "overlap_window": {
                            "start": latest_start.date().isoformat(),
                            "end": earliest_end.date().isoformat(),
                        },
                    }
                )
        return overlaps

    def _detect_resource_overlaps(
        self, project_ids: list[str], allocations: dict[str, Any]
    ) -> list[dict[str, Any]]:
        overlaps: list[dict[str, Any]] = []
        resources_by_project = {
            project_id: set(self._flatten_resource_allocations(allocations.get(project_id, {})))
            for project_id in project_ids
        }
        for project_a, project_b in combinations(project_ids, 2):
            resources_a = resources_by_project.get(project_a, set())
            resources_b = resources_by_project.get(project_b, set())
            shared = resources_a.intersection(resources_b)
            if shared:
                overlap_score = len(shared) / max(1, len(resources_a | resources_b))
                overlaps.append(
                    {
                        "project_a": project_a,
                        "project_b": project_b,
                        "shared_resources": sorted(shared),
                        "overlap_score": round(overlap_score, 3),
                    }
                )
        return overlaps

    def _flatten_resource_allocations(self, allocation: Any) -> list[str]:
        if isinstance(allocation, dict):
            resources = []
            for key, value in allocation.items():
                if isinstance(value, (list, tuple, set)):
                    resources.extend(str(item) for item in value)
                elif isinstance(value, dict):
                    resources.append(str(value.get("resource_id") or value.get("name") or key))
                else:
                    resources.append(str(key))
            return resources
        if isinstance(allocation, list):
            resources = []
            for item in allocation:
                if isinstance(item, dict):
                    resources.append(str(item.get("resource_id") or item.get("name") or item.get("role")))
                else:
                    resources.append(str(item))
            return resources
        return [str(allocation)] if allocation else []

    async def _analyze_dependency_graph(self, dependencies: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze dependency graph structure."""
        graph, nodes = self._build_dependency_graph(dependencies)
        in_degree = {node: 0 for node in nodes}
        out_degree = {node: 0 for node in nodes}
        for node, neighbors in graph.items():
            for neighbor in neighbors:
                in_degree[neighbor] = in_degree.get(neighbor, 0) + 1
                out_degree[node] = out_degree.get(node, 0) + 1
        return {
            "node_count": len(nodes),
            "edge_count": sum(len(edges) for edges in graph.values()),
            "adjacency_list": graph,
            "in_degree": in_degree,
            "out_degree": out_degree,
        }

    async def _identify_critical_dependencies(
        self, dependencies: list[dict[str, Any]], graph_analysis: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify critical dependencies."""
        # Baseline
        return []

    async def _detect_circular_dependencies(
        self, dependencies: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Detect circular dependencies."""
        graph, nodes = self._build_dependency_graph(dependencies)
        visited: set[str] = set()
        visiting: set[str] = set()
        stack: list[str] = []
        cycles: list[dict[str, Any]] = []

        def dfs(node: str) -> None:
            visiting.add(node)
            stack.append(node)
            for neighbor in graph.get(node, []):
                if neighbor in visiting:
                    cycle_start = stack.index(neighbor)
                    cycles.append({"cycle": stack[cycle_start:] + [neighbor]})
                elif neighbor not in visited:
                    dfs(neighbor)
            visiting.remove(node)
            visited.add(node)
            stack.pop()

        for node in nodes:
            if node not in visited:
                dfs(node)

        return cycles

    async def _generate_dependency_recommendations(
        self, dependencies: list[dict[str, Any]], circular_deps: list[dict[str, Any]]
    ) -> list[str]:
        """Generate recommendations for dependency management."""
        recommendations = []
        if circular_deps:
            recommendations.append("Resolve circular dependencies to avoid deadlocks")
        return recommendations

    async def _get_project_benefits(self, project_ids: list[str]) -> dict[str, Any]:
        """Query benefits from each project."""
        if project_ids:
            program_data = await self._ingest_external_program_data()
            if program_data.get("benefits"):
                return program_data["benefits"]
        if self.business_case_agent and project_ids:
            benefits = {}
            for project_id in project_ids:
                business_case_id = self.business_case_ids.get(project_id)
                if business_case_id:
                    response = await self.business_case_agent.process(
                        {"action": "get_business_case", "business_case_id": business_case_id}
                    )
                    benefit_breakdown = response.get("benefit_breakdown", {}) or response.get(
                        "benefits", {}
                    )
                    benefits[project_id] = {
                        "total_benefits": benefit_breakdown.get("total_benefits", 0),
                        "total_costs": response.get("total_cost", response.get("total_costs", 0)),
                        "benefit_breakdown": benefit_breakdown,
                    }
            if benefits:
                return benefits
        return {pid: {"total_benefits": 100000, "total_costs": 50000} for pid in project_ids}

    async def _adjust_for_overlaps(self, project_benefits: dict[str, Any]) -> float:
        """Adjust benefits for overlaps to avoid double-counting."""
        total = sum(pb.get("total_benefits", 0) for pb in project_benefits.values())
        if total <= 0:
            return 0.0

        overlap_groups: dict[str, list[str]] = {}
        for project_id, benefit in project_benefits.items():
            breakdown = benefit.get("benefit_breakdown") or benefit.get("benefits") or {}
            overlap_key = (
                breakdown.get("overlap_key")
                or breakdown.get("initiative")
                or benefit.get("overlap_key")
                or benefit.get("initiative")
            )
            if overlap_key:
                overlap_groups.setdefault(str(overlap_key), []).append(project_id)

        if not overlap_groups:
            return total

        penalty = 0.0
        for projects in overlap_groups.values():
            if len(projects) > 1:
                penalty += min(0.25, 0.05 * (len(projects) - 1))

        penalty = min(0.35, penalty)
        return total * (1 - penalty)

    async def _categorize_benefits(self, project_benefits: dict[str, Any]) -> dict[str, float]:
        """Categorize benefits by type."""
        categories = {
            "revenue_increase": 0.0,
            "cost_savings": 0.0,
            "risk_reduction": 0.0,
            "efficiency_gains": 0.0,
        }
        for benefit in project_benefits.values():
            breakdown = benefit.get("benefit_breakdown") or benefit.get("benefits") or {}
            categories["revenue_increase"] += breakdown.get("revenue_increase", 0)
            categories["cost_savings"] += breakdown.get("cost_savings", 0)
            categories["risk_reduction"] += breakdown.get("risk_reduction", 0)
            categories["efficiency_gains"] += breakdown.get("efficiency_gains", 0)
        return categories

    async def _generate_benefit_timeline(
        self, project_benefits: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate benefit realization timeline."""
        # Baseline
        return []

    async def _get_resource_allocations(self, project_ids: list[str]) -> dict[str, Any]:
        """Query resource allocations from Resource Management Agent."""
        if self.resource_agent and project_ids:
            allocations = {}
            for project_id in project_ids:
                response = await self.resource_agent.process(
                    {"action": "get_utilization", "project_id": project_id}
                )
                allocations[project_id] = response.get("allocations", response)
            if allocations:
                return allocations
        return {}

    async def _identify_resource_conflicts(
        self, allocations: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify resource allocation conflicts."""
        resource_usage: dict[str, list[str]] = {}
        for project_id, allocation in allocations.items():
            for resource in self._flatten_resource_allocations(allocation):
                resource_usage.setdefault(resource, []).append(project_id)

        conflicts = []
        for resource, projects in resource_usage.items():
            if len(projects) > 1:
                conflicts.append(
                    {
                        "resource": resource,
                        "projects": projects,
                        "severity": "high" if len(projects) >= 3 else "medium",
                    }
                )
        return conflicts

    async def _optimize_resource_allocation(
        self, allocations: dict[str, Any], conflicts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate resource optimization recommendations."""
        recommendations = []
        for conflict in conflicts:
            projects = conflict.get("projects", [])
            recommendations.append(
                {
                    "resource": conflict.get("resource"),
                    "action": "stagger_assignments",
                    "projects": projects,
                    "rationale": "Reduce simultaneous contention for shared resources",
                }
            )
            recommendations.append(
                {
                    "resource": conflict.get("resource"),
                    "action": "augment_capacity",
                    "projects": projects,
                    "rationale": "Consider adding temporary capacity or contractors",
                }
            )
        if not conflicts:
            recommendations.append(
                {
                    "action": "maintain_allocation",
                    "rationale": "Resource usage appears balanced across projects",
                }
            )
        return recommendations

    async def _calculate_program_utilization(self, allocations: dict[str, Any]) -> float:
        """Calculate average utilization across program."""
        if not allocations:
            return 0.0
        total_resources = 0
        shared_resources = 0
        resource_usage: dict[str, int] = {}
        for allocation in allocations.values():
            resources = self._flatten_resource_allocations(allocation)
            total_resources += len(resources)
            for resource in resources:
                resource_usage[resource] = resource_usage.get(resource, 0) + 1
        shared_resources = sum(1 for count in resource_usage.values() if count > 1)
        utilization = shared_resources / max(1, len(resource_usage))
        return round(min(1.0, 0.5 + utilization * 0.5), 2)

    async def _identify_shared_resources(self, allocations: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify resources shared across multiple projects."""
        resource_usage: dict[str, list[str]] = {}
        for project_id, allocation in allocations.items():
            for resource in self._flatten_resource_allocations(allocation):
                resource_usage.setdefault(resource, []).append(project_id)

        return [
            {"resource": resource, "projects": projects}
            for resource, projects in resource_usage.items()
            if len(projects) > 1
        ]

    async def _get_project_details(self, project_ids: list[str]) -> dict[str, Any]:
        """Get detailed project information."""
        if self.project_definition_agent and project_ids:
            details = {}
            for project_id in project_ids:
                response = await self.project_definition_agent.process(
                    {"action": "get_charter", "project_id": project_id}
                )
                details[project_id] = response
            if details:
                return details
        external = await self._ingest_external_program_data()
        if external.get("projects"):
            return external["projects"]
        return {pid: {"name": pid, "description": ""} for pid in project_ids}

    async def analyze_synergies(self, project_details: dict[str, Any]) -> dict[str, Any]:
        """Analyze synergies using Azure Cognitive Services Text Analytics."""
        documents = []
        project_ids = list(project_details.keys())
        for project_id in project_ids:
            detail = project_details.get(project_id, {})
            description = " ".join(
                str(value)
                for value in [
                    detail.get("name"),
                    detail.get("description"),
                    " ".join(detail.get("scope", []) or []),
                    " ".join(detail.get("resources", []) or []),
                ]
                if value
            )
            documents.append(description or project_id)

        key_phrases: list[set[str]] = []
        if self.text_analytics_client is None:
            endpoint = os.getenv("TEXT_ANALYTICS_ENDPOINT")
            key = os.getenv("TEXT_ANALYTICS_KEY")
            if endpoint and key:
                from azure.ai.textanalytics import TextAnalyticsClient
                from azure.core.credentials import AzureKeyCredential

                self.text_analytics_client = TextAnalyticsClient(
                    endpoint=endpoint, credential=AzureKeyCredential(key)
                )
        if self.text_analytics_client:
            results = self.text_analytics_client.extract_key_phrases(documents)
            for result in results:
                if not result.is_error:
                    key_phrases.append(set(result.key_phrases))
                else:
                    key_phrases.append(set())
        else:
            for doc in documents:
                tokens = {token for token in doc.lower().split() if token.isalpha()}
                key_phrases.append(tokens)

        shared_components = []
        vendor_synergies = []
        infrastructure_synergies = []
        for (idx_a, idx_b) in combinations(range(len(project_ids)), 2):
            overlap = key_phrases[idx_a].intersection(key_phrases[idx_b])
            union = key_phrases[idx_a].union(key_phrases[idx_b])
            similarity = len(overlap) / len(union) if union else 0
            if similarity >= self.synergy_detection_threshold:
                shared_components.append(
                    {
                        "projects": [project_ids[idx_a], project_ids[idx_b]],
                        "similarity": similarity,
                        "overlap_terms": sorted(overlap),
                    }
                )
                vendor_synergies.append(
                    {
                        "projects": [project_ids[idx_a], project_ids[idx_b]],
                        "opportunity": "Consolidate vendors",
                        "similarity": similarity,
                    }
                )
                infrastructure_synergies.append(
                    {
                        "projects": [project_ids[idx_a], project_ids[idx_b]],
                        "opportunity": "Share infrastructure",
                        "similarity": similarity,
                    }
                )

        return {
            "shared_components": shared_components,
            "vendor_consolidation": vendor_synergies,
            "infrastructure_synergies": infrastructure_synergies,
        }

    async def _calculate_synergy_savings(
        self,
        shared_components: list[dict[str, Any]],
        vendor_synergies: list[dict[str, Any]],
        infrastructure_synergies: list[dict[str, Any]],
        project_costs: dict[str, float],
    ) -> dict[str, float]:
        """Calculate potential cost savings from synergies."""
        def _pair_cost(pair: dict[str, Any]) -> float:
            projects = pair.get("projects", [])
            return sum(project_costs.get(project, 0) for project in projects)

        shared = sum(_pair_cost(item) * 0.06 for item in shared_components)
        vendor = sum(_pair_cost(item) * 0.04 for item in vendor_synergies)
        infrastructure = sum(_pair_cost(item) * 0.03 for item in infrastructure_synergies)
        return {
            "shared_components": shared,
            "vendor_consolidation": vendor,
            "infrastructure_sharing": infrastructure,
            "total": shared + vendor + infrastructure,
        }

    async def _generate_synergy_recommendations(self, synergies: dict[str, Any]) -> list[str]:
        """Generate recommendations for synergy realization."""
        recommendations = []
        if synergies.get("shared_components"):
            recommendations.append("Consolidate shared components into reusable modules")
        if synergies.get("vendor_consolidation"):
            recommendations.append("Negotiate combined vendor contracts for volume discounts")
        if synergies.get("optimization", {}).get("priority_actions"):
            recommendations.append("Execute prioritized synergy actions to maximize savings")
        return recommendations

    async def _get_project_dependencies(
        self, program_id: str, project_id: str
    ) -> list[dict[str, Any]]:
        """Get dependencies for a specific project."""
        stored = await self._get_dependency_graph(program_id)
        dependencies = stored.get("dependencies", [])
        return [dep for dep in dependencies if project_id in dep.values()]

    async def _analyze_cascading_effects(
        self, project_id: str, dependencies: list[dict[str, Any]], change_details: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Analyze cascading effects of a change."""
        cascading_effects = []
        delay_days = int(change_details.get("delay_days", 5))
        cost_delta = float(change_details.get("cost_delta", 0))

        for dependency in dependencies:
            predecessor = dependency.get("predecessor")
            successor = dependency.get("successor")
            if predecessor == project_id:
                impacted = successor
                direction = "downstream"
            elif successor == project_id:
                impacted = predecessor
                direction = "upstream"
            else:
                continue

            cascading_effects.append(
                {
                    "impacted_project_id": impacted,
                    "direction": direction,
                    "dependency_type": dependency.get("type"),
                    "schedule_delay_days": delay_days,
                    "cost_delta": cost_delta,
                    "shared_resources": dependency.get("shared_resources", []),
                }
            )

        return cascading_effects

    async def _calculate_schedule_impact(
        self, cascading_effects: list[dict[str, Any]], change_details: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate schedule impact from changes."""
        # Baseline
        return {"delay_days": 0, "affected_milestones": []}

    async def _calculate_cost_impact(
        self, cascading_effects: list[dict[str, Any]], change_details: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate cost impact from changes."""
        # Baseline
        return {"additional_cost": 0, "affected_budgets": []}

    async def _generate_mitigation_options(
        self,
        cascading_effects: list[dict[str, Any]],
        schedule_impact: dict[str, Any],
        cost_impact: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate mitigation options."""
        # Baseline
        return [
            {
                "option": "Parallelize dependent tasks",
                "schedule_reduction": "5 days",
                "cost": "$10,000",
            },
            {
                "option": "Add resources to critical path",
                "schedule_reduction": "10 days",
                "cost": "$25,000",
            },
            {
                "option": "Accept delay and adjust roadmap",
                "schedule_reduction": "0 days",
                "cost": "$0",
            },
        ]

    async def _select_best_mitigation(self, options: list[dict[str, Any]]) -> str:
        """Select the best mitigation option."""
        if not options:
            return "No mitigation needed"

        def _parse_days(value: str) -> float:
            digits = "".join(ch for ch in value if ch.isdigit() or ch == ".")
            return float(digits) if digits else 0.0

        def _parse_cost(value: str) -> float:
            digits = "".join(ch for ch in value if ch.isdigit() or ch == ".")
            return float(digits) if digits else 0.0

        scored = []
        for option in options:
            reduction = _parse_days(str(option.get("schedule_reduction", "0")))
            cost = _parse_cost(str(option.get("cost", "0")))
            score = reduction - (cost / 10000)
            scored.append((score, option))

        best_option = max(scored, key=lambda item: item[0])[1]
        return best_option.get("option", options[0].get("option", "No mitigation needed"))

    async def _get_schedule_health(self, project_ids: list[str]) -> float:
        """Get schedule health across projects."""
        action = self.health_actions.get("schedule")
        if self.schedule_agent and action and project_ids:
            response = await self.schedule_agent.process(
                {"action": action, "project_ids": project_ids}
            )
            return float(response.get("schedule_health", 0.85))
        return 0.85

    async def _get_budget_health(self, project_ids: list[str]) -> float:
        """Get budget health across projects."""
        action = self.health_actions.get("budget")
        if self.financial_agent and action and project_ids:
            response = await self.financial_agent.process(
                {"action": action, "project_ids": project_ids}
            )
            return float(response.get("budget_health", 0.80))
        return 0.80

    async def _get_risk_health(self, project_ids: list[str]) -> float:
        """Get risk health across projects."""
        action = self.health_actions.get("risk")
        if self.risk_agent and action and project_ids:
            response = await self.risk_agent.process(
                {"action": action, "project_ids": project_ids}
            )
            return float(response.get("risk_health", 0.75))
        return 0.75

    async def _get_quality_health(self, project_ids: list[str]) -> float:
        """Get quality health across projects."""
        action = self.health_actions.get("quality")
        if self.quality_agent and action and project_ids:
            response = await self.quality_agent.process(
                {"action": action, "project_ids": project_ids}
            )
            return float(response.get("quality_health", 0.90))
        return 0.90

    async def _get_resource_health(self, project_ids: list[str]) -> float:
        """Get resource health across projects."""
        action = self.health_actions.get("resource")
        if self.resource_agent and action and project_ids:
            response = await self.resource_agent.process(
                {"action": action, "project_ids": project_ids}
            )
            return float(response.get("resource_health", 0.70))
        return 0.70

    async def _determine_health_status(self, composite_score: float) -> str:
        """Determine health status from composite score."""
        if composite_score >= 0.85:
            return "Healthy"
        elif composite_score >= 0.70:
            return "At Risk"
        else:
            return "Critical"

    async def _identify_health_concerns(
        self, schedule: float, budget: float, risk: float, quality: float, resource: float
    ) -> list[str]:
        """Identify primary health concerns."""
        concerns = []
        if schedule < 0.70:
            concerns.append("Schedule variance exceeds acceptable thresholds")
        if budget < 0.70:
            concerns.append("Budget overruns across multiple projects")
        if risk < 0.70:
            concerns.append("High-priority risks not adequately mitigated")
        if quality < 0.70:
            concerns.append("Quality metrics below standards")
        if resource < 0.70:
            concerns.append("Resource over-allocation and bottlenecks")
        return concerns

    async def _generate_health_recommendations(
        self, composite_score: float, concerns: list[str]
    ) -> list[str]:
        """Generate health improvement recommendations."""
        recommendations = []
        for concern in concerns:
            if "schedule" in concern.lower():
                recommendations.append("Review and optimize critical path across projects")
            if "budget" in concern.lower():
                recommendations.append("Conduct cost review and identify savings opportunities")
            if "risk" in concern.lower():
                recommendations.append("Escalate high-priority risks to steering committee")
            if "quality" in concern.lower():
                recommendations.append("Implement additional quality controls and testing")
            if "resource" in concern.lower():
                recommendations.append("Rebalance resource allocation across program")
        return recommendations

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Program Management Agent...")
        if self.service_bus_task:
            self.service_bus_task.cancel()
        if self.service_bus_receiver:
            await self.service_bus_receiver.close()
        if self.service_bus_client:
            await self.service_bus_client.close()
        if self.cosmos_client:
            await self.cosmos_client.close()
        if self.ml_workspace and hasattr(self.ml_workspace, "close"):
            self.ml_workspace.close()
        if self.planview_connector and hasattr(self.planview_connector, "close"):
            self.planview_connector.close()
        if self.clarity_connector and hasattr(self.clarity_connector, "close"):
            self.clarity_connector.close()

    def _build_dependency_graph(
        self, dependencies: list[dict[str, Any]]
    ) -> tuple[dict[str, list[str]], set[str]]:
        graph: dict[str, list[str]] = {}
        nodes: set[str] = set()
        for dependency in dependencies:
            edges = self._extract_dependency_edges(dependency)
            for predecessor, successor in edges:
                nodes.update([predecessor, successor])
                graph.setdefault(predecessor, []).append(successor)
        for node in nodes:
            graph.setdefault(node, [])
        return graph, nodes

    def _extract_dependency_edges(self, dependency: dict[str, Any]) -> list[tuple[str, str]]:
        if dependency.get("predecessor") and dependency.get("successor"):
            return [(dependency["predecessor"], dependency["successor"])]
        if dependency.get("from") and dependency.get("to"):
            return [(dependency["from"], dependency["to"])]
        if dependency.get("source") and dependency.get("target"):
            return [(dependency["source"], dependency["target"])]
        if dependency.get("project_id") and dependency.get("depends_on"):
            depends_on = dependency["depends_on"]
            if isinstance(depends_on, list):
                return [(dep, dependency["project_id"]) for dep in depends_on]
            return [(depends_on, dependency["project_id"])]
        return []

    def _calculate_critical_path(
        self, schedules: dict[str, Any], dependencies: list[dict[str, Any]]
    ) -> list[str]:
        graph, nodes = self._build_dependency_graph(dependencies)
        if not nodes:
            nodes = set(schedules.keys())
            for node in nodes:
                graph.setdefault(node, [])

        durations: dict[str, float] = {}
        for node in nodes:
            schedule = schedules.get(node, {})
            start = schedule.get("start")
            end = schedule.get("end")
            duration = 0.0
            try:
                if start and end:
                    duration = (
                        datetime.fromisoformat(end) - datetime.fromisoformat(start)
                    ).days
            except (TypeError, ValueError):
                duration = 0.0
            durations[node] = max(duration, 0.0)

        in_degree = {node: 0 for node in nodes}
        for node, neighbors in graph.items():
            for neighbor in neighbors:
                in_degree[neighbor] = in_degree.get(neighbor, 0) + 1

        queue = [node for node in nodes if in_degree.get(node, 0) == 0]
        topo_order = []
        while queue:
            current = queue.pop(0)
            topo_order.append(current)
            for neighbor in graph.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(topo_order) != len(nodes):
            return []

        earliest_finish = {node: durations.get(node, 0.0) for node in nodes}
        predecessor: dict[str, str | None] = {node: None for node in nodes}

        for node in topo_order:
            for neighbor in graph.get(node, []):
                candidate_finish = earliest_finish[node] + durations.get(neighbor, 0.0)
                if candidate_finish > earliest_finish.get(neighbor, 0.0):
                    earliest_finish[neighbor] = candidate_finish
                    predecessor[neighbor] = node

        if not earliest_finish:
            return []

        end_node = max(earliest_finish, key=earliest_finish.get)
        path = []
        while end_node is not None:
            path.append(end_node)
            end_node = predecessor.get(end_node)

        return list(reversed(path))

    async def _initialize_cosmos(self) -> None:
        if self.dependency_container and self.mapping_container:
            return
        endpoint = os.getenv("COSMOS_ENDPOINT")
        key = os.getenv("COSMOS_KEY")
        if not endpoint or not key:
            return
        from azure.cosmos import PartitionKey
        from azure.cosmos.aio import CosmosClient

        self.cosmos_client = CosmosClient(endpoint, credential=key)
        database_name = self.config.get("cosmos_database", "ppm-programs") if self.config else None
        self.cosmos_database = await self.cosmos_client.create_database_if_not_exists(
            id=database_name or "ppm-programs"
        )
        indexing_policy = {
            "indexingMode": "consistent",
            "automatic": True,
            "includedPaths": [
                {"path": "/program_id/?"},
                {"path": "/tenant_id/?"},
                {"path": "/dependencies/*"},
                {"path": "/*"},
            ],
            "excludedPaths": [{"path": "/\"_etag\"/?"}],
        }
        self.dependency_container = await self.cosmos_database.create_container_if_not_exists(
            id="program_dependencies",
            partition_key=PartitionKey(path="/program_id"),
            indexing_policy=indexing_policy,
        )
        self.mapping_container = await self.cosmos_database.create_container_if_not_exists(
            id="program_mappings",
            partition_key=PartitionKey(path="/system"),
        )

    async def _initialize_ml(self) -> None:
        if self.ml_workspace or self.health_model:
            return
        ml_config = self.config.get("ml_config", {}) if self.config else {}
        if not ml_config.get("enabled"):
            return
        from azureml.core import Model, Workspace

        if ml_config.get("workspace_config"):
            self.ml_workspace = Workspace.from_config(path=ml_config["workspace_config"])
        else:
            self.ml_workspace = Workspace(
                subscription_id=ml_config.get("subscription_id"),
                resource_group=ml_config.get("resource_group"),
                workspace_name=ml_config.get("workspace_name"),
            )
        model_name = ml_config.get("model_name", "program_health_model")
        try:
            self.health_model = Model(self.ml_workspace, name=model_name)
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError):
            await self._train_health_model(model_name=model_name)

    async def _initialize_llm(self) -> None:
        if self.llm_client is None:
            llm_config = self.config.get("llm_config", {}) if self.config else {}
            provider = llm_config.get("provider") or (
                "azure_openai" if os.getenv("AZURE_OPENAI_ENDPOINT") else None
            )
            self.llm_client = LLMClient(provider=provider, config=llm_config)

    async def _initialize_integrations(self) -> None:
        if self.planview_connector is None:
            planview_config = self.config.get("planview_config") if self.config else None
            if planview_config:
                from integrations.connectors.planview.src.planview_connector import PlanviewConnector
                from integrations.connectors.sdk.src.base_connector import ConnectorConfig

                self.planview_connector = PlanviewConnector(
                    ConnectorConfig.from_dict(planview_config)
                )
        if self.clarity_connector is None:
            clarity_config = self.config.get("clarity_config") if self.config else None
            if clarity_config:
                from integrations.connectors.clarity.src.clarity_connector import ClarityConnector
                from integrations.connectors.sdk.src.base_connector import ConnectorConfig

                self.clarity_connector = ClarityConnector(
                    ConnectorConfig.from_dict(clarity_config)
                )
        self.jira_base_url = self.jira_base_url or os.getenv("JIRA_BASE_URL")
        self.jira_api_token = self.jira_api_token or os.getenv("JIRA_API_TOKEN")
        self.azure_devops_org_url = self.azure_devops_org_url or os.getenv("AZDO_ORG_URL")
        self.azure_devops_pat = self.azure_devops_pat or os.getenv("AZDO_PAT")

    async def _subscribe_to_program_events(self) -> None:
        if self.service_bus_client:
            return
        connection_string = os.getenv("SERVICE_BUS_CONNECTION_STRING")
        topic_name = os.getenv("SERVICE_BUS_TOPIC")
        subscription_name = os.getenv("SERVICE_BUS_SUBSCRIPTION")
        if not connection_string or not topic_name or not subscription_name:
            return
        from azure.servicebus.aio import ServiceBusClient

        self.service_bus_client = ServiceBusClient.from_connection_string(connection_string)
        self.service_bus_receiver = self.service_bus_client.get_subscription_receiver(
            topic_name=topic_name, subscription_name=subscription_name
        )
        self.service_bus_task = asyncio.create_task(self._listen_to_program_events())

    async def _listen_to_program_events(self) -> None:
        if not self.service_bus_receiver:
            return
        async with self.service_bus_receiver:
            async for message in self.service_bus_receiver:
                await self._handle_program_event(message)
                await self.service_bus_receiver.complete_message(message)

    async def _handle_program_event(self, message: Any) -> None:
        payload = getattr(message, "body", None)
        if hasattr(payload, "__iter__"):
            payload = "".join([part.decode("utf-8") for part in payload])
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {"raw": payload}
        if not isinstance(payload, dict):
            return
        program_id = payload.get("program_id")
        tenant_id = payload.get("tenant_id", "unknown")
        if not program_id:
            return
        program = self.program_store.get(tenant_id, program_id)
        if not program:
            return
        updates = payload.get("updates", {})
        program.update(updates)
        self.program_store.upsert(tenant_id, program_id, program)
        if self.db_service:
            await self.db_service.store("programs", program_id, program)
        if updates.get("dependencies"):
            await self._update_dependency_graph(
                program_id, updates["dependencies"], tenant_id=tenant_id
            )

    async def _create_dependency_graph(
        self, program_id: str, dependencies: list[dict[str, Any]], *, tenant_id: str
    ) -> dict[str, Any]:
        if not self.dependency_container:
            return {}
        item = {
            "id": program_id,
            "program_id": program_id,
            "tenant_id": tenant_id,
            "dependencies": dependencies,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.dependency_container.upsert_item(item)
        return item

    async def _update_dependency_graph(
        self, program_id: str, dependencies: list[dict[str, Any]], *, tenant_id: str
    ) -> dict[str, Any]:
        return await self._create_dependency_graph(program_id, dependencies, tenant_id=tenant_id)

    async def _upsert_dependency_graph(
        self, program_id: str, dependencies: list[dict[str, Any]], *, tenant_id: str
    ) -> None:
        if not self.dependency_container:
            return
        item = {
            "id": program_id,
            "program_id": program_id,
            "tenant_id": tenant_id,
            "dependencies": dependencies,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.dependency_container.upsert_item(item)

    async def _get_dependency_graph(self, program_id: str) -> dict[str, Any]:
        if not self.dependency_container:
            return {}
        try:
            return await self.dependency_container.read_item(
                item=program_id, partition_key=program_id
            )
        except (ConnectionError, TimeoutError, ValueError, KeyError, TypeError, RuntimeError, OSError):
            return {}

    async def _read_dependency_graph(self, program_id: str) -> dict[str, Any]:
        return await self._get_dependency_graph(program_id)

    async def _delete_dependency_graph(self, program_id: str) -> None:
        if not self.dependency_container:
            return
        await self.dependency_container.delete_item(item=program_id, partition_key=program_id)

    async def _list_dependency_graphs(self) -> list[dict[str, Any]]:
        if not self.dependency_container:
            return []
        query = "SELECT * FROM c"
        results = []
        async for item in self.dependency_container.query_items(query=query):
            results.append(item)
        return results

    async def _train_health_model(self, model_name: str) -> None:
        if not self.ml_workspace:
            return
        from azureml.core import Model

        model_path = Path(self.config.get("ml_model_path", "data/program_health_model.json"))
        training_data = await self._prepare_health_training_data()
        model_payload = {
            "weights": self.health_score_weights,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "training_data": training_data,
        }
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model_path.write_text(json.dumps(model_payload))
        self.health_model = Model.register(
            workspace=self.ml_workspace,
            model_path=str(model_path),
            model_name=model_name,
        )

    async def _predict_program_health(self, features: dict[str, float]) -> dict[str, Any]:
        if self.health_model and hasattr(self.health_model, "predict"):
            score = self.health_model.predict([features])[0]
            return {"score": score, "model": getattr(self.health_model, "name", "custom")}
        score = 1 - (
            0.35 * features.get("schedule_variance", 0)
            + 0.35 * features.get("cost_variance", 0)
            + 0.2 * features.get("risk_indicator", 0)
            + 0.1 * (1 - features.get("external_health", 0))
        )
        return {"score": max(min(score, 1.0), 0.0), "model": "baseline"}

    async def _compute_benefit_realization_metrics(
        self, program_id: str, project_ids: list[str]
    ) -> dict[str, Any]:
        if self.synapse_client:
            return await self.synapse_client.fetch_benefit_metrics(program_id)
        return {
            "realization_rate": 0.65,
            "benefits_realized": 125000,
            "benefits_target": 190000,
            "projects": project_ids,
        }

    async def _prepare_health_training_data(self) -> dict[str, Any]:
        external = await self._ingest_external_program_data()
        projects = external.get("projects", {})
        signals = []
        for project_id, payload in projects.items():
            signals.append(
                {
                    "project_id": project_id,
                    "schedule_variance": payload.get("schedule_variance", 0.1),
                    "cost_variance": payload.get("cost_variance", 0.1),
                    "risk_indicator": payload.get("risk_indicator", 0.2),
                    "health_score": payload.get("health_score", 0.8),
                }
            )
        return {"samples": signals, "source": "planview/clarity"}

    async def _collect_external_health_signals(
        self, program_id: str, project_ids: list[str]
    ) -> dict[str, Any]:
        external = await self._ingest_external_program_data()
        projects = external.get("projects", {})
        health_values = []
        dependency_load = 0.0
        for project_id in project_ids:
            project = projects.get(project_id, {})
            if project:
                health_values.append(project.get("health_score", 0.8))
                dependency_load += project.get("dependency_count", 0)
        if health_values:
            health_index = sum(health_values) / len(health_values)
        else:
            health_index = 0.8
        return {
            "program_id": program_id,
            "health_index": health_index,
            "dependency_load": dependency_load,
            "sources": ["planview", "clarity"],
        }

    async def _generate_program_narrative(
        self,
        program: dict[str, Any],
        *,
        schedule_health: float,
        budget_health: float,
        risk_health: float,
        quality_health: float,
        resource_health: float,
        benefit_metrics: dict[str, Any],
    ) -> str:
        if not self.llm_client:
            return "Narrative generation not configured."
        system_prompt = "You are a program management assistant summarizing program health."
        user_prompt = (
            f"Program: {program.get('name')}\n"
            f"Schedule health: {schedule_health:.2f}\n"
            f"Cost health: {budget_health:.2f}\n"
            f"Risk health: {risk_health:.2f}\n"
            f"Quality health: {quality_health:.2f}\n"
            f"Resource health: {resource_health:.2f}\n"
            f"Benefit realization rate: {benefit_metrics.get('realization_rate', 0):.2f}\n"
            "Provide a concise narrative summary of program status."
        )
        response = await self.llm_client.complete(system_prompt, user_prompt)
        return response.content

    async def _ingest_external_program_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {"projects": {}, "benefits": {}}
        if self.planview_connector and self.planview_connector.authenticate():
            response = self.planview_connector.read("projects")
            data["projects"].update({proj["id"]: proj for proj in response})
            health = self.planview_connector.read("program_health")
            for entry in health:
                data["projects"].setdefault(entry["id"], {}).update(entry)
        if self.clarity_connector and self.clarity_connector.authenticate():
            response = self.clarity_connector.read("projects")
            data["projects"].update({proj["id"]: proj for proj in response})
            health = self.clarity_connector.read("program_health")
            for entry in health:
                data["projects"].setdefault(entry["id"], {}).update(entry)
        for project_id, project in data["projects"].items():
            benefits = project.get("benefits") or {}
            total_benefits = benefits.get("total_benefits", project.get("benefit", 0))
            total_costs = project.get("investment", project.get("cost", 0))
            if total_benefits or total_costs:
                data["benefits"][project_id] = {
                    "total_benefits": total_benefits,
                    "total_costs": total_costs,
                    "benefit_breakdown": benefits,
                }
        return data

    async def _sync_work_management_mappings(
        self, program_id: str, program: dict[str, Any]
    ) -> None:
        mappings = []
        if self.jira_base_url and self.jira_api_token:
            mappings.extend(await self._fetch_jira_mappings(program_id, program))
        if self.azure_devops_org_url and self.azure_devops_pat:
            mappings.extend(await self._fetch_azure_devops_mappings(program_id, program))
        if not mappings:
            return
        if self.mapping_container:
            for mapping in mappings:
                await self.mapping_container.upsert_item(mapping)

    async def _fetch_jira_mappings(
        self, program_id: str, program: dict[str, Any]
    ) -> list[dict[str, Any]]:
        import httpx

        headers = {"Authorization": f"Bearer {self.jira_api_token}"}
        url = f"{self.jira_base_url}/rest/api/3/project/search"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            projects = response.json().get("values", [])
        mappings = []
        for project in projects:
            mappings.append(
                {
                    "id": f"jira:{project.get('id')}",
                    "system": "jira",
                    "program_id": program_id,
                    "project_id": project.get("id"),
                    "project_key": project.get("key"),
                    "project_name": project.get("name"),
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        return mappings

    async def _fetch_azure_devops_mappings(
        self, program_id: str, program: dict[str, Any]
    ) -> list[dict[str, Any]]:
        import base64
        import httpx

        token = base64.b64encode(f":{self.azure_devops_pat}".encode("utf-8")).decode("utf-8")
        headers = {"Authorization": f"Basic {token}"}
        url = f"{self.azure_devops_org_url}/_apis/projects?api-version=7.0"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            projects = response.json().get("value", [])
        mappings = []
        for project in projects:
            mappings.append(
                {
                    "id": f"azure-devops:{project.get('id')}",
                    "system": "azure_devops",
                    "program_id": program_id,
                    "project_id": project.get("id"),
                    "project_name": project.get("name"),
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        return mappings

    async def _optimize_dependency_graph(
        self,
        dependencies: list[dict[str, Any]],
        graph_analysis: dict[str, Any],
        circular_deps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        graph = graph_analysis.get("adjacency_list", {})
        conflicts = []
        for node, neighbors in graph.items():
            if len(neighbors) > 3:
                conflicts.append(
                    {
                        "node": node,
                        "issue": "Too many downstream dependencies",
                        "count": len(neighbors),
                    }
                )
        critical_path = self._calculate_critical_path({}, dependencies)
        recommendations = []
        if circular_deps:
            recommendations.append("Break circular dependencies to unblock delivery flow.")
        if conflicts:
            recommendations.append("Sequence downstream work to reduce dependency contention.")
        if critical_path:
            recommendations.append(
                f"Focus mitigation on critical path: {' > '.join(critical_path)}."
            )
        return {
            "conflicts": conflicts,
            "critical_path": critical_path,
            "recommendations": recommendations,
        }

    async def _optimize_synergy_portfolio(
        self,
        shared_components: list[dict[str, Any]],
        vendor_synergies: list[dict[str, Any]],
        infrastructure_synergies: list[dict[str, Any]],
    ) -> dict[str, Any]:
        opportunities = []
        for item in shared_components:
            opportunities.append(
                {
                    "type": "shared_component",
                    "projects": item.get("projects", []),
                    "score": item.get("similarity", 0) * 0.6 + 0.4,
                    "estimated_value": 15000,
                }
            )
        for item in vendor_synergies:
            opportunities.append(
                {
                    "type": "vendor_consolidation",
                    "projects": item.get("projects", []),
                    "score": item.get("similarity", 0) * 0.5 + 0.3,
                    "estimated_value": 10000,
                }
            )
        for item in infrastructure_synergies:
            opportunities.append(
                {
                    "type": "infrastructure_sharing",
                    "projects": item.get("projects", []),
                    "score": item.get("similarity", 0) * 0.4 + 0.2,
                    "estimated_value": 8000,
                }
            )
        opportunities.sort(key=lambda item: item["score"] * item["estimated_value"], reverse=True)
        priority_actions = opportunities[:3]
        return {
            "opportunities": opportunities,
            "priority_actions": priority_actions,
            "estimated_total_value": sum(item["estimated_value"] for item in priority_actions),
        }

    async def _propose_synergy_mitigations(self, optimization: dict[str, Any]) -> list[dict[str, Any]]:
        mitigations = []
        for action in optimization.get("priority_actions", []):
            mitigations.append(
                {
                    "action": action["type"],
                    "risk": "Adoption resistance",
                    "mitigation": "Engage stakeholders and align governance early",
                }
            )
        if not mitigations:
            mitigations.append(
                {
                    "action": "baseline",
                    "risk": "Limited synergy realization",
                    "mitigation": "Review portfolio for additional consolidation opportunities",
                }
            )
        return mitigations

    async def _estimate_project_costs(
        self, project_ids: list[str], *, tenant_id: str
    ) -> dict[str, float]:
        costs: dict[str, float] = {}
        if self.financial_agent:
            for project_id in project_ids:
                response = await self.financial_agent.process(
                    {
                        "action": "get_financial_summary",
                        "project_id": project_id,
                        "tenant_id": tenant_id,
                        "context": {"tenant_id": tenant_id},
                    }
                )
                costs[project_id] = float(
                    response.get("total_cost")
                    or response.get("total_costs")
                    or response.get("budget_total", 0)
                )
        if not costs:
            for project_id in project_ids:
                costs[project_id] = 100000.0
        return costs

    async def _estimate_project_risks(
        self, project_ids: list[str], *, tenant_id: str
    ) -> dict[str, float]:
        risks: dict[str, float] = {}
        if self.risk_agent:
            for project_id in project_ids:
                response = await self.risk_agent.process(
                    {
                        "action": "get_risk_dashboard",
                        "project_id": project_id,
                        "tenant_id": tenant_id,
                        "context": {"tenant_id": tenant_id},
                    }
                )
                risks[project_id] = float(response.get("risk_score", 0.3))
        if not risks:
            for project_id in project_ids:
                risks[project_id] = 0.3
        return risks

    async def _optimize_program_schedule(
        self,
        program_id: str,
        *,
        objectives: dict[str, float] | None,
        constraints: dict[str, Any],
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        self.logger.info(f"Optimizing program schedule for: {program_id}")

        program = self.program_store.get(tenant_id, program_id)
        if not program:
            raise ValueError(f"Program not found: {program_id}")

        constituent_projects = program.get("constituent_projects", [])
        project_schedules = await self._get_project_schedules(constituent_projects)
        resource_allocations = await self._get_resource_allocations(constituent_projects)
        project_costs = await self._estimate_project_costs(constituent_projects, tenant_id=tenant_id)
        project_risks = await self._estimate_project_risks(constituent_projects, tenant_id=tenant_id)
        project_details = await self._get_project_details(constituent_projects)
        strategic_objectives = program.get("strategic_objectives", [])

        base_schedule = self._build_initial_schedule(constituent_projects, project_schedules)
        dependencies = await self._identify_dependencies(
            constituent_projects,
            schedules=project_schedules,
            resource_allocations=resource_allocations,
        )
        synergy_analysis = await self.analyze_synergies(project_details)
        synergy_map = self._build_synergy_map(synergy_analysis)
        alignment_scores = self._calculate_alignment_scores(
            project_details, strategic_objectives
        )
        alignment_score = (
            sum(alignment_scores.values()) / max(1, len(alignment_scores)) if alignment_scores else 0.0
        )
        synergy_savings = await self._calculate_synergy_savings(
            synergy_analysis.get("shared_components", []),
            synergy_analysis.get("vendor_consolidation", []),
            synergy_analysis.get("infrastructure_synergies", []),
            project_costs,
        )

        target_objectives = objectives or self.optimization_objectives
        normalized_objectives = self._normalize_objectives(target_objectives)

        rng = random.Random(hash(program_id) % 10_000)
        best_schedule = base_schedule
        best_score, best_breakdown = self._score_schedule_candidate(
            base_schedule,
            base_schedule,
            resource_allocations,
            project_costs,
            project_risks,
            normalized_objectives,
            alignment_score,
            synergy_map,
        )

        optimization_method = constraints.get("optimization_method", "genetic_algorithm")
        iterations = constraints.get("iterations", 30)
        if optimization_method in {"mixed_integer", "mixed_integer_programming", "mip"}:
            best_schedule, best_score, best_breakdown = self._optimize_schedule_mip(
                base_schedule,
                dependencies,
                resource_allocations,
                project_costs,
                project_risks,
                normalized_objectives,
                alignment_score,
                synergy_map,
                max_shift_days=constraints.get("max_shift_days", 15),
            )
        elif optimization_method in {"genetic", "genetic_algorithm"}:
            best_schedule, best_score, best_breakdown = self._optimize_schedule_genetic(
                base_schedule,
                dependencies,
                resource_allocations,
                project_costs,
                project_risks,
                normalized_objectives,
                alignment_score,
                synergy_map,
                iterations=iterations,
                max_shift_days=constraints.get("max_shift_days", 15),
                rng=rng,
            )
        else:
            for _ in range(iterations):
                candidate = self._mutate_schedule(
                    base_schedule,
                    dependencies,
                    rng=rng,
                    max_shift_days=constraints.get("max_shift_days", 15),
                )
                score, breakdown = self._score_schedule_candidate(
                    candidate,
                    base_schedule,
                    resource_allocations,
                    project_costs,
                    project_risks,
                    normalized_objectives,
                    alignment_score,
                    synergy_map,
                )
                if score > best_score:
                    best_schedule = candidate
                    best_score = score
                    best_breakdown = breakdown

        optimized_schedule = {
            project_id: {
                "start": data["start"].isoformat(),
                "end": data["end"].isoformat(),
                "duration_days": data["duration_days"],
            }
            for project_id, data in best_schedule.items()
        }

        optimization = {
            "program_id": program_id,
            "optimized_schedule": optimized_schedule,
            "objective_score": round(best_score, 4),
            "objective_breakdown": best_breakdown,
            "algorithm": optimization_method,
            "constraints": constraints,
            "alignment_score": alignment_score,
            "alignment_scores": alignment_scores,
            "synergy_savings": synergy_savings,
            "synergy_analysis": synergy_analysis,
            "optimized_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.db_service:
            await self.db_service.store("program_optimizations", program_id, optimization)
            await self.db_service.store(
                "program_analytics",
                program_id,
                {
                    "program_id": program_id,
                    "optimization_score": best_score,
                    "objectives": normalized_objectives,
                },
            )
            await self.db_service.store(
                "program_optimization_models",
                program_id,
                {
                    "program_id": program_id,
                    "optimization_method": optimization_method,
                    "objectives": normalized_objectives,
                    "alignment_scores": alignment_scores,
                    "synergy_map": {f"{k[0]}::{k[1]}": v for k, v in synergy_map.items()},
                    "constraints": constraints,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        await self.event_bus.publish(
            "program.optimized",
            {
                "program_id": program_id,
                "tenant_id": tenant_id,
                "optimization": optimization,
                "correlation_id": correlation_id,
            },
        )

        await self._publish_program_status_update(
            program_id,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            status_type="optimization",
            payload={
                "optimization_score": best_score,
                "alignment_score": alignment_score,
                "synergy_savings": synergy_savings.get("total", 0.0),
            },
        )

        return optimization

    def _build_initial_schedule(
        self, project_ids: list[str], schedules: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        schedule_map: dict[str, dict[str, Any]] = {}
        default_start = datetime.now(timezone.utc)
        for idx, project_id in enumerate(project_ids):
            schedule = schedules.get(project_id, {})
            start = self._parse_date(schedule.get("start")) or default_start + timedelta(days=30 * idx)
            end = self._parse_date(schedule.get("end")) or start + timedelta(days=180)
            schedule_map[project_id] = {
                "start": start,
                "end": end,
                "duration_days": max(1, (end - start).days),
            }
        return schedule_map

    def _normalize_objectives(self, objectives: dict[str, float]) -> dict[str, float]:
        total = sum(max(0.0, value) for value in objectives.values())
        if total == 0:
            return self.optimization_objectives
        return {key: max(0.0, value) / total for key, value in objectives.items()}

    def _extract_alignment_terms(self, text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    def _calculate_alignment_scores(
        self, project_details: dict[str, Any], strategic_objectives: list[str]
    ) -> dict[str, float]:
        if not strategic_objectives:
            return {project_id: 0.7 for project_id in project_details}
        objective_terms = self._extract_alignment_terms(" ".join(str(obj) for obj in strategic_objectives))
        if not objective_terms:
            return {project_id: 0.7 for project_id in project_details}
        scores: dict[str, float] = {}
        for project_id, detail in project_details.items():
            project_text = " ".join(
                str(value)
                for value in [
                    detail.get("name"),
                    detail.get("description"),
                    " ".join(detail.get("scope", []) or []),
                    " ".join(detail.get("tags", []) or []),
                ]
                if value
            )
            project_terms = self._extract_alignment_terms(project_text)
            if not project_terms:
                scores[project_id] = 0.5
                continue
            overlap = len(project_terms & objective_terms)
            scores[project_id] = max(0.0, min(1.0, overlap / max(1, len(objective_terms))))
        return scores

    def _build_synergy_map(self, synergy_analysis: dict[str, Any]) -> dict[tuple[str, str], float]:
        synergy_map: dict[tuple[str, str], float] = {}

        def _add_synergies(items: list[dict[str, Any]], weight: float) -> None:
            for item in items:
                projects = item.get("projects", [])
                if len(projects) != 2:
                    continue
                pair = tuple(sorted(projects))
                synergy_map[pair] = synergy_map.get(pair, 0.0) + weight * float(
                    item.get("similarity", 0.0)
                )

        _add_synergies(synergy_analysis.get("shared_components", []), 0.6)
        _add_synergies(synergy_analysis.get("vendor_consolidation", []), 0.25)
        _add_synergies(synergy_analysis.get("infrastructure_synergies", []), 0.15)

        return synergy_map

    def _calculate_synergy_score(
        self, schedule: dict[str, dict[str, Any]], synergy_map: dict[tuple[str, str], float]
    ) -> float:
        if not synergy_map:
            return 0.0
        total_weight = sum(synergy_map.values())
        if total_weight <= 0:
            return 0.0
        realized = 0.0
        for (project_a, project_b), weight in synergy_map.items():
            data_a = schedule.get(project_a)
            data_b = schedule.get(project_b)
            if not data_a or not data_b:
                continue
            start_a = data_a["start"]
            end_a = data_a["end"]
            start_b = data_b["start"]
            end_b = data_b["end"]
            if start_a <= end_b and start_b <= end_a:
                realized += weight
                continue
            gap = min(abs((start_a - end_b).days), abs((start_b - end_a).days))
            if gap <= 14:
                realized += weight * 0.5
        return min(1.0, realized / total_weight)

    def _mutate_schedule(
        self,
        base_schedule: dict[str, dict[str, Any]],
        dependencies: list[dict[str, Any]],
        *,
        rng: random.Random,
        max_shift_days: int,
    ) -> dict[str, dict[str, Any]]:
        candidate = {}
        dependency_map: dict[str, list[str]] = {}
        for dep in dependencies:
            predecessor = dep.get("predecessor")
            successor = dep.get("successor")
            if predecessor and successor:
                dependency_map.setdefault(successor, []).append(predecessor)

        for project_id, data in base_schedule.items():
            shift = rng.randint(-max_shift_days, max_shift_days)
            start = data["start"] + timedelta(days=shift)
            duration = data.get("duration_days", 180)
            for predecessor in dependency_map.get(project_id, []):
                predecessor_end = base_schedule.get(predecessor, {}).get("end")
                if predecessor_end and start < predecessor_end:
                    start = predecessor_end + timedelta(days=1)
            candidate[project_id] = {
                "start": start,
                "end": start + timedelta(days=duration),
                "duration_days": duration,
            }
        return candidate

    def _optimize_schedule_genetic(
        self,
        base_schedule: dict[str, dict[str, Any]],
        dependencies: list[dict[str, Any]],
        resource_allocations: dict[str, Any],
        project_costs: dict[str, float],
        project_risks: dict[str, float],
        objectives: dict[str, float],
        alignment_score: float,
        synergy_map: dict[tuple[str, str], float],
        *,
        iterations: int,
        max_shift_days: int,
        rng: random.Random,
        population_size: int = 12,
    ) -> tuple[dict[str, dict[str, Any]], float, dict[str, float]]:
        population = [
            self._mutate_schedule(
                base_schedule, dependencies, rng=rng, max_shift_days=max_shift_days
            )
            for _ in range(max(2, population_size))
        ]
        population.append(base_schedule)
        scored = [
            self._score_schedule_candidate(
                candidate,
                base_schedule,
                resource_allocations,
                project_costs,
                project_risks,
                objectives,
                alignment_score,
                synergy_map,
            )
            for candidate in population
        ]
        best_idx = max(range(len(population)), key=lambda idx: scored[idx][0])
        best_schedule = population[best_idx]
        best_score, best_breakdown = scored[best_idx]

        for _ in range(iterations):
            ranked = sorted(
                zip(population, scored),
                key=lambda item: item[1][0],
                reverse=True,
            )
            elites = [item[0] for item in ranked[: max(2, len(ranked) // 3)]]
            new_population = elites[:]
            while len(new_population) < population_size:
                parent_a, parent_b = rng.sample(elites, 2)
                child = {}
                for project_id in base_schedule.keys():
                    child[project_id] = (
                        parent_a.get(project_id)
                        if rng.random() < 0.5
                        else parent_b.get(project_id)
                    )
                child = self._mutate_schedule(
                    child, dependencies, rng=rng, max_shift_days=max_shift_days
                )
                new_population.append(child)
            population = new_population
            scored = [
                self._score_schedule_candidate(
                    candidate,
                    base_schedule,
                    resource_allocations,
                    project_costs,
                    project_risks,
                    objectives,
                    alignment_score,
                    synergy_map,
                )
                for candidate in population
            ]
            best_idx = max(range(len(population)), key=lambda idx: scored[idx][0])
            candidate_score, candidate_breakdown = scored[best_idx]
            if candidate_score > best_score:
                best_schedule = population[best_idx]
                best_score = candidate_score
                best_breakdown = candidate_breakdown

        return best_schedule, best_score, best_breakdown

    def _optimize_schedule_mip(
        self,
        base_schedule: dict[str, dict[str, Any]],
        dependencies: list[dict[str, Any]],
        resource_allocations: dict[str, Any],
        project_costs: dict[str, float],
        project_risks: dict[str, float],
        objectives: dict[str, float],
        alignment_score: float,
        synergy_map: dict[tuple[str, str], float],
        *,
        max_shift_days: int,
    ) -> tuple[dict[str, dict[str, Any]], float, dict[str, float]]:
        candidate = {key: value.copy() for key, value in base_schedule.items()}
        best_score, best_breakdown = self._score_schedule_candidate(
            candidate,
            base_schedule,
            resource_allocations,
            project_costs,
            project_risks,
            objectives,
            alignment_score,
            synergy_map,
        )
        improved = True
        shift_options = [-max_shift_days, 0, max_shift_days]
        while improved:
            improved = False
            for project_id, data in candidate.items():
                best_local = (best_score, data)
                for shift in shift_options:
                    shifted = data.copy()
                    shifted_start = shifted["start"] + timedelta(days=shift)
                    shifted["start"] = shifted_start
                    shifted["end"] = shifted_start + timedelta(days=shifted["duration_days"])
                    test_schedule = candidate.copy()
                    test_schedule[project_id] = shifted
                    score, breakdown = self._score_schedule_candidate(
                        test_schedule,
                        base_schedule,
                        resource_allocations,
                        project_costs,
                        project_risks,
                        objectives,
                        alignment_score,
                        synergy_map,
                    )
                    if score > best_local[0]:
                        best_local = (score, shifted)
                        best_breakdown = breakdown
                if best_local[0] > best_score:
                    candidate[project_id] = best_local[1]
                    best_score = best_local[0]
                    improved = True
        return candidate, best_score, best_breakdown

    def _score_schedule_candidate(
        self,
        candidate: dict[str, dict[str, Any]],
        baseline: dict[str, dict[str, Any]],
        resource_allocations: dict[str, Any],
        project_costs: dict[str, float],
        project_risks: dict[str, float],
        objectives: dict[str, float],
        alignment_score: float,
        synergy_map: dict[tuple[str, str], float],
    ) -> tuple[float, dict[str, float]]:
        delay_days = 0.0
        for project_id, data in candidate.items():
            baseline_start = baseline.get(project_id, {}).get("start")
            if baseline_start and data["start"] > baseline_start:
                delay_days += (data["start"] - baseline_start).days

        total_cost = sum(project_costs.values()) or 1.0
        max_cost = total_cost * 1.2
        avg_risk = sum(project_risks.values()) / max(1, len(project_risks))

        overlap_conflicts = self._detect_resource_schedule_conflicts(
            candidate, resource_allocations
        )
        conflict_penalty = min(1.0, overlap_conflicts / max(1, len(candidate)))

        schedule_score = max(0.0, 1 - delay_days / (max(1, len(candidate)) * 30))
        cost_score = max(0.0, 1 - total_cost / max_cost)
        risk_score = max(0.0, 1 - avg_risk)
        utilization_score = max(0.0, 1 - conflict_penalty)
        synergy_score = self._calculate_synergy_score(candidate, synergy_map)

        breakdown = {
            "utilization": round(utilization_score, 4),
            "cost": round(cost_score, 4),
            "risk": round(risk_score, 4),
            "schedule": round(schedule_score, 4),
            "alignment": round(max(0.0, min(1.0, alignment_score)), 4),
            "synergy": round(synergy_score, 4),
        }
        overall = sum(breakdown[key] * objectives.get(key, 0.0) for key in breakdown)
        return overall, breakdown

    def _detect_resource_schedule_conflicts(
        self, schedule: dict[str, dict[str, Any]], resource_allocations: dict[str, Any]
    ) -> int:
        conflicts = 0
        for project_a, project_b in combinations(schedule.keys(), 2):
            data_a = schedule[project_a]
            data_b = schedule[project_b]
            if data_a["start"] <= data_b["end"] and data_b["start"] <= data_a["end"]:
                resources_a = set(self._flatten_resource_allocations(resource_allocations.get(project_a, {})))
                resources_b = set(self._flatten_resource_allocations(resource_allocations.get(project_b, {})))
                if resources_a.intersection(resources_b):
                    conflicts += 1
        return conflicts

    async def _submit_program_for_approval(
        self,
        program_id: str,
        *,
        decision_payload: dict[str, Any],
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        if not self.approval_agent and self.approval_agent_enabled:
            from approval_workflow_agent import ApprovalWorkflowAgent

            self.approval_agent = ApprovalWorkflowAgent(config=self.approval_agent_config)
        if not self.approval_agent:
            return {"status": "skipped", "reason": "approval_agent_not_configured"}

        approval = await self.approval_agent.process(
            {
                "request_type": "program_optimization",
                "request_id": program_id,
                "requester": decision_payload.get("requester", "system"),
                "details": decision_payload,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
                "context": {"tenant_id": tenant_id, "correlation_id": correlation_id},
            }
        )
        if self.db_service:
            await self.db_service.store(
                "program_approvals",
                program_id,
                {"program_id": program_id, "approval": approval},
            )
        return approval

    async def _record_program_decision(
        self,
        program_id: str,
        *,
        decision: dict[str, Any],
        tenant_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        program = self.program_store.get(tenant_id, program_id) or {}
        decision_entry = {
            "decision_id": str(uuid.uuid4()),
            "program_id": program_id,
            "decision": decision,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        program.setdefault("decision_log", []).append(decision_entry)
        self.program_store.upsert(tenant_id, program_id, program)
        if self.db_service:
            await self.db_service.store("program_decisions", decision_entry["decision_id"], decision_entry)

        await self.event_bus.publish(
            "program.decision.recorded",
            {
                "program_id": program_id,
                "tenant_id": tenant_id,
                "decision": decision_entry,
                "correlation_id": correlation_id,
            },
        )
        return {"status": "recorded", "decision": decision_entry}

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "program_definition",
            "roadmap_planning",
            "dependency_tracking",
            "benefits_aggregation",
            "resource_coordination",
            "synergy_identification",
            "change_impact_analysis",
            "program_health_monitoring",
            "program_governance",
            "cross_project_optimization",
        ]
