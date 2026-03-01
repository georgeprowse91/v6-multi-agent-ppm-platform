"""
Agent 19: Knowledge & Document Management Agent

Purpose:
Serves as the central hub for creating, storing, classifying, retrieving and sharing
documents, decisions and lessons learned across the project portfolio.

Specification: agents/operations-management/agent-19-knowledge-document-management/README.md
"""

import asyncio
import json
import os
import re
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from knowledge_db import KnowledgeDatabase

from agents.common.connector_integration import (
    ConnectorCategory,
    ConnectorConfig,
    DocumentManagementService,
    DocumentMetadata,
)
from agents.common.integration_services import (
    FaissBackedVectorSearchIndex,
    LocalEmbeddingService,
    NaiveBayesTextClassifier,
    VectorSearchIndex,
)
from agents.runtime import BaseAgent, get_event_bus
from agents.runtime.src.state_store import TenantStateStore
from jsonschema import ValidationError
from jsonschema import validate as jsonschema_validate
from packages.llm.prompt_sanitizer import detect_injection, sanitize_prompt
from prompt_registry import PromptRegistry

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - optional runtime dependency
    SentenceTransformer = None

try:
    import spacy
except ImportError:  # pragma: no cover - optional runtime dependency
    spacy = None


class SemanticEmbeddingService:
    """Embedding service backed by sentence-transformers with local fallback."""

    def __init__(
        self,
        model_name: str,
        fallback_service: LocalEmbeddingService,
        encoder: Any | None = None,
    ) -> None:
        self.model_name = model_name
        self.fallback_service = fallback_service
        self.encoder = encoder
        self.dimensions = fallback_service.dimensions

        if self.encoder is None and SentenceTransformer is not None:
            try:
                self.encoder = SentenceTransformer(model_name)
                dim_getter = getattr(self.encoder, "get_sentence_embedding_dimension", None)
                if callable(dim_getter):
                    self.dimensions = int(dim_getter())
            except (RuntimeError, ValueError, OSError) as exc:
                self.encoder = None
                self._load_error = str(exc)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.encoder is None:
            return self.fallback_service.embed(texts)
        vectors = self.encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return vectors.tolist()


class EntityExtractionPipeline:
    """Pluggable entity extraction with optional NLP backend and deterministic fallback."""

    PROJECT_ID_PATTERN = re.compile(r"\b(?:PRJ|PROJ|PROJECT)[-_]?[0-9]{2,6}\b", flags=re.IGNORECASE)
    DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
    ORG_PATTERN = re.compile(
        r"\b([A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*)*\s+(?:Inc|LLC|Ltd|Corp|Corporation|Company|Group|Systems|Technologies))\b"
    )
    PERSON_PATTERN = re.compile(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b")

    def __init__(
        self,
        backend: str = "auto",
        custom_extractor: Callable[[str], list[dict[str, Any]]] | None = None,
    ):
        self.backend = backend
        self.custom_extractor = custom_extractor
        self._nlp_model = None
        self._nlp_available = False
        if backend in {"auto", "spacy"} and spacy is not None:
            try:
                self._nlp_model = spacy.load("en_core_web_sm")
                self._nlp_available = True
            except (OSError, ValueError):
                self._nlp_model = None

    def extract(self, text: str, limit: int = 20) -> list[dict[str, Any]]:
        if not text:
            return []

        entities: list[dict[str, Any]]
        if self.custom_extractor is not None:
            entities = self._normalize_entities(self.custom_extractor(text), text)
        elif self._nlp_available and self.backend != "fallback":
            entities = self._extract_with_spacy(text)
        else:
            entities = self._extract_with_fallback(text)

        entities.sort(key=lambda item: (item["position"], -item["score"], item["text"]))
        return entities[:limit]

    def _extract_with_spacy(self, text: str) -> list[dict[str, Any]]:
        doc = self._nlp_model(text)
        mapped = {"PERSON": "person", "ORG": "organization", "DATE": "date"}
        entities = []
        for ent in doc.ents:
            mapped_type = mapped.get(ent.label_)
            if not mapped_type:
                continue
            entities.append(
                {
                    "text": ent.text.strip(),
                    "type": mapped_type,
                    "score": 0.85,
                    "position": int(ent.start_char),
                    "span": {"start": int(ent.start_char), "end": int(ent.end_char)},
                }
            )

        # Ensure project IDs are included even when backend misses domain-specific formats.
        entities.extend(self._regex_entities(text, only_types={"project_id"}, score=0.92))
        return self._deduplicate(entities)

    def _extract_with_fallback(self, text: str) -> list[dict[str, Any]]:
        entities = self._regex_entities(text, score=0.78)
        return self._deduplicate(entities)

    def _regex_entities(
        self,
        text: str,
        *,
        only_types: set[str] | None = None,
        score: float,
    ) -> list[dict[str, Any]]:
        specs = [
            (
                self.PROJECT_ID_PATTERN,
                "project_id",
                lambda value: value.upper().replace("PROJECT", "PRJ"),
            ),
            (self.DATE_PATTERN, "date", lambda value: value),
            (self.ORG_PATTERN, "organization", lambda value: value),
            (self.PERSON_PATTERN, "person", lambda value: value),
        ]
        entities: list[dict[str, Any]] = []
        for pattern, ent_type, normalizer in specs:
            if only_types and ent_type not in only_types:
                continue
            for match in pattern.finditer(text):
                extracted = match.group(1) if match.lastindex else match.group(0)
                normalized_text = normalizer(extracted.strip())
                entities.append(
                    {
                        "text": normalized_text,
                        "type": ent_type,
                        "score": score,
                        "position": int(match.start()),
                        "span": {"start": int(match.start()), "end": int(match.end())},
                    }
                )
        return entities

    def _normalize_entities(
        self, entities: list[dict[str, Any]], text: str
    ) -> list[dict[str, Any]]:
        normalized = []
        for entity in entities:
            raw_text = str(entity.get("text", "")).strip()
            if not raw_text:
                continue
            start = entity.get("position")
            span = entity.get("span") if isinstance(entity.get("span"), dict) else {}
            start = int(span.get("start", start if isinstance(start, int) else text.find(raw_text)))
            end = int(span.get("end", max(start + len(raw_text), start)))
            normalized.append(
                {
                    "text": raw_text,
                    "type": str(entity.get("type", "entity")).lower(),
                    "score": float(entity.get("score", entity.get("confidence", 0.5))),
                    "position": start,
                    "span": {"start": start, "end": end},
                }
            )
        return self._deduplicate(normalized)

    def _deduplicate(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        best: dict[tuple[str, str, int, int], dict[str, Any]] = {}
        for entity in entities:
            span = entity.get("span", {})
            key = (
                entity.get("text", "").strip(),
                entity.get("type", "entity"),
                int(span.get("start", entity.get("position", 0))),
                int(span.get("end", entity.get("position", 0))),
            )
            existing = best.get(key)
            if existing is None or entity.get("score", 0.0) > existing.get("score", 0.0):
                best[key] = entity
        return list(best.values())


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

    def __init__(self, agent_id: str = "knowledge-management-agent", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.max_summary_length = config.get("max_summary_length", 500) if config else 500
        self.search_result_limit = config.get("search_result_limit", 50) if config else 50
        self.similarity_threshold = config.get("similarity_threshold", 0.75) if config else 0.75
        self.embedding_dimensions = config.get("embedding_dimensions", 128) if config else 128
        self.embedding_model = (
            config.get("embedding_model", "all-MiniLM-L6-v2") if config else "all-MiniLM-L6-v2"
        )
        self.semantic_result_limit = config.get("semantic_result_limit", 5) if config else 5
        self.summary_token_limit = config.get("summary_token_limit", 120) if config else 120

        document_store_path = (
            Path(config.get("document_store_path", "data/knowledge_documents.json"))
            if config
            else Path("data/knowledge_documents.json")
        )
        knowledge_db_path = (
            Path(config.get("knowledge_db_path", "data/knowledge_management.db"))
            if config
            else Path("data/knowledge_management.db")
        )
        schema_path = (
            Path(config.get("document_schema_path", "data/schemas/document.schema.json"))
            if config
            else Path("data/schemas/document.schema.json")
        )

        self.document_store = TenantStateStore(document_store_path)
        self.document_schema = json.loads(schema_path.read_text())
        self.knowledge_db = KnowledgeDatabase(knowledge_db_path)

        # Document categories
        self.document_types = (
            config.get(
                "document_types",
                [
                    "charter",
                    "requirements",
                    "design",
                    "test_plan",
                    "meeting_minutes",
                    "lessons_learned",
                    "policy",
                    "procedure",
                    "report",
                ],
            )
            if config
            else [
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
        )

        self.event_bus = config.get("event_bus") if config else None
        if self.event_bus is None:
            try:
                self.event_bus = get_event_bus()
            except ValueError:
                self.event_bus = None

        self.document_management_service = DocumentManagementService(config)
        self.prompt_registry = PromptRegistry()
        self.summary_prompt_agent_id = (
            config.get("summary_prompt_agent_id", "knowledge-agent")
            if config
            else "knowledge-agent"
        )
        self.summary_prompt_template = (
            config.get(
                "summary_prompt_template",
                (
                    "Summarize the document below for enterprise knowledge retrieval. "
                    "Limit output to {token_limit} tokens and keep factual points concise.\n\n"
                    "Document:\n{text}"
                ),
            )
            if config
            else (
                "Summarize the document below for enterprise knowledge retrieval. "
                "Limit output to {token_limit} tokens and keep factual points concise.\n\n"
                "Document:\n{text}"
            )
        )

        fallback_embedding_service = LocalEmbeddingService(self.embedding_dimensions)
        self.embedding_service = SemanticEmbeddingService(
            self.embedding_model,
            fallback_service=fallback_embedding_service,
            encoder=config.get("embedding_encoder") if config else None,
        )
        self.vector_store_backend = (
            config.get("vector_store_backend", "in_memory") if config else "in_memory"
        )
        if self.vector_store_backend == "faiss":
            self.vector_index = FaissBackedVectorSearchIndex(
                self.embedding_service,
                index_name="knowledge_agent",
                config_path=(
                    Path(config.get("vector_store_config_path"))
                    if config and config.get("vector_store_config_path")
                    else None
                ),
            )
        else:
            self.vector_index = VectorSearchIndex(self.embedding_service)

        self.summarizer: Callable[[dict[str, Any]], Any] | None = (
            config.get("summarizer") if config else None
        )
        self.entity_extractor = EntityExtractionPipeline(
            backend=config.get("entity_extraction_backend", "auto") if config else "auto",
            custom_extractor=config.get("entity_extractor") if config else None,
        )
        self.classifier = NaiveBayesTextClassifier(self.document_types)
        self.classifier_trained = False
        self._confluence_connector = None
        self.integration_clients = config.get("integration_clients", {}) if config else {}
        self.integration_status: dict[str, bool] = {}
        self.async_processing_enabled = (
            config.get("async_processing_enabled", True) if config else True
        )
        self.github_extensions = (
            config.get("github_extensions", [".md", ".txt", ".rst"])
            if config
            else [".md", ".txt", ".rst"]
        )
        self.ingestion_max_files = config.get("ingestion_max_files", 200) if config else 200

        # Data stores (will be replaced with database)
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
        """Initialize document storage, search services, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Knowledge & Document Management Agent...")

        self._register_integrations()

        self._train_classifier_seed()

        if self.event_bus and hasattr(self.event_bus, "subscribe"):
            self.event_bus.subscribe("cognitive.summary.created", self._handle_cognitive_summary)
            self.event_bus.subscribe("agent.summary.created", self._handle_cognitive_summary)

        self.logger.info("Knowledge & Document Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
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
        ]

        if action not in valid_actions:
            self.logger.warning("Invalid action: %s", action)
            return False

        if action == "upload_document":
            document_data = input_data.get("document", {})
            if not document_data.get("title") or not document_data.get("content"):
                self.logger.warning("Missing required document fields")
                return False

        elif action == "ingest_sources":
            if not input_data.get("sources"):
                self.logger.warning("Missing ingestion sources")
                return False

        elif action == "ingest_agent_output":
            if not input_data.get("payload"):
                self.logger.warning("Missing agent output payload")
                return False

        elif action in {"search_documents", "search_semantic"}:
            if "query" not in input_data:
                self.logger.warning("Missing search query")
                return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process knowledge and document management requests.

        Args:
            input_data: {
                "action": "upload_document" | "search_documents" | "get_document" |
                          "update_document" | "delete_document" | "classify_document" |
                          "summarize_document" | "extract_entities" | "build_knowledge_graph" |
                          "capture_lesson_learned" | "recommend_documents" | "manage_taxonomy" |
                          "track_document_access" | "get_document_version_history",
                "document": Document data for upload/update,
                "document_id": Document identifier,
                "query": Search query string,
                "filters": Search filters,
                "lesson": Lesson learned data,
                "taxonomy": Taxonomy configuration,
                "user_context": User context for recommendations
            }

        Returns:
            Response based on action:
            - upload_document: Document ID, version, and classification
            - search_documents: Ranked search results with excerpts
            - get_document: Full document with metadata
            - update_document: Updated document version
            - delete_document: Deletion confirmation
            - classify_document: Document classification and tags
            - summarize_document: Generated summary
            - extract_entities: Extracted entities and relationships
            - build_knowledge_graph: Graph relationships
            - capture_lesson_learned: Lesson ID and categorization
            - recommend_documents: Recommended documents list
            - manage_taxonomy: Updated taxonomy structure
            - track_document_access: Access logs and statistics
            - get_document_version_history: Version history
        """
        action = input_data.get("action", "search_documents")
        tenant_id = (
            input_data.get("tenant_id")
            or input_data.get("context", {}).get("tenant_id")
            or "default"
        )
        access_context = input_data.get("access_context") or input_data.get("user_context") or {}

        if action == "upload_document":
            return await self._upload_document(tenant_id, input_data.get("document", {}))

        elif action == "ingest_sources":
            return await self._ingest_sources(tenant_id, input_data.get("sources", []))

        elif action == "ingest_agent_output":
            return await self._ingest_agent_output(tenant_id, input_data.get("payload", {}))

        elif action == "search_documents":
            return await self._search_documents(
                input_data.get("query"),
                input_data.get("filters", {}),  # type: ignore
                access_context,
                tenant_id,
            )

        elif action == "search_semantic":
            return await self._search_documents(
                input_data.get("query"),
                input_data.get("filters", {}),  # type: ignore
                access_context,
                tenant_id,
            )

        elif action == "get_document":
            return await self._get_document(
                input_data.get("document_id"), access_context, tenant_id  # type: ignore
            )

        elif action == "update_document":
            return await self._update_document(
                input_data.get("document_id"),  # type: ignore
                input_data.get("document", {}),
                tenant_id,
            )

        elif action == "delete_document":
            return await self._delete_document(input_data.get("document_id"), tenant_id)  # type: ignore

        elif action == "classify_document":
            return await self._classify_document(
                input_data.get("document_id"), tenant_id  # type: ignore
            )

        elif action == "summarize_document":
            return await self._summarize_document(
                input_data.get("document_id"), tenant_id  # type: ignore
            )

        elif action == "extract_entities":
            return await self._extract_entities(
                input_data.get("document_id"), tenant_id  # type: ignore
            )

        elif action == "build_knowledge_graph":
            return await self._build_knowledge_graph(
                input_data.get("document_id"), tenant_id  # type: ignore
            )

        elif action == "query_knowledge_graph":
            return await self._query_knowledge_graph(input_data.get("query", {}))

        elif action == "capture_lesson_learned":
            return await self._capture_lesson_learned(input_data.get("lesson", {}))

        elif action == "recommend_documents":
            return await self._recommend_documents(input_data.get("user_context", {}))

        elif action == "manage_taxonomy":
            return await self._manage_taxonomy(input_data.get("taxonomy", {}))

        elif action == "track_document_access":
            return await self._track_document_access(
                input_data.get("document_id"), tenant_id  # type: ignore
            )

        elif action == "get_document_version_history":
            return await self._get_document_version_history(
                input_data.get("document_id"), tenant_id  # type: ignore
            )

        elif action == "annotate_document":
            return await self._annotate_document(
                input_data.get("document_id"),
                input_data.get("annotation", {}),
                access_context,
                tenant_id,
            )

        elif action == "review_document":
            return await self._review_document(
                input_data.get("document_id"),
                input_data.get("review", {}),
                access_context,
                tenant_id,
            )

        elif action == "approve_document":
            return await self._approve_document(
                input_data.get("document_id"),
                input_data.get("approval", {}),
                access_context,
                tenant_id,
            )

        elif action == "link_documents":
            return await self._link_documents(input_data.get("links", []), tenant_id)

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _upload_document(
        self, tenant_id: str, document_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Upload and classify document.

        Returns document ID and metadata.
        """
        self.logger.info("Uploading document: %s", document_data.get("title"))

        # Generate document ID
        document_id = await self._generate_document_id()

        # Extract metadata
        metadata = await self._extract_metadata(document_data)

        # Auto-classify document
        classification = await self._auto_classify_document(document_data)

        # Generate initial tags
        tags = await self._generate_tags(document_data, classification)

        classification_label = document_data.get("classification", "internal")
        doc_type = await self._map_doc_type_for_schema(classification.get("type"))
        owner = document_data.get("owner") or document_data.get("author") or "unknown"
        status = document_data.get("status", "draft")

        # Create document record
        document = {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "title": document_data.get("title"),
            "content": document_data.get("content"),
            "type": classification.get("type"),
            "doc_type": doc_type,
            "tags": tags,
            "author": document_data.get("author"),
            "project_id": document_data.get("project_id"),
            "program_id": document_data.get("program_id"),
            "portfolio_id": document_data.get("portfolio_id"),
            "metadata": metadata,
            "source": document_data.get("source"),
            "version": 1,
            "permissions": document_data.get("permissions", {"public": False}),
            "classification": classification_label,
            "status": status,
            "owner": owner,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "modified_at": datetime.now(timezone.utc).isoformat(),
            "accessed_count": 0,
            "topic": classification.get("topic"),
            "phase": classification.get("phase"),
            "domain": classification.get("domain"),
        }

        await self._validate_document_schema(
            {
                "id": document_id,
                "tenant_id": tenant_id,
                "title": document.get("title"),
                "doc_type": doc_type,
                "status": status,
                "classification": classification_label,
                "owner": owner,
                "created_at": document.get("created_at"),
                "updated_at": document.get("modified_at"),
                "metadata": metadata,
            }
        )

        # Store document
        self.documents[document_id] = document
        self.document_store.upsert(tenant_id, document_id, document.copy())
        self.knowledge_db.upsert_document(document)
        self.knowledge_db.record_version(document)
        self._index_document(document)
        await self._update_graph_for_document(document)
        self._update_classifier_with_document(document)

        # Store version
        self.document_versions[document_id] = [document.copy()]

        # Generate summary asynchronously
        if self.async_processing_enabled:
            asyncio.create_task(self._summarize_document(document_id, tenant_id))
            asyncio.create_task(self._extract_entities(document_id, tenant_id))
        else:
            await self._summarize_document(document_id, tenant_id)
            await self._extract_entities(document_id, tenant_id)

        await self._publish_event(
            "knowledge.document.ingested",
            {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "title": document.get("title"),
                "type": document.get("type"),
                "source": document.get("source"),
            },
        )

        await self._publish_document_external(document)
        await self._publish_event(
            "document.uploaded",
            {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "title": document.get("title"),
                "type": document.get("type"),
                "uploaded_at": document.get("created_at"),
            },
        )

        return {
            "document_id": document_id,
            "title": document["title"],
            "version": document["version"],
            "type": document["type"],
            "tags": tags,
            "classification": classification,
            "topic": classification.get("topic"),
            "phase": classification.get("phase"),
            "domain": classification.get("domain"),
            "next_steps": "Document indexed and ready for search",
        }

    async def _ingest_sources(
        self, tenant_id: str, sources: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Ingest documents from configured sources."""
        ingestion_id = await self._generate_ingestion_id()
        ingested_documents: list[str] = []
        source_summaries: list[dict[str, Any]] = []

        for source in sources:
            source_type = source.get("type") or source.get("source_type") or "unknown"
            if source_type == "confluence":
                documents = await self._crawl_confluence(source)
            elif source_type == "sharepoint":
                documents = await self._crawl_sharepoint(source)
            elif source_type == "github":
                documents = await self._crawl_github(source)
            elif source_type in {"agent_output", "cognitive_summary"}:
                documents = await self._ingest_agent_outputs(source)
            else:
                documents = list(source.get("documents", []))

            processed_ids: list[str] = []
            for document in documents:
                normalized = await self._normalize_ingested_document(document, source_type, source)
                result = await self._upload_document(tenant_id, normalized)
                processed_ids.append(result["document_id"])
                ingested_documents.append(result["document_id"])

            source_summaries.append(
                {
                    "source_type": source_type,
                    "count": len(processed_ids),
                    "document_ids": processed_ids,
                }
            )

        run_record = {
            "ingestion_id": ingestion_id,
            "tenant_id": tenant_id,
            "sources": source_summaries,
            "total_documents": len(ingested_documents),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        self.ingestion_runs.append(run_record)

        await self._publish_event("knowledge.ingestion.completed", run_record)

        return run_record

    async def _ingest_agent_output(self, tenant_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Ingest agent output summaries as knowledge artifacts."""
        document_data = await self._build_agent_output_document(payload)
        result = await self._upload_document(tenant_id, document_data)
        await self._publish_event(
            "knowledge.agent_output.ingested",
            {"tenant_id": tenant_id, "document_id": result["document_id"]},
        )
        return result

    async def _handle_cognitive_summary(self, payload: dict[str, Any]) -> None:
        """Handle summaries from other agents published to the event bus."""
        tenant_id = payload.get("tenant_id") or "default"
        try:
            await self._ingest_agent_output(tenant_id, payload)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            self.logger.warning("Failed to ingest cognitive summary: %s", exc)

    async def _ingest_agent_outputs(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        documents = []
        for payload in source.get("payloads", []):
            documents.append(await self._build_agent_output_document(payload))
        return documents

    async def _build_agent_output_document(self, payload: dict[str, Any]) -> dict[str, Any]:
        source_agent = payload.get("source_agent") or payload.get("agent_id") or "agent"
        title = (
            payload.get("title") or payload.get("summary_title") or f"Summary from {source_agent}"
        )
        content = payload.get("summary") or payload.get("content") or payload.get("details", "")
        tags = payload.get("tags") or []
        tags.extend(["agent_summary", source_agent])
        return {
            "title": title,
            "content": content,
            "author": payload.get("author") or source_agent,
            "project_id": payload.get("project_id"),
            "program_id": payload.get("program_id"),
            "portfolio_id": payload.get("portfolio_id"),
            "tags": tags,
            "metadata": payload.get("metadata", {}),
            "source": payload.get("source") or "agent_output",
            "permissions": payload.get("permissions", {"public": False}),
            "status": payload.get("status", "draft"),
        }

    async def _crawl_confluence(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch documents from Confluence or provided payload."""
        documents = list(source.get("documents", []))
        connector = source.get("connector")
        if connector and hasattr(connector, "read"):
            try:
                records = connector.read("pages", filters=source.get("filters"))
                documents.extend(records)
            except (
                ConnectionError,
                TimeoutError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
                OSError,
            ) as exc:
                self.logger.warning("Confluence crawl failed: %s", exc)
            return documents

        connector = self._get_confluence_connector()
        if connector is None:
            return documents

        try:
            records = connector.read("pages", filters=source.get("filters"))
            documents.extend(records)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            self.logger.warning("Confluence crawl failed: %s", exc)
        return documents

    async def _crawl_sharepoint(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch documents from SharePoint or provided payload."""
        documents = list(source.get("documents", []))
        document_ids = source.get("document_ids", [])
        for document_id in document_ids:
            record = await self.document_management_service.get_document(document_id)
            if record:
                documents.append(record)
        if source.get("list_documents"):
            documents.extend(
                await self.document_management_service.list_documents(
                    folder_path=source.get("folder_path"),
                    filters=source.get("filters"),
                    limit=source.get("limit", 100),
                )
            )
        return documents

    async def _crawl_github(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch documents from GitHub or provided payload."""
        documents = list(source.get("documents", []))
        for file_record in source.get("files", []):
            documents.append(file_record)
        repo_path = source.get("repo_path")
        if repo_path:
            documents.extend(self._scan_repository(Path(repo_path), source))
        return documents

    async def _normalize_ingested_document(
        self, document: dict[str, Any], source_type: str, source: dict[str, Any]
    ) -> dict[str, Any]:
        title = document.get("title") or document.get("name") or "Untitled"
        content = document.get("content") or document.get("body") or document.get("text") or ""
        metadata = document.get("metadata", {})
        metadata.update({"source_type": source_type, "source_id": source.get("id")})
        extracted = self._extract_document_attributes(content)
        metadata.update(extracted.get("metadata", {}))
        return {
            "title": title,
            "content": content,
            "author": document.get("author") or document.get("owner") or extracted.get("author"),
            "project_id": document.get("project_id") or source.get("project_id"),
            "program_id": document.get("program_id") or source.get("program_id"),
            "portfolio_id": document.get("portfolio_id") or source.get("portfolio_id"),
            "tags": document.get("tags") or source.get("tags") or extracted.get("tags") or [],
            "metadata": metadata,
            "source": source_type,
            "permissions": document.get("permissions", {"public": False}),
            "status": document.get("status", "draft"),
        }

    async def _search_documents(
        self,
        query: str,
        filters: dict[str, Any],
        access_context: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        Search documents using semantic search.

        Returns ranked search results.
        """
        self.logger.info("Searching documents: %s", query)

        # Perform semantic search
        search_results = await self._semantic_search(query, filters, access_context, tenant_id)

        # Rank results
        ranked_results = await self._rank_search_results(search_results, query)

        # Generate excerpts
        results_with_excerpts = await self._generate_excerpts(ranked_results, query)

        return {
            "query": query,
            "total_results": len(results_with_excerpts),
            "results": results_with_excerpts[: self.semantic_result_limit],
            "filters": filters,
        }

    async def _get_document(
        self, document_id: str, access_context: dict[str, Any], tenant_id: str
    ) -> dict[str, Any]:
        """
        Retrieve document with metadata.

        Returns full document.
        """
        self.logger.info("Retrieving document: %s", document_id)

        document = self._load_document(tenant_id, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        if not await self._is_access_allowed(document, access_context):
            raise PermissionError("Access denied for requested document")

        # Update access count
        document["accessed_count"] = document.get("accessed_count", 0) + 1
        document["last_accessed_at"] = datetime.now(timezone.utc).isoformat()
        self.document_store.upsert(tenant_id, document_id, document.copy())

        # Get summary if available
        summary = self.summaries.get(document_id, {}).get("content")

        # Get related documents
        related_documents = await self._find_related_documents(document_id)

        access_payload = {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "accessed_at": document["last_accessed_at"],
            "actor": access_context.get("user_id"),
        }
        self.knowledge_db.record_interaction(document_id, "access", access_payload)

        return {
            "document_id": document_id,
            "title": document.get("title"),
            "content": document.get("content"),
            "type": document.get("type"),
            "tags": document.get("tags"),
            "metadata": document.get("metadata"),
            "summary": summary,
            "version": document.get("version"),
            "author": document.get("author"),
            "created_at": document.get("created_at"),
            "modified_at": document.get("modified_at"),
            "accessed_count": document.get("accessed_count"),
            "related_documents": related_documents,
            "annotations": self.document_annotations.get(document_id, []),
            "reviews": self.document_reviews.get(document_id, []),
            "approvals": self.document_approvals.get(document_id, []),
        }

    async def _update_document(
        self, document_id: str, updates: dict[str, Any], tenant_id: str
    ) -> dict[str, Any]:
        """
        Update document and create new version.

        Returns updated document version.
        """
        self.logger.info("Updating document: %s", document_id)

        document = self._load_document(tenant_id, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Save current version
        if document_id not in self.document_versions:
            self.document_versions[document_id] = []
        self.document_versions[document_id].append(document.copy())

        # Apply updates
        for key, value in updates.items():
            if key not in ["document_id", "created_at", "version"]:
                document[key] = value

        # Increment version
        document["version"] = document.get("version", 1) + 1
        document["modified_at"] = datetime.now(timezone.utc).isoformat()

        # Re-classify if content changed
        if "content" in updates:
            classification = await self._auto_classify_document(document)
            document["type"] = classification.get("type")

            # Regenerate summary
            await self._summarize_document(document_id, tenant_id)

        await self._validate_document_schema(
            {
                "id": document_id,
                "tenant_id": tenant_id,
                "title": document.get("title"),
                "doc_type": await self._map_doc_type_for_schema(document.get("type")),
                "status": document.get("status", "draft"),
                "classification": document.get("classification", "internal"),
                "owner": document.get("owner") or document.get("author") or "unknown",
                "created_at": document.get("created_at"),
                "updated_at": document.get("modified_at"),
                "metadata": document.get("metadata", {}),
            }
        )

        self.document_store.upsert(tenant_id, document_id, document.copy())
        self.knowledge_db.upsert_document(document)
        self.knowledge_db.record_version(document)
        self._index_document(document)
        await self._update_graph_for_document(document)
        self._update_classifier_with_document(document)

        await self._publish_event(
            "knowledge.document.updated",
            {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "version": document.get("version"),
                "changes": list(updates.keys()),
            },
        )
        await self._publish_event(
            "document.updated",
            {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "version": document.get("version"),
                "updated_at": document.get("modified_at"),
            },
        )

        return {
            "document_id": document_id,
            "version": document["version"],
            "modified_at": document["modified_at"],
            "changes": list(updates.keys()),
        }

    async def _delete_document(self, document_id: str, tenant_id: str) -> dict[str, Any]:
        """
        Delete document (soft delete).

        Returns deletion confirmation.
        """
        self.logger.info("Deleting document: %s", document_id)

        document = self._load_document(tenant_id, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Soft delete
        document["deleted"] = True
        document["deleted_at"] = datetime.now(timezone.utc).isoformat()
        self.document_store.upsert(tenant_id, document_id, document.copy())
        self.knowledge_db.upsert_document(document)

        await self._publish_event(
            "knowledge.document.deleted",
            {"document_id": document_id, "tenant_id": tenant_id},
        )
        await self._publish_event(
            "document.deleted",
            {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "deleted_at": document.get("deleted_at"),
            },
        )

        return {"document_id": document_id, "deleted": True, "deleted_at": document["deleted_at"]}

    async def _classify_document(self, document_id: str, tenant_id: str) -> dict[str, Any]:
        """
        Classify document using AI.

        Returns classification and tags.
        """
        self.logger.info("Classifying document: %s", document_id)

        document = self._load_document(tenant_id, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Auto-classify using AI
        classification = await self._auto_classify_document(document)

        # Generate tags
        tags = await self._generate_tags(document, classification)

        # Update document
        document["type"] = classification.get("type")
        document["tags"] = tags
        document["classification_confidence"] = classification.get("confidence")
        document["doc_type"] = await self._map_doc_type_for_schema(classification.get("type"))
        document["topic"] = classification.get("topic")
        document["phase"] = classification.get("phase")
        document["domain"] = classification.get("domain")
        self.document_store.upsert(tenant_id, document_id, document.copy())
        self.knowledge_db.upsert_document(document)
        self._index_document(document)

        return {
            "document_id": document_id,
            "type": classification.get("type"),
            "tags": tags,
            "confidence": classification.get("confidence"),
            "suggested_category": classification.get("category"),
            "topic": classification.get("topic"),
            "phase": classification.get("phase"),
            "domain": classification.get("domain"),
        }

    async def _summarize_document(self, document_id: str, tenant_id: str) -> dict[str, Any]:
        """
        Generate document summary using NLG.

        Returns generated summary.
        """
        self.logger.info("Summarizing document: %s", document_id)

        document = self._load_document(tenant_id, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Generate summary using AI
        summary_content = await self.summarise_document(document.get("content", ""))

        # Store summary
        self.summaries[document_id] = {
            "document_id": document_id,
            "content": summary_content,
            "length": len(summary_content),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        self.knowledge_db.record_interaction(
            document_id,
            "summary",
            {"summary": summary_content, "generated_at": datetime.now(timezone.utc).isoformat()},
        )

        return {
            "document_id": document_id,
            "summary": summary_content,
            "length": len(summary_content),
        }

    async def _extract_entities(self, document_id: str, tenant_id: str) -> dict[str, Any]:
        """
        Extract entities from document using NLP.

        Returns extracted entities.
        """
        self.logger.info("Extracting entities from document: %s", document_id)

        document = self._load_document(tenant_id, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Extract entities using NLP
        entities = await self._extract_entities_from_text(document.get("content", ""))

        # Store in knowledge graph
        if document_id not in self.knowledge_graph:
            self.knowledge_graph[document_id] = {"entities": [], "relationships": []}

        self.knowledge_graph[document_id]["entities"] = entities
        document_node = self._graph_document_id(document_id)
        self._register_graph_node(
            document_node,
            "document",
            {"title": document.get("title"), "doc_type": document.get("type")},
        )
        for entity in entities:
            entity_node = self._graph_entity_id(entity.get("text"))
            self._register_graph_node(entity_node, "entity", entity)
            self._register_graph_edge(document_node, entity_node, "mentions")
        self.knowledge_db.upsert_graph(self.graph_nodes, self.graph_edges)

        return {"document_id": document_id, "entities": entities, "entity_count": len(entities)}

    async def _build_knowledge_graph(self, document_id: str, tenant_id: str) -> dict[str, Any]:
        """
        Build knowledge graph relationships.

        Returns graph structure.
        """
        self.logger.info("Building knowledge graph for document: %s", document_id)

        document = self._load_document(tenant_id, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Get entities
        entities = self.knowledge_graph.get(document_id, {}).get("entities", [])

        # Build relationships
        relationships = await self._build_entity_relationships(document_id, entities)

        # Update knowledge graph
        if document_id not in self.knowledge_graph:
            self.knowledge_graph[document_id] = {"entities": [], "relationships": []}

        self.knowledge_graph[document_id]["relationships"] = relationships
        self.knowledge_db.upsert_graph(self.graph_nodes, self.graph_edges)

        return {
            "document_id": document_id,
            "entities": len(entities),
            "relationships": len(relationships),
            "graph": self.knowledge_graph[document_id],
        }

    async def _capture_lesson_learned(self, lesson_data: dict[str, Any]) -> dict[str, Any]:
        """
        Capture and categorize lesson learned.

        Returns lesson ID and categorization.
        """
        self.logger.info("Capturing lesson learned: %s", lesson_data.get("title"))

        # Generate lesson ID
        lesson_id = await self._generate_lesson_id()

        # Categorize lesson
        category = await self._categorize_lesson(lesson_data)

        # Find similar lessons
        similar_lessons = await self._find_similar_lessons(lesson_data)

        # Create lesson record
        lesson = {
            "lesson_id": lesson_id,
            "title": lesson_data.get("title"),
            "description": lesson_data.get("description"),
            "category": category,
            "root_cause": lesson_data.get("root_cause"),
            "impact": lesson_data.get("impact"),
            "recommendation": lesson_data.get("recommendation"),
            "project_id": lesson_data.get("project_id"),
            "program_id": lesson_data.get("program_id"),
            "date": lesson_data.get("date", datetime.now(timezone.utc).isoformat()),
            "owner": lesson_data.get("owner"),
            "similar_lessons": similar_lessons,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store lesson
        self.lessons_learned[lesson_id] = lesson
        await self._publish_event("knowledge.lesson.captured", lesson)
        self.knowledge_db.record_interaction(
            lesson_id,
            "lesson",
            {"lesson": lesson, "created_at": lesson.get("created_at")},
        )
        self.vector_index.add(
            f"lesson:{lesson_id}",
            f"{lesson.get('title', '')} {lesson.get('description', '')}",
            {"lesson_id": lesson_id, "category": lesson.get("category")},
        )
        await self._publish_event(
            "lesson.captured", {"lesson_id": lesson_id, "tenant_id": "shared"}
        )

        return {
            "lesson_id": lesson_id,
            "title": lesson["title"],
            "category": category,
            "similar_lessons": len(similar_lessons),
            "recommendations": lesson.get("recommendation"),
        }

    async def _recommend_documents(self, user_context: dict[str, Any]) -> dict[str, Any]:
        """
        Recommend relevant documents based on context.

        Returns recommended documents.
        """
        self.logger.info("Generating document recommendations")

        # Get user's current task/project
        current_task = user_context.get("current_task")
        project_id = user_context.get("project_id")
        role = user_context.get("role")

        # Find relevant documents
        recommendations = await self._find_relevant_documents(current_task, project_id, role)  # type: ignore

        # Rank by relevance
        ranked_recommendations = await self._rank_recommendations(recommendations, user_context)

        return {
            "recommendations": ranked_recommendations,
            "count": len(ranked_recommendations),
            "context": user_context,
        }

    async def _manage_taxonomy(self, taxonomy_data: dict[str, Any]) -> dict[str, Any]:
        """
        Manage knowledge taxonomy.

        Returns updated taxonomy structure.
        """
        self.logger.info("Managing taxonomy")

        action = taxonomy_data.get("action", "get")

        if action == "add_category":
            category = taxonomy_data.get("category", {})
            category_id = await self._add_taxonomy_category(category)
            return {"action": "add", "category_id": category_id}

        elif action == "update_category":
            category_id = taxonomy_data.get("category_id")  # type: ignore
            await self._update_taxonomy_category(category_id, taxonomy_data.get("updates", {}))
            return {"action": "update", "category_id": category_id}

        elif action == "delete_category":
            category_id = taxonomy_data.get("category_id")  # type: ignore
            await self._delete_taxonomy_category(category_id)
            return {"action": "delete", "category_id": category_id}

        else:  # get
            return {"taxonomy": self.taxonomy, "total_categories": len(self.taxonomy)}

    async def _track_document_access(self, document_id: str, tenant_id: str) -> dict[str, Any]:
        """
        Track document access patterns.

        Returns access statistics.
        """
        self.logger.info("Tracking access for document: %s", document_id)

        document = self._load_document(tenant_id, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Get access statistics
        interactions = self.knowledge_db.list_interactions(document_id)
        unique_users = {
            interaction.get("payload", {}).get("actor")
            for interaction in interactions
            if interaction.get("interaction_type") == "access"
        }
        access_trend = "stable"
        if len(interactions) >= 2:
            access_trend = (
                "increasing"
                if interactions[-1]["created_at"] > interactions[0]["created_at"]
                else "stable"
            )
        access_stats = {
            "total_accesses": document.get("accessed_count", 0),
            "last_accessed": document.get("last_accessed_at"),
            "unique_users": len([user for user in unique_users if user]),
            "access_trend": access_trend,
        }

        return {"document_id": document_id, "access_stats": access_stats}

    async def _get_document_version_history(
        self, document_id: str, tenant_id: str
    ) -> dict[str, Any]:
        """
        Get document version history.

        Returns version list.
        """
        self.logger.info("Retrieving version history for document: %s", document_id)

        if document_id not in self.document_versions:
            raise ValueError(f"Document not found: {document_id}")

        versions = self.document_versions.get(document_id, [])

        version_list = [
            {
                "version": v.get("version"),
                "modified_at": v.get("modified_at"),
                "author": v.get("author"),
            }
            for v in versions
        ]

        return {
            "document_id": document_id,
            "current_version": len(versions),
            "version_history": version_list,
        }

    async def _annotate_document(
        self,
        document_id: str,
        annotation: dict[str, Any],
        access_context: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        """Add annotation to a document."""
        document = self._load_document(tenant_id, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        if not await self._is_access_allowed(document, access_context):
            raise PermissionError("Access denied for requested document")

        record = {
            "annotation_id": f"ANN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "document_id": document_id,
            "text": annotation.get("text"),
            "selection": annotation.get("selection"),
            "author": access_context.get("user_id") or annotation.get("author"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.document_annotations.setdefault(document_id, []).append(record)
        self.knowledge_db.record_interaction(document_id, "annotation", record)
        await self._publish_event("knowledge.document.annotated", record)
        return {"document_id": document_id, "annotation": record}

    async def _review_document(
        self,
        document_id: str,
        review: dict[str, Any],
        access_context: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        """Capture document review feedback."""
        document = self._load_document(tenant_id, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        if not await self._is_access_allowed(document, access_context):
            raise PermissionError("Access denied for requested document")

        record = {
            "review_id": f"REV-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "document_id": document_id,
            "status": review.get("status", "in_review"),
            "comments": review.get("comments", []),
            "reviewer": access_context.get("user_id") or review.get("reviewer"),
            "version": document.get("version"),
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.document_reviews.setdefault(document_id, []).append(record)
        self.knowledge_db.record_interaction(document_id, "review", record)
        await self._publish_event("knowledge.document.reviewed", record)
        return {"document_id": document_id, "review": record}

    async def _approve_document(
        self,
        document_id: str,
        approval: dict[str, Any],
        access_context: dict[str, Any],
        tenant_id: str,
    ) -> dict[str, Any]:
        """Approve document changes."""
        document = self._load_document(tenant_id, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        if not await self._is_access_allowed(document, access_context):
            raise PermissionError("Access denied for requested document")

        record = {
            "approval_id": f"APR-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "document_id": document_id,
            "status": approval.get("status", "approved"),
            "approver": access_context.get("user_id") or approval.get("approver"),
            "version": document.get("version"),
            "notes": approval.get("notes"),
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }
        self.document_approvals.setdefault(document_id, []).append(record)
        document["status"] = (
            "approved" if record["status"] == "approved" else document.get("status", "draft")
        )
        self.document_store.upsert(tenant_id, document_id, document.copy())
        self.knowledge_db.upsert_document(document)
        self.knowledge_db.record_interaction(document_id, "approval", record)
        await self._publish_event("knowledge.document.approved", record)
        return {"document_id": document_id, "approval": record}

    async def _link_documents(self, links: list[dict[str, Any]], tenant_id: str) -> dict[str, Any]:
        """Link related documents in the knowledge graph."""
        created_links: list[dict[str, Any]] = []
        for link in links:
            source_id = link.get("source_document_id")
            target_id = link.get("target_document_id")
            relation = link.get("relation", "related")
            if not source_id or not target_id:
                continue
            source = self._load_document(tenant_id, source_id)
            target = self._load_document(tenant_id, target_id)
            if not source or not target:
                continue
            source_node = self._graph_document_id(source_id)
            target_node = self._graph_document_id(target_id)
            self._register_graph_node(
                source_node,
                "document",
                {"title": source.get("title"), "doc_type": source.get("type")},
            )
            self._register_graph_node(
                target_node,
                "document",
                {"title": target.get("title"), "doc_type": target.get("type")},
            )
            self._register_graph_edge(source_node, target_node, relation)
            created_links.append(
                {
                    "source_document_id": source_id,
                    "target_document_id": target_id,
                    "relation": relation,
                }
            )

        if created_links:
            await self._publish_event(
                "knowledge.document.linked", {"links": created_links, "tenant_id": tenant_id}
            )
            self.knowledge_db.upsert_graph(self.graph_nodes, self.graph_edges)
        return {"links": created_links, "count": len(created_links)}

    async def _query_knowledge_graph(self, query: dict[str, Any]) -> dict[str, Any]:
        """Query graph relationships for insights."""
        query_type = query.get("type", "traverse")
        if query_type == "impact_analysis":
            risk = query.get("risk")
            if not risk:
                raise ValueError("Missing risk for impact analysis")
            risk_node = self._graph_risk_id(risk)
            impacted = self._traverse_graph(risk_node, target_type="project")
            return {"risk": risk, "impacted_projects": impacted}

        start_node = query.get("start_node")
        relation = query.get("relation")
        target_type = query.get("target_type")
        if not start_node:
            raise ValueError("Missing start_node for graph query")
        results = self._traverse_graph(start_node, relation, target_type)
        return {
            "start_node": start_node,
            "relation": relation,
            "target_type": target_type,
            "results": results,
        }

    # Helper methods

    async def _generate_document_id(self) -> str:
        """Generate unique document ID."""
        import uuid
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"DOC-{timestamp}-{uuid.uuid4().hex[:8]}"

    async def _generate_lesson_id(self) -> str:
        """Generate unique lesson ID."""
        import uuid
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"LESSON-{timestamp}-{uuid.uuid4().hex[:8]}"

    async def _generate_ingestion_id(self) -> str:
        """Generate unique ingestion ID."""
        import uuid
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"INGEST-{timestamp}-{uuid.uuid4().hex[:8]}"

    def _train_classifier_seed(self) -> None:
        """Train classifier with seed samples for bootstrapping."""
        if self.classifier_trained:
            return
        seed_samples = [
            ("project charter objectives scope", "charter"),
            ("functional requirements shall must", "requirements"),
            ("test plan verification validation", "test_plan"),
            ("lessons learned retrospective", "lessons_learned"),
            ("meeting minutes decisions action items", "meeting_minutes"),
            ("policy procedure compliance", "policy"),
            ("design specification architecture", "design"),
            ("status report metrics", "report"),
        ]
        self.classifier.fit(seed_samples)
        self.classifier_trained = True

    async def _extract_metadata(self, document_data: dict[str, Any]) -> dict[str, Any]:
        """Extract metadata from document."""
        content = document_data.get("content", "")
        keywords = self._extract_keywords(content)
        extracted = self._extract_document_attributes(content)
        return {
            "file_size": len(document_data.get("content", "")),
            "format": document_data.get("format", "text"),
            "language": self._detect_language(content),
            "keywords": keywords,
            "source": document_data.get("source"),
            "author": extracted.get("author"),
            "published_at": extracted.get("date"),
            "tags": extracted.get("tags", []),
        }

    def _detect_language(self, content: str) -> str:
        if not content:
            return "unknown"
        ascii_ratio = sum(1 for char in content if ord(char) < 128) / len(content)
        return "en" if ascii_ratio > 0.9 else "unknown"

    async def _auto_classify_document(self, document_data: dict[str, Any]) -> dict[str, Any]:
        """Auto-classify document using AI."""
        content = document_data.get("content", "")
        if self.classifier_trained:
            label, scores = self.classifier.predict(content)
            confidence = max(scores.values()) if scores else 0.5
            extra = self._classify_topic_phase_domain(content)
            return {
                "type": label,
                "confidence": confidence,
                "category": label,
                "topic": extra.get("topic"),
                "phase": extra.get("phase"),
                "domain": extra.get("domain"),
            }

        # Fallback heuristic classification
        content_lower = content.lower()
        if "requirement" in content_lower or "shall" in content_lower:
            doc_type = "requirements"
        elif "test" in content_lower or "verify" in content_lower:
            doc_type = "test_plan"
        elif "lesson" in content_lower or "learned" in content_lower:
            doc_type = "lessons_learned"
        elif "charter" in content_lower or "objectives" in content_lower:
            doc_type = "charter"
        else:
            doc_type = "report"

        extra = self._classify_topic_phase_domain(content)
        return {
            "type": doc_type,
            "confidence": 0.85,
            "category": doc_type,
            "topic": extra.get("topic"),
            "phase": extra.get("phase"),
            "domain": extra.get("domain"),
        }

    async def _generate_tags(
        self, document_data: dict[str, Any], classification: dict[str, Any]
    ) -> list[str]:
        """Generate tags for document."""
        tags = set(document_data.get("tags", []))
        if classification.get("type"):
            tags.add(classification.get("type"))
        if classification.get("topic"):
            tags.add(classification.get("topic"))
        if classification.get("phase"):
            tags.add(classification.get("phase"))
        if classification.get("domain"):
            tags.add(classification.get("domain"))
        keywords = self._extract_keywords(document_data.get("content", ""))
        tags.update(keywords[:5])
        if document_data.get("project_id"):
            tags.add("project")
        if document_data.get("program_id"):
            tags.add("program")
        if document_data.get("portfolio_id"):
            tags.add("portfolio")
        return list(tags)

    def _extract_document_attributes(self, content: str) -> dict[str, Any]:
        """Extract author, date, and tags from content using simple NLP heuristics."""
        author_match = re.search(r"(?im)^author\\s*:\\s*(.+)$", content)
        date_match = re.search(r"(?im)^date\\s*:\\s*(.+)$", content)
        tag_match = re.search(r"(?im)^tags?\\s*:\\s*(.+)$", content)
        hash_tags = re.findall(r"#(\\w+)", content)
        tags = []
        if tag_match:
            tags.extend([tag.strip() for tag in tag_match.group(1).split(",") if tag.strip()])
        tags.extend(hash_tags)
        return {
            "author": author_match.group(1).strip() if author_match else None,
            "date": date_match.group(1).strip() if date_match else None,
            "tags": list(dict.fromkeys(tags)),
            "metadata": {"hashtags": hash_tags} if hash_tags else {},
        }

    def _classify_topic_phase_domain(self, content: str) -> dict[str, str | None]:
        content_lower = content.lower()
        phase_keywords = {
            "initiation": ["charter", "business case", "kickoff"],
            "planning": ["plan", "schedule", "scope", "requirements"],
            "execution": ["implementation", "delivery", "build"],
            "monitoring": ["status", "metrics", "risk", "issue"],
            "closure": ["handover", "retrospective", "closure", "lessons learned"],
        }
        domain_keywords = {
            "security": ["security", "vulnerability", "access control"],
            "finance": ["budget", "cost", "invoice", "capex"],
            "operations": ["operations", "runbook", "incident"],
            "compliance": ["compliance", "policy", "audit"],
            "engineering": ["architecture", "design", "code", "deployment"],
        }
        phase = None
        for candidate, keywords in phase_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                phase = candidate
                break
        domain = None
        for candidate, keywords in domain_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                domain = candidate
                break
        return {"topic": phase, "phase": phase, "domain": domain}

    def _update_classifier_with_document(self, document: dict[str, Any]) -> None:
        content = document.get("content")
        label = document.get("type")
        if not content or not label:
            return
        self.classifier.fit([(content, label)])
        self.classifier_trained = True

    def _extract_keywords(self, content: str, *, limit: int = 10) -> list[str]:
        """Extract simple keyword list from content."""
        tokens = [token.lower().strip(".,;:()[]") for token in content.split()]
        tokens = [token for token in tokens if len(token) > 3]
        counts = Counter(tokens)
        return [token for token, _ in counts.most_common(limit)]

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
        """Update knowledge graph with document relationships."""
        document_id = document.get("document_id")
        if not document_id:
            return
        doc_node = self._graph_document_id(document_id)
        self._register_graph_node(
            doc_node, "document", {"title": document.get("title"), "doc_type": document.get("type")}
        )

        for relation, key in [
            ("project", "project_id"),
            ("program", "program_id"),
            ("portfolio", "portfolio_id"),
        ]:
            related_id = document.get(key)
            if related_id:
                related_node = f"{relation}:{related_id}"
                self._register_graph_node(related_node, relation, {"id": related_id})
                self._register_graph_edge(doc_node, related_node, "relates_to")

        for risk in self._extract_risks(document.get("content", "")):
            risk_node = self._graph_risk_id(risk)
            self._register_graph_node(risk_node, "risk", {"name": risk})
            self._register_graph_edge(risk_node, doc_node, "documented_in")

        for decision in self._extract_decisions(document.get("content", "")):
            decision_node = self._graph_decision_id(decision)
            self._register_graph_node(decision_node, "decision", {"name": decision})
            self._register_graph_edge(decision_node, doc_node, "documented_in")
        self.knowledge_db.upsert_graph(self.graph_nodes, self.graph_edges)

    def _extract_risks(self, content: str) -> list[str]:
        keywords = [
            token.strip(".,:;") for token in content.split() if token.lower().startswith("risk")
        ]
        return keywords[:5]

    def _extract_decisions(self, content: str) -> list[str]:
        decisions = []
        for line in content.splitlines():
            if "decision" in line.lower():
                decisions.append(line.strip()[:80])
        return decisions[:5]

    def _get_confluence_connector(self) -> Any | None:
        if self._confluence_connector is not None:
            return self._confluence_connector
        try:
            from confluence_connector import ConfluenceConnector

            connector_config = ConnectorConfig(
                connector_id="confluence",
                name="Confluence",
                category=ConnectorCategory.DOC_MGMT,
                instance_url=os.getenv("CONFLUENCE_URL", ""),
            )
            self._confluence_connector = ConfluenceConnector(connector_config)
            return self._confluence_connector
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            self.logger.warning("Failed to initialize Confluence connector: %s", exc)
            return None

    def _scan_repository(self, repo_path: Path, source: dict[str, Any]) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        if not repo_path.exists():
            return documents
        extensions = source.get("extensions") or self.github_extensions
        max_files = source.get("max_files", self.ingestion_max_files)
        count = 0
        for path in repo_path.rglob("*"):
            if count >= max_files:
                break
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            try:
                content = path.read_text(errors="ignore")
            except OSError:
                continue
            documents.append(
                {
                    "title": path.stem,
                    "content": content,
                    "author": source.get("owner"),
                    "tags": source.get("tags", []),
                    "metadata": {
                        "path": str(path),
                        "extension": path.suffix,
                        "repo": str(repo_path),
                        "modified_at": datetime.utcfromtimestamp(path.stat().st_mtime).isoformat(),
                    },
                    "source": "github",
                }
            )
            count += 1
        return documents

    def _graph_document_id(self, document_id: str) -> str:
        return f"document:{document_id}"

    def _graph_entity_id(self, entity_text: str | None) -> str:
        return f"entity:{entity_text}" if entity_text else "entity:unknown"

    def _graph_risk_id(self, risk: str) -> str:
        return f"risk:{risk}"

    def _graph_decision_id(self, decision: str) -> str:
        return f"decision:{decision}"

    def _register_graph_node(
        self, node_id: str, node_type: str, attributes: dict[str, Any]
    ) -> None:
        if node_id not in self.graph_nodes:
            self.graph_nodes[node_id] = {"type": node_type, "attributes": attributes}
        else:
            self.graph_nodes[node_id]["attributes"].update(attributes)

    def _register_graph_edge(self, source: str, target: str, relation: str) -> None:
        self.graph_edges.append({"from": source, "to": target, "relation": relation})

    def _traverse_graph(
        self,
        start_node: str,
        relation: str | None = None,
        target_type: str | None = None,
        depth: int = 2,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        visited = set()
        frontier = [(start_node, 0)]
        while frontier:
            node_id, level = frontier.pop(0)
            if node_id in visited or level >= depth:
                continue
            visited.add(node_id)
            for edge in self.graph_edges:
                if edge["from"] != node_id:
                    continue
                if relation and edge["relation"] != relation:
                    continue
                target = edge["to"]
                node = self.graph_nodes.get(target)
                if target_type and node and node.get("type") != target_type:
                    frontier.append((target, level + 1))
                    continue
                if node:
                    results.append({"node_id": target, **node})
                frontier.append((target, level + 1))
        return results

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
        self.integration_status = {
            "blob_storage": bool(self.integration_clients.get("blob_storage")),
            "data_lake": bool(self.integration_clients.get("data_lake")),
            "metadata_db": True,
            "cognitive_search": bool(self.integration_clients.get("cognitive_search")),
            "summarization": bool(self.integration_clients.get("summarizer")),
            "graph_store": True,
            "sharepoint": bool(self.integration_clients.get("sharepoint")),
            "office_online": bool(self.integration_clients.get("office_online")),
            "form_recognizer": bool(self.integration_clients.get("form_recognizer")),
            "git_repos": bool(self.integration_clients.get("git_repos")),
            "service_bus": self.event_bus is not None,
            "rbac": bool(self.integration_clients.get("rbac")),
        }

    async def _publish_document_external(self, document: dict[str, Any]) -> None:
        metadata = {
            "title": document.get("title", ""),
            "description": document.get("description", ""),
            "classification": document.get("classification", "internal"),
            "tags": document.get("tags", []),
            "owner": document.get("owner") or document.get("author") or "",
            "retention_days": document.get("retention_days", 365),
        }
        if self.document_management_service:
            await self.document_management_service.publish_document(
                document_content=document.get("content", ""),
                metadata=DocumentMetadata(**metadata),
            )

    async def _semantic_search(
        self, query: str, filters: dict[str, Any], access_context: dict[str, Any], tenant_id: str
    ) -> list[dict[str, Any]]:
        """Perform semantic search."""
        results: list[dict[str, Any]] = []
        vector_hits = self.vector_index.search(query, top_k=self.search_result_limit)

        for hit in vector_hits:
            document = self._load_document(tenant_id, hit.doc_id)
            if not document or document.get("deleted"):
                continue
            if hit.score < self.similarity_threshold:
                continue
            if not await self._is_access_allowed(document, access_context):
                continue
            if not await self._matches_search_filters(document, filters):
                continue
            summary = await self.summarise_document(document.get("content", ""))
            results.append(
                {
                    "document_id": hit.doc_id,
                    "document": document,
                    "relevance_score": hit.score,
                    "summary": summary,
                }
            )

        if results:
            return results

        # Fallback to keyword search when embeddings are not populated.
        query_lower = query.lower()
        for doc_id, document in self.documents.items():
            if document.get("deleted"):
                continue
            if query_lower in document.get("content", "").lower():
                if not await self._is_access_allowed(document, access_context):
                    continue
                if await self._matches_search_filters(document, filters):
                    summary = await self.summarise_document(document.get("content", ""))
                    results.append(
                        {
                            "document_id": doc_id,
                            "document": document,
                            "relevance_score": 0.6,
                            "summary": summary,
                        }
                    )

        return results

    async def _rank_search_results(
        self, results: list[dict[str, Any]], query: str
    ) -> list[dict[str, Any]]:
        """Rank search results by relevance."""
        # Sort by relevance score
        return sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)

    async def _generate_excerpts(
        self, results: list[dict[str, Any]], query: str
    ) -> list[dict[str, Any]]:
        """Generate highlighted excerpts."""
        results_with_excerpts = []
        excerpt_limit = 240
        window_radius = 90
        query_terms = self._extract_query_terms(query)

        for result in results:
            document = result.get("document", {})
            content = document.get("content", "")
            semantic_offsets = result.get("semantic_match_offsets") or result.get("match_offsets")
            excerpt = self._build_excerpt(
                content=content,
                query_terms=query_terms,
                max_length=excerpt_limit,
                window_radius=window_radius,
                semantic_offsets=semantic_offsets if isinstance(semantic_offsets, list) else None,
            )

            results_with_excerpts.append(
                {
                    "document_id": result.get("document_id"),
                    "title": document.get("title"),
                    "type": document.get("type"),
                    "date": document.get("created_at"),
                    "excerpt": excerpt,
                    "relevance_score": result.get("relevance_score"),
                    "summary": result.get("summary"),
                }
            )

        return results_with_excerpts

    def _extract_query_terms(self, query: str) -> list[str]:
        return [token for token in re.findall(r"\w+", query, flags=re.UNICODE) if len(token) > 1]

    def _build_excerpt(
        self,
        *,
        content: str,
        query_terms: list[str],
        max_length: int,
        window_radius: int,
        semantic_offsets: list[Any] | None = None,
    ) -> str:
        text = self._normalize_excerpt_text(content)
        if not text:
            return ""

        match_spans = self._find_match_spans(text, query_terms)
        semantic_spans = self._normalize_offset_spans(semantic_offsets, len(text))
        candidate_spans = semantic_spans or match_spans

        if candidate_spans:
            center = candidate_spans[0][0]
            for start, end in candidate_spans:
                if (end - start) > 0:
                    center = start + ((end - start) // 2)
                    break
            start_idx = max(0, center - window_radius)
            end_idx = min(len(text), center + window_radius)
            excerpt = text[start_idx:end_idx].strip()
            if start_idx > 0:
                excerpt = "..." + excerpt
            if end_idx < len(text):
                excerpt = excerpt + "..."
        else:
            excerpt = text[:max_length].strip()
            if len(text) > max_length:
                excerpt += "..."

        excerpt = self._enforce_excerpt_limit(excerpt, max_length)
        return self._highlight_terms(excerpt, query_terms)

    def _normalize_excerpt_text(self, content: str) -> str:
        without_markup = re.sub(r"<[^>]+>", " ", content)
        return re.sub(r"\s+", " ", without_markup, flags=re.UNICODE).strip()

    def _normalize_offset_spans(
        self, offsets: list[Any] | None, content_length: int
    ) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        if not offsets:
            return spans

        for item in offsets:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                start, end = item[0], item[1]
            elif isinstance(item, dict):
                start = item.get("start")
                end = item.get("end")
            else:
                continue

            if not isinstance(start, int) or not isinstance(end, int):
                continue
            if end <= start:
                continue

            clamped_start = max(0, min(start, content_length))
            clamped_end = max(clamped_start, min(end, content_length))
            if clamped_end > clamped_start:
                spans.append((clamped_start, clamped_end))

        return sorted(spans)

    def _find_match_spans(self, text: str, query_terms: list[str]) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        for term in query_terms:
            escaped_term = re.escape(term)
            for match in re.finditer(escaped_term, text, flags=re.IGNORECASE | re.UNICODE):
                spans.append((match.start(), match.end()))
        return sorted(spans)

    def _enforce_excerpt_limit(self, excerpt: str, max_length: int) -> str:
        if len(excerpt) <= max_length:
            return excerpt

        clipped = excerpt[: max(0, max_length - 3)].rstrip()
        if clipped.startswith("...") and not clipped.endswith("..."):
            return clipped + "..."
        return clipped + "..."

    def _highlight_terms(self, excerpt: str, query_terms: list[str]) -> str:
        if not excerpt or not query_terms:
            return excerpt

        unique_terms = sorted({term for term in query_terms if term}, key=len, reverse=True)
        if not unique_terms:
            return excerpt

        pattern = "|".join(re.escape(term) for term in unique_terms)
        return re.sub(
            rf"(?i)({pattern})",
            r"<mark>\1</mark>",
            excerpt,
            flags=re.UNICODE,
        )

    async def _find_related_documents(self, document_id: str) -> list[dict[str, Any]]:
        """Find related documents."""
        document = self.documents.get(document_id)
        if not document:
            return []
        content = document.get("content", "")
        results = self.vector_index.search(content, top_k=5)
        related = []
        for result in results:
            if result.doc_id == document_id:
                continue
            related.append(
                {
                    "document_id": result.doc_id,
                    "score": result.score,
                    "title": self.documents.get(result.doc_id, {}).get("title"),
                }
            )
        return related

    async def _generate_summary(self, content: str, max_length: int) -> str:
        """Generate summary using NLG."""
        if len(content) <= max_length:
            return content

        sentences = content.split(". ")
        summary = ". ".join(sentences[:3])
        return summary[:max_length] + ("..." if len(summary) > max_length else "")

    async def summarise_document(self, text: str) -> str:
        """Create concise summary using LLM/prompt registry with prompt-injection sanitisation."""
        sanitized_text = sanitize_prompt(text)
        if detect_injection(text):
            self.logger.warning(
                "Potential prompt injection detected in summary input; sanitized text used"
            )

        prompt_template = self._load_summary_prompt_template()
        prompt = prompt_template.format(text=sanitized_text, token_limit=self.summary_token_limit)
        if self.summarizer:
            payload = {
                "prompt": prompt,
                "text": sanitized_text,
                "max_tokens": self.summary_token_limit,
            }
            result = await self._invoke_summarizer(payload)
            if result:
                return result

        fallback_char_limit = max(self.max_summary_length, self.summary_token_limit * 5)
        return await self._generate_summary(sanitized_text, fallback_char_limit)

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

    async def _extract_entities_from_text(self, text: str) -> list[dict[str, Any]]:
        """Extract normalized entities using pluggable NLP pipeline with deterministic fallback."""
        return self.entity_extractor.extract(text, limit=20)

    async def _build_entity_relationships(
        self, document_id: str, entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Build relationships between entities."""
        relationships = []

        for i, entity1 in enumerate(entities):
            for entity2 in entities[i + 1 :]:
                relationships.append(
                    {
                        "from": entity1.get("text"),
                        "to": entity2.get("text"),
                        "type": "related",
                        "confidence": 0.6,
                    }
                )

        return relationships

    async def _categorize_lesson(self, lesson_data: dict[str, Any]) -> str:
        """Categorize lesson learned."""
        description = lesson_data.get("description", "").lower()

        if "vendor" in description or "procurement" in description:
            return "vendor_management"
        elif "risk" in description:
            return "risk_management"
        elif "quality" in description or "defect" in description:
            return "quality_management"
        else:
            return "general"

    async def _find_similar_lessons(self, lesson_data: dict[str, Any]) -> list[str]:
        """Find similar lessons learned."""
        query = f"{lesson_data.get('title', '')} {lesson_data.get('description', '')}".strip()
        if not query:
            return []
        results = self.vector_index.search(query, top_k=5)
        similar = []
        for result in results:
            if result.doc_id.startswith("lesson:"):
                similar.append(result.doc_id.split("lesson:", 1)[1])
        return similar

    async def _find_relevant_documents(
        self, task: str, project_id: str, role: str
    ) -> list[dict[str, Any]]:
        """Find relevant documents for recommendation."""
        relevant = []

        for doc_id, document in self.documents.items():
            if document.get("deleted"):
                continue

            if document.get("project_id") == project_id:
                relevant.append({"document_id": doc_id, "document": document, "relevance": 0.8})

        return relevant

    async def _rank_recommendations(
        self, recommendations: list[dict[str, Any]], context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Rank recommendations by relevance."""
        return sorted(recommendations, key=lambda x: x.get("relevance", 0), reverse=True)[:10]

    async def _add_taxonomy_category(self, category: dict[str, Any]) -> str:
        """Add taxonomy category."""
        category_id = f"CAT-{len(self.taxonomy) + 1}"
        self.taxonomy[category_id] = category
        return category_id

    async def _update_taxonomy_category(self, category_id: str, updates: dict[str, Any]) -> None:
        """Update taxonomy category."""
        if category_id in self.taxonomy:
            self.taxonomy[category_id].update(updates)

    async def _delete_taxonomy_category(self, category_id: str) -> None:
        """Delete taxonomy category."""
        if category_id in self.taxonomy:
            del self.taxonomy[category_id]

    async def _matches_search_filters(
        self, document: dict[str, Any], filters: dict[str, Any]
    ) -> bool:
        """Check if document matches search filters."""
        if "type" in filters and document.get("type") != filters["type"]:
            return False

        if "project_id" in filters and document.get("project_id") != filters["project_id"]:
            return False

        if "tags" in filters:
            doc_tags = set(document.get("tags", []))
            filter_tags = set(filters["tags"])
            if not doc_tags.intersection(filter_tags):
                return False

        return True

    async def _validate_document_schema(self, record: dict[str, Any]) -> None:
        """Validate document record against schema."""
        try:
            jsonschema_validate(instance=record, schema=self.document_schema)
        except ValidationError as exc:
            raise ValueError(f"Document schema validation failed: {exc.message}") from exc

    async def _map_doc_type_for_schema(self, doc_type: str | None) -> str:
        """Map internal document type to schema doc_type."""
        if not doc_type:
            return "report"
        mapping = {
            "requirements": "requirement",
            "design": "specification",
            "test_plan": "specification",
            "charter": "report",
            "policy": "policy",
            "procedure": "policy",
            "report": "report",
            "lessons_learned": "report",
            "meeting_minutes": "report",
        }
        return mapping.get(doc_type, "report")

    async def _is_access_allowed(
        self, document: dict[str, Any], access_context: dict[str, Any]
    ) -> bool:
        """Evaluate RBAC/ABAC rules for document access."""
        if document.get("classification") == "public":
            return True

        permissions = document.get("permissions", {})
        if permissions.get("public"):
            return True

        if not access_context:
            return False

        user_id = access_context.get("user_id")
        if user_id and user_id in permissions.get("users", []):
            return True

        roles = set(access_context.get("roles", []))
        if roles and roles.intersection(set(permissions.get("roles", []))):
            return True

        required_attrs = permissions.get("attributes", {})
        if required_attrs:
            user_attrs = access_context.get("attributes", {})
            for key, value in required_attrs.items():
                if user_attrs.get(key) != value:
                    return False
            return True

        return False

    def _load_document(self, tenant_id: str, document_id: str) -> dict[str, Any] | None:
        """Load document from memory or persistent store."""
        document = self.documents.get(document_id)
        if document:
            return document
        stored = self.document_store.get(tenant_id, document_id)
        if stored:
            self.documents[document_id] = stored
        return stored

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Knowledge & Document Management Agent...")
        if self.event_bus and hasattr(self.event_bus, "stop"):
            await self.event_bus.stop()

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
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
