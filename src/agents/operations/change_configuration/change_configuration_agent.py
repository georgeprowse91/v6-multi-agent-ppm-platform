"""
Agent 17: Change & Configuration Management Agent

Purpose:
Governs controlled introduction of changes to projects, programs and configuration items.
Ensures changes are assessed, approved, implemented and documented to minimize disruption
and preserve integrity. Maintains CMDB for project artifacts and infrastructure.

Specification: docs_markdown/specs/agents/operations/change-configuration/Agent 17 Change & Configuration Management Agent.md
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from src.core.base_agent import BaseAgent
import logging


class ChangeConfigurationAgent(BaseAgent):
    """
    Change & Configuration Management Agent - Manages changes and configuration items.

    Key Capabilities:
    - Change request intake and classification
    - Impact assessment and risk evaluation
    - Approval workflow orchestration
    - Configuration management database (CMDB)
    - Baseline and version control
    - Change implementation tracking
    - Change audit and history
    - Configuration visualization and dependency mapping
    """

    def __init__(
        self,
        agent_id: str = "agent_017",
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.change_types = config.get("change_types", [
            "normal", "standard", "emergency"
        ]) if config else ["normal", "standard", "emergency"]

        self.priority_levels = config.get("priority_levels", [
            "critical", "high", "medium", "low"
        ]) if config else ["critical", "high", "medium", "low"]

        self.baseline_threshold = config.get("baseline_threshold", 0.10) if config else 0.10

        # Data stores (will be replaced with database)
        self.change_requests = {}
        self.cmdb = {}  # Configuration items
        self.baselines = {}
        self.change_history = {}
        self.cab_meetings = {}

    async def initialize(self) -> None:
        """Initialize database connections, ITSM integrations, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Change & Configuration Management Agent...")

        # TODO: Initialize Azure Cosmos DB or SQL Database for change requests and CMDB
        # TODO: Connect to ITSM tools (ServiceNow, Jira Service Management, Azure DevOps, BMC Remedy)
        # TODO: Integrate with Git repositories (GitHub, GitLab, Azure Repos)
        # TODO: Connect to infrastructure as code tools (Terraform, Azure Blueprint)
        # TODO: Set up Azure Durable Functions or Logic Apps for workflow orchestration
        # TODO: Initialize Azure Machine Learning for change impact prediction
        # TODO: Connect to CI/CD tools (Jenkins, Azure DevOps Pipelines)
        # TODO: Integrate with document repositories (SharePoint, Confluence)
        # TODO: Set up Azure Service Bus for change event publishing
        # TODO: Initialize graph database features for CI dependency mapping

        self.logger.info("Change & Configuration Management Agent initialized")

    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "submit_change_request",
            "classify_change",
            "assess_impact",
            "approve_change",
            "register_ci",
            "create_baseline",
            "track_change_implementation",
            "audit_changes",
            "visualize_dependencies",
            "get_change_dashboard",
            "generate_change_report"
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "submit_change_request":
            change_data = input_data.get("change", {})
            required_fields = ["title", "description", "requester"]
            for field in required_fields:
                if field not in change_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        return True

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process change and configuration management requests.

        Args:
            input_data: {
                "action": "submit_change_request" | "classify_change" | "assess_impact" |
                          "approve_change" | "register_ci" | "create_baseline" |
                          "track_change_implementation" | "audit_changes" |
                          "visualize_dependencies" | "get_change_dashboard" |
                          "generate_change_report",
                "change": Change request data,
                "ci": Configuration item data,
                "baseline": Baseline data,
                "change_id": Change request ID,
                "ci_id": Configuration item ID,
                "filters": Query filters
            }

        Returns:
            Response based on action
        """
        action = input_data.get("action", "get_change_dashboard")

        if action == "submit_change_request":
            return await self._submit_change_request(input_data.get("change", {}))

        elif action == "classify_change":
            return await self._classify_change(input_data.get("change_id"))

        elif action == "assess_impact":
            return await self._assess_impact(input_data.get("change_id"))

        elif action == "approve_change":
            return await self._approve_change(
                input_data.get("change_id"),
                input_data.get("approval", {})
            )

        elif action == "register_ci":
            return await self._register_ci(input_data.get("ci", {}))

        elif action == "create_baseline":
            return await self._create_baseline(input_data.get("baseline", {}))

        elif action == "track_change_implementation":
            return await self._track_change_implementation(input_data.get("change_id"))

        elif action == "audit_changes":
            return await self._audit_changes(input_data.get("filters", {}))

        elif action == "visualize_dependencies":
            return await self._visualize_dependencies(input_data.get("ci_id"))

        elif action == "get_change_dashboard":
            return await self._get_change_dashboard(input_data.get("filters", {}))

        elif action == "generate_change_report":
            return await self._generate_change_report(
                input_data.get("report_type", "summary"),
                input_data.get("filters", {})
            )

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _submit_change_request(self, change_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit change request."""
        self.logger.info(f"Submitting change request: {change_data.get('title')}")

        # Generate change ID
        change_id = await self._generate_change_id()

        # Auto-classify change type
        change_type = await self._auto_classify_change_type(change_data)

        # Identify impacted CIs
        impacted_cis = await self._identify_impacted_cis(change_data)

        # Create change request
        change = {
            "change_id": change_id,
            "title": change_data.get("title"),
            "description": change_data.get("description"),
            "type": change_type,
            "priority": change_data.get("priority", "medium"),
            "requester": change_data.get("requester"),
            "project_id": change_data.get("project_id"),
            "impacted_cis": impacted_cis,
            "impact_assessment": None,
            "risk_assessment": None,
            "approval_status": "Pending",
            "status": "Submitted",
            "created_at": datetime.utcnow().isoformat()
        }

        # Store change
        self.change_requests[change_id] = change

        # TODO: Store in database
        # TODO: Route to appropriate approval workflow

        return {
            "change_id": change_id,
            "type": change_type,
            "status": "Submitted",
            "impacted_cis": len(impacted_cis),
            "next_steps": "Impact assessment will be performed"
        }

    async def _classify_change(self, change_id: str) -> Dict[str, Any]:
        """Classify change request using AI."""
        self.logger.info(f"Classifying change: {change_id}")

        change = self.change_requests.get(change_id)
        if not change:
            raise ValueError(f"Change request not found: {change_id}")

        # Use NLP to classify
        # TODO: Use Azure ML for classification
        classification = await self._auto_classify_change_type({
            "description": change.get("description")
        })

        # Update change
        change["type"] = classification
        change["routing"] = await self._determine_routing(classification)

        return {
            "change_id": change_id,
            "type": classification,
            "routing": change["routing"]
        }

    async def _assess_impact(self, change_id: str) -> Dict[str, Any]:
        """Assess change impact."""
        self.logger.info(f"Assessing impact for change: {change_id}")

        change = self.change_requests.get(change_id)
        if not change:
            raise ValueError(f"Change request not found: {change_id}")

        # Consult other agents for impact
        # TODO: Call Schedule, Resource, Financial agents
        schedule_impact = await self._assess_schedule_impact(change)
        cost_impact = await self._assess_cost_impact(change)
        resource_impact = await self._assess_resource_impact(change)
        risk_impact = await self._assess_risk_impact(change)

        # Analyze CI dependencies
        dependency_impact = await self._analyze_dependency_impact(change)

        # Predict change impact using AI
        # TODO: Use Azure ML for impact prediction
        predicted_impact = await self._predict_change_impact(change)

        impact_assessment = {
            "schedule_impact": schedule_impact,
            "cost_impact": cost_impact,
            "resource_impact": resource_impact,
            "risk_impact": risk_impact,
            "dependency_impact": dependency_impact,
            "predicted_impact": predicted_impact,
            "overall_risk_score": await self._calculate_overall_risk(
                schedule_impact, cost_impact, risk_impact
            ),
            "assessed_at": datetime.utcnow().isoformat()
        }

        # Update change
        change["impact_assessment"] = impact_assessment

        # TODO: Store in database

        return {
            "change_id": change_id,
            "impact_assessment": impact_assessment,
            "recommendation": await self._generate_impact_recommendation(impact_assessment)
        }

    async def _approve_change(
        self,
        change_id: str,
        approval_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Approve or reject change."""
        self.logger.info(f"Processing approval for change: {change_id}")

        change = self.change_requests.get(change_id)
        if not change:
            raise ValueError(f"Change request not found: {change_id}")

        # Record approval/rejection
        decision = approval_data.get("decision", "approve")
        approver = approval_data.get("approver")
        comments = approval_data.get("comments", "")

        change["approval_status"] = "Approved" if decision == "approve" else "Rejected"
        change["approved_by"] = approver
        change["approval_date"] = datetime.utcnow().isoformat()
        change["approval_comments"] = comments

        if decision == "approve":
            change["status"] = "Approved"
        else:
            change["status"] = "Rejected"

        # TODO: Store in database
        # TODO: Publish change.approved or change.rejected event

        return {
            "change_id": change_id,
            "approval_status": change["approval_status"],
            "approved_by": approver,
            "next_steps": "Proceed with implementation" if decision == "approve" else "Review and resubmit"
        }

    async def _register_ci(self, ci_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register configuration item in CMDB."""
        self.logger.info(f"Registering CI: {ci_data.get('name')}")

        # Generate CI ID
        ci_id = await self._generate_ci_id()

        # Create CI entry
        ci = {
            "ci_id": ci_id,
            "name": ci_data.get("name"),
            "type": ci_data.get("type"),  # hardware, software, document, requirement
            "version": ci_data.get("version", "1.0"),
            "owner": ci_data.get("owner"),
            "status": ci_data.get("status", "active"),
            "project_id": ci_data.get("project_id"),
            "relationships": ci_data.get("relationships", []),
            "attributes": ci_data.get("attributes", {}),
            "created_at": datetime.utcnow().isoformat(),
            "last_modified": datetime.utcnow().isoformat()
        }

        # Store CI
        self.cmdb[ci_id] = ci

        # TODO: Store in database with graph features

        return {
            "ci_id": ci_id,
            "name": ci["name"],
            "type": ci["type"],
            "version": ci["version"]
        }

    async def _create_baseline(self, baseline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create configuration baseline."""
        self.logger.info(f"Creating baseline: {baseline_data.get('description')}")

        # Generate baseline ID
        baseline_id = await self._generate_baseline_id()

        # Snapshot current CI versions
        ci_ids = baseline_data.get("ci_ids", [])
        ci_snapshot = {}
        for ci_id in ci_ids:
            ci = self.cmdb.get(ci_id)
            if ci:
                ci_snapshot[ci_id] = {
                    "name": ci.get("name"),
                    "version": ci.get("version"),
                    "attributes": ci.get("attributes", {}).copy()
                }

        # Create baseline
        baseline = {
            "baseline_id": baseline_id,
            "project_id": baseline_data.get("project_id"),
            "description": baseline_data.get("description"),
            "ci_snapshot": ci_snapshot,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": baseline_data.get("created_by", "unknown"),
            "locked": True
        }

        # Store baseline
        self.baselines[baseline_id] = baseline

        # TODO: Store in database

        return {
            "baseline_id": baseline_id,
            "description": baseline["description"],
            "ci_count": len(ci_snapshot),
            "created_at": baseline["created_at"]
        }

    async def _track_change_implementation(self, change_id: str) -> Dict[str, Any]:
        """Track change implementation progress."""
        self.logger.info(f"Tracking implementation for change: {change_id}")

        change = self.change_requests.get(change_id)
        if not change:
            raise ValueError(f"Change request not found: {change_id}")

        # Get implementation tasks
        # TODO: Integrate with task management system
        implementation_tasks = await self._get_implementation_tasks(change_id)

        # Calculate completion percentage
        total_tasks = len(implementation_tasks)
        completed_tasks = sum(1 for t in implementation_tasks if t.get("status") == "completed")
        completion_pct = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Update change status
        if completion_pct == 100:
            change["status"] = "Implemented"
            change["implemented_at"] = datetime.utcnow().isoformat()

        return {
            "change_id": change_id,
            "status": change["status"],
            "completion_percentage": completion_pct,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "implementation_tasks": implementation_tasks
        }

    async def _audit_changes(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Audit change history."""
        self.logger.info("Auditing changes")

        # Filter changes
        changes_to_audit = []
        for change_id, change in self.change_requests.items():
            if await self._matches_filters(change, filters):
                changes_to_audit.append(change)

        # Analyze change patterns
        patterns = await self._analyze_change_patterns(changes_to_audit)

        return {
            "total_changes": len(changes_to_audit),
            "approved_changes": len([c for c in changes_to_audit if c.get("approval_status") == "Approved"]),
            "rejected_changes": len([c for c in changes_to_audit if c.get("approval_status") == "Rejected"]),
            "emergency_changes": len([c for c in changes_to_audit if c.get("type") == "emergency"]),
            "patterns": patterns,
            "audit_date": datetime.utcnow().isoformat()
        }

    async def _visualize_dependencies(self, ci_id: Optional[str]) -> Dict[str, Any]:
        """Visualize CI dependencies."""
        self.logger.info(f"Visualizing dependencies for CI: {ci_id}")

        # Get CI and its dependencies
        if ci_id:
            ci = self.cmdb.get(ci_id)
            if not ci:
                raise ValueError(f"CI not found: {ci_id}")

            # Build dependency graph
            dependency_graph = await self._build_dependency_graph(ci_id)
        else:
            # Get full CMDB graph
            dependency_graph = await self._build_full_cmdb_graph()

        return {
            "ci_id": ci_id,
            "dependency_graph": dependency_graph,
            "node_count": len(dependency_graph.get("nodes", [])),
            "edge_count": len(dependency_graph.get("edges", []))
        }

    async def _get_change_dashboard(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get change dashboard data."""
        self.logger.info("Getting change dashboard")

        # Get open changes
        open_changes = []
        for change_id, change in self.change_requests.items():
            if change.get("status") in ["Submitted", "Approved", "In Progress"]:
                if await self._matches_filters(change, filters):
                    open_changes.append(change)

        # Get change statistics
        stats = await self._calculate_change_statistics(filters)

        # Get CAB workload
        cab_workload = await self._calculate_cab_workload()

        return {
            "open_changes": len(open_changes),
            "change_statistics": stats,
            "cab_workload": cab_workload,
            "recent_changes": open_changes[:10],
            "dashboard_generated_at": datetime.utcnow().isoformat()
        }

    async def _generate_change_report(
        self,
        report_type: str,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate change management report."""
        self.logger.info(f"Generating {report_type} change report")

        if report_type == "summary":
            return await self._generate_summary_report(filters)
        elif report_type == "audit":
            return await self._audit_changes(filters)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    # Helper methods

    async def _generate_change_id(self) -> str:
        """Generate unique change ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"CHG-{timestamp}"

    async def _generate_ci_id(self) -> str:
        """Generate unique CI ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"CI-{timestamp}"

    async def _generate_baseline_id(self) -> str:
        """Generate unique baseline ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"BL-{timestamp}"

    async def _auto_classify_change_type(self, change_data: Dict[str, Any]) -> str:
        """Auto-classify change type using NLP."""
        # TODO: Use Azure ML for classification
        description = change_data.get("description", "").lower()

        if "emergency" in description or "critical" in description:
            return "emergency"
        elif "standard" in description or "routine" in description:
            return "standard"
        else:
            return "normal"

    async def _identify_impacted_cis(self, change_data: Dict[str, Any]) -> List[str]:
        """Identify impacted configuration items."""
        # TODO: Use NLP and CMDB relationships
        return []

    async def _determine_routing(self, change_type: str) -> str:
        """Determine approval routing based on change type."""
        routing_map = {
            "emergency": "Emergency CAB",
            "standard": "Auto-Approved",
            "normal": "CAB Review"
        }
        return routing_map.get(change_type, "CAB Review")

    async def _assess_schedule_impact(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Assess schedule impact of change."""
        # TODO: Integrate with Schedule Agent
        return {"impact_days": 0, "critical_path_affected": False}

    async def _assess_cost_impact(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Assess cost impact of change."""
        # TODO: Integrate with Financial Agent
        return {"cost_variance": 0, "budget_available": True}

    async def _assess_resource_impact(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Assess resource impact of change."""
        # TODO: Integrate with Resource Agent
        return {"resources_required": [], "availability": True}

    async def _assess_risk_impact(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk impact of change."""
        # TODO: Integrate with Risk Management Agent
        return {"new_risks": [], "risk_score_increase": 0}

    async def _analyze_dependency_impact(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze CI dependency impact."""
        # TODO: Use graph analysis
        return {"dependent_cis": [], "cascading_impact": False}

    async def _predict_change_impact(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Predict change impact using ML."""
        # TODO: Use Azure ML
        return {"success_probability": 0.8, "predicted_duration": 5}

    async def _calculate_overall_risk(
        self,
        schedule_impact: Dict[str, Any],
        cost_impact: Dict[str, Any],
        risk_impact: Dict[str, Any]
    ) -> float:
        """Calculate overall risk score for change."""
        score = 0.0

        if schedule_impact.get("critical_path_affected"):
            score += 30

        if cost_impact.get("cost_variance", 0) > 10000:
            score += 20

        score += risk_impact.get("risk_score_increase", 0)

        return min(100, score)

    async def _generate_impact_recommendation(
        self,
        impact_assessment: Dict[str, Any]
    ) -> str:
        """Generate recommendation based on impact assessment."""
        risk_score = impact_assessment.get("overall_risk_score", 0)

        if risk_score > 70:
            return "High risk change. Recommend detailed review by CAB and additional testing."
        elif risk_score > 40:
            return "Medium risk change. Recommend standard CAB review and testing."
        else:
            return "Low risk change. Can proceed with standard approval process."

    async def _get_implementation_tasks(self, change_id: str) -> List[Dict[str, Any]]:
        """Get implementation tasks for change."""
        # TODO: Query task management system
        return []

    async def _matches_filters(self, change: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if change matches filters."""
        if "status" in filters and change.get("status") != filters["status"]:
            return False

        if "type" in filters and change.get("type") != filters["type"]:
            return False

        return True

    async def _analyze_change_patterns(
        self,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze patterns in changes."""
        # TODO: Perform pattern analysis
        return {
            "most_common_type": "normal",
            "average_approval_time_days": 3,
            "rejection_rate": 0.15
        }

    async def _build_dependency_graph(self, ci_id: str) -> Dict[str, Any]:
        """Build dependency graph for CI."""
        # TODO: Use graph algorithms
        return {
            "nodes": [{"id": ci_id, "label": "CI"}],
            "edges": []
        }

    async def _build_full_cmdb_graph(self) -> Dict[str, Any]:
        """Build full CMDB dependency graph."""
        nodes = []
        edges = []

        for ci_id, ci in self.cmdb.items():
            nodes.append({
                "id": ci_id,
                "label": ci.get("name"),
                "type": ci.get("type")
            })

            for rel in ci.get("relationships", []):
                edges.append({
                    "source": ci_id,
                    "target": rel.get("target_ci_id"),
                    "type": rel.get("relationship_type")
                })

        return {"nodes": nodes, "edges": edges}

    async def _calculate_change_statistics(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate change statistics."""
        # TODO: Aggregate statistics
        return {
            "total_changes": 0,
            "approved_rate": 0,
            "average_lead_time": 0
        }

    async def _calculate_cab_workload(self) -> Dict[str, Any]:
        """Calculate CAB workload."""
        # TODO: Analyze pending changes
        return {
            "pending_reviews": 0,
            "next_meeting": None
        }

    async def _generate_summary_report(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary change report."""
        return {
            "report_type": "summary",
            "data": {},
            "generated_at": datetime.utcnow().isoformat()
        }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Change & Configuration Management Agent...")
        # TODO: Close database connections
        # TODO: Close ITSM connections
        # TODO: Flush any pending events

    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities."""
        return [
            "change_request_intake",
            "change_classification",
            "change_impact_prediction",
            "impact_assessment",
            "risk_evaluation",
            "approval_workflow_orchestration",
            "cmdb_management",
            "ci_registration",
            "baseline_management",
            "version_control",
            "change_implementation_tracking",
            "change_audit",
            "dependency_mapping",
            "configuration_visualization",
            "change_dashboards",
            "change_reporting"
        ]
