"""
Demand & Intake Agent

Purpose:
Captures incoming project requests, ideas, and change initiatives from stakeholders.
Manages the demand pipeline with automatic categorization and deduplication.

Specification: agents/portfolio-management/demand-intake-agent/README.md
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.bootstrap import ensure_monorepo_paths  # noqa: E402

ensure_monorepo_paths()

from data_quality.helpers import apply_rule_set, validate_against_schema  # noqa: E402
from demand_intake_actions import (  # noqa: E402
    check_duplicates as _act_check_duplicates,
)
from demand_intake_actions import (  # noqa: E402
    get_pipeline as _act_get_pipeline,
)
from demand_intake_actions import (  # noqa: E402
    submit_request as _act_submit_request,
)
from demand_intake_utils import (  # noqa: E402
    build_duplicate_rationale,
    combine_demand_text,
    cosine_similarity,
    generate_demand_id,
    semantic_similarity,
    strip_duplicate_rationale,
    tokenize,
)
from events import DemandCreatedEvent  # noqa: E402
from feature_flags import is_feature_enabled  # noqa: E402
from observability.tracing import get_trace_id  # noqa: E402

from agents.common.integration_services import (  # noqa: E402
    FaissBackedVectorSearchIndex,
    LocalEmbeddingService,
    NaiveBayesTextClassifier,
    NotificationService,
)
from agents.runtime import BaseAgent, get_event_bus  # noqa: E402
from agents.runtime.src.state_store import TenantStateStore  # noqa: E402


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

    def __init__(self, agent_id: str = "demand-intake-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)
        self.similarity_threshold = config.get("similarity_threshold", 0.85) if config else 0.85
        self.mandatory_fields = (
            config.get("mandatory_fields", ["title", "description", "business_objective"])
            if config
            else ["title", "description", "business_objective"]
        )
        store_path = (
            Path(config.get("demand_store_path", "data/demand_intake_store.json"))
            if config
            else Path("data/demand_intake_store.json")
        )
        self.demand_store = TenantStateStore(store_path)
        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            self.event_bus = get_event_bus()
        self.notification_service = NotificationService(self.event_bus)
        self.embedding_service = LocalEmbeddingService(
            dimensions=config.get("embedding_dimensions", 128) if config else 128
        )
        self.vector_index = FaissBackedVectorSearchIndex(
            self.embedding_service,
            index_name="demand_intake",
        )
        self.classifier = NaiveBayesTextClassifier(
            labels=["project", "change_request", "issue", "idea"]
        )
        environment = os.getenv("ENVIRONMENT", "dev")
        duplicate_resolution_flag = is_feature_enabled(
            "duplicate_resolution", environment=environment, default=False
        )
        self.duplicate_resolution_enabled = (
            config.get("duplicate_resolution_enabled", duplicate_resolution_flag)
            if config
            else duplicate_resolution_flag
        )
        self.demand_schema_path = Path(
            config.get("demand_schema_path", "data/schemas/demand.schema.json")
            if config
            else "data/schemas/demand.schema.json"
        )
        self.demand_rule_set = {
            "rules": [
                {
                    "id": "demand-required-fields",
                    "checks": [
                        {"field": "demand.title", "type": "required"},
                        {"field": "demand.description", "type": "required"},
                        {"field": "demand.business_objective", "type": "required"},
                    ],
                },
                {
                    "id": "demand-urgency-enum",
                    "checks": [
                        {
                            "field": "demand.urgency",
                            "type": "enum",
                            "values": ["Low", "Medium", "High", "Critical"],
                        }
                    ],
                },
            ]
        }
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
        training_samples = [
            ("new system implementation for finance", "project"),
            ("platform upgrade and modernization", "project"),
            ("change request for reporting dashboard", "change_request"),
            ("modify workflow approvals", "change_request"),
            ("bug in payroll processing", "issue"),
            ("system defect in billing", "issue"),
            ("idea for new analytics capability", "idea"),
            ("proposal for innovation lab", "idea"),
        ]
        self.classifier.fit(training_samples)
        existing_demands = self.demand_store.list("default")
        for item in existing_demands:
            text = self._combine_text(item)
            if item.get("demand_id"):
                self.vector_index.add(item["demand_id"], text, item)
        self.logger.info("Demand intake models and vector index ready.")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate intake request has required fields."""
        action = input_data.get("action", "")

        if action == "submit_request":
            request_data = input_data.get("request", {})
            if not await self._validate_request(request_data):
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
        context = input_data.get("context", {})
        correlation_id = (
            context.get("correlation_id") or input_data.get("correlation_id") or str(uuid.uuid4())
        )
        tenant_id = context.get("tenant_id") or input_data.get("tenant_id") or "unknown"

        if action == "submit_request":
            return await _act_submit_request(
                self,
                input_data.get("request", {}),
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
        elif action == "check_duplicates":
            return await _act_check_duplicates(
                self, input_data.get("request", {}), tenant_id=tenant_id
            )
        elif action == "get_pipeline":
            return await _act_get_pipeline(self, input_data.get("filters", {}), tenant_id=tenant_id)
        else:
            raise ValueError(f"Unknown action: {action}")

    async def _validate_request(self, request_data: dict[str, Any]) -> bool:
        payload = dict(request_data)
        payload.setdefault("urgency", "Medium")
        errors = validate_against_schema(self.demand_schema_path, payload)
        if errors:
            for error in errors:
                self.logger.warning("Schema validation error %s: %s", error.path, error.message)
            return False

        rule_result = apply_rule_set(self.demand_rule_set, {"demand": payload})
        if not rule_result.is_valid:
            for issue in rule_result.issues:
                self.logger.warning("Data quality issue %s: %s", issue.rule_id, issue.message)
            return False

        for field in self.mandatory_fields:
            if field not in request_data or not request_data[field]:
                self.logger.warning("Missing mandatory field: %s", field)
                return False

        return True

    async def _categorize_request(self, request_data: dict[str, Any]) -> str:
        """
        Automatically categorize the request using NLP.

        Returns category: "project", "change_request", "issue", "idea"
        """
        description = request_data.get("description", "")
        title = request_data.get("title", "")
        combined_text = f"{title} {description}"
        label, _scores = self.classifier.predict(combined_text)
        return label

    async def _find_duplicates(
        self,
        request_data: dict[str, Any],
        *,
        tenant_id: str,
        include_rationale: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Find similar existing requests using semantic similarity.

        Returns list of similar requests with similarity scores.
        """
        demands = self.demand_store.list(tenant_id)
        if not demands:
            return []

        candidate_text = self._combine_text(request_data)
        results = []
        for match in self.vector_index.search(candidate_text, top_k=10):
            if match.score >= self.similarity_threshold:
                metadata = match.metadata
                result = {
                    "demand_id": match.doc_id,
                    "title": metadata.get("title"),
                    "category": metadata.get("category"),
                    "similarity": round(match.score, 3),
                }
                if include_rationale:
                    result["rationale"] = self._build_duplicate_rationale(
                        request_data, metadata, match.score
                    )
                results.append(
                    {
                        **result,
                    }
                )

        def _similarity_key(item: dict[str, Any]) -> float:
            similarity = item.get("similarity")
            if similarity is None:
                return 0.0
            return float(similarity)

        results.sort(key=_similarity_key, reverse=True)
        return results

    def _combine_text(self, request_data: dict[str, Any]) -> str:
        """Delegate to utility function."""
        return combine_demand_text(request_data)

    def _build_duplicate_rationale(
        self, request_data: dict[str, Any], candidate_data: dict[str, Any], similarity: float
    ) -> dict[str, Any]:
        """Delegate to utility function."""
        return build_duplicate_rationale(
            request_data, candidate_data, similarity, frozenset(self.stopwords)
        )

    def _strip_duplicate_rationale(self, duplicates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Delegate to utility function."""
        return strip_duplicate_rationale(duplicates)

    def _semantic_similarity(self, query: str, corpus: list[str]) -> list[float]:
        """Delegate to utility function."""
        return semantic_similarity(query, corpus, frozenset(self.stopwords))

    def _tokenize(self, text: str) -> list[str]:
        """Delegate to utility function."""
        return tokenize(text, frozenset(self.stopwords))

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Delegate to utility function."""
        return cosine_similarity(a, b)

    async def _generate_demand_id(self) -> str:
        """Generate unique demand ID."""
        return generate_demand_id()

    async def _publish_demand_created(
        self, demand_item: dict[str, Any], *, tenant_id: str, correlation_id: str
    ) -> None:
        event = DemandCreatedEvent(
            event_name="demand.created",
            event_id=f"evt-{uuid.uuid4().hex}",
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            trace_id=get_trace_id(),
            payload={
                "demand_id": demand_item.get("demand_id", ""),
                "source": demand_item.get("source", "unknown"),
                "title": demand_item.get("title", ""),
                "submitted_by": demand_item.get("created_by", "unknown"),
                "submitted_at": datetime.fromisoformat(demand_item.get("created_at")),
            },
        )
        await self.event_bus.publish("demand.created", event.model_dump())

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
