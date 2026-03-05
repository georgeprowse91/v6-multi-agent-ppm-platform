# Agent Specifications

> This hub is the canonical reference for all 25 specialised AI agents in the Multi-Agent PPM Platform. It describes each agent's purpose, capabilities, interfaces, and connections to other agents. Agents are organized into four domains: Core Orchestration, Portfolio Management, Delivery Management, and Operations Management.

## Contents

- [Where to Find Agent Files](#where-to-find-agent-files)
- [Agent Quick Reference (25 agents)](#agent-quick-reference-25-agents)
- [Agent Configuration Reference](#agent-configuration-reference)
- [Architecture and Design Notes](#architecture-and-design-notes)
- [Integration Service Taxonomy](#integration-service-taxonomy)
- [Core Orchestration Agents](#core-orchestration-agents)
  - [Intent Router](#intent-router-agent-01)
  - [Response Orchestration](#response-orchestration-agent-02)
  - [Approval Workflow](#approval-workflow-agent-03)
  - [Workspace Setup](#workspace-setup-agent-24)
- [Portfolio Management Agents](#portfolio-management-agents)
  - [Demand Intake](#demand-intake-agent-04)
  - [Business Case and Investment Analysis](#business-case-and-investment-analysis-agent-05)
  - [Portfolio Strategy and Optimisation](#portfolio-strategy-and-optimisation-agent-06)
  - [Programme Management](#programme-management-agent-07)
- [Delivery Management Agents](#delivery-management-agents)
  - [Project Definition and Scope](#project-definition-and-scope-agent-08)
  - [Project Lifecycle and Governance](#project-lifecycle-and-governance-agent-09)
  - [Schedule and Planning](#schedule-and-planning-agent-10)
  - [Resource and Capacity Management](#resource-and-capacity-management-agent-11)
  - [Financial Management](#financial-management-agent-12)
  - [Vendor and Procurement Management](#vendor-and-procurement-management-agent-13)
  - [Quality Management](#quality-management-agent-14)
  - [Risk and Issue Management](#risk-and-issue-management-agent-15)
  - [Compliance and Regulatory](#compliance-and-regulatory-agent-16)
- [Operations Management Agents](#operations-management-agents)
  - [Change and Configuration Management](#change-and-configuration-management-agent-17)
  - [Release and Deployment](#release-and-deployment-agent-18)
  - [Knowledge and Document Management](#knowledge-and-document-management-agent-19)
  - [Continuous Improvement and Process Mining](#continuous-improvement-and-process-mining-agent-20)
  - [Stakeholder Communications](#stakeholder-communications-agent-21)
  - [Analytics and Insights](#analytics-and-insights-agent-22)
  - [Data Synchronisation and Quality](#data-synchronisation-and-quality-agent-23)
  - [System Health and Monitoring](#system-health-and-monitoring-agent-25)
- [Tooling](#tooling)

---

## Where to Find Agent Files

| What you need | Where to find it |
| --- | --- |
| Detailed agent specs (inputs, outputs, behaviour) | [agent-specifications.md](./agent-specifications.md) |
| Architecture — how agents orchestrate | [docs/architecture/agent-orchestration.md](../architecture/agent-orchestration.md) |
| Architecture — runtime lifecycle and state | [docs/architecture/agent-runtime.md](../architecture/agent-runtime.md) |
| Code-adjacent catalog with links to each agent's README | [agents/AGENT_CATALOG.md](../../agents/AGENT_CATALOG.md) |
| All agent configuration files | [ops/config/agents/](../../ops/config/agents/) |
| Agent source code | `agents/{category}/agent-{NN}-{name}/src/` |

---

## Agent Quick Reference (25 agents)

| # | Agent Name | Category | Role | Key Output |
|---|---|---|---|---|
| 01 | Intent Router | Core Orchestration | Platform Dispatcher | Routing plan to Response Orchestration |
| 02 | Response Orchestration | Core Orchestration | Execution Coordinator | Assembled multi-agent response to user |
| 03 | Approval Workflow | Core Orchestration | Workflow Orchestration and Governance | Workflow execution records, approval decisions, and audit events |
| 04 | Demand and Intake | Portfolio Management | Project Request Handler | Classified, triaged demand records |
| 05 | Business Case and Investment Analysis | Portfolio Management | Financial Justification and Investment Advisor | Business case documents and investment recommendations |
| 06 | Portfolio Strategy and Optimisation | Portfolio Management | Investment Prioritisation and Portfolio Advisor | Ranked portfolio and scenario models |
| 07 | Programme Management | Portfolio Management | Programme Coordinator and Benefits Tracker | Programme structures, dependency maps, benefits reports |
| 08 | Project Definition and Scope | Delivery Management | Project Charter and Scope Baseline Manager | Project charters, WBS, scope baselines |
| 09 | Project Lifecycle and Governance | Delivery Management | Stage-Gate Enforcer and Project Health Monitor | Stage-gate assessments, health scores, transition approvals |
| 10 | Schedule and Planning | Delivery Management | Schedule Builder and Milestone Manager | Baselined schedules, critical path analysis |
| 11 | Resource and Capacity Management | Delivery Management | Resource Allocator and Capacity Planner | Resource allocations, capacity forecasts |
| 12 | Financial Management | Delivery Management | Budget Tracker and Financial Controller | Budget reports, cost forecasts, variance analysis |
| 13 | Vendor and Procurement Management | Delivery Management | Vendor Lifecycle and Procurement Coordinator | RFPs, contracts, vendor performance records |
| 14 | Quality Management | Delivery Management | Quality Planner and Test Coordinator | Quality plans, defect records, gate assessment results |
| 15 | Risk and Issue Management | Delivery Management | Risk Identifier, Assessor, and Issue Tracker | Risk registers, issue logs, quantified exposure reports |
| 16 | Compliance and Regulatory | Delivery Management | Regulatory Framework Manager and Compliance Monitor | Compliance control records, evidence packages, audit reports |
| 17 | Change and Configuration Management | Operations Management | Change Controller and Configuration Authority | Change records, impact assessments, configuration baselines |
| 18 | Release and Deployment | Operations Management | Release Coordinator and Deployment Orchestrator | Release plans, deployment records, rollback procedures |
| 19 | Knowledge and Document Management | Operations Management | Document Librarian and Knowledge Curator | Indexed document repository, lessons-learned records |
| 20 | Continuous Improvement and Process Mining | Operations Management | Process Analyst and Improvement Engine | Process deviation reports, improvement recommendations |
| 21 | Stakeholder Communications | Operations Management | Communications Planner and Engagement Manager | Communication plans, stakeholder engagement records |
| 22 | Analytics and Insights | Operations Management | Portfolio Intelligence and Reporting Engine | Dashboards, reports, predictive forecasts |
| 23 | Data Synchronisation and Quality | Operations Management | Data Integrity Guardian and Sync Coordinator | Sync status reports, data quality dashboards |
| 24 | Workspace Setup | Core Orchestration | Project Workspace Initialiser | Configured workspaces, provisioned assets, setup status reports |
| 25 | System Health and Monitoring | Operations Management | Platform Reliability Guardian | Health status reports, alerts, SLO compliance reports |

---

## Agent Configuration Reference

All agent runtime configuration lives under `ops/config/agents/`. The table below covers the key files:

| File | Purpose | Key fields |
| --- | --- | --- |
| `ops/config/agents/intent-routing.yaml` | Intent definitions and routing targets (canonical design reference). | `intents[].name`, `intents[].routes[].agent_id`, `intents[].routes[].action` |
| `ops/config/agents/orchestration.yaml` | Intent routing + response orchestration settings. | `intent_router.model.*`, `intent_router.intents`, `response_orchestration.max_concurrency`, `response_orchestration.retry_policy.*` |
| `ops/config/agents/portfolio.yaml` | Domain agent configuration for demand, business case, portfolio strategy, and program management. | `demand_intake.*`, `business_case.*`, `portfolio_strategy.*`, `program_management.*` |
| `ops/config/agents/demo-participants.yaml` | Demo participant configuration for local and demo environments. | `participants[].name`, `participants[].role` |
| `ops/config/agents/data-synchronisation-agent/` | Per-agent config for the Data Synchronisation agent: mapping rules, quality thresholds, pipelines, schema registry, validation rules. | — |
| `ops/config/agents/approval-workflow-agent/` | Approval Workflow agent workflow configuration (durable workflow definitions and templates). | — |

> **Note on runtime config:** `services/agent-runtime/src/config/intent-routing.yaml` is a separate runtime-only copy that uses descriptive agent IDs (e.g. `risk-management-agent`) matching the IDs registered in `services/agent-runtime/src/runtime.py`. See the comment at the top of that file for details.

---

## Architecture and Design Notes

### The Approval Workflow agent as unified orchestration authority

Approvals are a specialised workflow pattern — a human decision step with routing, deadlines, escalation, and an immutable outcome record. The Approval Workflow agent is the platform's single canonical orchestration authority for long-running workflows. Every multi-step process — including approvals, automated task sequences, retry/compensation flows, and event-driven process automation — is defined and executed through one agent with a unified execution record and audit trail. Approval steps are represented as a first-class workflow step type (`approval_gate`) within the `ppm.workflow/v1` specification.

**Operational benefits:**
- One workflow definition language and one execution engine for all structured processes.
- One task inbox for human tasks and approvals, reducing context switching.
- One monitoring view for all workflow and approval activity.
- One audit trail covering the full lifecycle of every process.
- Simplified governance: every process follows the same versioning, retry, and compensation policies.

### The Workspace Setup agent

Before any delivery agent can write to a system of record (Jira, Planview, SAP, SharePoint, Teams), a project workspace must exist and be correctly configured. The Workspace Setup agent introduces a mandatory setup phase between the portfolio decision and the start of project delivery. It ensures that:
- An internal workspace exists with the correct folder structure and canvas views.
- All required connectors are enabled, authenticated, and have validated permissions.
- External artefacts (Teams channels, SharePoint sites, Jira projects, Planview shells) are provisioned or linked.
- The selected methodology lifecycle map and organisational template defaults are applied.

The agent publishes a `workspace.setup.completed` event that the Lifecycle Governance agent uses as a gate — no project can progress past initiation until workspace setup is complete.

---

## Integration Service Taxonomy

Agents interact with external systems through shared integration services defined in `agents/common/connector_integration.py`:

| Service | Responsibility | Connectors |
| --- | --- | --- |
| **DocumentManagementService** | Document CRUD, metadata, publishing | SharePoint, Confluence |
| **DocumentationPublishingService** | Thin facade over DocumentManagementService; Confluence-first publish with SharePoint fallback | Confluence (primary), SharePoint (fallback) |
| **ERPFinanceService** | Financial data sync — GL, cost centres, journal entries | SAP, Oracle, NetSuite, Dynamics 365 |
| **HRISService** | HR data sync — employees, org structure, resource capacity | Workday, SuccessFactors, ADP |
| **ProjectManagementService** | Project/task CRUD, schedule sync | Planview, MS Project, Jira, Azure DevOps, Smartsheet |
| **ITSMIntegrationService** | Incident, change, and service request management | ServiceNow, Jira Service Management, BMC Remedy |
| **GRCIntegrationService** | Governance, risk, and compliance record management | ServiceNow GRC, RSA Archer |
| **NotificationService** | Multi-channel notifications — email, Teams, Slack, SMS, push | SMTP/SendGrid, Teams, Slack, Twilio, Azure Notification Hubs |
| **CalendarIntegrationService** | Calendar event CRUD and availability checks | Outlook, Google Calendar |
| **DatabaseStorageService** | Persistent agent data storage | Azure SQL, Cosmos DB, local JSON |
| **MLPredictionService** | Classification, forecasting, anomaly detection | Azure ML |

**Agent-to-service usage:**

| Agent | Primary services | Optional services |
| --- | --- | --- |
| workspace-setup-agent | DocumentManagementService, ProjectManagementService, NotificationService, DatabaseStorageService | CalendarIntegrationService |
| approval-workflow-agent | NotificationService, DatabaseStorageService | CalendarIntegrationService |
| data-synchronisation-agent | DatabaseStorageService, ConnectorWriteGate (governed runtime) | — |
| financial-management-agent | ERPFinanceService, DatabaseStorageService, NotificationService | — |
| resource-management-agent | HRISService, DatabaseStorageService | CalendarIntegrationService |
| risk-management-agent | GRCIntegrationService, DocumentManagementService, DocumentationPublishingService, MLPredictionService, DatabaseStorageService | — |
| release-deployment-agent | DocumentationPublishingService, DatabaseStorageService, CalendarIntegrationService | — |

> **ConnectorWriteGate:** All services check the write gate before external writes. The gate enforces: connector configured + connected, approval present if policy requires, dry-run passed if required, idempotency key generated, and audit entry emitted.

---

## Core Orchestration Agents

### Intent Router (Agent 01)

**Category:** Core Orchestration | **Role:** Platform Dispatcher

The Intent Router is the first point of contact for every user interaction. It sits at the front of the agent network and acts as an intelligent dispatcher — classifying what a user has asked for, extracting relevant parameters, and directing the request to the right combination of specialist agents.

**What it does:**
- **Classifies intent** using an LLM-based classifier with a keyword-based fallback for resilience when the LLM is unavailable.
- **Extracts parameters** (project ID, portfolio scope, financial amounts, entity types, timeframes) embedded in the user's request.
- **Determines routing** — produces a structured routing plan specifying which domain agents to call, in what order, and with what inputs.
- **Detects multi-intent** requests (e.g., "create a project and generate a risk register") and constructs a routing plan that addresses each intent.

**What it produces:** A routing plan consumed by the Response Orchestration agent; an audit event for every request processed, capturing the intent classification, confidence score, and method used.

**Connects to:** Response Orchestration agent (passes routing plan); every request in the platform flows through the Intent Router first.

---

### Response Orchestration (Agent 02)

**Category:** Core Orchestration | **Role:** Execution Coordinator

The Response Orchestration agent picks up the routing plan produced by the Intent Router and carries it through to completion — calling agents in the right order, managing failures, caching results, and assembling everything into a single coherent response.

**What it does:**
- **Executes the routing plan**, calling each domain agent as directed.
- **Manages parallel and sequential execution** using a dependency graph with cycle detection.
- **Handles failures gracefully** with exponential backoff retries and a circuit breaker that prevents flooding struggling services.
- **Caches results** for expensive, frequently repeated tasks (15-minute TTL by default).
- **Enriches responses** with external research when configured.
- **Aggregates and synthesises** all agent outputs into a single structured response.

**What it produces:** The final response presented to the user; plan execution records for every task in the routing plan (visible to administrators in the Agent Runs view).

**Connects to:** Receives its instructions from the Intent Router; calls any combination of agents 03–25 depending on the routing plan.

---

### Approval Workflow (Agent 03)

**Category:** Core Orchestration | **Role:** Workflow Orchestration and Governance

The Approval Workflow agent is the platform's unified workflow and approval engine — the single canonical orchestration authority for all long-running, multi-step processes.

**Workflow engine capabilities:**
- Defines workflows as structured YAML/JSON or BPMN 2.0 specifications using the `ppm.workflow/v1` schema.
- Starts and manages workflow instances with full state persistence (PostgreSQL or JSON file backend).
- Executes parallel branches, conditional logic, and decision points.
- Manages human task inboxes with deadlines and context-rich notifications.
- Handles retries with exponential backoff and compensation workflows for rollback.
- Responds to events from other agents via configurable event subscriptions.
- Supports workflow versioning — in-flight instances continue on the version they started with.

**Approval capabilities:**
- Creates sequential or parallel approval chains with dynamic routing based on risk level, financial value, and organisational context.
- Supports delegation rules when approvers are unavailable.
- Sends notifications via email, Microsoft Teams, Slack, and push.
- Escalates automatically when deadlines are missed.
- Records every approval decision permanently in the immutable audit log.

**Approval workflow step example:**
```yaml
# ppm.workflow/v1
apiVersion: ppm.workflow/v1
kind: WorkflowDefinition
metadata:
  name: project-initiation
  version: "1.0"
spec:
  steps:
    - id: charter_review
      type: approval_gate
      config:
        request_type: charter_approval
        chain_type: sequential
        approvers:
          - role: project_sponsor
          - role: pmo_lead
        sla_hours: 48
        escalation_policy: risk_based
        notification_channels: [email, teams]
        deep_link_label: "View request"
      transitions:
        approved: requirements_phase
        rejected: revision_required
```

**Platform surfaces:** Workflow Designer (create/configure/import definitions), Workflow Monitoring (real-time instance view), Approvals page (pending and completed approvals), Task Inbox (human tasks and approval decisions).

**Connects to:** Used by virtually every other agent for governed multi-step processes. Key consumers: Business Case, Vendor Procurement, Change Control, Scope Definition, Workspace Setup, Release Deployment, Data Synchronisation, Continuous Improvement.

---

### Workspace Setup (Agent 24)

**Category:** Core Orchestration | **Role:** Project Workspace Initialiser

The Workspace Setup agent introduces a mandatory setup phase between portfolio approval and the start of project delivery, ensuring all tools and connectors are ready before any delivery agent begins work.

**What it does:**
- Creates the internal workspace with the correct folder structure, canvas views, and canvas defaults.
- Validates connector authentication and permissions for all required integrations.
- Provisions external artefacts: Teams channels, SharePoint sites, Jira projects, Planview shells.
- Applies the selected methodology lifecycle map and organisational template defaults.
- Publishes `workspace.setup.completed` — the Lifecycle Governance agent uses this as a hard gate before project initiation can proceed.

**Connects to:** Approval Workflow agent (for governed provisioning actions); Lifecycle Governance agent (gate consumer); Connector registry.

---

## Portfolio Management Agents

### Demand Intake (Agent 04)

**Category:** Portfolio Management | **Role:** Project Request Handler

The Demand and Intake agent is the front door for every project idea, request, and proposal. It ensures no request is lost and that every submission is consistently captured, classified, and reviewed.

**What it does:**
- Receives requests from multiple channels: web intake form, Slack, Teams, email.
- Classifies each request by category (capital project, technology initiative, regulatory compliance, etc.) and estimates complexity.
- Uses semantic similarity analysis (vector embeddings) to flag potential duplicate submissions.
- Enriches incomplete submissions by inferring business unit, portfolio, and categorisation from context.
- Routes submissions to reviewers and maintains a pipeline status view (submitted → under review → approved → rejected → converted).

**Connects to:** Business Case agent (hands off approved demand records); Approval Workflow agent (intake approval queue); Portfolio Optimisation agent (surfaces outputs in portfolio views).

---

### Business Case and Investment Analysis (Agent 05)

**Category:** Portfolio Management | **Role:** Financial Justification and Investment Advisor

The Business Case agent turns a project idea into a rigorous investment proposition, compressing days of analytical work into minutes.

**What it does:**
- Generates structured business case documents from configurable templates (capital, technology, regulatory, operational).
- Performs cost-benefit analysis across full project lifecycle (capital, implementation, operational, decommissioning costs).
- Calculates NPV, IRR, payback period, and TCO with configurable discount rates and multi-currency support.
- Models base/optimistic/conservative scenarios with sensitivity analysis identifying key assumptions.
- Runs Monte Carlo simulation for probabilistic outcome distributions.
- Benchmarks against historical projects for realism checks.
- Produces an investment recommendation (proceed / do not proceed / proceed with conditions) with confidence level.

**Connects to:** Receives input from Demand Intake; routes completed cases to Approval Workflow; feeds approved cases to Portfolio Optimisation; financial baseline feeds Financial Management.

---

### Portfolio Strategy and Optimisation (Agent 06)

**Category:** Portfolio Management | **Role:** Investment Prioritisation and Portfolio Advisor

The Portfolio Strategy and Optimisation agent provides evidence-based, multi-criteria analysis to answer the hardest portfolio question: given real constraints, what should we invest in?

**What it does:**
- Scores and ranks all active and proposed projects across: strategic alignment, ROI, risk, urgency, dependencies, and resource intensity (configurable weights per tenant).
- Performs capacity-constrained optimisation to find the maximum-value portfolio within actual budget and resource limits.
- Supports multiple optimisation approaches: integer programming, mean-variance, AHP, multi-objective.
- Runs what-if scenario analysis (e.g., "What if we cut budget by 15%?").
- Evaluates policy guardrails (minimum diversification, mandatory compliance investments, concentration limits).
- Produces rebalancing recommendations when the portfolio drifts from its optimal configuration.

**Connects to:** Draws on Business Case and Resource Management agent data; informs Programme Management and Financial Management; feeds Analytics and Insights for executive reporting.

---

### Programme Management (Agent 07)

**Category:** Portfolio Management | **Role:** Programme Coordinator and Benefits Tracker

The Programme Management agent provides the organisational layer between individual projects and the portfolio, managing the structure, dependencies, and benefits of related project groups.

**What it does:**
- Defines and creates programme records with mandate, objectives, benefit realisation plan, and governance structure.
- Builds and maintains live integrated roadmaps (updates automatically as project schedules change).
- Manages inter-project dependencies via a dependency graph, alerting on knock-on risks.
- Aggregates and tracks benefit realisation progress across constituent projects.
- Identifies cross-project resource conflicts and works with the Resource Management agent to recommend resolutions.
- Surfaces synergy opportunities between projects within the programme.
- Calculates a composite programme health score with narrative summary.
- Analyses change impact at programme level when scope/schedule changes are proposed for constituent projects.

**Connects to:** Draws on Portfolio Optimisation, Schedule Planning, Resource Management, and Financial Management agents; publishes events consumed by Analytics, Stakeholder Communications, and Governance agents.

---

## Delivery Management Agents

### Project Definition and Scope (Agent 08)

**Category:** Delivery Management | **Role:** Project Charter and Scope Baseline Manager

Drafts project charters, establishes scope baselines, and manages the Work Breakdown Structure for individual projects.

**Key outputs:** Project charters, WBS, scope baseline documents, scope change impact assessments.

**Connects to:** Demand Intake (receives demand record), Approval Workflow (charter sign-off), Change Control (scope baseline updates), Lifecycle Governance (initiation gate).

---

### Project Lifecycle and Governance (Agent 09)

**Category:** Delivery Management | **Role:** Stage-Gate Enforcer and Project Health Monitor

Enforces phase transitions, evaluates stage gate criteria, and monitors project health throughout the delivery lifecycle. Consumes the `workspace.setup.completed` event from the Workspace Setup agent as a hard gate before initiation can proceed.

**Key outputs:** Stage-gate assessments, health scores, transition approvals, lifecycle status updates.

**Connects to:** Workspace Setup (gate consumer), Approval Workflow (gate approvals), Compliance Governance (compliance gate inputs), Change Control (assesses whether changes require gate review).

---

### Schedule and Planning (Agent 10)

**Category:** Delivery Management | **Role:** Schedule Builder and Milestone Manager

Builds schedules and Work Breakdown Structures from scope inputs, manages baselines, and performs critical path analysis.

**Key outputs:** Baselined schedules, WBS, critical path analysis, milestone status, schedule variance reports.

**Connects to:** Scope Definition (scope inputs), Resource Management (resource constraints), Change Control (schedule baseline updates), Programme Management (programme roadmap).

---

### Resource and Capacity Management (Agent 11)

**Category:** Delivery Management | **Role:** Resource Allocator and Capacity Planner

Manages resource allocation and capacity planning across projects, identifying conflicts and forecasting demand.

**Key outputs:** Resource allocation plans, capacity forecasts, utilisation reports, resource conflict flags.

**Connects to:** Schedule Planning (schedule constraints), HR systems via HRISService (Workday, SuccessFactors, ADP), Portfolio Optimisation (capacity constraints), Programme Management (cross-project resource view).

---

### Financial Management (Agent 12)

**Category:** Delivery Management | **Role:** Budget Tracker and Financial Controller

Tracks budgets, actuals, and forecasts; produces variance and Earned Value Management reports; monitors profitability.

**Key outputs:** Budget reports, cost forecasts, EVM reports, variance analysis, profitability metrics.

**Connects to:** Business Case (financial baseline), ERP systems via ERPFinanceService (SAP, Oracle, NetSuite), Approval Workflow (financial approvals), Change Control (budget baseline updates).

---

### Vendor and Procurement Management (Agent 13)

**Category:** Delivery Management | **Role:** Vendor Lifecycle and Procurement Coordinator

Manages the end-to-end vendor and procurement lifecycle from RFP through contract management and performance tracking.

**Key outputs:** RFPs, vendor records, contracts, vendor performance reports, onboarding status.

**Connects to:** Financial Management (procurement costs), Compliance Governance (vendor compliance), Approval Workflow (procurement approvals), Document Management (contract storage).

---

### Quality Management (Agent 14)

**Category:** Delivery Management | **Role:** Quality Planner and Test Coordinator

Defines quality plans, manages test coordination, tracks defects, and evaluates quality gate criteria.

**Key outputs:** Quality plans, test results, defect records, quality gate assessments, acceptance test reports.

**Connects to:** Approval Workflow (quality gate approvals), Compliance Governance (quality standards compliance), Release Deployment (release quality clearance), Lifecycle Governance (quality gate inputs).

---

### Risk and Issue Management (Agent 15)

**Category:** Delivery Management | **Role:** Risk Identifier, Assessor, and Issue Tracker

Maintains risk and issue registers, performs quantitative risk analysis, and tracks mitigations and resolutions.

**Key outputs:** Risk registers, issue logs, quantified exposure reports, mitigation plans, risk trend analysis.

**Connects to:** GRC systems via GRCIntegrationService (ServiceNow GRC, RSA Archer), Programme Management (programme-level risk aggregation), Compliance Governance (compliance risk inputs), Analytics and Insights (risk dashboards).

---

### Compliance and Regulatory (Agent 16)

**Category:** Delivery Management | **Role:** Regulatory Framework Manager and Compliance Monitor

Verifies the platform's and projects' compliance posture against regulatory frameworks and internal policies, producing evidence packages for audit.

**Key outputs:** Compliance control records, evidence packages, audit reports, compliance gap assessments.

**Connects to:** Audit Log service (evidence source), Quality Management (test evidence), Risk Management (compliance risk inputs), Lifecycle Governance (compliance gate clearance), Release Deployment (release compliance clearance), Analytics and Insights (portfolio compliance reporting).

---

## Operations Management Agents

### Change and Configuration Management (Agent 17)

**Category:** Operations Management | **Role:** Change Controller and Configuration Authority

Governs the controlled evolution of project scope, schedule, budget, and technical baseline. Every significant change passes through this agent to be assessed, approved, and recorded before it takes effect.

**What it does:**
- Captures and classifies change requests using a text classification model (category: infrastructure, application, process, governance, scope, schedule, budget).
- Assesses multi-dimensional impact: scope, schedule, cost, compliance, and dependency effects.
- Parses IaC files (Terraform, ARM, Bicep) to identify specific resource-level changes for technology programmes.
- Uses a Neo4j dependency graph to trace downstream impacts through the dependency network.
- Routes changes to the appropriate approval authority (project manager, change control board, or expedited emergency path).
- Orchestrates change implementation workflows via Azure Durable Functions and Logic Apps.
- Maintains the current authorised configuration record of every project.

**Connects to:** Approval Workflow (change approval routing), Scope Definition, Schedule Planning, and Financial Management (baseline updates), Lifecycle Governance (gate review triggers), Release Deployment (configuration record for deployment readiness), Programme Management (programme-level change impact).

---

### Release and Deployment (Agent 18)

**Category:** Operations Management | **Role:** Release Coordinator and Deployment Orchestrator

Coordinates the controlled movement of project outputs from the delivery environment into production, managing planning, readiness assessment, deployment orchestration, and rollback.

**Key outputs:** Release plans, deployment records, rollback procedures, release readiness assessments, go/no-go decisions.

**Connects to:** Quality Management (release quality clearance), Compliance Governance (compliance clearance), Change Control (configuration record), Approval Workflow (deployment approvals), Calendar Integration (release scheduling).

---

### Knowledge and Document Management (Agent 19)

**Category:** Operations Management | **Role:** Document Librarian and Knowledge Curator

Manages the document lifecycle and maintains the platform's knowledge repository — indexing, versioning, and surfacing relevant knowledge assets.

**Key outputs:** Indexed document repository, lessons-learned records, knowledge search results, document version history.

**Connects to:** SharePoint and Confluence via DocumentManagementService, all agents that produce documents (Scope Definition, Business Case, Risk Management, etc.).

---

### Continuous Improvement and Process Mining (Agent 20)

**Category:** Operations Management | **Role:** Process Analyst and Improvement Engine

Captures retrospective outcomes and applies process mining to telemetry data, producing improvement recommendations and a structured backlog.

**Key outputs:** Process deviation reports, improvement recommendations, retrospective summaries, process mining insights.

**Connects to:** Approval Workflow (execution data for process analysis), Analytics and Insights (improvement metrics), Observability stack (telemetry inputs).

---

### Stakeholder Communications (Agent 21)

**Category:** Operations Management | **Role:** Communications Planner and Engagement Manager

Plans and delivers stakeholder communications — status updates, milestone notifications, and engagement records — across configured channels.

**Key outputs:** Communication plans, stakeholder engagement records, formatted status updates, notification messages.

**Connects to:** Programme Management (programme status signals), Schedule Planning (milestone triggers), Notification Service (delivery via Teams/Slack/email), Analytics and Insights (engagement metrics).

---

### Analytics and Insights (Agent 22)

**Category:** Operations Management | **Role:** Portfolio Intelligence and Reporting Engine

Produces dashboards, reports, and predictive forecasts across the full portfolio, programme, and project hierarchy.

**Key outputs:** KPI dashboards, portfolio health reports, predictive forecasts, trend analysis, executive summaries.

**Connects to:** All domain agents (data consumer), Canonical data schemas in the Data Service, Data Synchronisation agent (data quality inputs), Azure ML via MLPredictionService (forecasting).

---

### Data Synchronisation and Quality (Agent 23)

**Category:** Operations Management | **Role:** Data Integrity Guardian and Sync Coordinator

Synchronises data between the platform and external systems, scoring data quality and maintaining consistency across the integration layer.

**Key outputs:** Sync status reports, data quality dashboards, quality scores, sync logs, anomaly flags.

**Connects to:** All 40+ connectors via the governed connector runtime (ConnectorWriteGate), Approval Workflow (sync retry workflows), Data Lineage Service (provenance tracking).

---

### System Health and Monitoring (Agent 25)

**Category:** Operations Management | **Role:** Platform Reliability Guardian

Monitors platform health across all services, evaluates SLO compliance, and escalates alerts for degraded or failing components.

**Key outputs:** Health status reports, alerts, SLO compliance reports, degradation diagnostics.

**Connects to:** OpenTelemetry/Prometheus observability stack, Azure Monitor, all services via `/healthz` endpoints, Analytics and Insights (operational metrics).

---

## Tooling

Validate internal links across docs:

```bash
python ops/scripts/check-links.py
```

Verify the catalog contains all 25 agents:

```bash
rg -n "the System Health agent" agents/AGENT_CATALOG.md
```
