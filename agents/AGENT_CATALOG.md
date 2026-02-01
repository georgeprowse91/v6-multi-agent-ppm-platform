# Agent Catalogue

This catalogue enumerates the domain agents in `agents/**/agent-*`, summarizing their
capabilities and notable dependencies to help new maintainers understand scope and
integration points. Capabilities are sourced from the `Key Capabilities` sections in
agent implementations (or the agent class docstring when a `Key Capabilities` section
is not present). Dependencies list the notable integration/services referenced by the
agent code and are not exhaustive.

## Core orchestration

### Agent 01: Intent Router (`agent-01-intent-router`)
- **Location:** `agents/core-orchestration/agent-01-intent-router`
- **Capabilities:**
  - NLP-based intent classification
  - Query disambiguation
  - Multi-intent detection
  - Agent routing and prioritization
- **Notable dependencies:** LLM client, prompt registry, YAML routing config, Pydantic validation.

### Agent 02: Response Orchestration (`agent-02-response-orchestration`)
- **Location:** `agents/core-orchestration/agent-02-response-orchestration`
- **Capabilities:**
  - Multi-agent query planning
  - Parallel and sequential execution
  - Response aggregation
  - Timeout and fallback management
  - Result caching
- **Notable dependencies:** web search utilities, HTTP client, observability metrics/tracing, event bus.

### Agent 03: Approval Workflow (`agent-03-approval-workflow`)
- **Location:** `agents/core-orchestration/agent-03-approval-workflow`
- **Capabilities:**
  - Role-based approval routing and multi-level approval chains
  - Delegation management and escalation handling
  - Human-in-the-loop approvals with audit trail tracking
  - Approval notifications and subscription preferences
- **Notable dependencies:** notification service, analytics/event bus clients, data-sync status store, HTTP client.

## Portfolio management

### Agent 04: Demand Intake (`agent-04-demand-intake`)
- **Location:** `agents/portfolio-management/agent-04-demand-intake`
- **Capabilities:**
  - Multi-channel intake (email, web forms, Slack/Teams)
  - Automatic categorization using NLP
  - Duplicate detection via semantic similarity
  - Preliminary triage and screening
  - Pipeline visualization
- **Notable dependencies:** embeddings + vector search, Naive Bayes classifier, notification service.

### Agent 05: Business Case & Investment (`agent-05-business-case-investment`)
- **Location:** `agents/portfolio-management/agent-05-business-case-investment`
- **Capabilities:**
  - Business case generation using configurable templates
  - Cost-benefit and ROI analysis (NPV, payback period, TCO)
  - Scenario modelling and sensitivity analysis
  - Comparative analysis against historical projects
  - Investment recommendations with confidence levels
  - Market analysis integration
- **Notable dependencies:** data connectors, forecasting model, embeddings + vector search, optional ERP/CRM/market clients.

### Agent 06: Portfolio Strategy & Optimization (`agent-06-portfolio-strategy-optimisation`)
- **Location:** `agents/portfolio-management/agent-06-portfolio-strategy-optimisation`
- **Capabilities:**
  - Portfolio prioritization using multi-criteria decision analysis
  - Strategic alignment scoring
  - Capacity-constrained optimization
  - Risk/reward balancing
  - Scenario planning and what-if analysis
  - Portfolio rebalancing recommendations
  - Investment mix optimization
- **Notable dependencies:** embeddings + vector search, database storage connector.

### Agent 07: Program Management (`agent-07-program-management`)
- **Location:** `agents/portfolio-management/agent-07-program-management`
- **Capabilities:**
  - Program definition & roadmap planning
  - Inter-project dependency tracking
  - Benefits aggregation across projects
  - Cross-project resource coordination
  - Synergy identification and optimization
  - Program-level change impact analysis
  - Program governance & reporting
- **Notable dependencies:** LLM client, database storage connector, event bus.

## Delivery management

### Agent 08: Project Definition & Scope (`agent-08-project-definition-scope`)
- **Location:** `agents/delivery-management/agent-08-project-definition-scope`
- **Capabilities:**
  - Project charter generation
  - Scope management with WBS
  - Requirements management and traceability
  - Scope baseline management
  - Stakeholder analysis & RACI matrices
  - Requirements validation & verification
- **Notable dependencies:** approval workflow agent, embeddings + vector search, document/project management connectors, web search utilities.

### Agent 09: Project Lifecycle & Governance (`agent-09-lifecycle-governance`)
- **Location:** `agents/delivery-management/agent-09-lifecycle-governance`
- **Capabilities:**
  - Project phase management and transitions
  - Methodology selection and adaptation
  - Phase gate definition and enforcement
  - Project health scoring and monitoring
  - State transitions and approvals
  - Governance compliance monitoring
  - Dashboard generation
  - Health metric ingestion from domain agents
- **Notable dependencies:** workflow orchestration engine, monitoring client, AI model service, external sync service.

### Agent 10: Schedule & Planning (`agent-10-schedule-planning`)
- **Location:** `agents/delivery-management/agent-10-schedule-planning`
- **Capabilities:**
  - WBS to schedule conversion
  - Task duration estimation using AI and historical data
  - Dependency mapping (FS, SS, FF, SF)
  - Critical path method (CPM) analysis
  - Resource-constrained scheduling
  - Schedule risk analysis and Monte Carlo simulation
  - Milestone tracking and deadline management
  - Schedule optimization and what-if scenarios
  - Baseline management and variance tracking
- **Notable dependencies:** scenario engine, AI model services (including Azure ML/Databricks), analytics + cache clients, external sync clients.

### Agent 11: Resource & Capacity (`agent-11-resource-capacity`)
- **Location:** `agents/delivery-management/agent-11-resource-capacity`
- **Capabilities:**
  - Centralized resource pool management
  - Demand intake and approval routing
  - Skill matching and intelligent search
  - Capacity planning and forecasting
  - Scenario modeling and what-if analysis
  - Role-based vs named assignments
  - Cross-project resource management
  - HR and timesheet system integration
  - Alerts and notifications for over-allocation
- **Notable dependencies:** forecasting model, calendar + database connectors.

### Agent 12: Financial Management (`agent-12-financial-management`)
- **Location:** `agents/delivery-management/agent-12-financial-management`
- **Capabilities:**
  - Budget creation and baseline management
  - Cost tracking and accruals
  - Forecasting and re-forecasting
  - Variance and trend analysis
  - Multi-currency and tax handling
  - Financial approvals integration
  - Profitability and ROI analysis
  - Financial compliance and auditability
  - Reporting and dashboards
- **Notable dependencies:** forecasting model, ERP + database connectors, classification model.

### Agent 13: Vendor & Procurement (`agent-13-vendor-procurement`)
- **Location:** `agents/delivery-management/agent-13-vendor-procurement`
- **Capabilities:**
  - Vendor registry and onboarding
  - Procurement request intake and processing
  - RFP/RFQ generation and quote management
  - Vendor selection and scoring
  - Contract and agreement management
  - Purchase order creation and approval
  - Invoice receipt and reconciliation
  - Vendor performance monitoring
  - Compliance and audit support
- **Notable dependencies:** LLM client, document storage connectors, web search utilities.

### Agent 14: Quality Management (`agent-14-quality-management`)
- **Location:** `agents/delivery-management/agent-14-quality-management`
- **Capabilities:**
  - Quality planning and metric definition
  - Test management and execution
  - Defect and issue tracking
  - Review and audit management
  - Quality dashboards and reporting
  - Continuous improvement and root cause analysis
  - Compliance and standards management
- **Notable dependencies:** classification model, calendar/document/database connectors.

### Agent 15: Risk & Issue Management (`agent-15-risk-issue-management`)
- **Location:** `agents/delivery-management/agent-15-risk-issue-management`
- **Capabilities:**
  - Risk identification and capture
  - Risk classification and scoring
  - Risk prioritization and ranking
  - Mitigation and response planning
  - Trigger and threshold monitoring
  - Risk reporting and dashboards
  - Integration with other disciplines
  - Monte Carlo simulation
- **Notable dependencies:** LLM client, GRC + documentation connectors, ML prediction service, web search utilities.

### Agent 16: Compliance & Regulatory (`agent-16-compliance-regulatory`)
- **Location:** `agents/delivery-management/agent-16-compliance-regulatory`
- **Capabilities:**
  - Regulatory requirement management
  - Control library and mapping
  - Compliance assessment and gap analysis
  - Control assignment and testing
  - Policy management and versioning
  - Audit preparation and management
  - Compliance dashboards and reporting
  - Regulatory change monitoring
- **Notable dependencies:** LLM client, GRC + document connectors, notification service, web search utilities.

## Operations management

### Agent 17: Change & Configuration (`agent-17-change-configuration`)
- **Location:** `agents/operations-management/agent-17-change-configuration`
- **Capabilities:**
  - Change request intake and classification
  - Impact assessment and risk evaluation
  - Approval workflow orchestration
  - Configuration management database (CMDB)
  - Baseline and version control
  - Change implementation tracking
  - Change audit and history
  - Configuration visualization and dependency mapping
- **Notable dependencies:** classification model, ITSM + document/database connectors.

### Agent 18: Release & Deployment (`agent-18-release-deployment`)
- **Location:** `agents/operations-management/agent-18-release-deployment`
- **Capabilities:**
  - Release planning and scheduling
  - Release readiness assessment and go/no-go checks
  - Deployment orchestration across environments
  - Environment management and configuration tracking
  - Release approvals and gating
  - Change and incident coordination
  - Release documentation and communication
  - Deployment metrics and reporting
- **Notable dependencies:** calendar, documentation publishing, database connectors.

### Agent 19: Knowledge & Document Management (`agent-19-knowledge-document-management`)
- **Location:** `agents/operations-management/agent-19-knowledge-document-management`
- **Capabilities:**
  - Document repository and lifecycle management
  - Knowledge classification and taxonomy
  - Semantic search and discovery
  - Document summarization and extraction
  - Knowledge graph and linking
  - Lessons learned and best practices
  - Collaborative editing and reviews
  - Access control and permissions
- **Notable dependencies:** document management connectors, embeddings + vector search, classification model.

### Agent 20: Continuous Improvement & Process Mining (`agent-20-continuous-improvement-process-mining`)
- **Location:** `agents/operations-management/agent-20-continuous-improvement-process-mining`
- **Capabilities:**
  - Process discovery and visualization
  - Bottleneck and deviation detection
  - Root cause analysis and recommendations
  - Improvement backlog management
  - Benefit realization tracking
  - Benchmarking and best practices
  - Improvement culture enablement
- **Notable dependencies:** event bus, state store (no external connectors required by default).

### Agent 21: Stakeholder & Communications (`agent-21-stakeholder-comms`)
- **Location:** `agents/operations-management/agent-21-stakeholder-comms`
- **Capabilities:**
  - Stakeholder register and profiling
  - Stakeholder classification and segmentation
  - Communication plan creation
  - Message generation and scheduling
  - Feedback collection and sentiment analysis
  - Event and meeting coordination
  - Communication tracking and analytics
  - Stakeholder engagement dashboards
- **Notable dependencies:** calendar integration, notification service.

### Agent 22: Analytics & Insights (`agent-22-analytics-insights`)
- **Location:** `agents/operations-management/agent-22-analytics-insights`
- **Capabilities:**
  - Data aggregation and modeling
  - Interactive dashboards and visualizations
  - Self-service analytics and ad hoc reporting
  - Predictive and prescriptive analytics
  - Scenario analysis and what-if modeling
  - Narrative generation
  - KPI and OKR management
  - Data governance and lineage
  - Portfolio health aggregation from lifecycle events
- **Notable dependencies:** scenario engine, metrics catalog, health recommendations, lineage masking utilities.

### Agent 23: Data Synchronisation & Quality (`agent-23-data-synchronisation-quality`)
- **Location:** `agents/operations-management/agent-23-data-synchronisation-quality`
- **Capabilities:**
  - Master data management (MDM)
  - Data mapping and transformation
  - Event-driven synchronization
  - Conflict detection and resolution
  - Duplicate detection and merging
  - Data quality and validation
  - Audit and lineage tracking
  - Synchronization monitoring
- **Notable dependencies:** database connector helpers, observability tracing.

### Agent 24: Workflow & Process Engine (`agent-24-workflow-process-engine`)
- **Location:** `agents/operations-management/agent-24-workflow-process-engine`
- **Capabilities:**
  - Process definition and modeling
  - Workflow execution and orchestration
  - Event-driven triggers
  - Human task management
  - Dynamic workflow adaptation
  - Process versioning and rollback
  - Monitoring and analytics
  - Exception handling and compensation
- **Notable dependencies:** observability tracing, event bus.

### Agent 25: System Health & Monitoring (`agent-25-system-health-monitoring`)
- **Location:** `agents/operations-management/agent-25-system-health-monitoring`
- **Capabilities:**
  - Resource monitoring (compute, memory, storage, network)
  - Application and agent monitoring
  - Log and trace collection
  - Alerting and incident management
  - Anomaly detection and predictive maintenance
  - Dashboarding and reporting
  - Root cause analysis and diagnostics
  - Capacity planning and scaling recommendations
- **Notable dependencies:** observability metrics/tracing, analytics client.

### Agent 25: Analytics Insights (`agent-25-analytics-insights`)
- **Location:** `agents/operations-management/agent-25-analytics-insights`
- **Capabilities:**
  - Aggregated KPI and forecasting delivery (inherits Agent 22 capabilities)
  - Extended KPI coverage for schedule, cost, program, quality, compliance, and system health
  - Metrics ingestion and trend reporting
- **Notable dependencies:** inherits Agent 22 analytics stack; extends KPI definitions in the Agent 25 implementation.
