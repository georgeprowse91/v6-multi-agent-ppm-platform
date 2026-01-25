"""
Agent 11: Resource & Capacity Management Agent

Purpose:
Manages both supply of resources (people, equipment, skills) and demand from projects
and programs. Provides real-time insights into availability, utilization and skill gaps.

Specification: agents/delivery-management/agent-11-resource-capacity/README.md
"""

from datetime import datetime, timedelta
from typing import Any, cast

from agents.runtime import BaseAgent


class ResourceCapacityAgent(BaseAgent):
    """
    Resource & Capacity Management Agent - Manages resource pool, capacity planning, and allocation.

    Key Capabilities:
    - Centralized resource pool management
    - Demand intake and approval routing
    - Skill matching and intelligent search
    - Capacity planning and forecasting
    - Scenario modeling and what-if analysis
    - Role-based vs named assignments
    - Cross-project resource management
    - HR and timesheet system integration
    - Alerts and notifications for over-allocation
    """

    def __init__(
        self,
        agent_id: str = "resource-capacity-management",
        config: dict[str, Any] | None = None,
    ):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.max_allocation_threshold = (
            config.get("max_allocation_threshold", 1.0) if config else 1.0
        )
        self.skill_matching_threshold = (
            config.get("skill_matching_threshold", 0.70) if config else 0.70
        )
        self.forecast_horizon_months = config.get("forecast_horizon_months", 12) if config else 12
        self.utilization_target = config.get("utilization_target", 0.85) if config else 0.85

        # Data stores (will be replaced with database connections)
        self.resource_pool: dict[str, Any] = {}
        self.capacity_calendar: dict[str, Any] = {}
        self.allocations: dict[str, Any] = {}
        self.demand_requests: dict[str, Any] = {}
        self.utilization_metrics: dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize AI models, database connections, and external integrations."""
        await super().initialize()
        self.logger.info("Initializing Resource & Capacity Management Agent...")

        # TODO: Initialize Azure SQL Database for resource profiles and allocations
        # TODO: Connect to Azure Active Directory for employee data
        # TODO: Initialize SAP SuccessFactors/Workday integration for HR data
        # TODO: Connect to Planview Enterprise One/Jira Tempo for timesheet data
        # TODO: Initialize Azure Machine Learning for capacity forecasting models
        # TODO: Connect to Azure Cognitive Search for skill matching
        # TODO: Initialize Outlook/HR calendar integration for leave management
        # TODO: Set up Azure Service Bus/Event Grid for resource event notifications
        # TODO: Initialize Azure Redis Cache for real-time availability queries
        # TODO: Connect to learning management systems for training/certifications

        self.logger.info("Resource & Capacity Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "add_resource",
            "request_resource",
            "approve_request",
            "search_resources",
            "match_skills",
            "forecast_capacity",
            "plan_capacity",
            "scenario_analysis",
            "allocate_resource",
            "get_availability",
            "get_utilization",
            "identify_conflicts",
            "get_resource_pool",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "add_resource":
            resource_data = input_data.get("resource", {})
            required_fields = ["resource_id", "name", "role"]
            for field in required_fields:
                if field not in resource_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        elif action == "request_resource":
            request_data = input_data.get("request", {})
            required_fields = ["project_id", "required_skills", "start_date", "end_date"]
            for field in required_fields:
                if field not in request_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process resource and capacity management requests.

        Args:
            input_data: {
                "action": "add_resource" | "request_resource" | "approve_request" |
                          "search_resources" | "match_skills" | "forecast_capacity" |
                          "plan_capacity" | "scenario_analysis" | "allocate_resource" |
                          "get_availability" | "get_utilization" | "identify_conflicts" |
                          "get_resource_pool",
                "resource": Resource profile data,
                "request": Resource request data,
                "request_id": Request ID for approval,
                "search_criteria": Search criteria,
                "skills_required": Required skills for matching,
                "scenario_params": Scenario parameters,
                "allocation": Allocation details,
                "resource_id": Resource ID,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - add_resource: Resource ID, profile
            - request_resource: Request ID, recommended resources
            - approve_request: Approval status, allocated resource
            - search_resources: Matching resources with availability
            - match_skills: Ranked candidates with skill match scores
            - forecast_capacity: Capacity vs demand forecast
            - plan_capacity: Capacity plan with recommendations
            - scenario_analysis: Scenario comparison metrics
            - allocate_resource: Allocation ID, updated capacity
            - get_availability: Resource availability calendar
            - get_utilization: Utilization metrics and trends
            - identify_conflicts: Resource conflicts and recommendations
            - get_resource_pool: Complete resource pool data
        """
        action = input_data.get("action", "add_resource")

        if action == "add_resource":
            return await self._add_resource(input_data.get("resource", {}))

        elif action == "request_resource":
            return await self._request_resource(input_data.get("request", {}))

        elif action == "approve_request":
            request_id = input_data.get("request_id")
            assert isinstance(request_id, str), "request_id must be a string"
            return await self._approve_request(request_id, input_data.get("approval_decision", {}))

        elif action == "search_resources":
            return await self._search_resources(input_data.get("search_criteria", {}))

        elif action == "match_skills":
            return await self._match_skills(
                input_data.get("skills_required", []), input_data.get("project_context", {})
            )

        elif action == "forecast_capacity":
            return await self._forecast_capacity(input_data.get("filters", {}))

        elif action == "plan_capacity":
            return await self._plan_capacity(input_data.get("planning_horizon", {}))

        elif action == "scenario_analysis":
            return await self._scenario_analysis(input_data.get("scenario_params", {}))

        elif action == "allocate_resource":
            return await self._allocate_resource(input_data.get("allocation", {}))

        elif action == "get_availability":
            resource_id = input_data.get("resource_id")
            assert isinstance(resource_id, str), "resource_id must be a string"
            return await self._get_availability(resource_id, input_data.get("date_range", {}))

        elif action == "get_utilization":
            return await self._get_utilization(input_data.get("filters", {}))

        elif action == "identify_conflicts":
            return await self._identify_conflicts(input_data.get("filters", {}))

        elif action == "get_resource_pool":
            return await self._get_resource_pool(input_data.get("filters", {}))

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _add_resource(self, resource_data: dict[str, Any]) -> dict[str, Any]:
        """
        Add a resource to the pool.

        Returns resource ID and profile.
        """
        self.logger.info("Adding resource to pool")

        resource_id = resource_data.get("resource_id")
        assert isinstance(resource_id, str), "resource_id must be a string"
        name = resource_data.get("name")
        role = resource_data.get("role")
        skills = resource_data.get("skills", [])
        location = resource_data.get("location", "Unknown")
        cost_rate = resource_data.get("cost_rate", 0.0)
        certifications = resource_data.get("certifications", [])

        # Create resource profile
        resource_profile = {
            "resource_id": resource_id,
            "name": name,
            "role": role,
            "skills": skills,
            "location": location,
            "cost_rate": cost_rate,
            "certifications": certifications,
            "availability": 1.0,  # 100% available by default
            "team_memberships": resource_data.get("team_memberships", []),
            "created_at": datetime.utcnow().isoformat(),
            "status": "Active",
        }

        # Initialize capacity calendar
        self.capacity_calendar[resource_id] = {
            "resource_id": resource_id,
            "available_hours_per_day": 8,
            "working_days": [0, 1, 2, 3, 4],  # Monday-Friday
            "planned_leave": [],
            "holidays": [],
        }

        # Store resource
        self.resource_pool[resource_id] = resource_profile

        # TODO: Store in Azure SQL Database
        # TODO: Sync with Azure AD
        # TODO: Publish resource.added event

        self.logger.info(f"Added resource: {resource_id}")

        return {"resource_id": resource_id, "profile": resource_profile, "status": "Active"}

    async def _request_resource(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """
        Submit a resource request.

        Returns request ID and recommended resources.
        """
        self.logger.info("Processing resource request")

        # Generate unique request ID
        request_id = await self._generate_request_id()

        project_id = request_data.get("project_id")
        required_skills = request_data.get("required_skills", [])
        start_date = request_data.get("start_date")
        end_date = request_data.get("end_date")
        effort = request_data.get("effort", 1.0)  # FTE

        assert isinstance(start_date, str), "start_date must be a string"
        assert isinstance(end_date, str), "end_date must be a string"

        # Match skills and find candidates
        candidates = await self._match_skills(required_skills, {"project_id": project_id})

        # Check availability for each candidate
        available_candidates = []
        for candidate in candidates.get("candidates", []):
            availability = await self._check_availability(
                candidate["resource_id"], start_date, end_date, effort
            )

            if availability.get("is_available"):
                candidate["availability_windows"] = availability.get("windows", [])
                available_candidates.append(candidate)

        # Create request record
        request = {
            "request_id": request_id,
            "project_id": project_id,
            "required_skills": required_skills,
            "start_date": start_date,
            "end_date": end_date,
            "effort": effort,
            "requested_by": request_data.get("requested_by", "unknown"),
            "requested_at": datetime.utcnow().isoformat(),
            "status": "Pending",
            "recommended_candidates": available_candidates,
        }

        # Store request
        self.demand_requests[request_id] = request

        # Route to approver
        approver = await self._determine_approver(request)

        # TODO: Store in database
        # TODO: Send notification to approver
        # TODO: Publish resource_request.created event

        self.logger.info(f"Created resource request: {request_id}")

        return {
            "request_id": request_id,
            "status": "Pending",
            "recommended_candidates": available_candidates,
            "approver": approver,
            "next_steps": f"Request routed to {approver} for approval",
        }

    async def _approve_request(
        self, request_id: str, approval_decision: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Approve or reject a resource request.

        Returns approval status and allocation if approved.
        """
        self.logger.info(f"Processing approval for request: {request_id}")

        request = self.demand_requests.get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        approved = approval_decision.get("approved", False)
        selected_resource = approval_decision.get("selected_resource_id")
        comments = approval_decision.get("comments", "")

        if approved and selected_resource:
            # Create allocation
            allocation = await self._allocate_resource(
                {
                    "resource_id": selected_resource,
                    "project_id": request.get("project_id"),
                    "start_date": request.get("start_date"),
                    "end_date": request.get("end_date"),
                    "allocation_percentage": request.get("effort", 1.0) * 100,
                }
            )

            request["status"] = "Approved"
            request["approved_at"] = datetime.utcnow().isoformat()
            request["allocated_resource"] = selected_resource
            request["allocation_id"] = allocation.get("allocation_id")

            # Notify Schedule & Planning Agent
            # TODO: Integrate with Agent 10

            return {
                "request_id": request_id,
                "status": "Approved",
                "allocation": allocation,
                "comments": comments,
            }
        else:
            request["status"] = "Rejected"
            request["rejected_at"] = datetime.utcnow().isoformat()
            request["rejection_reason"] = comments

            # TODO: Notify requester
            # TODO: Publish resource_request.rejected event

            return {"request_id": request_id, "status": "Rejected", "rejection_reason": comments}

    async def _search_resources(self, search_criteria: dict[str, Any]) -> dict[str, Any]:
        """
        Search for resources by criteria.

        Returns matching resources.
        """
        self.logger.info("Searching for resources")

        role = search_criteria.get("role")
        location = search_criteria.get("location")
        skills = search_criteria.get("skills", [])
        availability_required = search_criteria.get("availability_required")

        matching_resources = []

        for resource_id, resource in self.resource_pool.items():
            # Check role
            if role and resource.get("role") != role:
                continue

            # Check location
            if location and resource.get("location") != location:
                continue

            # Check skills
            if skills:
                resource_skills = set(resource.get("skills", []))
                required_skills = set(skills)
                if not required_skills.issubset(resource_skills):
                    continue

            # Check availability if required
            if availability_required:
                if resource.get("availability", 0) < availability_required:
                    continue

            matching_resources.append(resource)

        return {
            "total_matches": len(matching_resources),
            "resources": matching_resources,
            "search_criteria": search_criteria,
        }

    async def _match_skills(
        self, skills_required: list[str], project_context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Match resources to required skills using AI.

        Returns ranked candidates with skill match scores.
        """
        self.logger.info("Matching skills to resources")

        # TODO: Use Azure Cognitive Search for semantic skill matching
        # TODO: Use NLP to parse skill descriptions

        candidates = []

        for resource_id, resource in self.resource_pool.items():
            resource_skills = set(resource.get("skills", []))
            required_skills = set(skills_required)

            # Calculate skill match score
            match_score = await self._calculate_skill_match_score(resource_skills, required_skills)

            # Get historical performance on similar projects
            # TODO: Query historical project data
            performance_score = await self._get_performance_score(resource_id, project_context)

            # Combined score
            combined_score = (match_score * 0.7) + (performance_score * 0.3)

            if combined_score >= self.skill_matching_threshold:
                candidates.append(
                    {
                        "resource_id": resource_id,
                        "resource_name": resource.get("name"),
                        "role": resource.get("role"),
                        "skills": list(resource_skills),
                        "match_score": match_score,
                        "performance_score": performance_score,
                        "combined_score": combined_score,
                        "cost_rate": resource.get("cost_rate"),
                    }
                )

        # Sort by combined score
        candidates.sort(key=lambda x: x["combined_score"], reverse=True)

        return {
            "skills_required": skills_required,
            "candidates": candidates,
            "total_candidates": len(candidates),
        }

    async def _forecast_capacity(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Forecast future capacity vs demand.

        Returns capacity forecast with bottlenecks.
        """
        self.logger.info("Forecasting capacity")

        # TODO: Use time-series ML model for forecasting (ARIMA, Prophet, LSTM)

        # Calculate current capacity
        current_capacity = await self._calculate_total_capacity()

        # Get current demand
        current_demand = await self._calculate_total_demand()

        # Forecast future capacity (accounting for attrition, hiring, etc.)
        future_capacity = await self._forecast_future_capacity(self.forecast_horizon_months)

        # Forecast future demand (from project pipeline)
        future_demand = await self._forecast_future_demand(self.forecast_horizon_months)

        # Identify bottlenecks
        bottlenecks = await self._identify_capacity_bottlenecks(future_capacity, future_demand)

        # Generate recommendations
        recommendations = await self._generate_capacity_recommendations(bottlenecks)

        return {
            "forecast_horizon_months": self.forecast_horizon_months,
            "current_capacity": current_capacity,
            "current_demand": current_demand,
            "current_utilization": current_demand / current_capacity if current_capacity > 0 else 0,
            "future_capacity": future_capacity,
            "future_demand": future_demand,
            "bottlenecks": bottlenecks,
            "recommendations": recommendations,
        }

    async def _plan_capacity(self, planning_horizon: dict[str, Any]) -> dict[str, Any]:
        """
        Create capacity plan.

        Returns capacity plan with allocation strategy.
        """
        self.logger.info("Planning capacity")

        # Get forecast
        forecast = await self._forecast_capacity({})

        # Identify gaps
        gaps = await self._identify_capacity_gaps(forecast)

        # Generate mitigation strategies
        strategies = await self._generate_mitigation_strategies(gaps)

        # Create capacity plan
        plan = {
            "planning_horizon": planning_horizon,
            "forecast": forecast,
            "gaps": gaps,
            "mitigation_strategies": strategies,
            "hiring_recommendations": await self._generate_hiring_recommendations(gaps),
            "training_recommendations": await self._generate_training_recommendations(gaps),
            "created_at": datetime.utcnow().isoformat(),
        }

        return plan

    async def _scenario_analysis(self, scenario_params: dict[str, Any]) -> dict[str, Any]:
        """
        Perform what-if scenario analysis.

        Returns scenario comparison metrics.
        """
        self.logger.info("Running scenario analysis")

        scenario_name = scenario_params.get("scenario_name", "Unnamed Scenario")
        changes = scenario_params.get("changes", {})

        # Create baseline scenario
        baseline = await self._create_baseline_scenario()

        # Apply changes to create new scenario
        scenario = await self._apply_scenario_changes(baseline, changes)

        # Calculate metrics for both scenarios
        baseline_metrics = await self._calculate_scenario_metrics(baseline)
        scenario_metrics = await self._calculate_scenario_metrics(scenario)

        # Compare scenarios
        comparison = await self._compare_scenarios(baseline_metrics, scenario_metrics)

        return {
            "scenario_name": scenario_name,
            "scenario_params": scenario_params,
            "baseline_metrics": baseline_metrics,
            "scenario_metrics": scenario_metrics,
            "comparison": comparison,
            "recommendation": await self._generate_scenario_recommendation(comparison),
        }

    async def _allocate_resource(self, allocation_data: dict[str, Any]) -> dict[str, Any]:
        """
        Allocate a resource to a project/task.

        Returns allocation ID and updated capacity.
        """
        self.logger.info("Allocating resource")

        # Generate unique allocation ID
        allocation_id = await self._generate_allocation_id()

        resource_id = allocation_data.get("resource_id")
        project_id = allocation_data.get("project_id")
        start_date = allocation_data.get("start_date")
        end_date = allocation_data.get("end_date")
        allocation_percentage = allocation_data.get("allocation_percentage", 100)

        assert isinstance(resource_id, str), "resource_id must be a string"
        assert isinstance(start_date, str), "start_date must be a string"
        assert isinstance(end_date, str), "end_date must be a string"

        # Validate allocation
        validation = await self._validate_allocation(
            resource_id, start_date, end_date, allocation_percentage
        )

        if not validation.get("valid"):
            raise ValueError(f"Invalid allocation: {validation.get('reason')}")

        # Create allocation record
        allocation = {
            "allocation_id": allocation_id,
            "resource_id": resource_id,
            "project_id": project_id,
            "start_date": start_date,
            "end_date": end_date,
            "allocation_percentage": allocation_percentage,
            "status": "Active",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store allocation
        if resource_id not in self.allocations:
            self.allocations[resource_id] = []
        self.allocations[resource_id].append(allocation)

        # Update resource availability
        await self._update_resource_availability(resource_id)

        # TODO: Store in database
        # TODO: Publish allocation.created event
        # TODO: Send notification to resource and project manager

        self.logger.info(f"Created allocation: {allocation_id}")

        return allocation

    async def _get_availability(
        self, resource_id: str, date_range: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Get resource availability for a date range.

        Returns availability calendar.
        """
        self.logger.info(f"Getting availability for resource: {resource_id}")

        resource = self.resource_pool.get(resource_id)
        if not resource:
            raise ValueError(f"Resource not found: {resource_id}")

        calendar = self.capacity_calendar.get(resource_id, {})
        allocations = self.allocations.get(resource_id, [])

        start_date_str = date_range.get("start_date")
        end_date_str = date_range.get("end_date")
        assert isinstance(start_date_str, str), "start_date must be a string"
        assert isinstance(end_date_str, str), "end_date must be a string"
        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str)

        # Calculate availability for each day in range
        availability_by_day = []
        current_date = start_date

        while current_date <= end_date:
            day_availability = await self._calculate_day_availability(
                resource_id, current_date, calendar, allocations
            )

            availability_by_day.append(day_availability)
            current_date += timedelta(days=1)

        return {
            "resource_id": resource_id,
            "resource_name": resource.get("name"),
            "date_range": date_range,
            "availability_by_day": availability_by_day,
            "average_availability": (
                sum(d.get("available_hours", 0) for d in availability_by_day)
                / len(availability_by_day)
                if availability_by_day
                else 0
            ),
        }

    async def _get_utilization(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Get utilization metrics.

        Returns utilization data and trends.
        """
        self.logger.info("Getting utilization metrics")

        # Calculate utilization for all resources
        utilization_data = []

        for resource_id, resource in self.resource_pool.items():
            utilization = await self._calculate_resource_utilization(resource_id)
            utilization_data.append(
                {
                    "resource_id": resource_id,
                    "resource_name": resource.get("name"),
                    "role": resource.get("role"),
                    "utilization": utilization,
                    "status": await self._get_utilization_status(utilization),
                }
            )

        # Calculate aggregate metrics
        average_utilization = (
            sum(u["utilization"] for u in utilization_data) / len(utilization_data)
            if utilization_data
            else 0
        )

        over_allocated = [u for u in utilization_data if u["utilization"] > 1.0]
        under_utilized = [u for u in utilization_data if u["utilization"] < 0.5]

        return {
            "total_resources": len(utilization_data),
            "average_utilization": average_utilization,
            "target_utilization": self.utilization_target,
            "utilization_variance": average_utilization - self.utilization_target,
            "over_allocated_count": len(over_allocated),
            "under_utilized_count": len(under_utilized),
            "over_allocated_resources": over_allocated,
            "under_utilized_resources": under_utilized,
            "utilization_by_resource": utilization_data,
        }

    async def _identify_conflicts(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Identify resource allocation conflicts.

        Returns conflicts and resolution recommendations.
        """
        self.logger.info("Identifying resource conflicts")

        conflicts = []

        for resource_id, resource_allocations in self.allocations.items():
            # Check for overlapping allocations
            for i, alloc1 in enumerate(resource_allocations):
                for alloc2 in resource_allocations[i + 1 :]:
                    overlap = await self._check_allocation_overlap(alloc1, alloc2)

                    if overlap.get("has_overlap"):
                        # Calculate over-allocation
                        total_allocation = alloc1.get("allocation_percentage", 0) + alloc2.get(
                            "allocation_percentage", 0
                        )

                        if total_allocation > 100:
                            conflicts.append(
                                {
                                    "resource_id": resource_id,
                                    "resource_name": self.resource_pool.get(resource_id, {}).get(
                                        "name"
                                    ),
                                    "allocation_1": alloc1,
                                    "allocation_2": alloc2,
                                    "overlap_period": overlap.get("period"),
                                    "over_allocation_percentage": total_allocation - 100,
                                    "severity": "high" if total_allocation > 150 else "medium",
                                }
                            )

        # Generate resolution recommendations
        recommendations = await self._generate_conflict_recommendations(conflicts)

        return {
            "total_conflicts": len(conflicts),
            "conflicts": conflicts,
            "recommendations": recommendations,
        }

    async def _get_resource_pool(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Retrieve resource pool data."""
        role_filter = filters.get("role")
        location_filter = filters.get("location")
        status_filter = filters.get("status", "Active")

        filtered_resources = []

        for resource_id, resource in self.resource_pool.items():
            if role_filter and resource.get("role") != role_filter:
                continue
            if location_filter and resource.get("location") != location_filter:
                continue
            if status_filter and resource.get("status") != status_filter:
                continue

            filtered_resources.append(resource)

        return {
            "total_resources": len(filtered_resources),
            "resources": filtered_resources,
            "filters_applied": filters,
        }

    # Helper methods

    async def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"REQ-{timestamp}"

    async def _generate_allocation_id(self) -> str:
        """Generate unique allocation ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"ALLOC-{timestamp}"

    async def _check_availability(
        self, resource_id: str, start_date: str, end_date: str, effort: float
    ) -> dict[str, Any]:
        """Check if resource is available for given period."""
        # TODO: Implement availability checking logic
        return {
            "is_available": True,
            "windows": [{"start": start_date, "end": end_date, "capacity": effort}],
        }

    async def _determine_approver(self, request: dict[str, Any]) -> str:
        """Determine who should approve the request."""
        # TODO: Implement approval routing logic
        return "resource_manager"

    async def _calculate_skill_match_score(
        self, resource_skills: set, required_skills: set
    ) -> float:
        """Calculate skill match score."""
        if not required_skills:
            return 1.0

        matching_skills = resource_skills.intersection(required_skills)
        match_score = len(matching_skills) / len(required_skills)
        return match_score

    async def _get_performance_score(
        self, resource_id: str, project_context: dict[str, Any]
    ) -> float:
        """Get historical performance score for resource."""
        # TODO: Query historical project performance data
        return 0.85  # Placeholder

    async def _calculate_total_capacity(self) -> float:
        """Calculate total resource capacity in FTE."""
        return len(self.resource_pool)  # Simplified

    async def _calculate_total_demand(self) -> float:
        """Calculate total resource demand in FTE."""
        total_demand = 0
        for allocations_list in self.allocations.values():
            for alloc in allocations_list:
                if alloc.get("status") == "Active":
                    total_demand += alloc.get("allocation_percentage", 0) / 100
        return total_demand

    async def _forecast_future_capacity(self, months: int) -> list[dict[str, Any]]:
        """Forecast future capacity."""
        # TODO: Use ML model for forecasting
        # Placeholder: assume constant capacity
        current_capacity = await self._calculate_total_capacity()
        return [{"month": i, "capacity": current_capacity} for i in range(months)]

    async def _forecast_future_demand(self, months: int) -> list[dict[str, Any]]:
        """Forecast future demand."""
        # TODO: Use ML model and project pipeline data
        # Placeholder
        return [
            {"month": i, "demand": 0.8 * await self._calculate_total_capacity()}
            for i in range(months)
        ]

    async def _identify_capacity_bottlenecks(
        self, capacity: list[dict[str, Any]], demand: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Identify capacity bottlenecks."""
        bottlenecks: list[dict[str, Any]] = []
        for i, (cap, dem) in enumerate(zip(capacity, demand)):
            dem_value = float(dem.get("demand", 0))
            cap_value = float(cap.get("capacity", 0))
            if dem_value > cap_value:
                bottlenecks.append(
                    {
                        "month": i,
                        "capacity": cap_value,
                        "demand": dem_value,
                        "shortfall": dem_value - cap_value,
                    }
                )
        return bottlenecks

    async def _generate_capacity_recommendations(
        self, bottlenecks: list[dict[str, Any]]
    ) -> list[str]:
        """Generate capacity recommendations."""
        recommendations = []
        if bottlenecks:
            recommendations.append(f"Capacity shortfall identified in {len(bottlenecks)} periods")
            recommendations.append("Consider hiring additional resources or outsourcing")
            recommendations.append("Review project priorities and timelines")
        return recommendations

    async def _identify_capacity_gaps(self, forecast: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify capacity gaps."""
        return forecast.get("bottlenecks", [])  # type: ignore

    async def _generate_mitigation_strategies(
        self, gaps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate mitigation strategies for capacity gaps."""
        return [
            {"strategy": "Hire permanent staff", "timeline": "3-6 months"},
            {"strategy": "Engage contractors", "timeline": "1-2 months"},
            {"strategy": "Cross-train existing staff", "timeline": "2-3 months"},
        ]

    async def _generate_hiring_recommendations(
        self, gaps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate hiring recommendations."""
        return [
            {"role": "Software Developer", "count": 2, "priority": "high"},
            {"role": "Project Manager", "count": 1, "priority": "medium"},
        ]

    async def _generate_training_recommendations(
        self, gaps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate training recommendations."""
        return [
            {"skill": "Cloud Architecture", "target_count": 3, "priority": "high"},
            {"skill": "Agile Methodologies", "target_count": 5, "priority": "medium"},
        ]

    async def _create_baseline_scenario(self) -> dict[str, Any]:
        """Create baseline scenario."""
        return {
            "resource_count": len(self.resource_pool),
            "allocations": self.allocations,
            "utilization": await self._calculate_total_demand()
            / await self._calculate_total_capacity(),
        }

    async def _apply_scenario_changes(
        self, baseline: dict[str, Any], changes: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply changes to create scenario."""
        scenario = baseline.copy()
        # TODO: Apply scenario changes
        return scenario

    async def _calculate_scenario_metrics(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Calculate metrics for scenario."""
        return {
            "average_utilization": scenario.get("utilization", 0),
            "resource_count": scenario.get("resource_count", 0),
        }

    async def _compare_scenarios(
        self, baseline: dict[str, Any], scenario: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare scenarios."""
        return {
            "utilization_difference": scenario.get("average_utilization", 0)
            - baseline.get("average_utilization", 0),
            "resource_count_difference": scenario.get("resource_count", 0)
            - baseline.get("resource_count", 0),
        }

    async def _generate_scenario_recommendation(self, comparison: dict[str, Any]) -> str:
        """Generate recommendation based on scenario comparison."""
        util_diff = comparison.get("utilization_difference", 0)
        if util_diff > 0.1:
            return "Scenario improves utilization significantly. Recommended."
        elif util_diff < -0.1:
            return "Scenario decreases utilization. Not recommended."
        else:
            return "Scenario has minimal impact on utilization."

    async def _validate_allocation(
        self, resource_id: str, start_date: str, end_date: str, allocation_percentage: float
    ) -> dict[str, Any]:
        """Validate allocation request."""
        # Check if resource exists
        if resource_id not in self.resource_pool:
            return {"valid": False, "reason": "Resource not found"}

        # Check if allocation percentage is valid
        if allocation_percentage <= 0 or allocation_percentage > 100:
            return {"valid": False, "reason": "Invalid allocation percentage"}

        # TODO: Check for conflicts with existing allocations

        return {"valid": True}

    async def _update_resource_availability(self, resource_id: str) -> None:
        """Update resource availability based on allocations."""
        allocations = self.allocations.get(resource_id, [])

        # Calculate total allocation
        total_allocation = sum(
            alloc.get("allocation_percentage", 0)
            for alloc in allocations
            if alloc.get("status") == "Active"
        )

        # Update availability
        availability = max(0, 100 - total_allocation) / 100
        self.resource_pool[resource_id]["availability"] = availability

    async def _calculate_day_availability(
        self,
        resource_id: str,
        date: datetime,
        calendar: dict[str, Any],
        allocations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Calculate availability for a specific day."""
        # Check if it's a working day
        weekday = date.weekday()
        if weekday not in calendar.get("working_days", []):
            return {"date": date.isoformat(), "available_hours": 0, "reason": "Non-working day"}

        # Check for leave or holidays
        # TODO: Implement leave/holiday checking

        # Calculate allocated hours
        allocated_hours = 0
        for alloc in allocations:
            alloc_start_str = alloc.get("start_date")
            alloc_end_str = alloc.get("end_date")
            if not isinstance(alloc_start_str, str) or not isinstance(alloc_end_str, str):
                continue
            alloc_start = datetime.fromisoformat(alloc_start_str)
            alloc_end = datetime.fromisoformat(alloc_end_str)

            if alloc_start <= date <= alloc_end:
                daily_hours = calendar.get("available_hours_per_day", 8)
                allocated_hours += daily_hours * (alloc.get("allocation_percentage", 0) / 100)

        # Calculate available hours
        total_hours = calendar.get("available_hours_per_day", 8)
        available_hours = max(0, total_hours - allocated_hours)

        return {
            "date": date.isoformat(),
            "total_hours": total_hours,
            "allocated_hours": allocated_hours,
            "available_hours": available_hours,
        }

    async def _calculate_resource_utilization(self, resource_id: str) -> float:
        """Calculate utilization for a resource."""
        allocations = self.allocations.get(resource_id, [])

        total_allocation = sum(
            float(alloc.get("allocation_percentage", 0))
            for alloc in allocations
            if alloc.get("status") == "Active"
        )

        return cast(float, total_allocation / 100)  # type: ignore

    async def _get_utilization_status(self, utilization: float) -> str:
        """Get utilization status."""
        if utilization > 1.0:
            return "Over-allocated"
        elif utilization >= self.utilization_target:
            return "Optimal"
        elif utilization >= 0.5:
            return "Under-utilized"
        else:
            return "Significantly Under-utilized"

    async def _check_allocation_overlap(
        self, alloc1: dict[str, Any], alloc2: dict[str, Any]
    ) -> dict[str, Any]:
        """Check if two allocations overlap."""
        start1_str = alloc1.get("start_date")
        end1_str = alloc1.get("end_date")
        start2_str = alloc2.get("start_date")
        end2_str = alloc2.get("end_date")
        assert isinstance(start1_str, str) and isinstance(
            end1_str, str
        ), "alloc1 dates must be strings"
        assert isinstance(start2_str, str) and isinstance(
            end2_str, str
        ), "alloc2 dates must be strings"
        start1 = datetime.fromisoformat(start1_str)
        end1 = datetime.fromisoformat(end1_str)
        start2 = datetime.fromisoformat(start2_str)
        end2 = datetime.fromisoformat(end2_str)

        # Check for overlap
        has_overlap = not (end1 < start2 or end2 < start1)

        if has_overlap:
            overlap_start = max(start1, start2)
            overlap_end = min(end1, end2)
            return {
                "has_overlap": True,
                "period": {"start": overlap_start.isoformat(), "end": overlap_end.isoformat()},
            }

        return {"has_overlap": False}

    async def _generate_conflict_recommendations(
        self, conflicts: list[dict[str, Any]]
    ) -> list[str]:
        """Generate recommendations for resolving conflicts."""
        recommendations = []
        for conflict in conflicts:
            severity = conflict.get("severity")
            if severity == "high":
                recommendations.append(
                    f"Critical: Resource {conflict.get('resource_name')} is over-allocated by "
                    f"{conflict.get('over_allocation_percentage')}%. "
                    "Consider reallocating or adding resources."
                )
        return recommendations

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Resource & Capacity Management Agent...")
        # TODO: Close database connections
        # TODO: Close external API connections
        # TODO: Flush any pending events

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "resource_pool_management",
            "demand_intake",
            "skill_matching",
            "capacity_planning",
            "capacity_forecasting",
            "scenario_modeling",
            "resource_allocation",
            "availability_tracking",
            "utilization_monitoring",
            "conflict_identification",
            "approval_routing",
            "cross_project_management",
            "what_if_analysis",
        ]
