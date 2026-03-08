from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentCatalogEntry:
    catalog_id: str
    agent_id: str
    component_name: str
    display_name: str
    source: str = "builtin"
    version: str | None = None
    description: str | None = None
    category: str | None = None
    author: dict[str, str] | None = None
    capabilities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    icon: str | None = None
    permissions_required: list[str] = field(default_factory=list)
    manifest_data: dict[str, Any] | None = None


AGENT_CATALOG: tuple[AgentCatalogEntry, ...] = (
    AgentCatalogEntry(
        catalog_id="intent-router-agent",
        agent_id="intent-router-agent",
        component_name="intent-router-agent",
        display_name="Intent Router",
    ),
    AgentCatalogEntry(
        catalog_id="response-orchestration-agent",
        agent_id="response-orchestration-agent",
        component_name="response-orchestration-agent",
        display_name="Response Orchestration",
    ),
    AgentCatalogEntry(
        catalog_id="approval-workflow-agent",
        agent_id="approval-workflow-agent",
        component_name="approval-workflow-agent",
        display_name="Approval Workflow",
    ),
    AgentCatalogEntry(
        catalog_id="demand-intake-agent",
        agent_id="demand-intake-agent",
        component_name="demand-intake-agent",
        display_name="Demand Intake",
    ),
    AgentCatalogEntry(
        catalog_id="business-case-agent",
        agent_id="business-case-agent",
        component_name="business-case-agent",
        display_name="Business Case",
    ),
    AgentCatalogEntry(
        catalog_id="portfolio-optimisation-agent",
        agent_id="portfolio-optimisation-agent",
        component_name="portfolio-optimisation-agent",
        display_name="Portfolio Optimisation",
    ),
    AgentCatalogEntry(
        catalog_id="program-management-agent",
        agent_id="program-management-agent",
        component_name="program-management-agent",
        display_name="Program Management",
    ),
    AgentCatalogEntry(
        catalog_id="scope-definition-agent",
        agent_id="scope-definition-agent",
        component_name="scope-definition-agent",
        display_name="Scope Definition",
    ),
    AgentCatalogEntry(
        catalog_id="lifecycle-governance-agent",
        agent_id="lifecycle-governance-agent",
        component_name="lifecycle-governance-agent",
        display_name="Lifecycle Governance",
    ),
    AgentCatalogEntry(
        catalog_id="schedule-planning-agent",
        agent_id="schedule-planning-agent",
        component_name="schedule-planning-agent",
        display_name="Schedule Planning",
    ),
    AgentCatalogEntry(
        catalog_id="resource-management-agent",
        agent_id="resource-management-agent",
        component_name="resource-management-agent",
        display_name="Resource Management",
    ),
    AgentCatalogEntry(
        catalog_id="financial-management-agent",
        agent_id="financial-management-agent",
        component_name="financial-management-agent",
        display_name="Financial Management",
    ),
    AgentCatalogEntry(
        catalog_id="vendor-procurement-agent",
        agent_id="vendor-procurement-agent",
        component_name="vendor-procurement-agent",
        display_name="Vendor Procurement",
    ),
    AgentCatalogEntry(
        catalog_id="quality-management-agent",
        agent_id="quality-management-agent",
        component_name="quality-management-agent",
        display_name="Quality Management",
    ),
    AgentCatalogEntry(
        catalog_id="risk-management-agent",
        agent_id="risk-management-agent",
        component_name="risk-management-agent",
        display_name="Risk Management",
    ),
    AgentCatalogEntry(
        catalog_id="compliance-governance-agent",
        agent_id="compliance-governance-agent",
        component_name="compliance-governance-agent",
        display_name="Compliance Governance",
    ),
    AgentCatalogEntry(
        catalog_id="change-control-agent",
        agent_id="change-control-agent",
        component_name="change-control-agent",
        display_name="Change Control",
    ),
    AgentCatalogEntry(
        catalog_id="release-deployment-agent",
        agent_id="release-deployment-agent",
        component_name="release-deployment-agent",
        display_name="Release Deployment",
    ),
    AgentCatalogEntry(
        catalog_id="knowledge-management-agent",
        agent_id="knowledge-management-agent",
        component_name="knowledge-management-agent",
        display_name="Knowledge Management",
    ),
    AgentCatalogEntry(
        catalog_id="continuous-improvement-agent",
        agent_id="continuous-improvement-agent",
        component_name="continuous-improvement-agent",
        display_name="Continuous Improvement",
    ),
    AgentCatalogEntry(
        catalog_id="stakeholder-communications-agent",
        agent_id="stakeholder-communications-agent",
        component_name="stakeholder-communications-agent",
        display_name="Stakeholder Communications",
    ),
    AgentCatalogEntry(
        catalog_id="analytics-insights-agent",
        agent_id="analytics-insights-agent",
        component_name="analytics-insights-agent",
        display_name="Analytics Insights",
    ),
    AgentCatalogEntry(
        catalog_id="data-synchronisation-agent",
        agent_id="data-synchronisation-agent",
        component_name="data-synchronisation-agent",
        display_name="Data Synchronisation",
    ),
    AgentCatalogEntry(
        catalog_id="workspace-setup-agent",
        agent_id="workspace-setup-agent",
        component_name="workspace-setup-agent",
        display_name="Workspace Setup",
    ),
    AgentCatalogEntry(
        catalog_id="system-health-agent",
        agent_id="system-health-agent",
        component_name="system-health-agent",
        display_name="System Health",
    ),
)

AGENT_CATALOG_BY_AGENT_ID = {entry.agent_id: entry for entry in AGENT_CATALOG}
AGENT_CATALOG_BY_COMPONENT = {entry.component_name: entry for entry in AGENT_CATALOG}

# --- Dynamic agent registry (thread-safe) ---

_dynamic_registry: dict[str, AgentCatalogEntry] = {}
_registry_lock = threading.Lock()


def get_catalog_entry(agent_id: str) -> AgentCatalogEntry | None:
    with _registry_lock:
        dynamic = _dynamic_registry.get(agent_id)
    if dynamic is not None:
        return dynamic
    return AGENT_CATALOG_BY_AGENT_ID.get(agent_id)


def get_catalog_id(agent_id: str) -> str | None:
    entry = get_catalog_entry(agent_id)
    return entry.catalog_id if entry else None


def register_agent(entry: AgentCatalogEntry) -> None:
    """Register a dynamic (marketplace) agent in the catalog.

    Raises ValueError if the agent_id conflicts with a built-in agent.
    """
    if entry.agent_id in AGENT_CATALOG_BY_AGENT_ID:
        raise ValueError(f"Cannot register '{entry.agent_id}': conflicts with a built-in agent")
    with _registry_lock:
        _dynamic_registry[entry.agent_id] = entry
    logger.info("Registered dynamic agent %s (source=%s)", entry.agent_id, entry.source)


def unregister_agent(agent_id: str) -> bool:
    """Remove a dynamically registered agent. Returns True if removed."""
    if agent_id in AGENT_CATALOG_BY_AGENT_ID:
        raise ValueError(f"Cannot unregister built-in agent '{agent_id}'")
    with _registry_lock:
        removed = _dynamic_registry.pop(agent_id, None)
    if removed:
        logger.info("Unregistered dynamic agent %s", agent_id)
    return removed is not None


def list_all_entries() -> list[AgentCatalogEntry]:
    """Return all catalog entries (built-in + dynamic)."""
    with _registry_lock:
        dynamic = list(_dynamic_registry.values())
    return list(AGENT_CATALOG) + dynamic


def list_dynamic_entries() -> list[AgentCatalogEntry]:
    """Return only dynamically registered (marketplace) entries."""
    with _registry_lock:
        return list(_dynamic_registry.values())


def get_dynamic_entry(agent_id: str) -> AgentCatalogEntry | None:
    """Look up a dynamically registered agent by ID."""
    with _registry_lock:
        return _dynamic_registry.get(agent_id)


def register_from_manifest(manifest_data: dict[str, Any]) -> AgentCatalogEntry:
    """Register an agent from a manifest dict. Returns the new entry."""
    agent_id = manifest_data["agent_id"]
    author_raw = manifest_data.get("author")
    author = author_raw if isinstance(author_raw, dict) else {"name": str(author_raw or "")}

    entry = AgentCatalogEntry(
        catalog_id=agent_id,
        agent_id=agent_id,
        component_name=agent_id,
        display_name=manifest_data.get("display_name", agent_id),
        source="marketplace",
        version=manifest_data.get("version"),
        description=manifest_data.get("description"),
        category=manifest_data.get("category"),
        author=author,
        capabilities=manifest_data.get("capabilities", []),
        tags=manifest_data.get("tags", []),
        icon=manifest_data.get("icon"),
        permissions_required=manifest_data.get("permissions_required", []),
        manifest_data=manifest_data,
    )
    register_agent(entry)
    return entry
