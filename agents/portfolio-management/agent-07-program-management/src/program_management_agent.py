"""
Agent 7: Program Management Agent

Purpose:
Coordinates groups of related projects (programs) to achieve shared strategic objectives
and realize synergies. Manages inter-project dependencies, plans integrated roadmaps
and monitors program health.

Specification: agents/portfolio-management/agent-07-program-management/README.md
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from events import ProgramCreatedEvent, ProgramRoadmapUpdatedEvent
from observability.tracing import get_trace_id

from agents.runtime import BaseAgent, InMemoryEventBus
from agents.runtime.src.state_store import TenantStateStore
from agents.common.connector_integration import DatabaseStorageService


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
            self.event_bus = InMemoryEventBus()
        self.db_service: DatabaseStorageService | None = None
        self.schedule_agent = config.get("schedule_agent") if config else None
        self.business_case_agent = config.get("business_case_agent") if config else None
        self.resource_agent = config.get("resource_agent") if config else None
        self.project_definition_agent = config.get("project_definition_agent") if config else None
        self.lifecycle_agent = config.get("lifecycle_agent") if config else None
        self.financial_agent = config.get("financial_agent") if config else None
        self.risk_agent = config.get("risk_agent") if config else None
        self.quality_agent = config.get("quality_agent") if config else None
        self.schedule_ids = config.get("schedule_ids", {}) if config else {}
        self.business_case_ids = config.get("business_case_ids", {}) if config else {}
        self.health_actions = config.get("health_actions", {}) if config else {}

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Program Management Agent...")

        # Future work: Initialize Azure Cosmos DB (Graph API) for dependency storage
        # Future work: Initialize Azure Machine Learning for program health prediction models
        # Future work: Connect to Planview/Clarity PPM for program structure sync
        # Future work: Initialize Azure OpenAI Service for roadmap narrative generation
        # Future work: Connect to Jira/Azure DevOps for epic and feature mapping
        # Future work: Initialize Azure Service Bus/Event Grid for project event subscriptions
        # Future work: Connect to Azure Synapse Analytics for benefits aggregation
        # Future work: Initialize Azure Cognitive Services for synergy detection

        db_config = self.config.get("database_storage", {}) if self.config else {}
        self.db_service = DatabaseStorageService(db_config)
        self.logger.info("Database Storage Service initialized")

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
            "get_program",
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

        elif action in ["track_dependencies", "analyze_change_impact"]:
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

        elif action == "get_program":
            return await self._get_program(
                input_data.get("program_id"),  # type: ignore
                tenant_id=tenant_id,
            )

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
            "created_at": datetime.utcnow().isoformat(),
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

        # Identify inter-project dependencies
        dependencies = await self._identify_dependencies(constituent_projects)

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
            "start_date": await self._calculate_program_start(project_schedules),
            "end_date": await self._calculate_program_end(project_schedules),
            "generated_at": datetime.utcnow().isoformat(),
        }

        self.roadmap_store.upsert(tenant_id, program_id, roadmap)
        self.dependency_store.upsert(
            tenant_id, program_id, {"program_id": program_id, "dependencies": dependencies}
        )
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
        dependencies = await self._identify_dependencies(constituent_projects)
        self.dependency_store.upsert(
            tenant_id, program_id, {"program_id": program_id, "dependencies": dependencies}
        )
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
        # Future work: Use Azure Cognitive Services for similarity analysis
        project_details = await self._get_project_details(constituent_projects)

        # Identify shared components
        shared_components = await self._identify_shared_components(project_details)

        # Identify vendor consolidation opportunities
        vendor_synergies = await self._identify_vendor_consolidation(project_details)

        # Identify infrastructure synergies
        infrastructure_synergies = await self._identify_infrastructure_synergies(project_details)

        # Calculate potential savings
        cost_savings = await self._calculate_synergy_savings(
            shared_components, vendor_synergies, infrastructure_synergies
        )

        synergies = {
            "shared_components": shared_components,
            "vendor_consolidation": vendor_synergies,
            "infrastructure_sharing": infrastructure_synergies,
            "estimated_savings": cost_savings,
        }

        # Store synergies
        self.synergies[program_id] = synergies
        if self.db_service:
            await self.db_service.store(
                "program_synergies",
                program_id,
                {"program_id": program_id, "synergies": synergies},
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

        # Determine health status
        health_status = await self._determine_health_status(composite_score)

        # Identify primary concerns
        concerns = await self._identify_health_concerns(
            schedule_health, budget_health, risk_health, quality_health, resource_health
        )

        return {
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
            "concerns": concerns,
            "recommendations": await self._generate_health_recommendations(
                composite_score, concerns
            ),
            "calculated_at": datetime.utcnow().isoformat(),
        }

    async def _get_program(self, program_id: str, *, tenant_id: str) -> dict[str, Any]:
        """Retrieve a program by ID."""
        program = self.program_store.get(tenant_id, program_id)
        if not program:
            raise ValueError(f"Program not found: {program_id}")
        return program  # type: ignore

    # Helper methods

    async def _generate_program_id(self) -> str:
        """Generate unique program ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"PROG-{timestamp}"

    async def _publish_program_created(
        self, program: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> None:
        event = ProgramCreatedEvent(
            event_name="program.created",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.utcnow(),
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
            timestamp=datetime.utcnow(),
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

    async def _identify_dependencies(self, project_ids: list[str]) -> list[dict[str, Any]]:
        """Identify inter-project dependencies."""
        dependencies = []
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
        return datetime.utcnow().isoformat()

    async def _calculate_program_end(self, schedules: dict[str, Any]) -> str:
        """Calculate program end date."""
        # Baseline
        return datetime.utcnow().isoformat()

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
        # Future work: Implement overlap detection
        # Baseline: assume 10% overlap
        total = sum(pb.get("total_benefits", 0) for pb in project_benefits.values())
        return total * 0.9  # type: ignore

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
        # Baseline
        return []

    async def _optimize_resource_allocation(
        self, allocations: dict[str, Any], conflicts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate resource optimization recommendations."""
        # Future work: Use optimization algorithms
        # Baseline
        return []

    async def _calculate_program_utilization(self, allocations: dict[str, Any]) -> float:
        """Calculate average utilization across program."""
        # Baseline
        return 0.75

    async def _identify_shared_resources(self, allocations: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify resources shared across multiple projects."""
        # Baseline
        return []

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
        return {}

    async def _identify_shared_components(
        self, project_details: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify shared components across projects."""
        # Future work: Use similarity analysis
        # Baseline
        return []

    async def _identify_vendor_consolidation(
        self, project_details: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify vendor consolidation opportunities."""
        # Baseline
        return []

    async def _identify_infrastructure_synergies(
        self, project_details: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify infrastructure sharing opportunities."""
        # Baseline
        return []

    async def _calculate_synergy_savings(
        self,
        shared_components: list[dict[str, Any]],
        vendor_synergies: list[dict[str, Any]],
        infrastructure_synergies: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Calculate potential cost savings from synergies."""
        # Baseline
        return {
            "shared_components": 0,
            "vendor_consolidation": 0,
            "infrastructure_sharing": 0,
            "total": 0,
        }

    async def _generate_synergy_recommendations(self, synergies: dict[str, Any]) -> list[str]:
        """Generate recommendations for synergy realization."""
        recommendations = []
        if synergies.get("shared_components"):
            recommendations.append("Consolidate shared components into reusable modules")
        if synergies.get("vendor_consolidation"):
            recommendations.append("Negotiate combined vendor contracts for volume discounts")
        return recommendations

    async def _get_project_dependencies(
        self, program_id: str, project_id: str
    ) -> list[dict[str, Any]]:
        """Get dependencies for a specific project."""
        # Baseline
        return []

    async def _analyze_cascading_effects(
        self, project_id: str, dependencies: list[dict[str, Any]], change_details: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Analyze cascading effects of a change."""
        # Future work: Implement impact propagation algorithm
        # Baseline
        return []

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
        # Future work: Use optimization logic
        # Baseline
        return options[0]["option"] if options else "No mitigation needed"

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
        # Future work: Close database connections
        # Future work: Close external API connections
        # Future work: Cancel pending event subscriptions
        # Future work: Flush any pending events

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
