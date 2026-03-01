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
        catalog_id="agent-01-intent-router",
        agent_id="intent-router-agent",
        component_name="agent-01-intent-router",
        display_name="Intent Router",
    ),
    AgentCatalogEntry(
        catalog_id="agent-02-response-orchestration",
        agent_id="response-orchestration-agent",
        component_name="agent-02-response-orchestration",
        display_name="Response Orchestration",
    ),
    AgentCatalogEntry(
        catalog_id="agent-03-approval-workflow",
        agent_id="approval-workflow-agent",
        component_name="agent-03-approval-workflow",
        display_name="Approval Workflow",
    ),
    AgentCatalogEntry(
        catalog_id="agent-04-demand-intake",
        agent_id="demand-intake-agent",
        component_name="agent-04-demand-intake",
        display_name="Demand Intake",
    ),
    AgentCatalogEntry(
        catalog_id="agent-05-business-case-investment",
        agent_id="business-case-agent",
        component_name="agent-05-business-case-investment",
        display_name="Business Case & Investment",
    ),
    AgentCatalogEntry(
        catalog_id="agent-06-portfolio-strategy-optimisation",
        agent_id="portfolio-optimisation-agent",
        component_name="agent-06-portfolio-strategy-optimisation",
        display_name="Portfolio Strategy & Optimization",
    ),
    AgentCatalogEntry(
        catalog_id="agent-07-program-management",
        agent_id="program-management-agent",
        component_name="agent-07-program-management",
        display_name="Program Management",
    ),
    AgentCatalogEntry(
        catalog_id="agent-08-project-definition-scope",
        agent_id="scope-definition-agent",
        component_name="agent-08-project-definition-scope",
        display_name="Project Definition & Scope",
    ),
    AgentCatalogEntry(
        catalog_id="agent-09-lifecycle-governance",
        agent_id="lifecycle-governance-agent",
        component_name="agent-09-lifecycle-governance",
        display_name="Project Lifecycle & Governance",
    ),
    AgentCatalogEntry(
        catalog_id="agent-10-schedule-planning",
        agent_id="schedule-planning-agent",
        component_name="agent-10-schedule-planning",
        display_name="Schedule & Planning",
    ),
    AgentCatalogEntry(
        catalog_id="agent-11-resource-capacity",
        agent_id="resource-management-agent",
        component_name="agent-11-resource-capacity",
        display_name="Resource & Capacity",
    ),
    AgentCatalogEntry(
        catalog_id="agent-12-financial-management",
        agent_id="financial-management-agent",
        component_name="agent-12-financial-management",
        display_name="Financial Management",
    ),
    AgentCatalogEntry(
        catalog_id="agent-13-vendor-procurement",
        agent_id="vendor-procurement-agent",
        component_name="agent-13-vendor-procurement",
        display_name="Vendor & Procurement",
    ),
    AgentCatalogEntry(
        catalog_id="agent-14-quality-management",
        agent_id="quality-management-agent",
        component_name="agent-14-quality-management",
        display_name="Quality Management",
    ),
    AgentCatalogEntry(
        catalog_id="agent-15-risk-issue-management",
        agent_id="risk-management-agent",
        component_name="agent-15-risk-issue-management",
        display_name="Risk & Issue Management",
    ),
    AgentCatalogEntry(
        catalog_id="agent-16-compliance-regulatory",
        agent_id="compliance-governance-agent",
        component_name="agent-16-compliance-regulatory",
        display_name="Compliance & Regulatory",
    ),
    AgentCatalogEntry(
        catalog_id="agent-17-change-configuration",
        agent_id="change-control-agent",
        component_name="agent-17-change-configuration",
        display_name="Change & Configuration",
    ),
    AgentCatalogEntry(
        catalog_id="agent-18-release-deployment",
        agent_id="release-deployment-agent",
        component_name="agent-18-release-deployment",
        display_name="Release & Deployment",
    ),
    AgentCatalogEntry(
        catalog_id="agent-19-knowledge-document-management",
        agent_id="knowledge-management-agent",
        component_name="agent-19-knowledge-document-management",
        display_name="Knowledge & Document Management",
    ),
    AgentCatalogEntry(
        catalog_id="agent-20-continuous-improvement-process-mining",
        agent_id="continuous-improvement-agent",
        component_name="agent-20-continuous-improvement-process-mining",
        display_name="Continuous Improvement",
    ),
    AgentCatalogEntry(
        catalog_id="agent-21-stakeholder-comms",
        agent_id="stakeholder-communications-agent",
        component_name="agent-21-stakeholder-comms",
        display_name="Stakeholder & Communications",
    ),
    AgentCatalogEntry(
        catalog_id="agent-22-analytics-insights",
        agent_id="analytics-insights-agent",
        component_name="agent-22-analytics-insights",
        display_name="Analytics & Insights",
    ),
    AgentCatalogEntry(
        catalog_id="agent-23-data-synchronisation-quality",
        agent_id="data-synchronisation-agent",
        component_name="agent-23-data-synchronisation-quality",
        display_name="Data Synchronization & Quality",
    ),
    AgentCatalogEntry(
        catalog_id="agent-24-workflow-process-engine",
        agent_id="workflow-engine-agent",
        component_name="agent-24-workflow-process-engine",
        display_name="Workflow & Process Engine",
    ),
    AgentCatalogEntry(
        catalog_id="agent-25-system-health-monitoring",
        agent_id="system-health-agent",
        component_name="agent-25-system-health-monitoring",
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
