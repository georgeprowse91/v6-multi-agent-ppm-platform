"""
Agent 9: Project Lifecycle & Governance Agent

Purpose:
Manages project progression through lifecycle stages, enforces methodology-specific
governance gates and continuously monitors project health.

Specification: docs_markdown/specs/agents/Agent 9 Project Lifecycle & Governance Agent.md
"""

from datetime import datetime
from typing import Any

from src.core.base_agent import BaseAgent


class ProjectLifecycleAgent(BaseAgent):
    """
    Project Lifecycle & Governance Agent - Manages project phases and health monitoring.

    Key Capabilities:
    - Project phase management and transitions
    - Methodology selection and adaptation
    - Phase gate definition and enforcement
    - Project health scoring and monitoring
    - State transitions and approvals
    - Governance compliance monitoring
    - Dashboard generation
    """

    def __init__(
        self,
        agent_id: str = "project-lifecycle-governance",
        config: dict[str, Any] | None = None,
    ):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.gate_criteria = config.get("gate_criteria", {}) if config else {}
        self.health_score_weights = (
            config.get(
                "health_score_weights",
                {"schedule": 0.25, "cost": 0.25, "risk": 0.20, "quality": 0.15, "resource": 0.15},
            )
            if config
            else {"schedule": 0.25, "cost": 0.25, "risk": 0.20, "quality": 0.15, "resource": 0.15}
        )
        self.monitoring_frequency = (
            config.get("monitoring_frequency", "hourly") if config else "hourly"
        )
        self.methodology_rules = config.get("methodology_rules", {}) if config else {}

        # Data stores (will be replaced with database connections)
        self.projects = {}  # type: ignore
        self.lifecycle_states = {}  # type: ignore
        self.health_scores = {}  # type: ignore
        self.gate_evaluations = {}  # type: ignore

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Project Lifecycle & Governance Agent...")

        # TODO: Initialize Azure Durable Functions for stateful workflows
        # TODO: Connect to Azure Cosmos DB for lifecycle state storage
        # TODO: Initialize Azure Machine Learning for readiness scoring models
        # TODO: Connect to Planview/Clarity PPM for lifecycle metadata sync
        # TODO: Initialize Jira/Azure DevOps integration for Agile sprint data
        # TODO: Set up Azure Service Bus/Event Grid for lifecycle event subscriptions
        # TODO: Connect to Azure Cognitive Services for dashboard summarization
        # TODO: Initialize Azure Monitor for health metrics collection

        self.logger.info("Project Lifecycle & Governance Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "initiate_project",
            "transition_phase",
            "evaluate_gate",
            "monitor_health",
            "recommend_methodology",
            "adjust_methodology",
            "get_project_status",
            "get_health_dashboard",
            "override_gate",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "initiate_project":
            project_data = input_data.get("project_data", {})
            required_fields = ["project_id", "name", "methodology"]
            for field in required_fields:
                if field not in project_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        elif action in ["transition_phase", "evaluate_gate", "override_gate"]:
            if "project_id" not in input_data:
                self.logger.warning("Missing project_id")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process project lifecycle and governance requests.

        Args:
            input_data: {
                "action": "initiate_project" | "transition_phase" | "evaluate_gate" |
                          "monitor_health" | "recommend_methodology" | "adjust_methodology" |
                          "get_project_status" | "get_health_dashboard" | "override_gate",
                "project_data": Project initialization data,
                "project_id": ID of existing project,
                "target_phase": Target phase for transition,
                "override_reason": Reason for gate override,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - initiate_project: Project ID, initial state, methodology map
            - transition_phase: Transition status, gate results, next steps
            - evaluate_gate: Gate criteria status, readiness score, gaps
            - monitor_health: Composite health score, metrics, alerts
            - recommend_methodology: Recommended methodology with rationale
            - adjust_methodology: Updated methodology configuration
            - get_project_status: Current phase, health, pending gates
            - get_health_dashboard: Complete dashboard data
            - override_gate: Override confirmation, audit record
        """
        action = input_data.get("action", "initiate_project")

        if action == "initiate_project":
            return await self._initiate_project(input_data.get("project_data", {}))

        elif action == "transition_phase":
            return await self._transition_phase(
                input_data.get("project_id"), input_data.get("target_phase")  # type: ignore
            )

        elif action == "evaluate_gate":
            return await self._evaluate_gate(
                input_data.get("project_id"), input_data.get("gate_name")  # type: ignore
            )

        elif action == "monitor_health":
            return await self._monitor_health(input_data.get("project_id"))  # type: ignore

        elif action == "recommend_methodology":
            return await self._recommend_methodology(input_data.get("project_data", {}))

        elif action == "adjust_methodology":
            return await self._adjust_methodology(
                input_data.get("project_id"), input_data.get("new_methodology")  # type: ignore
            )

        elif action == "get_project_status":
            return await self._get_project_status(input_data.get("project_id"))  # type: ignore

        elif action == "get_health_dashboard":
            return await self._get_health_dashboard(input_data.get("project_id"))  # type: ignore

        elif action == "override_gate":
            return await self._override_gate(
                input_data.get("project_id"),  # type: ignore
                input_data.get("gate_name"),  # type: ignore
                input_data.get("override_reason", ""),
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _initiate_project(self, project_data: dict[str, Any]) -> dict[str, Any]:
        """
        Initiate a new project and set initial lifecycle state.

        Returns project record and methodology map.
        """
        self.logger.info("Initiating project")

        project_id = project_data.get("project_id")
        name = project_data.get("name")
        methodology = project_data.get("methodology", "hybrid")

        # Select or validate methodology
        recommended_methodology = await self._recommend_methodology(project_data)
        if methodology != recommended_methodology.get("methodology"):
            self.logger.warning(
                f"Provided methodology '{methodology}' differs from recommended '{recommended_methodology.get('methodology')}'"
            )

        # Load methodology map
        methodology_map = await self._load_methodology_map(methodology)

        # Create project record
        project = {
            "project_id": project_id,
            "name": name,
            "methodology": methodology,
            "current_phase": methodology_map["initial_phase"],
            "phase_history": [],
            "created_at": datetime.utcnow().isoformat(),
            "status": "Active",
        }

        # Create initial lifecycle state
        lifecycle_state = {
            "project_id": project_id,
            "current_phase": methodology_map["initial_phase"],
            "phase_start_date": datetime.utcnow().isoformat(),
            "methodology_map": methodology_map,
            "transitions": [],
            "gates_passed": [],
            "gates_pending": [],
        }

        # Store project and state
        self.projects[project_id] = project
        self.lifecycle_states[project_id] = lifecycle_state

        # Trigger charter generation
        # TODO: Integrate with Project Definition Agent (Agent 8)

        # TODO: Store in Azure Cosmos DB
        # TODO: Publish project.initiated event to Service Bus

        self.logger.info(f"Initiated project: {project_id}")

        return {
            "project_id": project_id,
            "current_phase": methodology_map["initial_phase"],
            "methodology": methodology,
            "methodology_map": methodology_map,
            "next_steps": "Generate project charter and complete initiation activities",
        }

    async def _transition_phase(self, project_id: str, target_phase: str) -> dict[str, Any]:
        """
        Transition project to a new phase.

        Returns transition status and gate evaluation results.
        """
        self.logger.info(f"Attempting phase transition for project: {project_id}")

        lifecycle_state = self.lifecycle_states.get(project_id)
        if not lifecycle_state:
            raise ValueError(f"Lifecycle state not found for project: {project_id}")

        current_phase = lifecycle_state.get("current_phase")
        methodology_map = lifecycle_state.get("methodology_map", {})

        # Validate transition is allowed
        allowed_transitions = (
            methodology_map.get("phases", {}).get(current_phase, {}).get("next_phases", [])
        )
        if target_phase not in allowed_transitions:
            return {
                "success": False,
                "reason": f"Invalid transition from {current_phase} to {target_phase}",
                "allowed_transitions": allowed_transitions,
            }

        # Get gate name for this transition
        gate_name = await self._get_gate_name(current_phase, target_phase)

        # Evaluate gate criteria
        gate_evaluation = await self._evaluate_gate(project_id, gate_name)

        # Check if gate criteria are met
        if not gate_evaluation.get("criteria_met"):
            return {
                "success": False,
                "reason": "Gate criteria not met",
                "gate_evaluation": gate_evaluation,
                "missing_criteria": gate_evaluation.get("missing_criteria", []),
                "next_steps": "Complete missing activities or request override",
            }

        # Perform transition
        transition_record = {
            "from_phase": current_phase,
            "to_phase": target_phase,
            "gate_name": gate_name,
            "transitioned_at": datetime.utcnow().isoformat(),
            "transitioned_by": "system",  # TODO: Get from user context
        }

        lifecycle_state["current_phase"] = target_phase
        lifecycle_state["phase_start_date"] = datetime.utcnow().isoformat()
        lifecycle_state["transitions"].append(transition_record)
        lifecycle_state["gates_passed"].append(gate_name)

        # Update project
        self.projects[project_id]["current_phase"] = target_phase
        self.projects[project_id]["phase_history"].append(transition_record)

        # TODO: Update in Azure Cosmos DB
        # TODO: Publish project.transitioned event

        self.logger.info(
            f"Transitioned project {project_id} from {current_phase} to {target_phase}"
        )

        return {
            "success": True,
            "project_id": project_id,
            "previous_phase": current_phase,
            "current_phase": target_phase,
            "gate_evaluation": gate_evaluation,
            "transition_record": transition_record,
        }

    async def _evaluate_gate(self, project_id: str, gate_name: str) -> dict[str, Any]:
        """
        Evaluate phase gate criteria.

        Returns gate evaluation results and readiness score.
        """
        self.logger.info(f"Evaluating gate '{gate_name}' for project: {project_id}")

        lifecycle_state = self.lifecycle_states.get(project_id)
        if not lifecycle_state:
            raise ValueError(f"Lifecycle state not found for project: {project_id}")

        # Get gate criteria definition
        gate_criteria_def = await self._get_gate_criteria(gate_name)

        # Check each criterion
        criteria_status = []
        for criterion in gate_criteria_def:
            status = await self._check_criterion(project_id, criterion)
            criteria_status.append(
                {
                    "criterion": criterion,
                    "met": status,
                    "description": await self._get_criterion_description(criterion),
                }
            )

        # Calculate readiness score
        # TODO: Use ML model for readiness prediction
        readiness_score = (
            sum(1 for c in criteria_status if c["met"]) / len(criteria_status)
            if criteria_status
            else 0
        )

        # Identify missing criteria
        missing_criteria = [c for c in criteria_status if not c["met"]]

        # Determine if gate can be passed
        criteria_met = readiness_score >= 0.90  # 90% threshold

        evaluation = {
            "project_id": project_id,
            "gate_name": gate_name,
            "criteria_met": criteria_met,
            "readiness_score": readiness_score,
            "criteria_status": criteria_status,
            "missing_criteria": missing_criteria,
            "evaluated_at": datetime.utcnow().isoformat(),
            "recommendation": "Proceed" if criteria_met else "Complete missing activities",
        }

        # Store evaluation
        if project_id not in self.gate_evaluations:
            self.gate_evaluations[project_id] = []
        self.gate_evaluations[project_id].append(evaluation)

        # TODO: Store in database
        # TODO: Publish gate.evaluated event

        return evaluation

    async def _monitor_health(self, project_id: str) -> dict[str, Any]:
        """
        Monitor project health continuously.

        Returns composite health score and metrics.
        """
        self.logger.info(f"Monitoring health for project: {project_id}")

        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        # Gather metrics from domain agents
        # TODO: Integrate with Schedule & Planning Agent (Agent 10)
        # TODO: Integrate with Financial Management Agent (Agent 12)
        # TODO: Integrate with Risk Management Agent (Agent 15)
        # TODO: Integrate with Quality Assurance Agent (Agent 14)
        # TODO: Integrate with Resource & Capacity Management Agent (Agent 11)

        schedule_health = await self._get_schedule_health(project_id)
        cost_health = await self._get_cost_health(project_id)
        risk_health = await self._get_risk_health(project_id)
        quality_health = await self._get_quality_health(project_id)
        resource_health = await self._get_resource_health(project_id)

        # Calculate composite health score
        composite_score = (
            schedule_health * self.health_score_weights["schedule"]
            + cost_health * self.health_score_weights["cost"]
            + risk_health * self.health_score_weights["risk"]
            + quality_health * self.health_score_weights["quality"]
            + resource_health * self.health_score_weights["resource"]
        )

        # Determine health status
        health_status = await self._determine_health_status(composite_score)

        # Identify concerns and anomalies
        concerns = await self._identify_concerns(
            schedule_health, cost_health, risk_health, quality_health, resource_health
        )

        # Detect early warning signals
        warnings = await self._detect_warnings(project_id)

        # Generate recommendations
        recommendations = await self._generate_health_recommendations(
            composite_score, concerns, warnings
        )

        health_data = {
            "project_id": project_id,
            "composite_score": composite_score,
            "health_status": health_status,
            "metrics": {
                "schedule": {
                    "score": schedule_health,
                    "status": await self._get_metric_status(schedule_health),
                },
                "cost": {
                    "score": cost_health,
                    "status": await self._get_metric_status(cost_health),
                },
                "risk": {
                    "score": risk_health,
                    "status": await self._get_metric_status(risk_health),
                },
                "quality": {
                    "score": quality_health,
                    "status": await self._get_metric_status(quality_health),
                },
                "resource": {
                    "score": resource_health,
                    "status": await self._get_metric_status(resource_health),
                },
            },
            "concerns": concerns,
            "warnings": warnings,
            "recommendations": recommendations,
            "monitored_at": datetime.utcnow().isoformat(),
        }

        # Store health score
        self.health_scores[project_id] = health_data

        # TODO: Store in database
        # TODO: Publish health.updated event
        # TODO: Trigger alerts if health is critical

        return health_data

    async def _recommend_methodology(self, project_data: dict[str, Any]) -> dict[str, Any]:
        """
        Recommend appropriate methodology based on project characteristics.

        Returns recommended methodology with rationale.
        """
        self.logger.info("Recommending methodology")

        # Extract project characteristics
        project_data.get("size", "medium")
        complexity = project_data.get("complexity", "medium")
        requirement_volatility = project_data.get("requirement_volatility", "medium")
        stakeholder_engagement = project_data.get("stakeholder_engagement", "medium")
        regulatory_requirements = project_data.get("regulatory_requirements", False)

        # TODO: Use ML model for methodology recommendation
        # Simplified rule-based logic
        if requirement_volatility == "high" and stakeholder_engagement == "high":
            methodology = "agile"
            rationale = (
                "High requirement volatility and stakeholder engagement favor Agile approach"
            )
        elif regulatory_requirements or complexity == "high":
            methodology = "waterfall"
            rationale = "Regulatory requirements and high complexity favor Waterfall approach"
        else:
            methodology = "hybrid"
            rationale = "Mixed characteristics suggest Hybrid approach for optimal flexibility"

        return {
            "methodology": methodology,
            "rationale": rationale,
            "confidence": 0.85,
            "alternatives": await self._get_alternative_methodologies(methodology),
        }

    async def _adjust_methodology(self, project_id: str, new_methodology: str) -> dict[str, Any]:
        """
        Adjust project methodology.

        Returns updated methodology configuration.
        """
        self.logger.info(f"Adjusting methodology for project: {project_id}")

        lifecycle_state = self.lifecycle_states.get(project_id)
        if not lifecycle_state:
            raise ValueError(f"Lifecycle state not found for project: {project_id}")

        old_methodology = self.projects[project_id].get("methodology")

        # Load new methodology map
        new_methodology_map = await self._load_methodology_map(new_methodology)

        # Map current phase to equivalent in new methodology
        current_phase = lifecycle_state.get("current_phase")
        new_phase = await self._map_phase_to_methodology(
            current_phase, old_methodology, new_methodology
        )

        # Update project and lifecycle state
        self.projects[project_id]["methodology"] = new_methodology
        lifecycle_state["methodology_map"] = new_methodology_map
        lifecycle_state["current_phase"] = new_phase

        # TODO: Update in database
        # TODO: Publish methodology.adjusted event

        return {
            "project_id": project_id,
            "old_methodology": old_methodology,
            "new_methodology": new_methodology,
            "current_phase": new_phase,
            "methodology_map": new_methodology_map,
        }

    async def _get_project_status(self, project_id: str) -> dict[str, Any]:
        """Get current project status."""
        project = self.projects.get(project_id)
        lifecycle_state = self.lifecycle_states.get(project_id)

        if not project or not lifecycle_state:
            raise ValueError(f"Project not found: {project_id}")

        # Get health data
        health_data = self.health_scores.get(project_id, {})

        # Get pending gates
        pending_gates = await self._get_pending_gates(project_id)

        return {
            "project_id": project_id,
            "name": project.get("name"),
            "current_phase": project.get("current_phase"),
            "methodology": project.get("methodology"),
            "status": project.get("status"),
            "health_status": health_data.get("health_status", "Unknown"),
            "composite_score": health_data.get("composite_score", 0),
            "pending_gates": pending_gates,
            "phase_start_date": lifecycle_state.get("phase_start_date"),
            "transitions_count": len(lifecycle_state.get("transitions", [])),
        }

    async def _get_health_dashboard(self, project_id: str) -> dict[str, Any]:
        """Generate comprehensive health dashboard."""
        health_data = await self._monitor_health(project_id)
        project_status = await self._get_project_status(project_id)

        # Generate trend data
        # TODO: Query historical health scores
        trends = await self._generate_health_trends(project_id)

        # Generate alerts
        alerts = await self._generate_alerts(health_data)

        return {
            "project_id": project_id,
            "project_status": project_status,
            "health_data": health_data,
            "trends": trends,
            "alerts": alerts,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _override_gate(
        self, project_id: str, gate_name: str, override_reason: str
    ) -> dict[str, Any]:
        """
        Override a gate that doesn't meet criteria.

        Returns override confirmation and audit record.
        """
        self.logger.info(f"Overriding gate '{gate_name}' for project: {project_id}")

        # Evaluate gate first to document what's being overridden
        gate_evaluation = await self._evaluate_gate(project_id, gate_name)

        # Create override record
        override_record = {
            "project_id": project_id,
            "gate_name": gate_name,
            "gate_evaluation": gate_evaluation,
            "override_reason": override_reason,
            "overridden_by": "system",  # TODO: Get from user context
            "overridden_at": datetime.utcnow().isoformat(),
        }

        # Mark gate as passed despite not meeting criteria
        lifecycle_state = self.lifecycle_states.get(project_id)
        if lifecycle_state:
            lifecycle_state["gates_passed"].append(f"{gate_name} (OVERRIDDEN)")

        # TODO: Store override record in database
        # TODO: Publish gate.overridden event
        # TODO: Send notification to PMO and stakeholders

        self.logger.warning(f"Gate override recorded for {project_id}: {gate_name}")

        return {
            "success": True,
            "override_record": override_record,
            "warning": "Gate criteria were not met. Override has been recorded for audit.",
        }

    # Helper methods

    async def _load_methodology_map(self, methodology: str) -> dict[str, Any]:
        """Load methodology map with phases and gates."""
        # TODO: Load from configuration or database

        if methodology == "agile":
            return {
                "initial_phase": "Sprint 0",
                "phases": {
                    "Sprint 0": {
                        "name": "Sprint 0",
                        "next_phases": ["Sprint 1"],
                        "gates": ["sprint_planning_complete"],
                    },
                    "Sprint 1": {
                        "name": "Sprint 1",
                        "next_phases": ["Sprint 2", "Release"],
                        "gates": ["sprint_review", "sprint_retrospective"],
                    },
                    "Release": {
                        "name": "Release",
                        "next_phases": [],
                        "gates": ["release_criteria_met"],
                    },
                },
            }
        elif methodology == "waterfall":
            return {
                "initial_phase": "Initiate",
                "phases": {
                    "Initiate": {
                        "name": "Initiate",
                        "next_phases": ["Plan"],
                        "gates": ["charter_approved"],
                    },
                    "Plan": {
                        "name": "Plan",
                        "next_phases": ["Execute"],
                        "gates": ["baseline_approved"],
                    },
                    "Execute": {
                        "name": "Execute",
                        "next_phases": ["Monitor", "Close"],
                        "gates": ["deliverables_complete"],
                    },
                    "Monitor": {
                        "name": "Monitor",
                        "next_phases": ["Close"],
                        "gates": ["acceptance_complete"],
                    },
                    "Close": {"name": "Close", "next_phases": [], "gates": ["closure_approved"]},
                },
            }
        else:  # hybrid
            return {
                "initial_phase": "Initiate",
                "phases": {
                    "Initiate": {
                        "name": "Initiate",
                        "next_phases": ["Plan"],
                        "gates": ["charter_approved"],
                    },
                    "Plan": {
                        "name": "Plan",
                        "next_phases": ["Iterate"],
                        "gates": ["baseline_approved"],
                    },
                    "Iterate": {
                        "name": "Iterate",
                        "next_phases": ["Release", "Iterate"],
                        "gates": ["iteration_complete"],
                    },
                    "Release": {
                        "name": "Release",
                        "next_phases": ["Close"],
                        "gates": ["release_approved"],
                    },
                    "Close": {"name": "Close", "next_phases": [], "gates": ["closure_approved"]},
                },
            }

    async def _get_gate_name(self, from_phase: str, to_phase: str) -> str:
        """Get gate name for phase transition."""
        return f"{from_phase}_to_{to_phase}_gate"

    async def _get_gate_criteria(self, gate_name: str) -> list[str]:
        """Get criteria for a specific gate."""
        # TODO: Load from configuration
        # Simplified criteria
        if "charter" in gate_name.lower():
            return ["charter_document_complete", "charter_approved", "sponsor_assigned"]
        elif "baseline" in gate_name.lower():
            return ["scope_baseline_approved", "schedule_baseline_approved", "budget_approved"]
        else:
            return ["deliverables_complete", "quality_criteria_met"]

    async def _check_criterion(self, project_id: str, criterion: str) -> bool:
        """Check if a specific criterion is met."""
        # TODO: Implement actual criterion checking
        # Placeholder: randomly return True/False
        return True

    async def _get_criterion_description(self, criterion: str) -> str:
        """Get description for a criterion."""
        descriptions = {
            "charter_document_complete": "Project charter document is complete with all sections filled",
            "charter_approved": "Project charter has been approved by sponsor",
            "sponsor_assigned": "Project sponsor has been assigned",
            "scope_baseline_approved": "Scope baseline has been approved",
            "schedule_baseline_approved": "Schedule baseline has been approved",
            "budget_approved": "Project budget has been approved",
            "deliverables_complete": "All phase deliverables are complete",
            "quality_criteria_met": "Quality criteria have been met",
        }
        return descriptions.get(criterion, criterion)

    async def _get_schedule_health(self, project_id: str) -> float:
        """Get schedule health metric."""
        # TODO: Query Schedule & Planning Agent (Agent 10)
        return 0.85  # Placeholder

    async def _get_cost_health(self, project_id: str) -> float:
        """Get cost health metric."""
        # TODO: Query Financial Management Agent (Agent 12)
        return 0.90  # Placeholder

    async def _get_risk_health(self, project_id: str) -> float:
        """Get risk health metric."""
        # TODO: Query Risk Management Agent (Agent 15)
        return 0.75  # Placeholder

    async def _get_quality_health(self, project_id: str) -> float:
        """Get quality health metric."""
        # TODO: Query Quality Assurance Agent (Agent 14)
        return 0.88  # Placeholder

    async def _get_resource_health(self, project_id: str) -> float:
        """Get resource health metric."""
        # TODO: Query Resource & Capacity Management Agent (Agent 11)
        return 0.80  # Placeholder

    async def _determine_health_status(self, composite_score: float) -> str:
        """Determine health status from composite score."""
        if composite_score >= 0.85:
            return "Healthy"
        elif composite_score >= 0.70:
            return "At Risk"
        else:
            return "Critical"

    async def _get_metric_status(self, score: float) -> str:
        """Get status for individual metric."""
        if score >= 0.85:
            return "green"
        elif score >= 0.70:
            return "yellow"
        else:
            return "red"

    async def _identify_concerns(
        self, schedule: float, cost: float, risk: float, quality: float, resource: float
    ) -> list[str]:
        """Identify health concerns."""
        concerns = []
        if schedule < 0.70:
            concerns.append("Schedule variance exceeds acceptable threshold")
        if cost < 0.70:
            concerns.append("Cost variance indicates budget overrun risk")
        if risk < 0.70:
            concerns.append("High-priority risks not adequately mitigated")
        if quality < 0.70:
            concerns.append("Quality metrics below acceptable standards")
        if resource < 0.70:
            concerns.append("Resource constraints affecting delivery")
        return concerns

    async def _detect_warnings(self, project_id: str) -> list[dict[str, Any]]:
        """Detect early warning signals."""
        # TODO: Implement pattern recognition for warnings
        return []

    async def _generate_health_recommendations(
        self, composite_score: float, concerns: list[str], warnings: list[dict[str, Any]]
    ) -> list[str]:
        """Generate health improvement recommendations."""
        recommendations = []
        for concern in concerns:
            if "schedule" in concern.lower():
                recommendations.append(
                    "Review critical path and consider fast-tracking or crashing"
                )
            if "cost" in concern.lower():
                recommendations.append(
                    "Conduct budget review and identify cost reduction opportunities"
                )
            if "risk" in concern.lower():
                recommendations.append("Escalate high-priority risks to steering committee")
            if "quality" in concern.lower():
                recommendations.append("Implement additional quality controls and testing")
            if "resource" in concern.lower():
                recommendations.append("Review resource allocation and consider augmentation")
        return recommendations

    async def _get_alternative_methodologies(self, primary: str) -> list[str]:
        """Get alternative methodologies."""
        all_methodologies = ["agile", "waterfall", "hybrid"]
        return [m for m in all_methodologies if m != primary]

    async def _map_phase_to_methodology(
        self, current_phase: str, old_methodology: str, new_methodology: str
    ) -> str:
        """Map current phase to equivalent in new methodology."""
        # TODO: Implement intelligent phase mapping
        # Simplified mapping
        new_map = await self._load_methodology_map(new_methodology)
        return new_map["initial_phase"]  # type: ignore

    async def _get_pending_gates(self, project_id: str) -> list[str]:
        """Get list of pending gates."""
        lifecycle_state = self.lifecycle_states.get(project_id)
        if not lifecycle_state:
            return []

        current_phase = lifecycle_state.get("current_phase")
        methodology_map = lifecycle_state.get("methodology_map", {})

        phase_info = methodology_map.get("phases", {}).get(current_phase, {})
        return phase_info.get("gates", [])  # type: ignore

    async def _generate_health_trends(self, project_id: str) -> dict[str, Any]:
        """Generate health trend data."""
        # TODO: Query historical health scores
        return {
            "schedule_trend": "improving",
            "cost_trend": "stable",
            "risk_trend": "declining",
            "quality_trend": "improving",
            "resource_trend": "stable",
        }

    async def _generate_alerts(self, health_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate alerts based on health data."""
        alerts = []
        if health_data.get("health_status") == "Critical":
            alerts.append(
                {
                    "severity": "high",
                    "message": "Project health is critical. Immediate action required.",
                    "recommended_action": "Escalate to PMO and steering committee",
                }
            )
        return alerts

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Project Lifecycle & Governance Agent...")
        # TODO: Close database connections
        # TODO: Cancel monitoring timers
        # TODO: Close external API connections
        # TODO: Flush any pending events

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "project_initiation",
            "phase_management",
            "phase_transition",
            "gate_enforcement",
            "health_monitoring",
            "methodology_recommendation",
            "methodology_adaptation",
            "compliance_monitoring",
            "dashboard_generation",
            "early_warning_detection",
            "governance_reporting",
        ]
