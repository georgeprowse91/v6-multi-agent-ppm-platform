"""Classification, summarization, taxonomy and lessons-learned action handlers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from knowledge_utils import (
    classify_topic_phase_domain,
    detect_language,
    extract_document_attributes,
    extract_keywords,
    generate_lesson_id,
)

if TYPE_CHECKING:
    from knowledge_management_agent import KnowledgeManagementAgent


async def classify_document(
    agent: KnowledgeManagementAgent, document_id: str, tenant_id: str
) -> dict[str, Any]:
    """
    Classify document using AI.

    Returns classification and tags.
    """
    agent.logger.info("Classifying document: %s", document_id)

    document = agent._load_document(tenant_id, document_id)
    if not document:
        raise ValueError(f"Document not found: {document_id}")

    # Auto-classify using AI
    classification = await auto_classify_document(agent, document)

    # Generate tags
    tags = await generate_tags(agent, document, classification)

    # Update document
    document["type"] = classification.get("type")
    document["tags"] = tags
    document["classification_confidence"] = classification.get("confidence")
    document["doc_type"] = await agent._map_doc_type_for_schema(classification.get("type"))
    document["topic"] = classification.get("topic")
    document["phase"] = classification.get("phase")
    document["domain"] = classification.get("domain")
    agent.document_store.upsert(tenant_id, document_id, document.copy())
    agent.knowledge_db.upsert_document(document)
    agent._index_document(document)

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


async def summarize_document(
    agent: KnowledgeManagementAgent, document_id: str, tenant_id: str
) -> dict[str, Any]:
    """
    Generate document summary using NLG.

    Returns generated summary.
    """
    agent.logger.info("Summarizing document: %s", document_id)

    document = agent._load_document(tenant_id, document_id)
    if not document:
        raise ValueError(f"Document not found: {document_id}")

    # Generate summary using AI
    summary_content = await agent.summarise_document(document.get("content", ""))

    # Store summary
    agent.summaries[document_id] = {
        "document_id": document_id,
        "content": summary_content,
        "length": len(summary_content),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    agent.knowledge_db.record_interaction(
        document_id,
        "summary",
        {"summary": summary_content, "generated_at": datetime.now(timezone.utc).isoformat()},
    )

    return {
        "document_id": document_id,
        "summary": summary_content,
        "length": len(summary_content),
    }


async def capture_lesson_learned(
    agent: KnowledgeManagementAgent, lesson_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Capture and categorize lesson learned.

    Returns lesson ID and categorization.
    """
    agent.logger.info("Capturing lesson learned: %s", lesson_data.get("title"))

    # Generate lesson ID
    lesson_id = await generate_lesson_id()

    # Categorize lesson
    category = await categorize_lesson(lesson_data)

    # Find similar lessons
    similar_lessons = await find_similar_lessons(agent, lesson_data)

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
    agent.lessons_learned[lesson_id] = lesson
    await agent._publish_event("knowledge.lesson.captured", lesson)
    agent.knowledge_db.record_interaction(
        lesson_id,
        "lesson",
        {"lesson": lesson, "created_at": lesson.get("created_at")},
    )
    agent.vector_index.add(
        f"lesson:{lesson_id}",
        f"{lesson.get('title', '')} {lesson.get('description', '')}",
        {"lesson_id": lesson_id, "category": lesson.get("category")},
    )
    await agent._publish_event("lesson.captured", {"lesson_id": lesson_id, "tenant_id": "shared"})

    return {
        "lesson_id": lesson_id,
        "title": lesson["title"],
        "category": category,
        "similar_lessons": len(similar_lessons),
        "recommendations": lesson.get("recommendation"),
    }


async def manage_taxonomy(
    agent: KnowledgeManagementAgent, taxonomy_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Manage knowledge taxonomy.

    Returns updated taxonomy structure.
    """
    agent.logger.info("Managing taxonomy")

    action = taxonomy_data.get("action", "get")

    if action == "add_category":
        category = taxonomy_data.get("category", {})
        category_id = f"CAT-{len(agent.taxonomy) + 1}"
        agent.taxonomy[category_id] = category
        return {"action": "add", "category_id": category_id}

    elif action == "update_category":
        category_id = taxonomy_data.get("category_id")  # type: ignore
        if category_id in agent.taxonomy:
            agent.taxonomy[category_id].update(taxonomy_data.get("updates", {}))
        return {"action": "update", "category_id": category_id}

    elif action == "delete_category":
        category_id = taxonomy_data.get("category_id")  # type: ignore
        if category_id in agent.taxonomy:
            del agent.taxonomy[category_id]
        return {"action": "delete", "category_id": category_id}

    else:  # get
        return {"taxonomy": agent.taxonomy, "total_categories": len(agent.taxonomy)}


# ---------------------------------------------------------------------------
# Shared classification / metadata helpers (used by document_actions too)
# ---------------------------------------------------------------------------


async def extract_metadata(
    agent: KnowledgeManagementAgent, document_data: dict[str, Any]
) -> dict[str, Any]:
    """Extract metadata from document."""
    content = document_data.get("content", "")
    keywords = extract_keywords(content)
    extracted = extract_document_attributes(content)
    return {
        "file_size": len(document_data.get("content", "")),
        "format": document_data.get("format", "text"),
        "language": detect_language(content),
        "keywords": keywords,
        "source": document_data.get("source"),
        "author": extracted.get("author"),
        "published_at": extracted.get("date"),
        "tags": extracted.get("tags", []),
    }


async def auto_classify_document(
    agent: KnowledgeManagementAgent, document_data: dict[str, Any]
) -> dict[str, Any]:
    """Auto-classify document using AI."""
    content = document_data.get("content", "")
    if agent.classifier_trained:
        label, scores = agent.classifier.predict(content)
        confidence = max(scores.values()) if scores else 0.5
        extra = classify_topic_phase_domain(content)
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

    extra = classify_topic_phase_domain(content)
    return {
        "type": doc_type,
        "confidence": 0.85,
        "category": doc_type,
        "topic": extra.get("topic"),
        "phase": extra.get("phase"),
        "domain": extra.get("domain"),
    }


async def generate_tags(
    agent: KnowledgeManagementAgent,
    document_data: dict[str, Any],
    classification: dict[str, Any],
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
    keywords = extract_keywords(document_data.get("content", ""))
    tags.update(keywords[:5])
    if document_data.get("project_id"):
        tags.add("project")
    if document_data.get("program_id"):
        tags.add("program")
    if document_data.get("portfolio_id"):
        tags.add("portfolio")
    return list(tags)


async def categorize_lesson(lesson_data: dict[str, Any]) -> str:
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


async def find_similar_lessons(
    agent: KnowledgeManagementAgent, lesson_data: dict[str, Any]
) -> list[str]:
    """Find similar lessons learned."""
    query = f"{lesson_data.get('title', '')} {lesson_data.get('description', '')}".strip()
    if not query:
        return []
    results = agent.vector_index.search(query, top_k=5)
    similar = []
    for result in results:
        if result.doc_id.startswith("lesson:"):
            similar.append(result.doc_id.split("lesson:", 1)[1])
    return similar
