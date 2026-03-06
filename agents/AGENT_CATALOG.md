# Agent Catalogue

This catalogue is generated from the agent README files under
`agents/**/*-agent/README.md`. Update the README content and rerun the
generator to refresh this file and the web UI metadata.

## Core Orchestration

### Approval Workflow Agent Specification (`approval-workflow-agent`)
- **Location:** `agents/core-orchestration/approval-workflow-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Approval Workflow Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.
  - The Approval Workflow agent is the platform's canonical orchestration authority for long-running, multi-step workflows — including human approval chains, automated task sequences, event-driven process automation, and governed business processes. It defines, executes, monitors, and audits every structured process in the platform through a single unified engine.
  - Approvals are represented as a workflow pattern (`approval_gate` step type) within the workflow specification. This means every approval chain — sequential or parallel — is defined and executed as a first-class workflow, sharing the same execution engine, state persistence, audit trail, and monitoring infrastructure as any other automated process.

### Intent Router Agent Specification (`intent-router-agent`)
- **Location:** `agents/core-orchestration/intent-router-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Intent Router Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Response Orchestration Agent Specification (`response-orchestration-agent`)
- **Location:** `agents/core-orchestration/response-orchestration-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Response Orchestration Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Workspace Setup Agent Specification (`workspace-setup-agent`)
- **Location:** `agents/core-orchestration/workspace-setup-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Workspace Setup Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.
  - The Workspace Setup agent manages the initialisation and configuration of project workspaces before any data is written to systems of record. It acts as a governed "setup wizard" phase that ensures connectors are enabled, authentication is complete, field mappings are set, and all required external artefacts and containers exist (Teams channels, SharePoint sites, Jira projects, Planview shells, etc.) before downstream delivery begins.
  - No write to a system of record is permitted until workspace setup is complete. This agent enforces that gate.


## Delivery Management

### Compliance Governance Agent Specification (`compliance-governance-agent`)
- **Location:** `agents/delivery-management/compliance-governance-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Compliance Governance Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Financial Management Agent Specification (`financial-management-agent`)
- **Location:** `agents/delivery-management/financial-management-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Financial Management Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Lifecycle Governance Agent Specification (`lifecycle-governance-agent`)
- **Location:** `agents/delivery-management/lifecycle-governance-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Lifecycle Governance Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Quality Management Agent Specification (`quality-management-agent`)
- **Location:** `agents/delivery-management/quality-management-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Quality Management Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Resource Management Agent Specification (`resource-management-agent`)
- **Location:** `agents/delivery-management/resource-management-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Resource Management Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Risk Management Agent Specification (`risk-management-agent`)
- **Location:** `agents/delivery-management/risk-management-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Risk Management Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Schedule Planning Agent Specification (`schedule-planning-agent`)
- **Location:** `agents/delivery-management/schedule-planning-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Schedule Planning Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Scope Definition Agent Specification (`scope-definition-agent`)
- **Location:** `agents/delivery-management/scope-definition-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Scope Definition Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Vendor Procurement Agent Specification (`vendor-procurement-agent`)
- **Location:** `agents/delivery-management/vendor-procurement-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Vendor Procurement Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.


## Operations Management

### Analytics Insights Agent Specification (`analytics-insights-agent`)
- **Location:** `agents/operations-management/analytics-insights-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Analytics Insights Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Change Control Agent Specification (`change-control-agent`)
- **Location:** `agents/operations-management/change-control-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Change Control Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Continuous Improvement Agent Specification (`continuous-improvement-agent`)
- **Location:** `agents/operations-management/continuous-improvement-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Continuous Improvement Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Data Synchronisation Agent Specification (`data-synchronisation-agent`)
- **Location:** `agents/operations-management/data-synchronisation-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Data Synchronisation Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Knowledge Management Agent Specification (`knowledge-management-agent`)
- **Location:** `agents/operations-management/knowledge-management-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Knowledge Management Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Release Deployment Agent Specification (`release-deployment-agent`)
- **Location:** `agents/operations-management/release-deployment-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Release Deployment Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Stakeholder Communications Agent Specification (`stakeholder-communications-agent`)
- **Location:** `agents/operations-management/stakeholder-communications-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Stakeholder Communications Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### System Health Agent Specification (`system-health-agent`)
- **Location:** `agents/operations-management/system-health-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the System Health Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.


## Portfolio Management

### Business Case Agent Specification (`business-case-agent`)
- **Location:** `agents/portfolio-management/business-case-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Business Case Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Demand Intake Agent Specification (`demand-intake-agent`)
- **Location:** `agents/portfolio-management/demand-intake-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Demand Intake Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Portfolio Optimisation Agent Specification (`portfolio-optimisation-agent`)
- **Location:** `agents/portfolio-management/portfolio-optimisation-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Portfolio Optimisation Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.

### Program Management Agent Specification (`program-management-agent`)
- **Location:** `agents/portfolio-management/program-management-agent`
- **Purpose:**
  - Define the responsibilities, workflows, and integration points for the Program Management Agent. This README captures how the agent is expected to behave in the multi-agent orchestration flow.
