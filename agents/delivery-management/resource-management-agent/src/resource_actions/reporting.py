"""Action handlers: search_resources, match_skills, get_resource_pool."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from resource_models import EmbeddingClient
from resource_utils import cosine_similarity, get_effective_skills

from resource_actions.helpers import find_matching_resources, get_performance_score

if TYPE_CHECKING:
    from resource_capacity_agent import ResourceCapacityAgent


async def handle_search_resources(
    agent: ResourceCapacityAgent,
    search_criteria: dict[str, Any],
) -> dict[str, Any]:
    """
    Search for resources by criteria.

    Returns matching resources.
    """
    agent.logger.info("Searching for resources")

    role = search_criteria.get("role")
    location = search_criteria.get("location")
    skills = search_criteria.get("skills", [])
    availability_required = search_criteria.get("availability_required")

    matching_resources = []

    for resource_id, resource in agent.resource_pool.items():
        # Check role
        if role and resource.get("role") != role:
            continue

        # Check location
        if location and resource.get("location") != location:
            continue

        # Check skills
        if skills:
            resource_skills = set(get_effective_skills(resource))
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


async def handle_match_skills(
    agent: ResourceCapacityAgent,
    skills_required: list[str],
    project_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Match resources to required skills using AI.

    Returns ranked candidates with skill match scores.
    """
    agent.logger.info("Matching skills to resources")

    candidates = []
    query_text = " ".join(skills_required)
    embedding_client = agent.embedding_client or EmbeddingClient(None, None, None)
    query_embedding = embedding_client.get_embedding(query_text)
    search_candidates = []
    if agent.search_client and agent.search_client.is_configured():
        if not agent._skills_indexed:
            await agent._index_skills()
        search_candidates = agent.search_client.query_documents(
            query_embedding, query_text=query_text, top_k=10
        )
    if search_candidates:
        for result in search_candidates:
            resource_id = result.get("resource_id")
            resource = agent.resource_pool.get(resource_id, {})
            if not resource_id:
                continue
            performance_score = await get_performance_score(agent, resource_id, project_context)
            semantic_score = float(result.get("@search.score", 0.0))
            combined_score = (semantic_score * 0.6) + (performance_score * 0.4)
            if combined_score >= agent.skill_matching_threshold:
                candidates.append(
                    {
                        "resource_id": resource_id,
                        "resource_name": resource.get("name"),
                        "role": resource.get("role"),
                        "skills": get_effective_skills(resource),
                        "match_score": semantic_score,
                        "weighted_score": semantic_score,
                        "availability_score": resource.get("availability", 0.0),
                        "cost_score": resource.get("cost_rate", 0.0),
                        "performance_score": performance_score,
                        "combined_score": combined_score,
                        "cost_rate": resource.get("cost_rate"),
                    }
                )
    else:
        matches = await find_matching_resources(agent, skills_required)
        for match in matches:
            resource_id = match["resource_id"]
            resource_skills = " ".join(match.get("skills", []))
            resource_embedding = embedding_client.get_embedding(resource_skills)
            semantic_similarity = cosine_similarity(query_embedding, resource_embedding)
            performance_score = await get_performance_score(agent, resource_id, project_context)
            combined_score = (
                match["weighted_score"] * 0.5 + semantic_similarity * 0.3 + performance_score * 0.2
            )

            if combined_score >= agent.skill_matching_threshold:
                candidates.append(
                    {
                        "resource_id": resource_id,
                        "resource_name": match.get("resource_name"),
                        "role": match.get("role"),
                        "skills": match.get("skills", []),
                        "match_score": semantic_similarity,
                        "weighted_score": match.get("weighted_score"),
                        "availability_score": match.get("availability_score"),
                        "cost_score": match.get("cost_score"),
                        "performance_score": performance_score,
                        "combined_score": combined_score,
                        "cost_rate": agent.resource_pool.get(resource_id, {}).get("cost_rate"),
                    }
                )

    candidates.sort(key=lambda x: x["combined_score"], reverse=True)

    return {
        "skills_required": skills_required,
        "candidates": candidates,
        "total_candidates": len(candidates),
    }


async def handle_get_resource_pool(
    agent: ResourceCapacityAgent,
    filters: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """Retrieve resource pool data."""
    role_filter = filters.get("role")
    location_filter = filters.get("location")
    status_filter = filters.get("status", "Active")

    filtered_resources = []

    resources = list(agent.resource_pool.values())
    if not resources:
        resources = agent.resource_store.list(tenant_id)
        for resource in resources:
            resource_id = resource.get("resource_id")
            if resource_id:
                agent.resource_pool[resource_id] = resource

    for resource in resources:
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
