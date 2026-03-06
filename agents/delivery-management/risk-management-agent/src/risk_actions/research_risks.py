"""Action handler for external risk research."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from llm.client import LLMGateway, LLMProviderError
from risk_utils import (
    coerce_rating,
    extract_sources,
    fallback_risk_classification,
    normalize_risk_category,
    risk_signature,
)

from agents.common.web_search import build_search_query

if TYPE_CHECKING:
    from risk_management_agent import RiskManagementAgent


async def research_risks_public(
    agent: RiskManagementAgent,
    domain: str,
    region: str | None,
    categories: list[str] | None,
    *,
    llm_client: LLMGateway | None = None,
    result_limit: int | None = None,
) -> list[dict[str, Any]]:
    """Research emerging risks using external sources."""
    if not agent.enable_external_risk_research:
        return []

    context_parts = [domain, region or "", ", ".join(categories or [])]
    context = " ".join(part for part in context_parts if part)
    query = build_search_query(
        context,
        "risk",
        extra_keywords=agent.risk_search_keywords,
    )

    # NOTE: Only high-level, non-sensitive context should be sent to the search API.
    import risk_management_agent as _agent_module

    snippets = await _agent_module.search_web(
        query, result_limit=result_limit or agent.risk_search_result_limit
    )
    if not snippets:
        return []

    summary = await _agent_module.summarize_snippets(snippets, llm_client=llm_client, purpose="risk")
    return await agent._classify_external_risks(
        summary,
        snippets,
        categories,
        llm_client=llm_client,
    )


async def research_risks_action(
    agent: RiskManagementAgent,
    *,
    project_id: str | None,
    domain: str,
    region: str | None,
    categories: list[str] | None,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Fetch and merge externally researched risks into the risk register."""
    if not agent.enable_external_risk_research:
        return {
            "project_id": project_id,
            "external_risks": [],
            "added_risks": [],
            "used_external_research": False,
            "notice": "External risk research is disabled.",
            "correlation_id": correlation_id,
        }

    try:
        external_risks = await research_risks_public(agent, domain, region, categories)
    except (
        ConnectionError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        OSError,
    ) as exc:
        agent.logger.warning(
            "Risk research failed",
            extra={
                "error": str(exc),
                "project_id": project_id,
                "correlation_id": correlation_id,
            },
        )
        return {
            "project_id": project_id,
            "external_risks": [],
            "added_risks": [],
            "used_external_research": False,
            "notice": "External risk research failed; internal risk processes continue.",
            "correlation_id": correlation_id,
        }

    added = await _merge_external_risks(
        agent,
        external_risks,
        project_id=project_id,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )

    return {
        "project_id": project_id,
        "external_risks": external_risks,
        "added_risks": added,
        "used_external_research": bool(external_risks),
        "notice": None,
        "correlation_id": correlation_id,
    }


async def _classify_external_risks(
    agent: RiskManagementAgent,
    summary: str,
    snippets: list[str],
    categories: list[str] | None,
    *,
    llm_client: LLMGateway | None = None,
) -> list[dict[str, Any]]:
    allowed_categories = ["technical", "schedule", "cost", "compliance"]
    category_context = categories or allowed_categories
    sources = extract_sources(snippets)

    system_prompt = (
        "You are a PMO risk analyst. Use the external summary and snippets to identify "
        "emerging risks. Return ONLY valid JSON as an array of objects with fields: "
        "title, description, category (technical, schedule, cost, compliance), "
        "probability (1-5), impact (1-5), sources (array of {url, citation})."
    )
    user_prompt = json.dumps(
        {
            "summary": summary,
            "snippets": snippets,
            "preferred_categories": category_context,
            "sources": sources,
        },
        indent=2,
    )

    llm = llm_client or LLMGateway()
    try:
        response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        data = json.loads(response.content)
    except (LLMProviderError, ValueError, json.JSONDecodeError) as exc:
        agent.logger.warning("Risk classification failed", extra={"error": str(exc)})
        return fallback_risk_classification(summary, sources)

    risks: list[dict[str, Any]] = []
    if not isinstance(data, list):
        return fallback_risk_classification(summary, sources)

    for entry in data:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "")).strip()
        description = str(entry.get("description", "")).strip()
        if not title or not description:
            continue
        category = normalize_risk_category(entry.get("category"), allowed_categories)
        probability = coerce_rating(entry.get("probability"), fallback=3)
        impact = coerce_rating(entry.get("impact"), fallback=3)
        entry_sources = entry.get("sources")
        if not isinstance(entry_sources, list) or not entry_sources:
            entry_sources = sources
        risks.append(
            {
                "title": title,
                "description": description,
                "category": category,
                "probability": probability,
                "impact": impact,
                "sources": entry_sources,
            }
        )

    return risks or fallback_risk_classification(summary, sources)


async def _merge_external_risks(
    agent: RiskManagementAgent,
    external_risks: list[dict[str, Any]],
    *,
    project_id: str | None,
    tenant_id: str,
    correlation_id: str,
) -> list[dict[str, Any]]:
    from risk_actions.identify_risk import identify_risk

    if not project_id or not external_risks:
        return []

    existing_signatures = {
        risk_signature(risk_item)
        for risk_item in agent.risk_register.values()
        if risk_item.get("project_id") == project_id
    }
    added: list[dict[str, Any]] = []
    for risk in external_risks:
        sig = risk_signature(risk)
        if sig in existing_signatures:
            continue
        risk_data = {
            "project_id": project_id,
            "title": risk.get("title"),
            "description": risk.get("description"),
            "category": risk.get("category", "external"),
            "probability": risk.get("probability", 3),
            "impact": risk.get("impact", 3),
            # "external" is not a valid schema value; external research risks
            # default to "internal" classification (org-visible but not public).
            "classification": risk.get("classification", "internal"),
            "owner": risk.get("owner", "risk-management-system"),
            "created_by": "external_research",
            "sources": risk.get("sources", []),
        }
        try:
            created = await identify_risk(
                agent, risk_data, tenant_id=tenant_id, correlation_id=correlation_id
            )
            added.append(created)
            existing_signatures.add(sig)
        except (
            ConnectionError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
            OSError,
        ) as exc:
            agent.logger.warning(
                "Failed to merge external risk",
                extra={"error": str(exc), "project_id": project_id},
            )
    return added
