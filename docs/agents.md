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

The Project Definition and Scope agent is the starting point for every project's delivery lifecycle — turning an approved demand record into a structured project charter, a hierarchical Work Breakdown Structure, and a locked scope baseline that downstream agents depend on.

**What it does:**
- **Generates project charters** from configurable templates (capital, technology, regulatory, operational) with objectives, constraints, success criteria, and methodology selection.
- **Builds a hierarchical Work Breakdown Structure (WBS)** from scope statements, assigning unique WBS item identifiers for traceability.
- **Manages requirements** — captures, organises, and prioritises requirements with metadata (priority thresholds: critical 0.9, high 0.7, medium 0.4, low 0.0).
- **Creates traceability matrices** linking requirements to WBS deliverables with coverage status tracking (90% coverage threshold enforced).
- **Performs stakeholder analysis** — identifies stakeholders, scores them by influence, and produces a stakeholder register with RACI matrix across deliverables.
- **Locks scope baselines** in a SQL-backed repository, creating immutable snapshots with approval status tracking.
- **Detects scope creep** by comparing the current scope against the locked baseline and flagging deviations that exceed a configurable threshold (default 10%).
- **Enriches scope with external research** via optional AI-powered web search when configured.

**What it produces:** Project charters, WBS hierarchies with unique IDs, requirements repositories, traceability matrices, stakeholder registers, RACI matrices, scope baseline snapshots, and scope creep variance reports. Publishes `baseline.created`, `traceability.matrix.created`, and `scope.baseline.locked` events.

**Connects to:** Demand Intake (receives demand record), Approval Workflow (charter sign-off), Change Control (scope baseline updates), Lifecycle Governance (initiation gate). The scope baseline and WBS are critical inputs consumed by the Schedule Planning and Resource Management agents — neither can proceed until a scope baseline exists.

---

### Project Lifecycle and Governance (Agent 09)

**Category:** Delivery Management | **Role:** Stage-Gate Enforcer and Project Health Monitor

The Project Lifecycle and Governance agent is the platform's phase-gate enforcer and health monitor — it controls how projects progress through their lifecycle, ensures gate criteria are met before transitions, and maintains a continuous composite health score that reflects the real state of every active project.

**What it does:**
- **Manages project phase progression** through a configurable lifecycle (Initiate → Plan → Execute → Monitor → Iterate → Release → Close) with methodology-aware gate criteria for predictive, adaptive, and hybrid approaches.
- **Evaluates stage gate criteria** before allowing phase transitions — blocking progression when criteria are unmet unless an override is approved via the Approval Workflow agent.
- **Recommends and adapts methodologies** (predictive, adaptive, hybrid) based on project context, maintaining methodology maps and gate criteria per methodology.
- **Monitors project health continuously** using a composite score weighted across schedule (25%), cost (25%), risk (20%), quality (15%), and resource (15%) dimensions, ingesting metrics from domain agents.
- **Applies machine learning readiness scoring** trained on project history to predict gate readiness before formal evaluation.
- **Tracks governance compliance** by consuming compliance sign-offs and attestations from the Compliance Governance agent as gate evidence.
- **Publishes lifecycle events** (`gate.passed`, `gate.failed`, `gate.overridden`, `phase.changed`, `project.health.updated`) consumed by downstream agents.

**What it produces:** Lifecycle records with current phase and gates passed, gate evaluation results with criteria status and readiness scores, health telemetry with composite scores, status classifications, and recommendations.

**Connects to:** Workspace Setup (consumes `workspace.setup.completed` as a hard gate — no project can progress past initiation until workspace setup is complete), Approval Workflow (gate override approvals), Compliance Governance (compliance attestations as gate evidence), Change Control (assesses whether changes require gate review). All domain agents feed health metrics via a configured metrics catalog.

---

### Schedule and Planning (Agent 10)

**Category:** Delivery Management | **Role:** Schedule Builder and Milestone Manager

The Schedule and Planning agent transforms the scope baseline and WBS into an executable, resource-aware schedule — applying critical path analysis, Monte Carlo simulation, and what-if modelling to give project teams a realistic plan and continuous visibility into schedule risk.

**What it does:**
- **Converts WBS to schedule** — transforms the Work Breakdown Structure into a sequenced, task-based schedule with dependency mapping (Finish-to-Start, Start-to-Start, Finish-to-Finish, Start-to-Finish).
- **Estimates durations** using AI and historical data with confidence intervals, applying risk adjustments (high: 20% buffer, medium: 10%, low: 5%) from configuration.
- **Calculates the critical path** using the Critical Path Method (CPM) — computing early/late start/finish dates, identifying the critical path, and determining total project duration and float.
- **Performs resource-constrained scheduling** — applies resource availability constraints and performs resource levelling when resource data is provided by the Resource Management agent.
- **Runs Monte Carlo simulation** (configurable iterations, default 1,000) for probabilistic schedule analysis — producing completion date distributions and risk scores.
- **Supports what-if analysis** — compares scenarios (e.g., "+20% risk buffer", "resource constraints") with baseline to inform planning decisions.
- **Manages schedule baselines** — locks baselines and tracks variance against actuals with trend analysis.
- **Tracks milestones** — identifies milestone status, upcoming deadlines, and schedule health.

**What it produces:** Baselined schedules with Gantt data and task sequencing, critical path analysis with duration and float, risk-adjusted durations and buffers, Monte Carlo results with percentiles and risk drivers, milestone status, schedule variance reports, and what-if scenario comparisons.

**Connects to:** Scope Definition (consumes WBS and scope baseline), Resource Management (exchanges resource availability and allocation events), Risk Management (publishes schedule risk metrics, consumes risk register updates), Change Control (schedule baseline updates), Programme Management (programme roadmap integration).

---

### Resource and Capacity Management (Agent 11)

**Category:** Delivery Management | **Role:** Resource Allocator and Capacity Planner

The Resource and Capacity Management agent is the single source of truth for who is available, where they are allocated, and what capacity the organisation has for future work — ensuring projects are staffed with the right skills and no one is over-committed.

**What it does:**
- **Maintains a centralised resource pool** of people and equipment with skills, certifications, availability windows, and cost rates.
- **Matches resources to demand** using a weighted scoring algorithm (skills 60%, availability 20%, cost 10%, performance 10%) with a configurable skill match threshold (default 70%).
- **Creates and validates allocations** with overlap and threshold enforcement — checking concurrent allocation limits (default 3) and total allocation percentage (default 100%).
- **Forecasts capacity** across a configurable horizon (default 12 months) with seasonality factors, training impact (10% capacity reduction), and attrition rate modelling.
- **Runs scenario analysis** — compares baseline capacity against scenarios (e.g., "+10% hiring", "−15% attrition") to inform workforce planning.
- **Detects resource conflicts** — identifies over-allocations across projects and produces mitigation recommendations.
- **Monitors utilisation** against a target threshold (default 85%), flagging both over- and under-utilisation.
- **Syncs with HR systems** — integrates with Workday, SAP SuccessFactors, and Azure AD for employee profiles, and with Planview and Jira Tempo for external capacity data.
- **Routes resource requests** to approvers based on configured routing rules, publishing `resource.allocation.created` and `resource.request.approved/rejected` events.

**What it produces:** Resource profiles with skills and certifications, allocation records, capacity and demand forecasts with bottleneck identification, utilisation summaries, conflict reports with resolution recommendations.

**Connects to:** Schedule Planning (provides resource availability for resource-constrained scheduling, consumes schedule constraints), Financial Management (provides allocation facts and cost rates for budget tracking), HR systems via HRISService (Workday, SuccessFactors, ADP), Portfolio Optimisation (capacity constraints), Programme Management (cross-project resource view and conflict resolution).

---

### Financial Management (Agent 12)

**Category:** Delivery Management | **Role:** Budget Tracker and Financial Controller

The Financial Management agent provides continuous financial visibility across the delivery lifecycle — from budget baseline creation through cost tracking, forecasting, earned value analysis, and profitability reporting, with full ERP integration for actuals.

**What it does:**
- **Creates and manages budget baselines** with cost breakdowns by category (labour, overhead, materials, contracts, travel, software, other) and routes baselines through the Approval Workflow agent.
- **Tracks actual costs and accruals** against budget, integrating with ERP systems (SAP, Oracle, NetSuite, Dynamics 365) for accounts payable transactions via Azure Data Factory pipelines.
- **Generates ML-based cost and cash flow forecasts** with estimate-at-completion (EAC) values and confidence intervals.
- **Performs variance analysis** comparing actuals to budget with configurable threshold alerting (default 10% or $10,000 absolute).
- **Calculates Earned Value Management (EVM) metrics** — EV, PV, AC, CPI (cost performance index), and SPI (schedule performance index).
- **Supports multi-currency budgets** with exchange rate lookup and tax handling by jurisdiction.
- **Computes profitability metrics** — ROI, NPV (configurable discount rates), IRR, and payback period.
- **Generates financial reports** in multiple formats: summary, variance, forecast, cash flow, and profitability.
- **Publishes finance lifecycle events** (budget.created, costs.tracked, variance.alerted) to the Service Bus for downstream consumers.

**What it produces:** Budget baselines with approval status, cost tracking summaries and accruals, variance and trend reports, EAC forecasts with confidence intervals, EVM metrics, profitability analysis (ROI, NPV, IRR, payback), and financial reports across multiple formats.

**Connects to:** Business Case (consumes approved cash flows for baseline tracking), Vendor Procurement (consumes invoice and actuals data, provides budget availability checks), Resource Management (consumes allocation facts and cost rates), ERP systems via ERPFinanceService (SAP, Oracle, NetSuite), Approval Workflow (financial approvals), Change Control (budget baseline updates), Analytics and Insights (financial events and metrics).

---

### Vendor and Procurement Management (Agent 13)

**Category:** Delivery Management | **Role:** Vendor Lifecycle and Procurement Coordinator

The Vendor and Procurement Management agent is the system of record for the entire vendor and procurement lifecycle — from vendor onboarding and compliance screening, through RFP generation and proposal evaluation, to contract management, invoice reconciliation, and ongoing performance monitoring.

**What it does:**
- **Onboards vendors** with compliance screening — sanctions checks, credit ratings, and anti-corruption verification — assigning risk scores and compliance status.
- **Processes procurement requests** with ML-based categorisation, budget availability checks via Financial Management, and approval routing based on procurement thresholds.
- **Generates RFPs** from configurable templates (software, services, consulting, cloud) using AI-based or template-based content generation, and publishes to external procurement connectors (SAP Ariba, Coupa, Oracle Procurement).
- **Evaluates proposals** using an AI/ML scoring framework with multi-criteria vendor ranking and selection recommendations.
- **Manages contracts** with clause extraction via Azure Form Recognizer, document publishing to managed storage, and key terms tracking.
- **Handles the purchase order and invoice lifecycle** — PO creation and approval, invoice receipt, three-way matching (PO ↔ Invoice ↔ Receipt), and reconciliation with configurable tolerance.
- **Monitors vendor performance** — tracks SLA metrics, quality and compliance KPIs, and generates vendor scorecards with trend analysis.
- **Enforces vendor compliance policies** with configurable rules (block on failure, flag on watchlist, risk threshold enforcement).

**What it produces:** Vendor records with compliance status and risk scores, procurement request decisions, RFP documents, proposal evaluations with scoring, contracts with extracted metadata, PO confirmations, invoice reconciliation results, vendor scorecards, and procurement lifecycle events (vendor.onboarded, rfp.published, contract.created, invoice.reconciled, performance.updated).

**Connects to:** Financial Management (budget availability checks, cost tracking for POs and invoices), Compliance Governance (vendor compliance outcomes as evidence, regulatory policy updates), Risk Management (vendor compliance failures as risk signals), Approval Workflow (procurement approvals), Document Management (contract storage), Stakeholder Communications (procurement milestone notifications).

---

### Quality Management (Agent 14)

**Category:** Delivery Management | **Role:** Quality Planner and Test Coordinator

The Quality Management agent owns the quality planning, testing, defect management, and continuous improvement lifecycle across delivery workstreams — ensuring projects meet defined quality standards and providing release readiness signals to downstream agents.

**What it does:**
- **Creates quality plans** with standards definitions, acceptance criteria, and quality metric goals, routing plans through the Approval Workflow agent when enabled.
- **Manages test cases and execution** — creates test cases linked to requirements, organises test suites, tracks execution with pass/fail results, and calculates coverage percentages with trending.
- **Tracks and analyses defects** — logs defects with severity classification (critical, high, medium, low), manages defect workflow transitions, performs density calculations, and recommends root cause analysis (RCA).
- **Predicts defects using ML** — trains Naive Bayes classifiers for defect categorisation and clustering for pattern identification.
- **Evaluates quality gates** against execution-ready criteria: coverage ≥ 80%, defect density ≤ 0.05 per KLOC, pass rate ≥ 95%, and audit score ≥ 90% for regulated projects.
- **Maintains requirement traceability** — maps test cases to requirements and verifies coverage completeness.
- **Manages reviews and audits** — schedules reviews with calendar integration, tracks audit findings, and verifies compliance against standards (ISO 9001, CMMI, IEEE 829).
- **Synchronises with external tools** — syncs defect tickets with Jira, Azure DevOps, and TestRail.

**What it produces:** Quality plans with objectives and metrics, test cases and suites, test execution results with coverage reports, defect records with RCA summaries, quality metrics (coverage %, pass rate, defect density), quality dashboards with heat maps and trends, quality gate assessments (pass/fail with exceptions), and release readiness signals.

**Connects to:** Release Deployment (provides quality gate results for release decisioning), Risk Management (publishes defect rate as risk signal), Lifecycle Governance (supplies quality gate inputs for phase gate decisions), Compliance Governance (quality test results as compliance evidence), Approval Workflow (quality plan and gate approvals), Analytics and Insights (quality metrics for reporting).

---

### Risk and Issue Management (Agent 15)

**Category:** Delivery Management | **Role:** Risk Identifier, Assessor, and Issue Tracker

The Risk and Issue Management agent owns the end-to-end risk lifecycle — from identification and assessment through scoring, mitigation planning, and continuous monitoring — across projects, programmes, and portfolios, using both qualitative analysis and quantitative simulation.

**What it does:**
- **Identifies risks from multiple sources** — user input, document mining (SharePoint, Confluence), project management connector signals (schedule delays, cost overruns, quality defect rates, resource utilisation), and ML-based prediction models.
- **Assesses and scores risks** using both qualitative (low/medium/high) and quantitative (numerical) probability and impact scales, with category-based classification (technical, resource, schedule, financial, compliance, external, organisational).
- **Runs Monte Carlo simulation** (default 10,000 iterations) for schedule and financial risk analysis, producing probability distributions, sensitivity analysis, and correlation between risks.
- **Creates mitigation plans** with response strategies (avoid, mitigate, transfer, accept), action items, ownership assignment, and trigger thresholds.
- **Monitors risk triggers in real time** — subscribes to schedule delay, cost overrun, quality defect rate, resource utilisation, milestone missed, and financial update signals, automatically updating risk scores and escalating when thresholds are breached.
- **Searches a knowledge base** via Azure Cognitive Search for historical risk guidance and lessons learned.
- **Exports risk data** to Azure Data Lake and Synapse for enterprise risk analytics.

**What it produces:** Risk records with full metadata (probability, impact, score, status, category), risk assessments, mitigation plans with ownership, Monte Carlo simulation results with probability distributions, sensitivity analyses, risk matrices, risk dashboards, and risk reports. Publishes `risk.created`, `risk.updated`, `risk.triggered`, and `risk.escalated` events.

**Connects to:** Quality Management (consumes defect rate as risk signal), Lifecycle Governance (supplies risk status for governance scorecards), Schedule Planning (consumes schedule delays and milestone misses), Financial Management (consumes cost overruns and budget updates), Resource Management (consumes resource utilisation signals), Compliance Governance (escalates compliance-related risks), Approval Workflow (escalates critical risks for governance review), GRC systems via GRCIntegrationService (ServiceNow GRC, RSA Archer), Programme Management (programme-level risk aggregation), Analytics and Insights (risk dashboards).

---

### Compliance and Regulatory (Agent 16)

**Category:** Delivery Management | **Role:** Regulatory Framework Manager and Compliance Monitor

The Compliance and Regulatory agent ensures projects, programmes, and portfolios adhere to external regulations, industry standards, and internal policies — managing the full compliance lifecycle from framework applicability through control mapping, evidence collection, gap analysis, and audit preparation.

**What it does:**
- **Manages a regulatory framework library** (Privacy Act 1988, APRA CPS 234, ISO 27001, ASD ISM, PSPF — configurable) with applicability determination based on industry, geography, and data sensitivity.
- **Maintains a control library** with requirement specifications (implementation, evidence, testing, audit logs, risk mitigation, quality tests, deployment checks, privacy, security scans) and test frequency assignment (critical: monthly, high: quarterly, medium: semi-annually, low: annually).
- **Maps controls to projects** based on applicability rules and produces compliance assessments with gap identification, risk scoring, and remediation recommendations.
- **Calculates compliance scores** (0–100%) using a rule engine that evaluates evidence against control requirements.
- **Manages evidence collection** — uploads evidence artifacts (snapshots, audit logs, test results, security scans) and validates evidence completeness per control.
- **Prepares audit packages** — scopes audits, defines samples, tracks execution, documents findings, and generates audit reports.
- **Monitors regulatory changes** via optional external search, identifies impacted controls, and creates stakeholder tasks for affected regulations.
- **Verifies release compliance** — performs pre-release compliance checks and publishes pass/fail signals for the Release Deployment agent.
- **Responds to events** — subscribes to release, deployment, configuration, quality, risk, security, incident, and change events, automatically triggering compliance assessments and raising alerts when gaps are detected.

**What it produces:** Regulation records, control definitions with test frequencies, control-to-project mappings, compliance assessments with gap analysis and scores, remediation recommendations, control test results, evidence artifacts, audit packages and findings, compliance dashboards (controls by status, score, gaps by severity), compliance reports, release compliance verdicts, and regulatory change notifications.

**Connects to:** Lifecycle Governance (provides compliance inputs for gate decisions), Vendor Procurement (receives vendor compliance outcomes as evidence, supplies policy updates), Release Deployment (supplies release compliance verification for deployment decisions), Quality Management (consumes quality test results as evidence), Risk Management (consumes high-severity risks for compliance escalation), Audit Log service (evidence source), GRC systems via GRCIntegrationService (ServiceNow GRC, RSA Archer), Analytics and Insights (portfolio compliance reporting).

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

The Release and Deployment agent coordinates the controlled movement of project outputs from delivery environments into production — managing release planning, readiness assessment, deployment orchestration, post-deployment verification, and rollback when things go wrong.

**What it does:**
- **Plans and schedules releases** across environments (dev, test, staging, production) with release calendar entries and environment reservation.
- **Evaluates release readiness** via a multi-factor go/no-go assessment — checking approvals, change readiness, environment availability, test and coverage gates, and blocker status, producing an actionable recommendation with scoring.
- **Orchestrates deployments** across multiple environments with minimal risk, integrating with CI/CD systems (Azure DevOps, GitHub Actions, Durable Functions).
- **Manages environments** — reserves environments, tracks allocation, maintains an inventory, and detects configuration drift against CMDB baselines.
- **Enforces release gates** configurable per environment, requiring approval via the Approval Workflow agent for production deployments.
- **Handles rollback** — triggers automatic rollback on anomaly detection and supports manual rollback with scripted procedures.
- **Generates release notes** automatically from release metadata and change records.
- **Verifies deployments** post-deployment — runs verification checks and detects anomalies using monitoring integration.
- **Tracks deployment metrics** and KPIs for release performance analysis.

**What it produces:** Release calendar entries and schedules, readiness assessments with go/no-go status and compliance scores, deployment plans with workflow steps, rollback outcomes, configuration drift reports, release notes, deployment metrics and telemetry, and verification results.

**Connects to:** Quality Management (consumes quality metrics, test results, and coverage gates), Change Control (exchanges approved change tickets, configuration baselines, and risk/impact summaries), Compliance Governance (consumes release compliance verification), Approval Workflow (requests and enforces approval for protected environments), System Health (consumes environment health for deployment gates), Calendar Integration (environment reservation and deployment window scheduling), Documentation Publishing (Confluence/SharePoint for release notes).

---

### Knowledge and Document Management (Agent 19)

**Category:** Operations Management | **Role:** Document Librarian and Knowledge Curator

The Knowledge and Document Management agent is the platform's institutional memory — it ingests, classifies, indexes, and surfaces documents and knowledge assets, maintaining a semantic search index and a knowledge graph that connects documents, projects, risks, decisions, and lessons learned.

**What it does:**
- **Manages the full document lifecycle** — CRUD operations with versioning, retention management, and metadata validation against the canonical document schema.
- **Ingests from multiple sources** — user uploads, agent outputs, and external repositories (Confluence, SharePoint, Git) with normalisation and metadata enrichment.
- **Auto-classifies documents** using a Naive Bayes classifier with taxonomy management and tagging.
- **Provides semantic search** using sentence-transformer embeddings with a FAISS vector index (or in-memory vector store), returning results with relevance scores and summaries.
- **Generates LLM-driven summaries** with configurable token limits and prompt injection sanitisation.
- **Extracts entities** using an NLP pipeline and builds a knowledge graph linking documents, projects, programmes, portfolios, risks, and decisions.
- **Supports knowledge graph traversal** — queries relationships to discover connected artifacts across the platform.
- **Captures lessons learned** — records and retrieves lessons learned and best practices, categorised for future reuse.
- **Enforces access control** — applies RBAC/ABAC before retrieval and tracks document access logs for audit.

**What it produces:** Document records with versions and classification labels, search results with relevance scores and summaries, knowledge graph relationships and entity links, lessons learned artifacts, access logs and version history for audit, extracted entities and taxonomy assignments.

**Connects to:** Stakeholder Communications (hands off curated knowledge — summaries, decision logs, lessons learned — for distribution), Analytics and Insights (provides document corpora and knowledge artifacts to enrich analytics models), Approval Workflow (coordinates approval of formal knowledge documents), SharePoint and Confluence via DocumentManagementService, all agents that produce documents (Scope Definition, Business Case, Risk Management, etc.).

---

### Continuous Improvement and Process Mining (Agent 20)

**Category:** Operations Management | **Role:** Process Analyst and Improvement Engine

The Continuous Improvement and Process Mining agent discovers how processes actually execute by mining event logs, compares actual behaviour against designed process models, identifies bottlenecks and deviations, and produces a prioritised improvement backlog with measurable benefit tracking.

**What it does:**
- **Discovers as-is process models** from execution event logs using multiple algorithms (alpha miner, inductive miner, heuristic miner, fuzzy miner) and generates BPMN/Petri net representations.
- **Checks conformance** — validates actual processes against expected/designed models and computes compliance rates.
- **Detects bottlenecks** — identifies activities causing delays or resource constraints using configurable thresholds.
- **Identifies deviations** from expected process paths and triggers configurable alerts.
- **Performs root cause analysis** — analyses issues to identify contributing factors and actionable improvements.
- **Creates improvement initiatives** as backlog items with priority scoring and expected benefits, assigning owners and target dates.
- **Tracks benefit realisation and ROI** — measures realised benefits and financial impact of completed improvements.
- **Benchmarks process performance** against internal and external benchmarks, sharing successful patterns across the organisation.
- **Ingests events from across the platform** — subscribes to schedule, task, deployment, risk, approval, change, and incident events for process mining analysis.
- **Generates KPI reports** with process-level metrics and trends at project, programme, and portfolio levels.

**What it produces:** Process models with activities and transitions, conformance reports with compliance rates and deviation lists, bottleneck and deviation analyses with root causes and recommendations, improvement backlog entries with owners and expected benefits, benefit realisation metrics and ROI summaries, and KPI rollups across organisational levels.

**Connects to:** Analytics and Insights (receives periodic analytics reports, publishes process insights and benefit events), Approval Workflow (emits improvement recommendations as workflow events, receives workflow execution events for process mining), Knowledge Management (publishes best practices and improvement backlog), Financial Management (tracks financial impact of improvements), Observability stack (telemetry inputs).

---

### Stakeholder Communications (Agent 21)

**Category:** Operations Management | **Role:** Communications Planner and Engagement Manager

The Stakeholder Communications agent plans, personalises, and delivers communications across every channel the organisation uses — maintaining a stakeholder register, tracking engagement, collecting feedback with sentiment analysis, and ensuring the right people receive the right information at the right time.

**What it does:**
- **Maintains a stakeholder register** with profiles, roles, organisations, and communication preferences.
- **Classifies stakeholders** by influence/interest matrix and recommends engagement strategies per segment.
- **Creates communication plans** tied to portfolio and project updates with schedules, target audiences, and channel assignments.
- **Generates personalised messages** from templates using AI (Azure OpenAI), supporting editing before delivery.
- **Delivers across multiple channels** — email (Exchange/Azure Communication Services/SendGrid), Microsoft Teams, Slack, SMS (Twilio), push notifications (Firebase Cloud Messaging), and portal.
- **Supports flexible scheduling** — immediate, scheduled, or digest (batched with configurable window and batch size) delivery modes with send-time optimisation.
- **Collects feedback and analyses sentiment** using Azure Text Analytics, alerting on disengagement when sentiment drops below threshold.
- **Tracks engagement metrics** — delivery status, bounce rates, open rates, and engagement scores with ML-based engagement scoring.
- **Coordinates events and meetings** — schedules meetings with invitations via Calendar and Teams integration.
- **Maintains full communication history** in a database with audit trail, emitting events to the Service Bus for analytics.

**What it produces:** Stakeholder profiles with classifications and engagement strategies, communication plans and schedules, message drafts and delivery confirmations, feedback and sentiment scores, engagement dashboards, calendar events and meeting invitations, communication reports by project/role/locale, and delivery telemetry.

**Connects to:** Approval Workflow (submits message drafts requiring approval for external-facing communications), Knowledge Management (requests curated knowledge snippets for use in communications, submits post-communication summaries), Programme Management (programme status signals), Schedule Planning (milestone triggers), Notification Service (delivery via Teams/Slack/email), Analytics and Insights (engagement metrics), CRM systems (Salesforce for stakeholder profile sync).

---

### Analytics and Insights (Agent 22)

**Category:** Operations Management | **Role:** Portfolio Intelligence and Reporting Engine

The Analytics and Insights agent is the platform's intelligence layer — aggregating data from every domain agent, producing interactive dashboards and reports, running predictive models, and generating narrative insights that help executives and project teams make evidence-based decisions.

**What it does:**
- **Aggregates data from multiple sources** via Azure Synapse Analytics and Azure Data Lake, building portfolio-wide analytics from lifecycle events across all domain agents.
- **Creates interactive dashboards** with configurable widgets (max 20 per dashboard), embedding Power BI reports for rich visualisation with scheduled refresh.
- **Generates comprehensive reports** with visualisations, supporting natural language queries for ad-hoc self-service analytics.
- **Runs ML predictions** with configurable confidence thresholds (default 0.75) — including cost overrun prediction, schedule slip forecasting, and custom KPI models trained on historical data.
- **Performs scenario and what-if analysis** — compares baseline against scenarios with simulations for portfolio planning.
- **Produces narrative insights** using Azure OpenAI — generating insight stories, anomaly explanations, and pattern summaries embedded in reports and dashboards.
- **Tracks KPIs and OKRs** with trend analysis and threshold monitoring, publishing `analytics.kpi.threshold_breached` alerts when thresholds are exceeded.
- **Maintains data lineage** with source-to-sink mapping and PII masking for governance transparency.
- **Orchestrates Azure analytics services** — Synapse pools, Data Factory ETL pipelines, Event Hub streaming, and Stream Analytics for real-time event ingestion.
- **Generates periodic performance reports** (monthly by default) with cross-project metrics (cycle time, risk frequency, budget variance, late task ratio) and process improvement recommendations consumed by the Continuous Improvement agent.

**What it produces:** Dashboard specifications with widget layouts and Power BI embed URLs, reports with visualisations and download URLs, prediction results with confidence intervals and recommendations, scenario comparisons, KPI values with trends and threshold statuses, narrative content, data lineage records, and periodic performance reports with anomalies and recommendations.

**Connects to:** All domain agents (data consumer via event subscriptions), System Health (consumes health signals for dashboards), Continuous Improvement (receives periodic reports with improvement recommendations), Lifecycle Governance (consumes health and governance events), Data Synchronisation (data quality inputs), Canonical data schemas in the Data Service, Azure ML via MLPredictionService (forecasting).

---

### Data Synchronisation and Quality (Agent 23)

**Category:** Operations Management | **Role:** Data Integrity Guardian and Sync Coordinator

The Data Synchronisation and Quality agent is the platform's data integrity backbone — managing master data records, synchronising data between the platform and external systems in real time, resolving conflicts, detecting duplicates, enforcing data quality rules, and maintaining a full audit trail of every sync operation.

**What it does:**
- **Manages master data records** for PPM entities (project, resource, vendor, financial) with unique canonical IDs, tracking authoritative sources and sync authorisations.
- **Synchronises data in real time** triggered by source system events, supporting both single-record and batch operations with incremental and full sync modes.
- **Maps and transforms data** from source system fields to the canonical schema using configurable mapping rules, applying field defaults and computed values for each source (Planview, SAP, Jira, Workday).
- **Detects and resolves conflicts** when multiple sources modify the same entity, with configurable strategies: last-write-wins, timestamp-based, authoritative-source, prefer-existing, or manual (queued for human review via Approval Workflow).
- **Identifies duplicates** using fuzzy matching with a configurable confidence threshold (default 0.85) and merges records with primary record selection.
- **Enforces data quality** — validates inbound payloads against JSON schemas, applies rule-based validation, and checks completeness, consistency, timeliness, and uniqueness against configurable quality thresholds.
- **Manages a retry queue** for failed validations with configurable max retry attempts (default 3) and backoff strategies.
- **Maintains a schema registry** with versioning to prevent mismatched validation across schema evolution.
- **Tracks sync metrics** — latency (target SLA 60 seconds), success/failure rates, and quality dimensions, publishing metrics to Log Analytics.

**What it produces:** Master records in canonical schema, sync status indicators (success, duplicate, failed, conflict), quality reports with completeness/consistency/timeliness scores, retry queue entries, audit and lineage events, conflict records for manual resolution, sync metrics for analytics, and dashboard data for sync monitoring.

**Connects to:** All 40+ connectors via the governed connector runtime (ConnectorWriteGate), Approval Workflow (conflict and retry queue signals for workflow routing and human review), Analytics and Insights (consumes quality metrics and sync telemetry for dashboards), System Health (reports sync health metrics and latency anomalies), Continuous Improvement (sync quality trends for process recommendations), Data Lineage Service (provenance tracking).

---

### System Health and Monitoring (Agent 25)

**Category:** Operations Management | **Role:** Platform Reliability Guardian

The System Health and Monitoring agent is the platform's reliability guardian — continuously monitoring infrastructure, application, and agent health across all services, detecting anomalies, managing incidents, and providing capacity planning recommendations to keep the platform running within its SLO targets.

**What it does:**
- **Monitors compute resources** — tracks CPU, memory, network, and storage utilisation across Kubernetes and Azure infrastructure, scraping Prometheus targets for container metrics.
- **Probes application health** — checks `/healthz`, `/livez`, and `/readyz` endpoints at configurable intervals (default 60 seconds) with timeout settings, and collects application-specific metrics (request counts, error rates, latency).
- **Tracks agent health** — monitors PPM agent execution metrics, health status, and performance.
- **Manages alerts and incidents** — creates threshold-based alerts, manages alert acknowledgement lifecycle, routes high-priority alerts to PagerDuty/OpsGenie webhooks, and creates incidents in ServiceNow.
- **Detects anomalies** using Azure Anomaly Detector with ML-based anomaly detection on metric streams, flagging unusual patterns in time-series data.
- **Performs root cause analysis** — correlates events and metrics to identify patterns, generating diagnostic summaries with PII redaction.
- **Plans capacity** — forecasts capacity needs based on growth trends and provides scaling recommendations (CPU, memory, queue depth) with auto-scaling via Logic App/Azure Automation webhooks.
- **Generates dashboards and reports** — produces health dashboards with time range filters and Grafana integration, and creates postmortem reports after incidents.
- **Exposes Prometheus metrics** on a configurable `/metrics` endpoint for integration with the observability stack.
- **Streams telemetry** — publishes metrics to Event Hub for real-time streaming and stores metric history with configurable retention (default 90 days).

**What it produces:** Health status summaries with per-service indicators, metric collections with timestamps and values, alert records with threshold info and acknowledgement status, incident records with ServiceNow/PagerDuty IDs, anomaly detections with confidence scores, capacity forecasts with scaling recommendations, postmortem reports with timeline and root cause, health dashboards, and Prometheus metrics.

**Connects to:** Analytics and Insights (provides health signals for portfolio dashboards and narrative generation), Release Deployment (provides environment health gates for deployment decisions), Approval Workflow (routes alerts and incidents for response automation), Continuous Improvement (health trends and incident data for process recommendations), OpenTelemetry/Prometheus observability stack, Azure Monitor, all services via `/healthz` endpoints.

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
