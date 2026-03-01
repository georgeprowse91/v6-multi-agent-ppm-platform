from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentCatalogEntry:
    catalog_id: str
    agent_id: str
    component_name: str
    display_name: str


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
        display_name="Business Case & Investment",
    ),
    AgentCatalogEntry(
        catalog_id="portfolio-optimisation-agent",
        agent_id="portfolio-optimisation-agent",
        component_name="portfolio-optimisation-agent",
        display_name="Portfolio Strategy & Optimization",
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
        display_name="Project Definition & Scope",
    ),
    AgentCatalogEntry(
        catalog_id="lifecycle-governance-agent",
        agent_id="lifecycle-governance-agent",
        component_name="lifecycle-governance-agent",
        display_name="Project Lifecycle & Governance",
    ),
    AgentCatalogEntry(
        catalog_id="schedule-planning-agent",
        agent_id="schedule-planning-agent",
        component_name="schedule-planning-agent",
        display_name="Schedule & Planning",
    ),
    AgentCatalogEntry(
        catalog_id="resource-management-agent",
        agent_id="resource-management-agent",
        component_name="resource-management-agent",
        display_name="Resource & Capacity",
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
        display_name="Vendor & Procurement",
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
        display_name="Risk & Issue Management",
    ),
    AgentCatalogEntry(
        catalog_id="compliance-governance-agent",
        agent_id="compliance-governance-agent",
        component_name="compliance-governance-agent",
        display_name="Compliance & Regulatory",
    ),
    AgentCatalogEntry(
        catalog_id="change-control-agent",
        agent_id="change-control-agent",
        component_name="change-control-agent",
        display_name="Change & Configuration",
    ),
    AgentCatalogEntry(
        catalog_id="release-deployment-agent",
        agent_id="release-deployment-agent",
        component_name="release-deployment-agent",
        display_name="Release & Deployment",
    ),
    AgentCatalogEntry(
        catalog_id="knowledge-management-agent",
        agent_id="knowledge-management-agent",
        component_name="knowledge-management-agent",
        display_name="Knowledge & Document Management",
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
        display_name="Stakeholder & Communications",
    ),
    AgentCatalogEntry(
        catalog_id="analytics-insights-agent",
        agent_id="analytics-insights-agent",
        component_name="analytics-insights-agent",
        display_name="Analytics & Insights",
    ),
    AgentCatalogEntry(
        catalog_id="data-synchronisation-agent",
        agent_id="data-synchronisation-agent",
        component_name="data-synchronisation-agent",
        display_name="Data Synchronization & Quality",
    ),
    AgentCatalogEntry(
        catalog_id="workflow-engine-agent",
        agent_id="workflow-engine-agent",
        component_name="workflow-engine-agent",
        display_name="Workflow & Process Engine",
    ),
    AgentCatalogEntry(
        catalog_id="system-health-agent",
        agent_id="system-health-agent",
        component_name="system-health-agent",
        display_name="System Health & Monitoring",
    ),
)

AGENT_CATALOG_BY_AGENT_ID = {entry.agent_id: entry for entry in AGENT_CATALOG}
AGENT_CATALOG_BY_COMPONENT = {entry.component_name: entry for entry in AGENT_CATALOG}


def get_catalog_entry(agent_id: str) -> AgentCatalogEntry | None:
    return AGENT_CATALOG_BY_AGENT_ID.get(agent_id)


def get_catalog_id(agent_id: str) -> str | None:
    entry = get_catalog_entry(agent_id)
    return entry.catalog_id if entry else None
