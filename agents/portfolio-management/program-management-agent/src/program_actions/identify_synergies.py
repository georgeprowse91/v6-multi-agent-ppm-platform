"""Action handler for identifying synergy opportunities across projects."""

from __future__ import annotations

import os
from itertools import combinations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from program_management_agent import ProgramManagementAgent


async def handle_identify_synergies(
    agent: ProgramManagementAgent,
    program_id: str,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Identify synergy opportunities across projects.

    Returns synergies with potential cost savings and efficiency gains.
    """
    agent.logger.info("Identifying synergies for program: %s", program_id)

    program = agent.program_store.get(tenant_id, program_id)
    if not program:
        raise ValueError(f"Program not found: {program_id}")

    constituent_projects = program.get("constituent_projects", [])

    # Analyze project scopes and technologies
    project_details = await agent._get_project_details(constituent_projects)
    synergy_analysis = await analyze_synergies(agent, project_details)

    shared_components = synergy_analysis.get("shared_components", [])
    vendor_synergies = synergy_analysis.get("vendor_consolidation", [])
    infrastructure_synergies = synergy_analysis.get("infrastructure_synergies", [])

    # Calculate potential savings
    project_costs = await agent._estimate_project_costs(constituent_projects, tenant_id=tenant_id)
    cost_savings = await _calculate_synergy_savings(
        shared_components, vendor_synergies, infrastructure_synergies, project_costs
    )
    optimization = await _optimize_synergy_portfolio(
        shared_components, vendor_synergies, infrastructure_synergies
    )
    mitigations = await _propose_synergy_mitigations(optimization)

    synergies = {
        "shared_components": shared_components,
        "vendor_consolidation": vendor_synergies,
        "infrastructure_sharing": infrastructure_synergies,
        "estimated_savings": cost_savings,
        "optimization": optimization,
        "mitigations": mitigations,
    }

    # Store synergies
    agent.synergies[program_id] = synergies
    if agent.db_service:
        await agent.db_service.store(
            "program_synergies",
            program_id,
            {"program_id": program_id, "synergies": synergies},
        )
        await agent.db_service.store(
            "program_analytics",
            program_id,
            {"program_id": program_id, "synergy_savings": cost_savings},
        )

    await agent.event_bus.publish(
        "program.synergy.identified",
        {
            "program_id": program_id,
            "tenant_id": tenant_id,
            "synergies": synergies,
            "estimated_savings": cost_savings,
        },
    )

    return {
        "program_id": program_id,
        "synergies": synergies,
        "total_savings": cost_savings.get("total", 0),
        "recommendations": await _generate_synergy_recommendations(synergies),
    }


# ---------------------------------------------------------------------------
# Public helper (also called from optimize_program)
# ---------------------------------------------------------------------------


async def analyze_synergies(
    agent: ProgramManagementAgent,
    project_details: dict[str, Any],
) -> dict[str, Any]:
    """Analyze synergies using Azure Cognitive Services Text Analytics."""
    documents = []
    project_ids = list(project_details.keys())
    for project_id in project_ids:
        detail = project_details.get(project_id, {})
        description = " ".join(
            str(value)
            for value in [
                detail.get("name"),
                detail.get("description"),
                " ".join(detail.get("scope", []) or []),
                " ".join(detail.get("resources", []) or []),
            ]
            if value
        )
        documents.append(description or project_id)

    key_phrases: list[set[str]] = []
    if agent.text_analytics_client is None:
        endpoint = os.getenv("TEXT_ANALYTICS_ENDPOINT")
        key = os.getenv("TEXT_ANALYTICS_KEY")
        if endpoint and key:
            from azure.ai.textanalytics import TextAnalyticsClient
            from azure.core.credentials import AzureKeyCredential

            agent.text_analytics_client = TextAnalyticsClient(
                endpoint=endpoint, credential=AzureKeyCredential(key)
            )
    if agent.text_analytics_client:
        results = agent.text_analytics_client.extract_key_phrases(documents)
        for result in results:
            if not result.is_error:
                key_phrases.append(set(result.key_phrases))
            else:
                key_phrases.append(set())
    else:
        for doc in documents:
            tokens = {token for token in doc.lower().split() if token.isalpha()}
            key_phrases.append(tokens)

    shared_components = []
    vendor_synergies = []
    infrastructure_synergies = []
    for idx_a, idx_b in combinations(range(len(project_ids)), 2):
        overlap = key_phrases[idx_a].intersection(key_phrases[idx_b])
        union = key_phrases[idx_a].union(key_phrases[idx_b])
        similarity = len(overlap) / len(union) if union else 0
        if similarity >= agent.synergy_detection_threshold:
            shared_components.append(
                {
                    "projects": [project_ids[idx_a], project_ids[idx_b]],
                    "similarity": similarity,
                    "overlap_terms": sorted(overlap),
                }
            )
            vendor_synergies.append(
                {
                    "projects": [project_ids[idx_a], project_ids[idx_b]],
                    "opportunity": "Consolidate vendors",
                    "similarity": similarity,
                }
            )
            infrastructure_synergies.append(
                {
                    "projects": [project_ids[idx_a], project_ids[idx_b]],
                    "opportunity": "Share infrastructure",
                    "similarity": similarity,
                }
            )

    return {
        "shared_components": shared_components,
        "vendor_consolidation": vendor_synergies,
        "infrastructure_synergies": infrastructure_synergies,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _calculate_synergy_savings(
    shared_components: list[dict[str, Any]],
    vendor_synergies: list[dict[str, Any]],
    infrastructure_synergies: list[dict[str, Any]],
    project_costs: dict[str, float],
) -> dict[str, float]:
    """Calculate potential cost savings from synergies."""

    def _pair_cost(pair: dict[str, Any]) -> float:
        projects = pair.get("projects", [])
        return sum(project_costs.get(project, 0) for project in projects)

    shared = sum(_pair_cost(item) * 0.06 for item in shared_components)
    vendor = sum(_pair_cost(item) * 0.04 for item in vendor_synergies)
    infrastructure = sum(_pair_cost(item) * 0.03 for item in infrastructure_synergies)
    return {
        "shared_components": shared,
        "vendor_consolidation": vendor,
        "infrastructure_sharing": infrastructure,
        "total": shared + vendor + infrastructure,
    }


async def _generate_synergy_recommendations(synergies: dict[str, Any]) -> list[str]:
    """Generate recommendations for synergy realization."""
    recommendations: list[str] = []
    if synergies.get("shared_components"):
        recommendations.append("Consolidate shared components into reusable modules")
    if synergies.get("vendor_consolidation"):
        recommendations.append("Negotiate combined vendor contracts for volume discounts")
    if synergies.get("optimization", {}).get("priority_actions"):
        recommendations.append("Execute prioritized synergy actions to maximize savings")
    return recommendations


async def _optimize_synergy_portfolio(
    shared_components: list[dict[str, Any]],
    vendor_synergies: list[dict[str, Any]],
    infrastructure_synergies: list[dict[str, Any]],
) -> dict[str, Any]:
    opportunities: list[dict[str, Any]] = []
    for item in shared_components:
        opportunities.append(
            {
                "type": "shared_component",
                "projects": item.get("projects", []),
                "score": item.get("similarity", 0) * 0.6 + 0.4,
                "estimated_value": 15000,
            }
        )
    for item in vendor_synergies:
        opportunities.append(
            {
                "type": "vendor_consolidation",
                "projects": item.get("projects", []),
                "score": item.get("similarity", 0) * 0.5 + 0.3,
                "estimated_value": 10000,
            }
        )
    for item in infrastructure_synergies:
        opportunities.append(
            {
                "type": "infrastructure_sharing",
                "projects": item.get("projects", []),
                "score": item.get("similarity", 0) * 0.4 + 0.2,
                "estimated_value": 8000,
            }
        )
    opportunities.sort(key=lambda item: item["score"] * item["estimated_value"], reverse=True)
    priority_actions = opportunities[:3]
    return {
        "opportunities": opportunities,
        "priority_actions": priority_actions,
        "estimated_total_value": sum(item["estimated_value"] for item in priority_actions),
    }


async def _propose_synergy_mitigations(
    optimization: dict[str, Any],
) -> list[dict[str, Any]]:
    mitigations: list[dict[str, Any]] = []
    for action in optimization.get("priority_actions", []):
        mitigations.append(
            {
                "action": action["type"],
                "risk": "Adoption resistance",
                "mitigation": "Engage stakeholders and align governance early",
            }
        )
    if not mitigations:
        mitigations.append(
            {
                "action": "baseline",
                "risk": "Limited synergy realization",
                "mitigation": "Review portfolio for additional consolidation opportunities",
            }
        )
    return mitigations
