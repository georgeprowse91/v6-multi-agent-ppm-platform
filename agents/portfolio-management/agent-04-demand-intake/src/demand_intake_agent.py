"""
Agent 4: Demand & Intake Agent

Purpose:
Captures incoming project requests, ideas, and change initiatives from stakeholders.
Manages the demand pipeline with automatic categorization and deduplication.

Specification: agents/portfolio-management/agent-04-demand-intake/README.md
"""

from datetime import datetime
from typing import Any

from agents.runtime import BaseAgent


class DemandIntakeAgent(BaseAgent):
    """
    Demand & Intake Agent - Manages demand capture and triage.

    Key Capabilities:
    - Multi-channel intake (email, web forms, Slack/Teams)
    - Automatic categorization using NLP
    - Duplicate detection via semantic similarity
    - Preliminary triage and screening
    - Pipeline visualization
    """

    def __init__(self, agent_id: str = "demand-intake", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)
        self.similarity_threshold = config.get("similarity_threshold", 0.85) if config else 0.85
        self.mandatory_fields = (
            config.get("mandatory_fields", ["title", "description", "business_objective"])
            if config
            else ["title", "description", "business_objective"]
        )

    async def initialize(self) -> None:
        """Initialize NLP models and database connections."""
        await super().initialize()
        self.logger.info("Loading classification and similarity models...")
        # Future work: Load Azure OpenAI for classification and embeddings
        # Future work: Initialize database connection for demand repository
        # Future work: Initialize vector search (Azure Cognitive Search)

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate intake request has required fields."""
        action = input_data.get("action", "")

        if action == "submit_request":
            request_data = input_data.get("request", {})
            for field in self.mandatory_fields:
                if field not in request_data or not request_data[field]:
                    self.logger.warning(f"Missing mandatory field: {field}")
                    return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process demand intake request.

        Args:
            input_data: {
                "action": "submit_request" | "check_duplicates" | "get_pipeline",
                "request": Request data (for submit_request),
                "filters": Filters for pipeline query
            }

        Returns:
            Response based on action:
            - submit_request: Demand ID, category, duplicates found
            - check_duplicates: List of similar existing requests
            - get_pipeline: Current demand pipeline status
        """
        action = input_data.get("action", "submit_request")

        if action == "submit_request":
            return await self._submit_request(input_data.get("request", {}))
        elif action == "check_duplicates":
            return await self._check_duplicates(input_data.get("request", {}))
        elif action == "get_pipeline":
            return await self._get_pipeline(input_data.get("filters", {}))
        else:
            raise ValueError(f"Unknown action: {action}")

    async def _submit_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """
        Submit a new demand intake request.

        Returns demand ID and categorization results.
        """
        self.logger.info("Processing new demand intake request")

        # Categorize the request
        category = await self._categorize_request(request_data)

        # Check for duplicates
        duplicates = await self._find_duplicates(request_data)

        # Generate demand ID
        demand_id = await self._generate_demand_id()

        # Store the request
        {
            "demand_id": demand_id,
            "title": request_data.get("title"),
            "description": request_data.get("description"),
            "business_objective": request_data.get("business_objective"),
            "category": category,
            "status": "Received",
            "created_at": datetime.utcnow().isoformat(),
            "created_by": request_data.get("requester", "unknown"),
            "business_unit": request_data.get("business_unit", ""),
            "urgency": request_data.get("urgency", "Medium"),
        }

        # Future work: Store in database
        self.logger.info(f"Created demand request: {demand_id}")

        # Send confirmation to requester
        # Future work: Integrate with notification system

        return {
            "demand_id": demand_id,
            "category": category,
            "status": "Received",
            "duplicates_found": len(duplicates) > 0,
            "similar_requests": duplicates[:5],  # Top 5 most similar
            "next_steps": "Request is in screening queue. You will be notified of status updates.",
        }

    async def _categorize_request(self, request_data: dict[str, Any]) -> str:
        """
        Automatically categorize the request using NLP.

        Returns category: "project", "change_request", "issue", "idea"
        """
        # Future work: Implement Azure OpenAI classification
        description = request_data.get("description", "").lower()
        title = request_data.get("title", "").lower()
        combined_text = f"{title} {description}"

        # Simple keyword-based classification (baseline)
        if any(word in combined_text for word in ["new system", "implementation", "initiative"]):
            return "project"
        elif any(word in combined_text for word in ["change", "update", "modify"]):
            return "change_request"
        elif any(word in combined_text for word in ["bug", "defect", "problem", "issue"]):
            return "issue"
        else:
            return "idea"

    async def _find_duplicates(self, request_data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Find similar existing requests using semantic similarity.

        Returns list of similar requests with similarity scores.
        """
        # Future work: Implement vector search using Azure Cognitive Search
        # For now, return empty list
        return []

    async def _check_duplicates(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """
        Check for duplicate requests without submitting.

        Returns list of similar requests.
        """
        duplicates = await self._find_duplicates(request_data)

        return {
            "duplicates_found": len(duplicates) > 0,
            "similar_requests": duplicates,
        }

    async def _get_pipeline(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Get current demand pipeline status.

        Returns pipeline statistics and items by stage.
        """
        # Future work: Query database for pipeline data
        # Baseline response
        return {
            "total_requests": 0,
            "by_status": {
                "Received": 0,
                "Screening": 0,
                "Analysis": 0,
                "Approved": 0,
                "Rejected": 0,
            },
            "by_category": {
                "project": 0,
                "change_request": 0,
                "issue": 0,
                "idea": 0,
            },
            "items": [],
        }

    async def _generate_demand_id(self) -> str:
        """Generate unique demand ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        # Future work: Add sequence number from database
        return f"DEM-{timestamp}"

    def get_capabilities(self) -> list[str]:
        """Return list of capabilities."""
        return [
            "multi_channel_intake",
            "automatic_categorization",
            "duplicate_detection",
            "preliminary_triage",
            "pipeline_visualization",
            "requester_communication",
        ]
