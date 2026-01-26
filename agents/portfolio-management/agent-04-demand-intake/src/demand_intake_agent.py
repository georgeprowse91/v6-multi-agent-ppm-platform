"""
Agent 4: Demand & Intake Agent

Purpose:
Captures incoming project requests, ideas, and change initiatives from stakeholders.
Manages the demand pipeline with automatic categorization and deduplication.

Specification: agents/portfolio-management/agent-04-demand-intake/README.md
"""

import math
import re
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
        self.demands: list[dict[str, Any]] = []
        self.stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "for",
            "of",
            "in",
            "on",
            "with",
            "via",
            "from",
            "is",
            "are",
        }

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
        demand_item = {
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
        self.demands.append(demand_item)

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
        if not self.demands:
            return []

        candidate_text = self._combine_text(request_data)
        corpus = [self._combine_text(item) for item in self.demands]
        similarities = self._semantic_similarity(candidate_text, corpus)

        results = []
        for item, score in zip(self.demands, similarities):
            if score >= self.similarity_threshold:
                results.append(
                    {
                        "demand_id": item.get("demand_id"),
                        "title": item.get("title"),
                        "category": item.get("category"),
                        "similarity": round(score, 3),
                    }
                )

        def _similarity_key(item: dict[str, Any]) -> float:
            similarity = item.get("similarity")
            if similarity is None:
                return 0.0
            return float(similarity)

        results.sort(key=_similarity_key, reverse=True)
        return results

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
        query = filters.get("query", "")
        status_filter = filters.get("status")
        items = self.demands

        if status_filter:
            items = [item for item in items if item.get("status") == status_filter]

        if query:
            corpus = [self._combine_text(item) for item in items]
            scores = self._semantic_similarity(query, corpus)
            scored_items = [
                (item, score) for item, score in zip(items, scores) if score > 0.05
            ]
            scored_items.sort(key=lambda x: x[1], reverse=True)
            items = [item for item, _ in scored_items]

        by_status: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for item in self.demands:
            by_status[item.get("status", "Unknown")] = by_status.get(
                item.get("status", "Unknown"), 0
            ) + 1
            by_category[item.get("category", "unknown")] = by_category.get(
                item.get("category", "unknown"), 0
            ) + 1

        return {
            "total_requests": len(self.demands),
            "by_status": by_status,
            "by_category": by_category,
            "items": items,
        }

    def _combine_text(self, request_data: dict[str, Any]) -> str:
        title = request_data.get("title", "")
        description = request_data.get("description", "")
        objective = request_data.get("business_objective", "")
        return f"{title} {description} {objective}".strip().lower()

    def _semantic_similarity(self, query: str, corpus: list[str]) -> list[float]:
        tokens_list = [self._tokenize(text) for text in corpus + [query]]
        vocabulary = sorted({token for tokens in tokens_list for token in tokens})

        if not vocabulary:
            return [0.0 for _ in corpus]

        doc_freq = {term: 0 for term in vocabulary}
        for tokens in tokens_list:
            for term in set(tokens):
                doc_freq[term] += 1

        total_docs = len(tokens_list)
        idf = {term: math.log((total_docs + 1) / (doc_freq[term] + 1)) + 1 for term in vocabulary}

        vectors = []
        for tokens in tokens_list:
            term_counts: dict[str, int] = {}
            for token in tokens:
                term_counts[token] = term_counts.get(token, 0) + 1
            vector = [term_counts.get(term, 0) * idf[term] for term in vocabulary]
            vectors.append(vector)

        query_vector = vectors[-1]
        results = []
        for vector in vectors[:-1]:
            similarity = self._cosine_similarity(query_vector, vector)
            results.append(similarity)
        return results

    def _tokenize(self, text: str) -> list[str]:
        tokens = re.findall(r"[a-z0-9']+", text.lower())
        return [token for token in tokens if token and token not in self.stopwords]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

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
