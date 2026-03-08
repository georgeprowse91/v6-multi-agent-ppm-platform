"""
Knowledge & Document Management Agent

Purpose:
Serves as the central hub for creating, storing, classifying, retrieving and sharing
documents, decisions and lessons learned across the project portfolio.

Specification: agents/operations-management/knowledge-management-agent/README.md
"""

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jsonschema import ValidationError
from jsonschema import validate as jsonschema_validate

# Action handlers -----------------------------------------------------------
from knowledge_actions.classification_actions import (
    capture_lesson_learned as _act_capture_lesson_learned,
)
from knowledge_actions.classification_actions import (
    classify_document as _act_classify_document,
)
from knowledge_actions.classification_actions import (
    manage_taxonomy as _act_manage_taxonomy,
)
from knowledge_actions.classification_actions import (
    summarize_document as _act_summarize_document,
)
from knowledge_actions.collaboration_actions import (
    annotate_document as _act_annotate_document,
)
from knowledge_actions.collaboration_actions import (
    approve_document as _act_approve_document,
)
from knowledge_actions.collaboration_actions import (
    link_documents as _act_link_documents,
)
from knowledge_actions.collaboration_actions import (
    review_document as _act_review_document,
)
from knowledge_actions.document_actions import (
    delete_document as _act_delete_document,
)
from knowledge_actions.document_actions import (
    get_document as _act_get_document,
)
from knowledge_actions.document_actions import (
    get_document_version_history as _act_get_document_version_history,
)
from knowledge_actions.document_actions import (
    track_document_access as _act_track_document_access,
)
from knowledge_actions.document_actions import (
    update_document as _act_update_document,
)
from knowledge_actions.document_actions import (
    upload_document as _act_upload_document,
)
from knowledge_actions.ingestion_actions import (
    handle_cognitive_summary as _act_handle_cognitive_summary,
)
from knowledge_actions.ingestion_actions import (
    ingest_agent_output as _act_ingest_agent_output,
)
from knowledge_actions.ingestion_actions import (
    ingest_sources as _act_ingest_sources,
)
from knowledge_actions.knowledge_graph_actions import (
    build_knowledge_graph as _act_build_knowledge_graph,
)
from knowledge_actions.knowledge_graph_actions import (
    extract_entities as _act_extract_entities,
)
from knowledge_actions.knowledge_graph_actions import (
    query_knowledge_graph as _act_query_knowledge_graph,
)
from knowledge_actions.search_actions import (
    recommend_documents as _act_recommend_documents,
)
from knowledge_actions.search_actions import (
    search_documents as _act_search_documents,
)
from knowledge_db import KnowledgeDatabase
from knowledge_models import EntityExtractionPipeline, SemanticEmbeddingService
from knowledge_utils import (
    is_access_allowed,
    map_doc_type_for_schema,
    matches_search_filters,
    register_graph_edge,
    register_graph_node,
    traverse_graph,
    update_graph_for_document,
)
from prompt_registry import PromptRegistry

from agents.common.connector_integration import DocumentManagementService, DocumentMetadata
from agents.common.integration_services import (
    FaissBackedVectorSearchIndex,
    LocalEmbeddingService,
    NaiveBayesTextClassifier,
    VectorSearchIndex,
)
from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore
from packages.llm.prompt_sanitizer import detect_injection, sanitize_prompt


class KnowledgeManagementAgent(BaseAgent):
    """
    Knowledge & Document Management Agent - Manages organizational knowledge and documents.

    Key Capabilities:
    - Document repository and lifecycle management
    - Knowledge classification and taxonomy
    - Semantic search and discovery
    - Document summarization and extraction
    - Knowledge graph and linking
    - Lessons learned and best practices
    - Collaborative editing and reviews
    - Access control and permissions
    """

    _DEFAULT_DOC_TYPES = [
        "charter",
        "requirements",
        "design",
        "test_plan",
        "meeting_minutes",
        "lessons_learned",
        "policy",
        "procedure",
        "report",
    ]
    _DEFAULT_SUMMARY_PROMPT = (
        "Summarize the document below for enterprise knowledge retrieval. "
        "Limit output to {token_limit} tokens and keep factual points concise.\n\n"
        "Document:\n{text}"
    )

    def __init__(
        self, agent_id: str = "knowledge-management-agent", config: dict[str, Any] | None = None
    ):
        super().__init__(agent_id, config)
        _c = config or {}

        # Scalar configuration
        self.max_summary_length: int = _c.get("max_summary_length", 500)
        self.search_result_limit: int = _c.get("search_result_limit", 50)
        self.similarity_threshold: float = _c.get("similarity_threshold", 0.75)
        self.embedding_dimensions: int = _c.get("embedding_dimensions", 128)
        self.embedding_model: str = _c.get("embedding_model", "all-MiniLM-L6-v2")
        self.semantic_result_limit: int = _c.get("semantic_result_limit", 5)
        self.summary_token_limit: int = _c.get("summary_token_limit", 120)
        self.async_processing_enabled: bool = _c.get("async_processing_enabled", True)
        self.ingestion_max_files: int = _c.get("ingestion_max_files", 200)
        self.github_extensions: list[str] = _c.get("github_extensions", [".md", ".txt", ".rst"])
        self.document_types: list[str] = _c.get("document_types", self._DEFAULT_DOC_TYPES)
        self.summary_prompt_agent_id: str = _c.get("summary_prompt_agent_id", "knowledge-agent")
        self.summary_prompt_template: str = _c.get(
            "summary_prompt_template", self._DEFAULT_SUMMARY_PROMPT
        )

        # Persistent stores
        self.document_store = TenantStateStore(
            Path(_c.get("document_store_path", "data/knowledge_documents.json"))
        )
        self.document_schema = json.loads(
            Path(_c.get("document_schema_path", "data/schemas/document.schema.json")).read_text()
        )
        self.knowledge_db = KnowledgeDatabase(
            Path(_c.get("knowledge_db_path", "data/knowledge_management.db"))
        )

        # Event bus
        self.event_bus = _c.get("event_bus")
        if self.event_bus is None:
            try:
                self.event_bus = get_event_bus()
            except ValueError:
                self.event_bus = None

        # External services
        self.document_management_service = DocumentManagementService(config)
        self.prompt_registry = PromptRegistry()

        # Embedding / vector index
        fallback_embedding_service = LocalEmbeddingService(self.embedding_dimensions)
        self.embedding_service = SemanticEmbeddingService(
            self.embedding_model,
            fallback_service=fallback_embedding_service,
            encoder=_c.get("embedding_encoder"),
        )
        self.vector_store_backend: str = _c.get("vector_store_backend", "in_memory")
        if self.vector_store_backend == "faiss":
            self.vector_index = FaissBackedVectorSearchIndex(
                self.embedding_service,
                index_name="knowledge_agent",
                config_path=(
                    Path(_c["vector_store_config_path"])
                    if _c.get("vector_store_config_path")
                    else None
                ),
            )
        else:
            self.vector_index = VectorSearchIndex(self.embedding_service)

        # NLP components
        self.summarizer: Callable[[dict[str, Any]], Any] | None = _c.get("summarizer")
        self.entity_extractor = EntityExtractionPipeline(
            backend=_c.get("entity_extraction_backend", "auto"),
            custom_extractor=_c.get("entity_extractor"),
        )
        self.classifier = NaiveBayesTextClassifier(self.document_types)
        self.classifier_trained = False

        # Integration clients
        self._confluence_connector = None
        self.integration_clients: dict[str, Any] = _c.get("integration_clients", {})
        self.integration_status: dict[str, bool] = {}

        # In-memory data stores
        self.documents: dict[str, Any] = {}
        self.document_versions: dict[str, Any] = {}
        self.summaries: dict[str, Any] = {}
        self.knowledge_graph: dict[str, Any] = {}
        self.lessons_learned: dict[str, Any] = {}
        self.taxonomy: dict[str, Any] = {}
        self.document_annotations: dict[str, list[dict[str, Any]]] = {}
        self.document_reviews: dict[str, list[dict[str, Any]]] = {}
        self.document_approvals: dict[str, list[dict[str, Any]]] = {}
        self.graph_nodes: dict[str, dict[str, Any]] = {}
        self.graph_edges: list[dict[str, Any]] = []
        self.ingestion_runs: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        await super().initialize()
        self.logger.info("Initializing Knowledge & Document Management Agent...")
        self._register_integrations()
        self._train_classifier_seed()
        if self.event_bus and hasattr(self.event_bus, "subscribe"):
            self.event_bus.subscribe("cognitive.summary.created", self._handle_cognitive_summary)
            self.event_bus.subscribe("agent.summary.created", self._handle_cognitive_summary)
        self.logger.info("Knowledge & Document Management Agent initialized")

    async def cleanup(self) -> None:
        self.logger.info("Cleaning up Knowledge & Document Management Agent...")
        if self.event_bus and hasattr(self.event_bus, "stop"):
            await self.event_bus.stop()

    _VALID_ACTIONS = {
        "upload_document",
        "ingest_sources",
        "ingest_agent_output",
        "search_documents",
        "search_semantic",
        "get_document",
        "update_document",
        "delete_document",
        "classify_document",
        "summarize_document",
        "extract_entities",
        "build_knowledge_graph",
        "query_knowledge_graph",
        "capture_lesson_learned",
        "recommend_documents",
        "manage_taxonomy",
        "track_document_access",
        "get_document_version_history",
        "annotate_document",
        "review_document",
        "approve_document",
        "link_documents",
    }

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")
        if not action:
            self.logger.warning("No action specified")
            return False
        if action not in self._VALID_ACTIONS:
            self.logger.warning("Invalid action: %s", action)
            return False
        if action == "upload_document":
            doc = input_data.get("document", {})
            if not doc.get("title") or not doc.get("content"):
                self.logger.warning("Missing required document fields")
                return False
        elif action == "ingest_sources" and not input_data.get("sources"):
            self.logger.warning("Missing ingestion sources")
            return False
        elif action == "ingest_agent_output" and not input_data.get("payload"):
            self.logger.warning("Missing agent output payload")
            return False
        elif action in {"search_documents", "search_semantic"} and "query" not in input_data:
            self.logger.warning("Missing search query")
            return False
        return True

    # ------------------------------------------------------------------
    # Process (dispatch)
    # ------------------------------------------------------------------

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process knowledge and document management requests.

        Dispatches *input_data* to the appropriate action handler based on the
        ``action`` key.  Returns the handler's result dict unchanged.
        """
        action = input_data.get("action", "search_documents")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )
        access_context = input_data.get("access_context") or input_data.get("user_context") or {}
        doc_id = input_data.get("document_id")
        filters = input_data.get("filters", {})

        # fmt: off
        dispatch: dict[str, Any] = {
            "upload_document":             lambda: _act_upload_document(self, tenant_id, input_data.get("document", {})),
            "ingest_sources":              lambda: _act_ingest_sources(self, tenant_id, input_data.get("sources", [])),
            "ingest_agent_output":         lambda: _act_ingest_agent_output(self, tenant_id, input_data.get("payload", {})),
            "search_documents":            lambda: _act_search_documents(self, input_data.get("query"), filters, access_context, tenant_id),
            "search_semantic":             lambda: _act_search_documents(self, input_data.get("query"), filters, access_context, tenant_id),
            "get_document":                lambda: _act_get_document(self, doc_id, access_context, tenant_id),
            "update_document":             lambda: _act_update_document(self, doc_id, input_data.get("document", {}), tenant_id),
            "delete_document":             lambda: _act_delete_document(self, doc_id, tenant_id),
            "classify_document":           lambda: _act_classify_document(self, doc_id, tenant_id),
            "summarize_document":          lambda: _act_summarize_document(self, doc_id, tenant_id),
            "extract_entities":            lambda: _act_extract_entities(self, doc_id, tenant_id),
            "build_knowledge_graph":       lambda: _act_build_knowledge_graph(self, doc_id, tenant_id),
            "query_knowledge_graph":       lambda: _act_query_knowledge_graph(self, input_data.get("query", {})),
            "capture_lesson_learned":      lambda: _act_capture_lesson_learned(self, input_data.get("lesson", {})),
            "recommend_documents":         lambda: _act_recommend_documents(self, input_data.get("user_context", {})),
            "manage_taxonomy":             lambda: _act_manage_taxonomy(self, input_data.get("taxonomy", {})),
            "track_document_access":       lambda: _act_track_document_access(self, doc_id, tenant_id),
            "get_document_version_history": lambda: _act_get_document_version_history(self, doc_id, tenant_id),
            "annotate_document":           lambda: _act_annotate_document(self, doc_id, input_data.get("annotation", {}), access_context, tenant_id),
            "review_document":             lambda: _act_review_document(self, doc_id, input_data.get("review", {}), access_context, tenant_id),
            "approve_document":            lambda: _act_approve_document(self, doc_id, input_data.get("approval", {}), access_context, tenant_id),
            "link_documents":              lambda: _act_link_documents(self, input_data.get("links", []), tenant_id),
        }
        # fmt: on

        handler = dispatch.get(action)
        if handler is None:
            raise ValueError(f"Unknown action: {action}")
        return await handler()

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[str]:
        return [
            "document_repository",
            "document_versioning",
            "document_classification",
            "semantic_search",
            "document_summarization",
            "entity_extraction",
            "knowledge_graph",
            "knowledge_ingestion",
            "knowledge_graph_traversal",
            "lessons_learned_capture",
            "document_recommendations",
            "taxonomy_management",
            "collaborative_editing",
            "document_curation",
            "access_control",
            "audit_logging",
            "nlp_processing",
            "content_analysis",
        ]

    # ------------------------------------------------------------------
    # Internal infrastructure (called by action modules via ``agent.*``)
    # ------------------------------------------------------------------

    async def _handle_cognitive_summary(self, payload: dict[str, Any]) -> None:
        await _act_handle_cognitive_summary(self, payload)

    _SEED_SAMPLES = [
        ("project charter objectives scope", "charter"),
        ("functional requirements shall must", "requirements"),
        ("test plan verification validation", "test_plan"),
        ("lessons learned retrospective", "lessons_learned"),
        ("meeting minutes decisions action items", "meeting_minutes"),
        ("policy procedure compliance", "policy"),
        ("design specification architecture", "design"),
        ("status report metrics", "report"),
    ]

    def _train_classifier_seed(self) -> None:
        if self.classifier_trained:
            return
        self.classifier.fit(self._SEED_SAMPLES)
        self.classifier_trained = True

    def _update_classifier_with_document(self, document: dict[str, Any]) -> None:
        content, label = document.get("content"), document.get("type")
        if content and label:
            self.classifier.fit([(content, label)])
            self.classifier_trained = True

    def _index_document(self, document: dict[str, Any]) -> None:
        """Index document into the vector search index."""
        doc_id = document.get("document_id")
        if not doc_id:
            return
        combined = " ".join(
            [
                document.get("title", ""),
                document.get("content", ""),
                " ".join(document.get("tags", [])),
                document.get("topic") or "",
                document.get("domain") or "",
                json.dumps(document.get("metadata", {})),
            ]
        )
        self.vector_index.add(doc_id, combined, {"title": document.get("title")})

    async def _update_graph_for_document(self, document: dict[str, Any]) -> None:
        update_graph_for_document(document, self.graph_nodes, self.graph_edges)
        self.knowledge_db.upsert_graph(self.graph_nodes, self.graph_edges)

    def _register_graph_node(
        self, node_id: str, node_type: str, attributes: dict[str, Any]
    ) -> None:
        register_graph_node(self.graph_nodes, node_id, node_type, attributes)

    def _register_graph_edge(self, source: str, target: str, relation: str) -> None:
        register_graph_edge(self.graph_edges, source, target, relation)

    def _traverse_graph(
        self,
        start_node: str,
        relation: str | None = None,
        target_type: str | None = None,
        depth: int = 2,
    ) -> list[dict[str, Any]]:
        return traverse_graph(
            self.graph_nodes, self.graph_edges, start_node, relation, target_type, depth
        )

    async def _publish_event(self, topic: str, payload: dict[str, Any]) -> None:
        if not self.event_bus:
            return
        try:
            await self.event_bus.publish(topic, payload)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            self.logger.warning("Failed to publish event %s: %s", topic, exc)

    def _register_integrations(self) -> None:
        ic = self.integration_clients
        self.integration_status = {
            k: bool(ic.get(k))
            for k in [
                "blob_storage",
                "data_lake",
                "cognitive_search",
                "summarization",
                "sharepoint",
                "office_online",
                "form_recognizer",
                "git_repos",
                "rbac",
            ]
        }
        self.integration_status.update(
            {"metadata_db": True, "graph_store": True, "service_bus": self.event_bus is not None}
        )

    async def _publish_document_external(self, document: dict[str, Any]) -> None:
        if not self.document_management_service:
            return
        meta = DocumentMetadata(
            title=document.get("title", ""),
            description=document.get("description", ""),
            classification=document.get("classification", "internal"),
            tags=document.get("tags", []),
            owner=document.get("owner") or document.get("author") or "",
            retention_days=document.get("retention_days", 365),
        )
        await self.document_management_service.publish_document(
            document_content=document.get("content", ""), metadata=meta
        )

    async def summarise_document(self, text: str) -> str:
        """Create concise summary with prompt-injection sanitisation."""
        sanitized_text = sanitize_prompt(text)
        if detect_injection(text):
            self.logger.warning("Potential prompt injection detected; sanitized text used")
        prompt_template = self._load_summary_prompt_template()
        prompt = prompt_template.format(text=sanitized_text, token_limit=self.summary_token_limit)
        if self.summarizer:
            result = await self._invoke_summarizer(
                {"prompt": prompt, "text": sanitized_text, "max_tokens": self.summary_token_limit}
            )
            if result:
                return result
        return await self._generate_summary(
            sanitized_text, max(self.max_summary_length, self.summary_token_limit * 5)
        )

    async def _invoke_summarizer(self, payload: dict[str, Any]) -> str:
        if not self.summarizer:
            return ""
        response = self.summarizer(payload)
        if asyncio.iscoroutine(response):
            response = await response
        if isinstance(response, dict):
            return str(response.get("summary") or response.get("content") or "").strip()
        return str(response).strip()

    def _load_summary_prompt_template(self) -> str:
        try:
            record = self.prompt_registry.get_prompt_record(self.summary_prompt_agent_id)
            if "{text}" in record.content:
                return record.content
        except ValueError:
            pass
        return self.summary_prompt_template

    async def _generate_summary(self, content: str, max_length: int) -> str:
        if len(content) <= max_length:
            return content
        summary = ". ".join(content.split(". ")[:3])
        return summary[:max_length] + ("..." if len(summary) > max_length else "")

    async def _validate_document_schema(self, record: dict[str, Any]) -> None:
        try:
            jsonschema_validate(instance=record, schema=self.document_schema)
        except ValidationError as exc:
            raise ValueError(f"Document schema validation failed: {exc.message}") from exc

    async def _map_doc_type_for_schema(self, doc_type: str | None) -> str:
        return map_doc_type_for_schema(doc_type)

    async def _is_access_allowed(
        self, document: dict[str, Any], access_context: dict[str, Any]
    ) -> bool:
        return is_access_allowed(document, access_context)

    async def _matches_search_filters(
        self, document: dict[str, Any], filters: dict[str, Any]
    ) -> bool:
        return matches_search_filters(document, filters)

    # ------------------------------------------------------------------
    # Thin delegation wrappers (preserve API used by tests & other callers)
    # ------------------------------------------------------------------

    async def _upload_document(
        self, tenant_id: str, document_data: dict[str, Any]
    ) -> dict[str, Any]:
        return await _act_upload_document(self, tenant_id, document_data)

    async def _ingest_sources(
        self, tenant_id: str, sources: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return await _act_ingest_sources(self, tenant_id, sources)

    async def _search_documents(
        self, query: str, filters: dict[str, Any], access_context: dict[str, Any], tenant_id: str
    ) -> dict[str, Any]:
        return await _act_search_documents(self, query, filters, access_context, tenant_id)

    async def _extract_entities(self, document_id: str, tenant_id: str) -> dict[str, Any]:
        return await _act_extract_entities(self, document_id, tenant_id)

    async def _build_knowledge_graph(self, document_id: str, tenant_id: str) -> dict[str, Any]:
        return await _act_build_knowledge_graph(self, document_id, tenant_id)

    async def _annotate_document(
        self,
        document_id: str,
        annotation: dict[str, Any],
        access_context: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        return await _act_annotate_document(
            self, document_id, annotation, access_context, tenant_id
        )

    async def _review_document(
        self,
        document_id: str,
        review: dict[str, Any],
        access_context: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        return await _act_review_document(self, document_id, review, access_context, tenant_id)

    async def _approve_document(
        self,
        document_id: str,
        approval: dict[str, Any],
        access_context: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        return await _act_approve_document(self, document_id, approval, access_context, tenant_id)

    async def _generate_excerpts(
        self, results: list[dict[str, Any]], query: str
    ) -> list[dict[str, Any]]:
        from knowledge_actions.search_actions import _generate_excerpts

        return await _generate_excerpts(results, query)

    async def _extract_entities_from_text(self, text: str) -> list[dict[str, Any]]:
        return self.entity_extractor.extract(text, limit=20)

    def _load_document(self, tenant_id: str, document_id: str) -> dict[str, Any] | None:
        """Load document from memory or persistent store."""
        document = self.documents.get(document_id)
        if document:
            return document
        stored = self.document_store.get(tenant_id, document_id)
        if stored:
            self.documents[document_id] = stored
        return stored
