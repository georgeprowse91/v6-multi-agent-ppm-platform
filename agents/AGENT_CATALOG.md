# Agent Catalogue

This catalogue is generated from the agent README files under
`agents/**/*-agent/README.md`. Update the README content and rerun the
generator to refresh this file and the web UI metadata.

## Core Orchestration

### Intent Router Agent Specification ([`intent-router-agent`](core-orchestration/intent-router-agent/README.md))
- **Location:** [`agents/core-orchestration/intent-router-agent`](core-orchestration/intent-router-agent/README.md)
- **Purpose:**
  - Classifies user queries into one or more intents using an LLM-backed classifier with a deterministic keyword-based fallback. Enforces minimum confidence thresholds before routing, maps validated intents to downstream agent routes defined in `config/agents/intent-routing.yaml`, extracts query parameters (project/portfolio IDs, currency, amount, schedule focus), and emits audit events for all classification and fallback decisions.

### Response Orchestration Agent Specification ([`response-orchestration-agent`](core-orchestration/response-orchestration-agent/README.md))
- **Location:** [`agents/core-orchestration/response-orchestration-agent`](core-orchestration/response-orchestration-agent/README.md)
- **Purpose:**
  - Executes the multi-agent plan produced by the Intent Router, coordinating parallel and sequential agent calls. Aggregates responses into a single payload for the caller and owns orchestration-specific concerns such as retry logic, response caching, circuit breaking, and audit event emission. Does not decide which intents or agents to invoke.

### Approval Workflow Agent Specification ([`approval-workflow-agent`](core-orchestration/approval-workflow-agent/README.md))
- **Location:** [`agents/core-orchestration/approval-workflow-agent`](core-orchestration/approval-workflow-agent/README.md)
- **Purpose:**
  - Unified workflow and approval engine — orchestrates long-running workflows, approval chains, task inboxes, and process automation across the platform. Approvals are modelled as `approval_gate` steps within a shared workflow specification, giving every process the same execution engine, state persistence, audit trail, and monitoring infrastructure.

### Workspace Setup Agent Specification ([`workspace-setup-agent`](core-orchestration/workspace-setup-agent/README.md))
- **Location:** [`agents/core-orchestration/workspace-setup-agent`](core-orchestration/workspace-setup-agent/README.md)
- **Purpose:**
  - Manages project workspace initialisation and enforces a pre-write gate: no system-of-record write is permitted until connectors are enabled, authentication is complete, field mappings are verified, and all required external artefacts exist (Teams channels, SharePoint sites, Jira projects, Planview shells, etc.). Invoked after portfolio decisions and before delivery agents begin work.


## Delivery Management

### Scope Definition Agent Specification ([`scope-definition-agent`](delivery-management/scope-definition-agent/README.md))
- **Location:** [`agents/delivery-management/scope-definition-agent`](delivery-management/scope-definition-agent/README.md)
- **Purpose:**
  - Owns project definition artefacts through the approved scope baseline. Creates and maintains the project charter (objectives, constraints, success criteria), scope statement (in/out of scope, deliverables), WBS structure, requirements traceability matrix, stakeholder register, and RACI artefacts. Detects and reports scope creep against the established baseline.

### Lifecycle Governance Agent Specification ([`lifecycle-governance-agent`](delivery-management/lifecycle-governance-agent/README.md))
- **Location:** [`agents/delivery-management/lifecycle-governance-agent`](delivery-management/lifecycle-governance-agent/README.md)
- **Purpose:**
  - Owns project lifecycle state, phase transitions, and governance gate enforcement. Evaluates and records gate criteria before any phase change; escalates overrides to the Approval Workflow agent. Monitors project health, publishes health events, and produces dashboards and reports. Recommends and adapts delivery methodologies based on project signals.

### Schedule Planning Agent Specification ([`schedule-planning-agent`](delivery-management/schedule-planning-agent/README.md))
- **Location:** [`agents/delivery-management/schedule-planning-agent`](delivery-management/schedule-planning-agent/README.md)
- **Purpose:**
  - Converts WBS into a schedule with task sequencing, dependencies, and milestone identification. Estimates durations using AI and historical signals. Calculates CPM metrics (early/late dates, critical path, total duration). Produces schedule optimisation, what-if analysis, and Monte Carlo risk simulations. Manages schedule baselines and variance tracking for timeline governance, and provides sprint planning artefacts when requested.

### Resource Management Agent Specification ([`resource-management-agent`](delivery-management/resource-management-agent/README.md))
- **Location:** [`agents/delivery-management/resource-management-agent`](delivery-management/resource-management-agent/README.md)
- **Purpose:**
  - Manages the resource pool (people and equipment), capacity calendars, and allocations. Intakes resource demand, matches skills to open assignments, and routes approval requests for over-capacity or constrained resources to the Approval Workflow agent.

### Financial Management Agent Specification ([`financial-management-agent`](delivery-management/financial-management-agent/README.md))
- **Location:** [`agents/delivery-management/financial-management-agent`](delivery-management/financial-management-agent/README.md)
- **Purpose:**
  - Owns financial execution for in-flight portfolios, programs, and projects. Manages budget baselines, cost tracking, forecasts, variance analysis, earned value management (EVM), and profitability reporting. Integrates with ERP systems to reconcile funding and actuals, supports multi-currency conversions, and publishes finance events to the service bus for downstream consumers.

### Vendor Procurement Agent Specification ([`vendor-procurement-agent`](delivery-management/vendor-procurement-agent/README.md))
- **Location:** [`agents/delivery-management/vendor-procurement-agent`](delivery-management/vendor-procurement-agent/README.md)
- **Purpose:**
  - Manages vendor selection, evaluation, procurement requests, contract management, and invoice processing. Supports AI-based RFP generation and proposal scoring, ML-based vendor ranking and recommendations, and third-party risk/sanctions screening. Integrates with procurement connectors (SAP Ariba, Coupa, Oracle Procurement, Dynamics 365) and delegates approval decisions to the Approval Workflow agent.

### Quality Management Agent Specification ([`quality-management-agent`](delivery-management/quality-management-agent/README.md))
- **Location:** [`agents/delivery-management/quality-management-agent`](delivery-management/quality-management-agent/README.md)
- **Purpose:**
  - Owns quality planning, test management, defect tracking, and quality analytics across delivery workstreams. Creates and manages quality plans, acceptance criteria, test cases/suites, execution tracking, coverage reporting, defect logs, trend analysis, and root cause analysis. Produces quality dashboards and reports; does not triage or close defects from other agents directly.

### Risk Management Agent Specification ([`risk-management-agent`](delivery-management/risk-management-agent/README.md))
- **Location:** [`agents/delivery-management/risk-management-agent`](delivery-management/risk-management-agent/README.md)
- **Purpose:**
  - Owns the end-to-end risk and issue lifecycle: identification, assessment, scoring, prioritisation, mitigation planning, and ongoing monitoring across projects, programs, and portfolios. Maintains a central risk register with probability/impact scoring, trigger definitions, and mitigation plans. Produces quantitative outputs (Monte Carlo, sensitivity analysis) and qualitative mitigation guidance. Publishes risk events (`risk.triggered`, `risk.created`, `risk.updated`) for downstream governance and escalation.

### Compliance Governance Agent Specification ([`compliance-governance-agent`](delivery-management/compliance-governance-agent/README.md))
- **Location:** [`agents/delivery-management/compliance-governance-agent`](delivery-management/compliance-governance-agent/README.md)
- **Purpose:**
  - Manages regulatory frameworks, controls, evidence, and audit packages across projects/programs/portfolios. Monitors regulatory updates and notifies stakeholders. Conducts compliance assessments and control testing, manages policy definitions, prepares and executes audit packages, and verifies release compliance signals from delivery events. Produces compliance dashboards and reports.


## Operations Management

### Change Control Agent Specification ([`change-control-agent`](operations-management/change-control-agent/README.md))
- **Location:** [`agents/operations-management/change-control-agent`](operations-management/change-control-agent/README.md)
- **Purpose:**
  - Handles change request intake, classification, and risk/impact assessment. Coordinates approval workflows and maintains full change audit trails. Manages CMDB/CI registration, baselines, and dependency visualisation. Gates change implementation against staging/automated tests and triggers rollback when required. Publishes change events and metrics to the event bus and notifies affected stakeholders.

### Release Deployment Agent Specification ([`release-deployment-agent`](operations-management/release-deployment-agent/README.md))
- **Location:** [`agents/operations-management/release-deployment-agent`](operations-management/release-deployment-agent/README.md)
- **Purpose:**
  - Owns release planning, readiness assessment (go/no-go), deployment orchestration, environment management, rollback, and post-deployment verification across dev/test/stage/prod environments. Integrates with approvals, scheduling, environment reservation, configuration management, CI/CD pipelines, monitoring, analytics, and documentation publishing to provide end-to-end release execution governance.

### Knowledge Management Agent Specification ([`knowledge-management-agent`](operations-management/knowledge-management-agent/README.md))
- **Location:** [`agents/operations-management/knowledge-management-agent`](operations-management/knowledge-management-agent/README.md)
- **Purpose:**
  - Owns the knowledge and document lifecycle across the portfolio: ingesting from users, agent outputs, and connected repositories (Confluence, SharePoint, Git); normalising metadata; enforcing schema validation and retention; generating summaries, tags, and entity extractions; and maintaining knowledge graph relationships (projects, programs, risks, decisions, lessons learned). Provides keyword and semantic search, access-controlled retrieval, and knowledge recommendations.

### Continuous Improvement Agent Specification ([`continuous-improvement-agent`](operations-management/continuous-improvement-agent/README.md))
- **Location:** [`agents/operations-management/continuous-improvement-agent`](operations-management/continuous-improvement-agent/README.md)
- **Purpose:**
  - Owns continuous improvement and process mining for operational workflows. Ingests execution event logs, discovers as-is process models, checks conformance against designed processes, detects bottlenecks and deviations, and generates improvement recommendations and backlog items. Tracks benefit realization for implemented improvements and shares best practices with the Knowledge Management agent.

### Stakeholder Communications Agent Specification ([`stakeholder-communications-agent`](operations-management/stakeholder-communications-agent/README.md))
- **Location:** [`agents/operations-management/stakeholder-communications-agent`](operations-management/stakeholder-communications-agent/README.md)
- **Purpose:**
  - Manages the stakeholder register, engagement profiles, and influence/interest classification. Builds communication plans tied to portfolio and project updates. Generates, schedules, and sends outbound messages across channels (email, Teams, Slack, SMS, push notifications, portal). Collects feedback and sentiment, tracks engagement, coordinates events/meetings, and produces comms reports. Delegates approval of outbound communications to the Approval Workflow agent.

### Analytics Insights Agent Specification ([`analytics-insights-agent`](operations-management/analytics-insights-agent/README.md))
- **Location:** [`agents/operations-management/analytics-insights-agent`](operations-management/analytics-insights-agent/README.md)
- **Purpose:**
  - Provides portfolio-level analytics, dashboards, reporting, and narrative insights for project health, KPI tracking, and scenario analysis. Ingests cross-domain events (schedule, deployment, risk, quality, resource) and computes KPIs from event history. Orchestrates the Azure analytics stack (Synapse, Data Lake, Data Factory) and supports Power BI report embedding and natural language narrative generation.

### Data Synchronisation Agent Specification ([`data-synchronisation-agent`](operations-management/data-synchronisation-agent/README.md))
- **Location:** [`agents/operations-management/data-synchronisation-agent`](operations-management/data-synchronisation-agent/README.md)
- **Purpose:**
  - Governs data synchronisation quality for mastered PPM entities (project, resource, vendor, financial, etc.) flowing between source systems and the canonical model. Validates inbound payloads, maps them to canonical schemas, enforces data-quality thresholds before propagation, detects duplicates and conflicts, and applies configurable resolution strategies (last-write-wins, timestamp-based, authoritative-source, manual). Emits audit, lineage, and telemetry events for downstream analytics and monitoring.

### System Health Agent Specification ([`system-health-agent`](operations-management/system-health-agent/README.md))
- **Location:** [`agents/operations-management/system-health-agent`](operations-management/system-health-agent/README.md)
- **Purpose:**
  - Monitors platform system health via Azure Monitor, Application Insights, and Log Analytics. Exposes a Prometheus `/metrics` endpoint and delivers telemetry to Azure Event Hub. Routes high-priority alerts to PagerDuty and OpsGenie, triggers auto-scaling via Logic App/Azure Automation webhooks based on CPU/memory/queue-depth thresholds, and creates/updates ServiceNow incidents. Supports anomaly detection via Azure Anomaly Detector and configurable health probes across all platform services.


## Portfolio Management

### Demand Intake Agent Specification ([`demand-intake-agent`](portfolio-management/demand-intake-agent/README.md))
- **Location:** [`agents/portfolio-management/demand-intake-agent`](portfolio-management/demand-intake-agent/README.md)
- **Purpose:**
  - Captures new demand requests from any intake channel and normalises them into a single demand record. Validates minimum intake criteria and schema compliance, categorises demand (project, change request, issue, idea), flags likely duplicates, provides a demand pipeline view for screening and routing, and notifies requesters that intake is queued.

### Business Case Agent Specification ([`business-case-agent`](portfolio-management/business-case-agent/README.md))
- **Location:** [`agents/portfolio-management/business-case-agent`](portfolio-management/business-case-agent/README.md)
- **Purpose:**
  - Supports the creation, evaluation, and lifecycle management of business cases for proposed projects and initiatives. Structures financial projections, benefit realisation plans, strategic alignment assessments, and risk summaries. Provides business case templates and scoring to inform portfolio prioritisation and investment decisions.

### Portfolio Optimisation Agent Specification ([`portfolio-optimisation-agent`](portfolio-management/portfolio-optimisation-agent/README.md))
- **Location:** [`agents/portfolio-management/portfolio-optimisation-agent`](portfolio-management/portfolio-optimisation-agent/README.md)
- **Purpose:**
  - Prioritises portfolio candidates using multi-criteria scoring (strategic alignment, ROI, risk, resource feasibility, compliance). Optimises portfolio composition against constraints (budget ceiling, resource capacity, risk appetite, minimum alignment). Runs scenario analysis to compare outcomes and generate rebalancing recommendations. Emits portfolio prioritisation events and audit records for traceability.

### Program Management Agent Specification ([`program-management-agent`](portfolio-management/program-management-agent/README.md))
- **Location:** [`agents/portfolio-management/program-management-agent`](portfolio-management/program-management-agent/README.md)
- **Purpose:**
  - Owns program setup and coordination across multiple constituent projects. Generates integrated roadmaps, tracks inter-project dependencies, aggregates benefits, coordinates shared resources, identifies synergies, analyses change impact, monitors program health, and optimises program schedules. Acts as the program-level orchestrator, pulling data from delivery agents (schedule, resource, financial, risk, quality, lifecycle) to compute cross-project insights and outcomes.
