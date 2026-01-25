"""
Agent 19: Knowledge & Document Management Agent

Purpose:
Serves as the central hub for creating, storing, classifying, retrieving and sharing
documents, decisions and lessons learned across the project portfolio.

Specification: docs_markdown/specs/agents/Agent 19 Knowledge & Document Management Agent.md
"""

from datetime import datetime
from typing import Any

from src.core.base_agent import BaseAgent


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

    def __init__(self, agent_id: str = "agent_019", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.max_summary_length = config.get("max_summary_length", 500) if config else 500
        self.search_result_limit = config.get("search_result_limit", 50) if config else 50
        self.similarity_threshold = config.get("similarity_threshold", 0.75) if config else 0.75

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

        # Data stores (will be replaced with database)
        self.documents: dict[str, Any] = {}
        self.document_versions: dict[str, Any] = {}
        self.summaries: dict[str, Any] = {}
        self.knowledge_graph: dict[str, Any] = {}
        self.lessons_learned: dict[str, Any] = {}
        self.taxonomy: dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize document storage, search services, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Knowledge & Document Management Agent...")

        # TODO: Initialize Azure Blob Storage with versioning for document storage
        # TODO: Set up Azure Data Lake Storage Gen2 for large files
        # TODO: Connect to Azure SQL Database or Cosmos DB for metadata
        # TODO: Initialize Azure Cognitive Search with semantic ranking
        # TODO: Set up Azure OpenAI Service for summarization and NLU
        # TODO: Initialize Cosmos DB Gremlin API for knowledge graph
        # TODO: Connect to SharePoint/OneDrive via Microsoft Graph API
        # TODO: Set up Office Online Server for in-browser editing
        # TODO: Initialize Azure Form Recognizer for entity extraction
        # TODO: Connect to Git repositories for technical documentation
        # TODO: Set up Azure Service Bus for document event publishing
        # TODO: Initialize Azure AD for authentication and RBAC

        self.logger.info("Knowledge & Document Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "upload_document",
            "search_documents",
            "get_document",
            "update_document",
            "delete_document",
            "classify_document",
            "summarize_document",
            "extract_entities",
            "build_knowledge_graph",
            "capture_lesson_learned",
            "recommend_documents",
            "manage_taxonomy",
            "track_document_access",
            "get_document_version_history",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "upload_document":
            document_data = input_data.get("document", {})
            if not document_data.get("title") or not document_data.get("content"):
                self.logger.warning("Missing required document fields")
                return False

        elif action == "search_documents":
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

        if action == "upload_document":
            return await self._upload_document(input_data.get("document", {}))

        elif action == "search_documents":
            return await self._search_documents(
                input_data.get("query"), input_data.get("filters", {})  # type: ignore
            )

        elif action == "get_document":
            return await self._get_document(input_data.get("document_id"))  # type: ignore

        elif action == "update_document":
            return await self._update_document(
                input_data.get("document_id"), input_data.get("document", {})  # type: ignore
            )

        elif action == "delete_document":
            return await self._delete_document(input_data.get("document_id"))  # type: ignore

        elif action == "classify_document":
            return await self._classify_document(input_data.get("document_id"))  # type: ignore

        elif action == "summarize_document":
            return await self._summarize_document(input_data.get("document_id"))  # type: ignore

        elif action == "extract_entities":
            return await self._extract_entities(input_data.get("document_id"))  # type: ignore

        elif action == "build_knowledge_graph":
            return await self._build_knowledge_graph(input_data.get("document_id"))  # type: ignore

        elif action == "capture_lesson_learned":
            return await self._capture_lesson_learned(input_data.get("lesson", {}))

        elif action == "recommend_documents":
            return await self._recommend_documents(input_data.get("user_context", {}))

        elif action == "manage_taxonomy":
            return await self._manage_taxonomy(input_data.get("taxonomy", {}))

        elif action == "track_document_access":
            return await self._track_document_access(input_data.get("document_id"))  # type: ignore

        elif action == "get_document_version_history":
            return await self._get_document_version_history(input_data.get("document_id"))  # type: ignore

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _upload_document(self, document_data: dict[str, Any]) -> dict[str, Any]:
        """
        Upload and classify document.

        Returns document ID and metadata.
        """
        self.logger.info(f"Uploading document: {document_data.get('title')}")

        # Generate document ID
        document_id = await self._generate_document_id()

        # Extract metadata
        metadata = await self._extract_metadata(document_data)

        # Auto-classify document
        classification = await self._auto_classify_document(document_data)

        # Generate initial tags
        tags = await self._generate_tags(document_data, classification)

        # Create document record
        document = {
            "document_id": document_id,
            "title": document_data.get("title"),
            "content": document_data.get("content"),
            "type": classification.get("type"),
            "tags": tags,
            "author": document_data.get("author"),
            "project_id": document_data.get("project_id"),
            "program_id": document_data.get("program_id"),
            "portfolio_id": document_data.get("portfolio_id"),
            "metadata": metadata,
            "version": 1,
            "permissions": document_data.get("permissions", {"public": False}),
            "created_at": datetime.utcnow().isoformat(),
            "modified_at": datetime.utcnow().isoformat(),
            "accessed_count": 0,
        }

        # Store document
        self.documents[document_id] = document

        # Store version
        self.document_versions[document_id] = [document.copy()]

        # Generate summary asynchronously
        # TODO: Queue for async processing
        await self._summarize_document(document_id)

        # Extract entities for knowledge graph
        await self._extract_entities(document_id)

        # TODO: Store in Azure Blob Storage
        # TODO: Index in Azure Cognitive Search
        # TODO: Store metadata in database
        # TODO: Publish document.uploaded event

        return {
            "document_id": document_id,
            "title": document["title"],
            "version": document["version"],
            "type": document["type"],
            "tags": tags,
            "classification": classification,
            "next_steps": "Document indexed and ready for search",
        }

    async def _search_documents(self, query: str, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Search documents using semantic search.

        Returns ranked search results.
        """
        self.logger.info(f"Searching documents: {query}")

        # Perform semantic search
        # TODO: Use Azure Cognitive Search with semantic ranking
        search_results = await self._semantic_search(query, filters)

        # Rank results
        ranked_results = await self._rank_search_results(search_results, query)

        # Generate excerpts
        results_with_excerpts = await self._generate_excerpts(ranked_results, query)

        return {
            "query": query,
            "total_results": len(results_with_excerpts),
            "results": results_with_excerpts[: self.search_result_limit],
            "filters": filters,
        }

    async def _get_document(self, document_id: str) -> dict[str, Any]:
        """
        Retrieve document with metadata.

        Returns full document.
        """
        self.logger.info(f"Retrieving document: {document_id}")

        document = self.documents.get(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Update access count
        document["accessed_count"] = document.get("accessed_count", 0) + 1
        document["last_accessed_at"] = datetime.utcnow().isoformat()

        # Get summary if available
        summary = self.summaries.get(document_id, {}).get("content")

        # Get related documents
        related_documents = await self._find_related_documents(document_id)

        # TODO: Log access for audit
        # TODO: Track document access

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
        }

    async def _update_document(self, document_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """
        Update document and create new version.

        Returns updated document version.
        """
        self.logger.info(f"Updating document: {document_id}")

        document = self.documents.get(document_id)
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
        document["modified_at"] = datetime.utcnow().isoformat()

        # Re-classify if content changed
        if "content" in updates:
            classification = await self._auto_classify_document(document)
            document["type"] = classification.get("type")

            # Regenerate summary
            await self._summarize_document(document_id)

        # TODO: Store in database
        # TODO: Update search index
        # TODO: Publish document.updated event

        return {
            "document_id": document_id,
            "version": document["version"],
            "modified_at": document["modified_at"],
            "changes": list(updates.keys()),
        }

    async def _delete_document(self, document_id: str) -> dict[str, Any]:
        """
        Delete document (soft delete).

        Returns deletion confirmation.
        """
        self.logger.info(f"Deleting document: {document_id}")

        document = self.documents.get(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Soft delete
        document["deleted"] = True
        document["deleted_at"] = datetime.utcnow().isoformat()

        # TODO: Mark as deleted in database
        # TODO: Remove from search index
        # TODO: Publish document.deleted event

        return {"document_id": document_id, "deleted": True, "deleted_at": document["deleted_at"]}

    async def _classify_document(self, document_id: str) -> dict[str, Any]:
        """
        Classify document using AI.

        Returns classification and tags.
        """
        self.logger.info(f"Classifying document: {document_id}")

        document = self.documents.get(document_id)
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

        # TODO: Store in database
        # TODO: Update search index

        return {
            "document_id": document_id,
            "type": classification.get("type"),
            "tags": tags,
            "confidence": classification.get("confidence"),
            "suggested_category": classification.get("category"),
        }

    async def _summarize_document(self, document_id: str) -> dict[str, Any]:
        """
        Generate document summary using NLG.

        Returns generated summary.
        """
        self.logger.info(f"Summarizing document: {document_id}")

        document = self.documents.get(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Generate summary using AI
        # TODO: Use Azure OpenAI for summarization
        summary_content = await self._generate_summary(
            document.get("content", ""), self.max_summary_length
        )

        # Store summary
        self.summaries[document_id] = {
            "document_id": document_id,
            "content": summary_content,
            "length": len(summary_content),
            "generated_at": datetime.utcnow().isoformat(),
        }

        # TODO: Store in database

        return {
            "document_id": document_id,
            "summary": summary_content,
            "length": len(summary_content),
        }

    async def _extract_entities(self, document_id: str) -> dict[str, Any]:
        """
        Extract entities from document using NLP.

        Returns extracted entities.
        """
        self.logger.info(f"Extracting entities from document: {document_id}")

        document = self.documents.get(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Extract entities using NLP
        # TODO: Use Azure Form Recognizer or Azure OpenAI
        entities = await self._extract_entities_from_text(document.get("content", ""))

        # Store in knowledge graph
        if document_id not in self.knowledge_graph:
            self.knowledge_graph[document_id] = {"entities": [], "relationships": []}

        self.knowledge_graph[document_id]["entities"] = entities

        # TODO: Store in graph database

        return {"document_id": document_id, "entities": entities, "entity_count": len(entities)}

    async def _build_knowledge_graph(self, document_id: str) -> dict[str, Any]:
        """
        Build knowledge graph relationships.

        Returns graph structure.
        """
        self.logger.info(f"Building knowledge graph for document: {document_id}")

        document = self.documents.get(document_id)
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

        # TODO: Store in graph database (Cosmos DB Gremlin API)

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
        self.logger.info(f"Capturing lesson learned: {lesson_data.get('title')}")

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
            "date": lesson_data.get("date", datetime.utcnow().isoformat()),
            "owner": lesson_data.get("owner"),
            "similar_lessons": similar_lessons,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store lesson
        self.lessons_learned[lesson_id] = lesson

        # TODO: Store in database
        # TODO: Index for search
        # TODO: Publish lesson.captured event

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
        # TODO: Use recommendation engine
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

    async def _track_document_access(self, document_id: str) -> dict[str, Any]:
        """
        Track document access patterns.

        Returns access statistics.
        """
        self.logger.info(f"Tracking access for document: {document_id}")

        document = self.documents.get(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Get access statistics
        # TODO: Query from audit logs
        access_stats = {
            "total_accesses": document.get("accessed_count", 0),
            "last_accessed": document.get("last_accessed_at"),
            "unique_users": 0,  # TODO: Calculate from logs
            "access_trend": "stable",  # TODO: Calculate trend
        }

        return {"document_id": document_id, "access_stats": access_stats}

    async def _get_document_version_history(self, document_id: str) -> dict[str, Any]:
        """
        Get document version history.

        Returns version list.
        """
        self.logger.info(f"Retrieving version history for document: {document_id}")

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

    # Helper methods

    async def _generate_document_id(self) -> str:
        """Generate unique document ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"DOC-{timestamp}"

    async def _generate_lesson_id(self) -> str:
        """Generate unique lesson ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"LESSON-{timestamp}"

    async def _extract_metadata(self, document_data: dict[str, Any]) -> dict[str, Any]:
        """Extract metadata from document."""
        return {
            "file_size": len(document_data.get("content", "")),
            "format": document_data.get("format", "text"),
            "language": "en",  # TODO: Detect language
        }

    async def _auto_classify_document(self, document_data: dict[str, Any]) -> dict[str, Any]:
        """Auto-classify document using AI."""
        # TODO: Use Azure ML for classification
        content = document_data.get("content", "").lower()

        if "requirement" in content or "shall" in content:
            doc_type = "requirements"
        elif "test" in content or "verify" in content:
            doc_type = "test_plan"
        elif "lesson" in content or "learned" in content:
            doc_type = "lessons_learned"
        elif "charter" in content or "objectives" in content:
            doc_type = "charter"
        else:
            doc_type = "report"

        return {"type": doc_type, "confidence": 0.85, "category": doc_type}

    async def _generate_tags(
        self, document_data: dict[str, Any], classification: dict[str, Any]
    ) -> list[str]:
        """Generate tags for document."""
        # TODO: Use NLP for tag generation
        tags = [classification.get("type")]

        if document_data.get("project_id"):
            tags.append("project")

        return tags  # type: ignore

    async def _semantic_search(self, query: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Perform semantic search."""
        # TODO: Use Azure Cognitive Search
        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        for doc_id, document in self.documents.items():
            if document.get("deleted"):
                continue

            # Simple text matching (replace with semantic search)
            if query_lower in document.get("content", "").lower():
                # Apply filters
                if await self._matches_search_filters(document, filters):
                    results.append(
                        {
                            "document_id": doc_id,
                            "document": document,
                            "relevance_score": 0.8,  # TODO: Calculate actual score
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

        for result in results:
            document = result.get("document", {})
            content = document.get("content", "")

            # Simple excerpt generation (replace with better algorithm)
            excerpt = content[:200] + "..." if len(content) > 200 else content

            results_with_excerpts.append(
                {
                    "document_id": result.get("document_id"),
                    "title": document.get("title"),
                    "type": document.get("type"),
                    "excerpt": excerpt,
                    "relevance_score": result.get("relevance_score"),
                }
            )

        return results_with_excerpts

    async def _find_related_documents(self, document_id: str) -> list[dict[str, Any]]:
        """Find related documents."""
        # TODO: Use knowledge graph and similarity
        return []

    async def _generate_summary(self, content: str, max_length: int) -> str:
        """Generate summary using NLG."""
        # TODO: Use Azure OpenAI for summarization
        if len(content) <= max_length:
            return content

        return content[:max_length] + "..."

    async def _extract_entities_from_text(self, text: str) -> list[dict[str, Any]]:
        """Extract entities from text using NLP."""
        # TODO: Use Azure Form Recognizer or Azure OpenAI
        entities = []

        # Simple entity extraction (replace with NLP)
        words = text.split()
        for i, word in enumerate(words):
            if word.istitle() and len(word) > 3:
                entities.append({"text": word, "type": "entity", "position": i})

        return entities[:10]  # Limit to 10

    async def _build_entity_relationships(
        self, document_id: str, entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Build relationships between entities."""
        # TODO: Use graph algorithms
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
        # TODO: Use AI for categorization
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
        # TODO: Use similarity search
        similar = []

        for lesson_id, lesson in self.lessons_learned.items():
            if lesson.get("category") == await self._categorize_lesson(lesson_data):
                similar.append(lesson_id)

        return similar[:5]

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

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Knowledge & Document Management Agent...")
        # TODO: Close database connections
        # TODO: Close blob storage connections
        # TODO: Close search service connections
        # TODO: Flush pending events

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
            "lessons_learned_capture",
            "document_recommendations",
            "taxonomy_management",
            "collaborative_editing",
            "access_control",
            "audit_logging",
            "nlp_processing",
            "content_analysis",
        ]
