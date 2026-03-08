"""
Program Management Agent

Purpose:
Coordinates groups of related projects (programs) to achieve shared strategic objectives
and realize synergies. Manages inter-project dependencies, plans integrated roadmaps
and monitors program health.

Specification: agents/portfolio-management/program-management-agent/README.md
"""

import asyncio
import uuid
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

from program_actions import (
    handle_aggregate_benefits,
    handle_analyze_change_impact,
    handle_coordinate_resources,
    handle_create_program,
    handle_generate_roadmap,
    handle_get_program,
    handle_get_program_health,
    handle_identify_synergies,
    handle_optimize_program,
    handle_record_program_decision,
    handle_submit_program_for_approval,
    handle_track_dependencies,
)
from program_infrastructure import (
    collect_external_health_signals,
    compute_benefit_realization_metrics,
    generate_program_narrative,
    ingest_external_program_data,
    initialize_cosmos,
    initialize_integrations,
    initialize_llm,
    initialize_ml,
    predict_program_health,
    subscribe_to_program_events,
)
from program_models import (
    DEFAULT_DEPENDENCY_TYPES,
    DEFAULT_HEALTH_SCORE_WEIGHTS,
    DEFAULT_OPTIMIZATION_OBJECTIVES,
    PROGRAM_ID_REQUIRED_ACTIONS,
    PROGRAM_REQUIRED_FIELDS,
    VALID_ACTIONS,
)
from program_utils import (
    calculate_critical_path,
    detect_resource_overlaps,
    detect_schedule_overlaps,
    parse_date,
)

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

    def __init__(
        self, agent_id: str = "program-management-agent", config: dict[str, Any] | None = None
    ):
        super().__init__(agent_id, config)

        self.dependency_types = (
            config.get("dependency_types", DEFAULT_DEPENDENCY_TYPES)
            if config
            else DEFAULT_DEPENDENCY_TYPES
        )
        self.synergy_detection_threshold = (
            config.get("synergy_detection_threshold", 0.75) if config else 0.75
        )
        self.health_score_weights = (
            config.get("health_score_weights", DEFAULT_HEALTH_SCORE_WEIGHTS)
            if config
            else DEFAULT_HEALTH_SCORE_WEIGHTS
        )
        self.optimization_objectives = (
            config.get("optimization_objectives", DEFAULT_OPTIMIZATION_OBJECTIVES)
            if config
            else DEFAULT_OPTIMIZATION_OBJECTIVES
        )

        self.program_store = TenantStateStore(
            Path(config.get("program_store_path", "data/program_store.json"))
            if config
            else Path("data/program_store.json")
        )
        self.roadmap_store = TenantStateStore(
            Path(config.get("program_roadmap_store_path", "data/program_roadmap_store.json"))
            if config
            else Path("data/program_roadmap_store.json")
        )
        self.dependency_store = TenantStateStore(
            Path(config.get("program_dependency_store_path", "data/program_dependency_store.json"))
            if config
            else Path("data/program_dependency_store.json")
        )
        self.synergies: dict[str, Any] = {}
        self.event_bus = (config.get("event_bus") if config else None) or get_event_bus()
        self.db_service: DatabaseStorageService | None = None

        # Peer agent references
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
        self.approval_agent_enabled = config.get("approval_agent_enabled", True) if config else True
        self.schedule_ids = config.get("schedule_ids", {}) if config else {}
        self.business_case_ids = config.get("business_case_ids", {}) if config else {}
        self.health_actions = config.get("health_actions", {}) if config else {}

        # Azure / external service clients
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

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Program Management Agent...")
        db_config = self.config.get("database_storage", {}) if self.config else {}
        self.db_service = DatabaseStorageService(db_config)
        self.logger.info("Database Storage Service initialized")
        await initialize_cosmos(self)
        await initialize_ml(self)
        await initialize_llm(self)
        await initialize_integrations(self)
        await subscribe_to_program_events(self)
        self.logger.info("Program Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")
        if not action:
            self.logger.warning("No action specified")
            return False
        if action not in VALID_ACTIONS:
            self.logger.warning("Invalid action: %s", action)
            return False
        if action == "create_program":
            program_data = input_data.get("program", {})
            for field in PROGRAM_REQUIRED_FIELDS:
                if field not in program_data:
                    self.logger.warning("Missing required field: %s", field)
                    return False
        elif action in PROGRAM_ID_REQUIRED_ACTIONS:
            if "program_id" not in input_data:
                self.logger.warning("Missing program_id")
                return False
        return True

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

    # ------------------------------------------------------------------
    # Process dispatcher
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Route program management requests to the appropriate action handler."""
        action = input_data.get("action", "create_program")
        context = input_data.get("context", {})
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"

        if action == "create_program":
            return await handle_create_program(
                self,
                input_data.get("program", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
        elif action == "generate_roadmap":
            return await handle_generate_roadmap(self, input_data.get("program_id"), tenant_id=tenant_id, correlation_id=correlation_id)  # type: ignore
        elif action == "track_dependencies":
            return await handle_track_dependencies(self, input_data.get("program_id"), tenant_id=tenant_id)  # type: ignore
        elif action == "aggregate_benefits":
            return await handle_aggregate_benefits(self, input_data.get("program_id"), tenant_id=tenant_id)  # type: ignore
        elif action == "coordinate_resources":
            return await handle_coordinate_resources(self, input_data.get("program_id"), tenant_id=tenant_id)  # type: ignore
        elif action == "identify_synergies":
            return await handle_identify_synergies(self, input_data.get("program_id"), tenant_id=tenant_id)  # type: ignore
        elif action == "analyze_change_impact":
            return await handle_analyze_change_impact(self, input_data.get("program_id"), input_data.get("change", {}), tenant_id=tenant_id)  # type: ignore
        elif action == "get_program_health":
            return await handle_get_program_health(self, input_data.get("program_id"), tenant_id=tenant_id)  # type: ignore
        elif action == "optimize_program":
            return await handle_optimize_program(self, input_data.get("program_id"), objectives=input_data.get("objectives"), constraints=input_data.get("constraints", {}), tenant_id=tenant_id, correlation_id=correlation_id)  # type: ignore
        elif action == "submit_program_for_approval":
            return await handle_submit_program_for_approval(self, input_data.get("program_id"), decision_payload=input_data.get("decision_payload", {}), tenant_id=tenant_id, correlation_id=correlation_id)  # type: ignore
        elif action == "record_program_decision":
            return await handle_record_program_decision(self, input_data.get("program_id"), decision=input_data.get("decision", {}), tenant_id=tenant_id, correlation_id=correlation_id)  # type: ignore
        elif action == "get_program":
            return await handle_get_program(self, input_data.get("program_id"), tenant_id=tenant_id)  # type: ignore
        elif action == "list_dependency_graphs":
            return {"dependency_graphs": await self._list_dependency_graphs()}
        elif action == "get_dependency_graph":
            return await self._read_dependency_graph(input_data.get("program_id"))  # type: ignore
        elif action == "delete_dependency_graph":
            await self._delete_dependency_graph(input_data.get("program_id"))  # type: ignore
            return {"status": "deleted", "program_id": input_data.get("program_id")}
        else:
            raise ValueError(f"Unknown action: {action}")

    # ------------------------------------------------------------------
    # Shared helpers called by action modules via agent reference
    # ------------------------------------------------------------------

    async def _get_project_schedules(self, project_ids: list[str]) -> dict[str, Any]:
        """Query project schedules from Schedule & Planning Agent."""
        if self.schedule_agent and project_ids:
            schedules: dict[str, Any] = {}
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
        deps: list[dict[str, Any]] = []
        schedules = schedules or {}
        resource_allocations = resource_allocations or {}
        sched_overlaps = detect_schedule_overlaps(project_ids, schedules)
        res_overlaps = detect_resource_overlaps(project_ids, resource_allocations)
        overlap_pairs = {(i["project_a"], i["project_b"]) for i in sched_overlaps}
        res_map = {(i["project_a"], i["project_b"]): i for i in res_overlaps}

        for o in sched_overlaps:
            deps.append(
                {
                    "predecessor": o["project_a"],
                    "successor": o["project_b"],
                    "type": "schedule_overlap",
                    "overlap_days": o["overlap_days"],
                    "overlap_window": o["overlap_window"],
                }
            )
        for o in res_overlaps:
            deps.append(
                {
                    "predecessor": o["project_a"],
                    "successor": o["project_b"],
                    "type": "shared_resource",
                    "shared_resources": o["shared_resources"],
                    "overlap_score": o["overlap_score"],
                }
            )

        for pa, pb in combinations(project_ids, 2):
            if (pa, pb) not in overlap_pairs and (pb, pa) not in overlap_pairs:
                continue
            ro = res_map.get((pa, pb)) or res_map.get((pb, pa))
            if not ro:
                continue
            sa, sb = schedules.get(pa, {}), schedules.get(pb, {})
            a0, a1 = parse_date(sa.get("start")), parse_date(sa.get("end"))
            b0, b1 = parse_date(sb.get("start")), parse_date(sb.get("end"))
            if not (a0 and a1 and b0 and b1):
                continue
            shared = ro.get("shared_resources", [])
            if a0 <= b1 and b0 <= a1:
                deps.append(
                    {
                        "predecessor": pa,
                        "successor": pb,
                        "type": "resource_contention",
                        "shared_resources": shared,
                        "overlap_window": {
                            "start": max(a0, b0).date().isoformat(),
                            "end": min(a1, b1).date().isoformat(),
                        },
                    }
                )
            elif a1 < b0:
                deps.append(
                    {
                        "predecessor": pa,
                        "successor": pb,
                        "type": "resource_sequence",
                        "lag_days": (b0 - a1).days,
                        "shared_resources": shared,
                    }
                )
            elif b1 < a0:
                deps.append(
                    {
                        "predecessor": pb,
                        "successor": pa,
                        "type": "resource_sequence",
                        "lag_days": (a0 - b1).days,
                        "shared_resources": shared,
                    }
                )

        for idx in range(len(project_ids) - 1):
            deps.append(
                {
                    "predecessor": project_ids[idx],
                    "successor": project_ids[idx + 1],
                    "type": self.dependency_types[idx % len(self.dependency_types)],
                }
            )
        return deps

    async def _calculate_program_critical_path(
        self, schedules: dict[str, Any], dependencies: list[dict[str, Any]]
    ) -> list[str]:
        return calculate_critical_path(schedules, dependencies)

    async def _get_resource_allocations(self, project_ids: list[str]) -> dict[str, Any]:
        if self.resource_agent and project_ids:
            allocs: dict[str, Any] = {}
            for pid in project_ids:
                r = await self.resource_agent.process(
                    {"action": "get_utilization", "project_id": pid}
                )
                allocs[pid] = r.get("allocations", r)
            if allocs:
                return allocs
        return {}

    async def _get_project_benefits(self, project_ids: list[str]) -> dict[str, Any]:
        if project_ids:
            ext = await ingest_external_program_data(self)
            if ext.get("benefits"):
                return ext["benefits"]
        if self.business_case_agent and project_ids:
            benefits: dict[str, Any] = {}
            for pid in project_ids:
                bcid = self.business_case_ids.get(pid)
                if bcid:
                    r = await self.business_case_agent.process(
                        {"action": "get_business_case", "business_case_id": bcid}
                    )
                    bd = r.get("benefit_breakdown", {}) or r.get("benefits", {})
                    benefits[pid] = {
                        "total_benefits": bd.get("total_benefits", 0),
                        "total_costs": r.get("total_cost", r.get("total_costs", 0)),
                        "benefit_breakdown": bd,
                    }
            if benefits:
                return benefits
        return {pid: {"total_benefits": 100000, "total_costs": 50000} for pid in project_ids}

    async def _get_project_details(self, project_ids: list[str]) -> dict[str, Any]:
        if self.project_definition_agent and project_ids:
            details: dict[str, Any] = {}
            for pid in project_ids:
                details[pid] = await self.project_definition_agent.process(
                    {"action": "get_charter", "project_id": pid}
                )
            if details:
                return details
        ext = await ingest_external_program_data(self)
        if ext.get("projects"):
            return ext["projects"]
        return {pid: {"name": pid, "description": ""} for pid in project_ids}

    async def _get_project_dependencies(
        self, program_id: str, project_id: str
    ) -> list[dict[str, Any]]:
        stored = await self._get_dependency_graph(program_id)
        return [d for d in stored.get("dependencies", []) if project_id in d.values()]

    async def _estimate_project_costs(
        self, project_ids: list[str], *, tenant_id: str
    ) -> dict[str, float]:
        costs: dict[str, float] = {}
        if self.financial_agent:
            for pid in project_ids:
                r = await self.financial_agent.process(
                    {
                        "action": "get_financial_summary",
                        "project_id": pid,
                        "tenant_id": tenant_id,
                        "context": {"tenant_id": tenant_id},
                    }
                )
                costs[pid] = float(
                    r.get("total_cost") or r.get("total_costs") or r.get("budget_total", 0)
                )
        if not costs:
            costs = {pid: 100000.0 for pid in project_ids}
        return costs

    async def _estimate_project_risks(
        self, project_ids: list[str], *, tenant_id: str
    ) -> dict[str, float]:
        risks: dict[str, float] = {}
        if self.risk_agent:
            for pid in project_ids:
                r = await self.risk_agent.process(
                    {
                        "action": "get_risk_dashboard",
                        "project_id": pid,
                        "tenant_id": tenant_id,
                        "context": {"tenant_id": tenant_id},
                    }
                )
                risks[pid] = float(r.get("risk_score", 0.3))
        if not risks:
            risks = {pid: 0.3 for pid in project_ids}
        return risks

    # Event publishing
    async def _publish_program_status_update(
        self,
        program_id: str,
        *,
        tenant_id: str,
        correlation_id: str,
        status_type: str,
        payload: dict[str, Any],
    ) -> None:
        sp = {
            "program_id": program_id,
            "status_type": status_type,
            "payload": payload,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.db_service:
            await self.db_service.store(
                "program_status_updates", f"{program_id}-{status_type}-{uuid.uuid4().hex}", sp
            )
        await self.event_bus.publish(
            "program.status.updated",
            {
                "program_id": program_id,
                "tenant_id": tenant_id,
                "status": sp,
                "correlation_id": correlation_id,
            },
        )

    # Cosmos dependency-graph CRUD
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

    async def _get_dependency_graph(self, program_id: str) -> dict[str, Any]:
        if not self.dependency_container:
            return {}
        try:
            return await self.dependency_container.read_item(
                item=program_id, partition_key=program_id
            )
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ):
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
        results: list[dict[str, Any]] = []
        async for item in self.dependency_container.query_items(query="SELECT * FROM c"):
            results.append(item)
        return results

    # ML / health prediction (delegate to infrastructure module)
    async def _predict_program_health(self, features: dict[str, float]) -> dict[str, Any]:
        return await predict_program_health(self, features)

    async def _compute_benefit_realization_metrics(
        self, program_id: str, project_ids: list[str]
    ) -> dict[str, Any]:
        return await compute_benefit_realization_metrics(self, program_id, project_ids)

    async def _collect_external_health_signals(
        self, program_id: str, project_ids: list[str]
    ) -> dict[str, Any]:
        return await collect_external_health_signals(self, program_id, project_ids)

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
        return await generate_program_narrative(
            self,
            program,
            schedule_health=schedule_health,
            budget_health=budget_health,
            risk_health=risk_health,
            quality_health=quality_health,
            resource_health=resource_health,
            benefit_metrics=benefit_metrics,
        )

    # Backward-compatible public method
    async def analyze_synergies(self, project_details: dict[str, Any]) -> dict[str, Any]:
        """Analyze synergies using Azure Cognitive Services Text Analytics."""
        from program_actions.identify_synergies import analyze_synergies as _analyze

        return await _analyze(self, project_details)
