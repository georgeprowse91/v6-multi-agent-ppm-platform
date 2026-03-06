"""Action handlers: monitor_regulatory_changes, monitor_regulations"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import requests
from compliance_utils import (
    extract_sources,
    identify_control_gaps,
    normalize_regulatory_update,
    parse_rss_updates,
)
from llm.client import LLMGateway, LLMProviderError

import importlib

from agents.common.web_search import build_search_query

if TYPE_CHECKING:
    from compliance_regulatory_agent import ComplianceRegulatoryAgent


async def handle_monitor_regulatory_changes(
    agent: ComplianceRegulatoryAgent,
    *,
    domain: str | None,
    region: str | None,
    tenant_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """
    Monitor regulatory changes and updates.

    Returns change notifications and impacts.
    """
    agent.logger.info("Monitoring regulatory changes")

    # Check for regulatory updates
    changes = await _check_regulatory_feeds(agent)

    # Assess impact on existing regulations and controls
    impacted_regulations = []
    for change in changes:
        impact_assessment = await _assess_regulatory_change_impact(agent, change)
        if impact_assessment.get("projects_affected"):
            impacted_regulations.append(
                {
                    "regulation": change.get("regulation"),
                    "change_description": change.get("description"),
                    "effective_date": change.get("effective_date"),
                    "impact_assessment": impact_assessment,
                }
            )

    external_monitoring: dict[str, Any] | None = None
    if agent.enable_regulatory_monitoring and domain:
        try:
            external_monitoring = await handle_monitor_regulations(agent, domain, region)
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
                "External regulatory monitoring failed",
                extra={"error": str(exc), "correlation_id": correlation_id},
            )
            external_monitoring = {
                "summary": "",
                "updates": [],
                "gaps": [],
                "sources": [],
                "used_external_research": False,
            }

    external_updates = external_monitoring.get("updates", []) if external_monitoring else []
    all_updates = [
        *changes,
        *external_updates,
    ]

    if all_updates:
        await _sync_regulatory_updates(agent, all_updates)

    new_obligations = [
        update
        for update in all_updates
        if update.get("description") or update.get("obligation")
    ]
    tasks_created = await agent._create_stakeholder_tasks(new_obligations, tenant_id)

    if new_obligations:
        await agent._publish_event(
            "compliance.regulation.change_detected",
            {
                "changes": new_obligations,
                "impacted_regulations": impacted_regulations,
                "tenant_id": tenant_id,
                "correlation_id": correlation_id,
            },
        )
        await agent._notify_stakeholders(
            subject="Regulatory updates detected",
            message=f"{len(new_obligations)} regulatory updates require review.",
        )

    return {
        "changes_detected": len(changes),
        "regulations_impacted": len(impacted_regulations),
        "impacted_regulations": impacted_regulations,
        "external_monitoring": external_monitoring,
        "tasks_created": tasks_created,
        "last_check": datetime.now(timezone.utc).isoformat(),
    }


async def handle_monitor_regulations(
    agent: ComplianceRegulatoryAgent,
    domain: str,
    region: str | None,
    *,
    llm_client: LLMGateway | None = None,
    result_limit: int | None = None,
) -> dict[str, Any]:
    """Monitor external sources for new or changing regulations."""
    if not agent.enable_regulatory_monitoring:
        return {
            "summary": "",
            "updates": [],
            "gaps": [],
            "sources": [],
            "used_external_research": False,
        }

    context = f"{domain} {region or ''}".strip()
    query = build_search_query(
        context,
        "compliance",
        extra_keywords=agent.regulatory_search_keywords,
    )

    # NOTE: Only high-level context should be sent to external search providers.
    snippets = await search_web(
        query, result_limit=result_limit or agent.regulatory_search_result_limit
    )
    if not snippets:
        return {
            "summary": "",
            "updates": [],
            "gaps": [],
            "sources": [],
            "used_external_research": False,
        }

    summary = await summarize_snippets(snippets, llm_client=llm_client, purpose="compliance")
    updates = await _extract_regulatory_updates(agent, summary, snippets, llm_client=llm_client)
    gaps = identify_control_gaps(updates, agent.regulation_library)
    sources = extract_sources(snippets)

    return {
        "summary": summary,
        "updates": updates,
        "gaps": gaps,
        "sources": sources,
        "used_external_research": True,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _check_regulatory_feeds(agent: ComplianceRegulatoryAgent) -> list[dict[str, Any]]:
    """Check regulatory feeds for updates."""
    feeds = agent.config.get("regulatory_feeds", []) if agent.config else []
    if not feeds:
        return []

    updates: list[dict[str, Any]] = []
    for feed in feeds:
        feed_config = feed if isinstance(feed, dict) else {"url": str(feed)}
        url = feed_config.get("url")
        if not url:
            continue
        headers = feed_config.get("headers", {})
        api_key = feed_config.get("api_key") or os.getenv(feed_config.get("api_key_env", ""))
        if api_key:
            headers = {**headers, "Authorization": f"Bearer {api_key}"}
        params = feed_config.get("params", {})
        timeout = float(feed_config.get("timeout", 10))

        try:
            response = await asyncio.to_thread(
                requests.get,
                url,
                headers=headers,
                params=params,
                timeout=timeout,
            )
            response.raise_for_status()
            if feed_config.get("type") == "rss" or url.endswith((".rss", ".xml")):
                payload = response.text
            else:
                payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            agent.logger.warning("Regulatory feed fetch failed", extra={"error": str(exc)})
            continue

        if isinstance(payload, str):
            updates.extend(parse_rss_updates(payload, feed_config))
        else:
            feed_updates = payload
            if isinstance(payload, dict):
                feed_updates = payload.get("updates") or payload.get("items") or []
            if isinstance(feed_updates, list):
                for entry in feed_updates:
                    normalized = normalize_regulatory_update(entry, feed_config)
                    if normalized:
                        updates.append(normalized)

    return updates


async def _assess_regulatory_change_impact(
    agent: ComplianceRegulatoryAgent, change: dict[str, Any]
) -> dict[str, Any]:
    """Assess impact of regulatory change."""
    affected_projects = []
    affected_controls = []
    regulation_key = str(change.get("regulation") or change.get("id") or "").lower()
    for project_id, mapping in agent.compliance_mappings.items():
        scope = [str(item).lower() for item in mapping.get("regulations", [])]
        if regulation_key and regulation_key in scope:
            affected_projects.append(project_id)
            affected_controls.extend(mapping.get("applicable_controls", []))
    effort = "low"
    if affected_controls:
        effort = "high" if len(affected_controls) > 5 else "medium"
    return {
        "projects_affected": affected_projects,
        "controls_affected": list(dict.fromkeys(affected_controls)),
        "estimated_effort": effort,
    }


async def _sync_regulatory_updates(
    agent: ComplianceRegulatoryAgent, updates: list[dict[str, Any]]
) -> None:
    for update in updates:
        regulation_name = update.get("regulation")
        if not regulation_name:
            continue
        regulation_id = None
        for existing_id, regulation in agent.regulation_library.items():
            if regulation.get("name") == regulation_name:
                regulation_id = existing_id
                break
        if not regulation_id:
            regulation_id = f"REG-{uuid.uuid4().hex[:6].upper()}"
            regulation_record = {
                "regulation_id": regulation_id,
                "name": regulation_name,
                "description": update.get("description", ""),
                "jurisdiction": [update.get("region")] if update.get("region") else [],
                "industry": [],
                "effective_date": update.get("effective_date"),
                "obligations": [],
                "related_controls": [],
                "applicability_rules": {
                    "applies_to_all": False,
                    "jurisdiction_filter": (
                        [update.get("region")] if update.get("region") else []
                    ),
                    "industry_filter": [],
                },
                "metadata": {"source_url": update.get("source_url")},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            agent.regulation_library[regulation_id] = regulation_record
            await agent.db_service.store("regulations", regulation_id, regulation_record)


async def _extract_regulatory_updates(
    agent: ComplianceRegulatoryAgent,
    summary: str,
    snippets: list[str],
    *,
    llm_client: LLMGateway | None = None,
) -> list[dict[str, Any]]:
    sources = extract_sources(snippets)
    system_prompt = (
        "You are a compliance analyst. Extract new or changing regulations from the "
        "summary and snippets. Return ONLY JSON as an array of objects with fields: "
        "regulation, description, effective_date, region, source_url."
    )
    user_prompt = json.dumps(
        {"summary": summary, "snippets": snippets, "sources": sources},
        indent=2,
    )

    llm = llm_client or LLMGateway()
    try:
        response = await llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        data = json.loads(response.content)
    except (LLMProviderError, ValueError, json.JSONDecodeError) as exc:
        agent.logger.warning("Regulatory extraction failed", extra={"error": str(exc)})
        return []

    updates: list[dict[str, Any]] = []
    if not isinstance(data, list):
        return updates
    for entry in data:
        if not isinstance(entry, dict):
            continue
        regulation = str(entry.get("regulation", "")).strip()
        description = str(entry.get("description", "")).strip()
        if not regulation or not description:
            continue
        updates.append(
            {
                "regulation": regulation,
                "description": description,
                "effective_date": str(entry.get("effective_date", "")).strip(),
                "region": str(entry.get("region", "")).strip(),
                "source_url": str(entry.get("source_url", "")).strip(),
            }
        )
    return updates
