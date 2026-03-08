"""Search and recommendation action handlers for the Knowledge Management Agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from knowledge_utils import build_excerpt, extract_query_terms

if TYPE_CHECKING:
    from knowledge_management_agent import KnowledgeManagementAgent


async def search_documents(
    agent: KnowledgeManagementAgent,
    query: str,
    filters: dict[str, Any],
    access_context: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """
    Search documents using semantic search.

    Returns ranked search results.
    """
    agent.logger.info("Searching documents: %s", query)

    # Perform semantic search
    search_results = await _semantic_search(agent, query, filters, access_context, tenant_id)

    # Rank results
    ranked_results = await _rank_search_results(search_results, query)

    # Generate excerpts
    results_with_excerpts = await _generate_excerpts(ranked_results, query)

    return {
        "query": query,
        "total_results": len(results_with_excerpts),
        "results": results_with_excerpts[: agent.semantic_result_limit],
        "filters": filters,
    }


async def recommend_documents(
    agent: KnowledgeManagementAgent, user_context: dict[str, Any]
) -> dict[str, Any]:
    """
    Recommend relevant documents based on context.

    Returns recommended documents.
    """
    agent.logger.info("Generating document recommendations")

    # Get user's current task/project
    current_task = user_context.get("current_task")
    project_id = user_context.get("project_id")
    role = user_context.get("role")

    # Find relevant documents
    recommendations = await _find_relevant_documents(agent, current_task, project_id, role)  # type: ignore

    # Rank by relevance
    ranked_recommendations = await _rank_recommendations(recommendations, user_context)

    return {
        "recommendations": ranked_recommendations,
        "count": len(ranked_recommendations),
        "context": user_context,
    }


async def find_related_documents(
    agent: KnowledgeManagementAgent, document_id: str
) -> list[dict[str, Any]]:
    """Find related documents."""
    document = agent.documents.get(document_id)
    if not document:
        return []
    content = document.get("content", "")
    results = agent.vector_index.search(content, top_k=5)
    related = []
    for result in results:
        if result.doc_id == document_id:
            continue
        related.append(
            {
                "document_id": result.doc_id,
                "score": result.score,
                "title": agent.documents.get(result.doc_id, {}).get("title"),
            }
        )
    return related


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _semantic_search(
    agent: KnowledgeManagementAgent,
    query: str,
    filters: dict[str, Any],
    access_context: dict[str, Any],
    tenant_id: str,
) -> list[dict[str, Any]]:
    """Perform semantic search."""
    results: list[dict[str, Any]] = []
    vector_hits = agent.vector_index.search(query, top_k=agent.search_result_limit)

    for hit in vector_hits:
        document = agent._load_document(tenant_id, hit.doc_id)
        if not document or document.get("deleted"):
            continue
        if hit.score < agent.similarity_threshold:
            continue
        if not await agent._is_access_allowed(document, access_context):
            continue
        if not await agent._matches_search_filters(document, filters):
            continue
        summary = await agent.summarise_document(document.get("content", ""))
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
    for doc_id, document in agent.documents.items():
        if document.get("deleted"):
            continue
        if query_lower in document.get("content", "").lower():
            if not await agent._is_access_allowed(document, access_context):
                continue
            if await agent._matches_search_filters(document, filters):
                summary = await agent.summarise_document(document.get("content", ""))
                results.append(
                    {
                        "document_id": doc_id,
                        "document": document,
                        "relevance_score": 0.6,
                        "summary": summary,
                    }
                )

    return results


async def _rank_search_results(results: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Rank search results by relevance."""
    return sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)


async def _generate_excerpts(results: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Generate highlighted excerpts."""
    results_with_excerpts = []
    excerpt_limit = 240
    window_radius = 90
    query_terms = extract_query_terms(query)

    for result in results:
        document = result.get("document", {})
        content = document.get("content", "")
        semantic_offsets = result.get("semantic_match_offsets") or result.get("match_offsets")
        excerpt = build_excerpt(
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


async def _find_relevant_documents(
    agent: KnowledgeManagementAgent, task: str, project_id: str, role: str
) -> list[dict[str, Any]]:
    """Find relevant documents for recommendation."""
    relevant = []

    for doc_id, document in agent.documents.items():
        if document.get("deleted"):
            continue

        if document.get("project_id") == project_id:
            relevant.append({"document_id": doc_id, "document": document, "relevance": 0.8})

    return relevant


async def _rank_recommendations(
    recommendations: list[dict[str, Any]], context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Rank recommendations by relevance."""
    return sorted(recommendations, key=lambda x: x.get("relevance", 0), reverse=True)[:10]
