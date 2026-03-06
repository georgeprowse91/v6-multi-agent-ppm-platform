# Platform Description

This document is the canonical reference for the Multi-Agent PPM Platform's product definition. It covers the product vision, strategy, scope, requirements, user experience, methodology flows, governance, and template catalog.

**Owner:** Product Management
**Last reviewed:** 2026-03-01

---

## Contents

- [Product Strategy and Scope](#product-strategy-and-scope)
- [The Problem We Are Solving](#the-problem-we-are-solving)
- [What the Platform Is](#what-the-platform-is)
- [Product Scope](#product-scope)
- [Implementation Alignment](#implementation-alignment)
- [Core Value Proposition](#core-value-proposition)
- [Unique Differentiators](#unique-differentiators)
- [Requirements Specification](#requirements-specification)
- [Functional Requirements](#functional-requirements)
- [Non-Functional Requirements](#non-functional-requirements)
- [Success Metrics and Acceptance Criteria](#success-metrics-and-acceptance-criteria)
- [Personas and UX Guidelines](#personas-and-ux-guidelines)
- [Layout and Navigation](#layout-and-navigation)
- [Visual Style and Branding](#visual-style-and-branding)
- [Component Specifications](#component-specifications)
- [User Journeys and Stage Gates](#user-journeys-and-stage-gates)
- [Adaptive Process Flow](#1-adaptive-process-flow)
- [Predictive Process Flow](#2-predictive-process-flow)
- [Hybrid Process Flow](#3-hybrid-process-flow)
- [Templates and Methodology Catalog](#templates-and-methodology-catalog)

---

## Product Strategy and Scope

### The Problem We Are Solving

Every large organisation runs dozens -- sometimes hundreds -- of projects simultaneously. The teams responsible for governing those projects, programmes and portfolios spend most of their time doing the wrong things: copy-pasting data between spreadsheets and systems, chasing status updates by email, re-creating documents that already exist in another tool, and manually enforcing governance processes that are only written down somewhere in a SharePoint folder nobody visits.

The result is predictable. Projects run over budget. Milestones slip. Governance is applied inconsistently. Executives lack the real-time visibility they need to make good investment decisions. And delivery teams feel buried under administrative work that gets in the way of actually delivering.

This is not a people problem. It is a tooling and process problem. The tools organisations use were not designed to work together, and none of them were designed to think.

### What the Platform Is

The **Multi-Agent PPM Platform** is an AI-native project portfolio management workspace. It gives organisations a single, intelligent environment in which to manage the full lifecycle of every project, programme and portfolio -- from initial idea through to benefits realisation and lessons learned.

The platform does not replace the specialist tools your organisation already uses. Jira still tracks your development work. SAP still holds your financial data. Planview or Clarity still manages your resource capacity. What the platform does is sit above all of those systems and act as the thinking layer: it reads and writes to your tools, interprets your intent in natural language, enforces your governance processes, automates your routine work, and surfaces the right information at the right time to the right person.

At its heart, the platform is built around three ideas:

1. **Your methodology is your navigation.** Rather than giving users a generic menu of features, the platform turns your chosen project delivery approach -- whether that is predictive waterfall, agile adaptive, or a hybrid of the two -- into the actual navigation structure of the application. You always know where you are in the lifecycle, what you need to complete before moving forward, and what the platform expects of you.

2. **AI is the primary interface.** Users do not have to learn complex menus or know which agent to invoke. They simply describe what they need in plain English, and an orchestration layer routes that request to the right combination of specialist agents, assembles a coherent response, and presents it in the workspace.

3. **Agents are the workforce.** Behind the natural language interface is a network of 25 specialised AI agents, each responsible for a specific domain of project and portfolio management. They collaborate automatically, take direction from users, and can act autonomously on routine tasks -- freeing delivery teams to focus on work that requires human judgement. For full agent specifications, see [Readme](README.md).

### Product Scope

#### In Scope

The platform covers the full project and portfolio lifecycle:

- **Demand and intake** -- capturing, classifying, and routing project requests from any channel.
- **Business case and investment** -- generating business cases, modelling ROI, supporting funding decisions.
- **Portfolio strategy and optimisation** -- prioritising investments, capacity-constrained portfolio selection, scenario modelling.
- **Programme management** -- grouping related projects, managing cross-project dependencies, tracking benefits.
- **Project delivery** -- charter generation, scope management, scheduling, resource management, financial tracking, vendor procurement, quality assurance, risk and issue management, compliance, change management, release management, and knowledge management.
- **Platform operations** -- workflow automation, analytics and reporting, data synchronisation, system health monitoring.
- **Governance** -- stage-gate enforcement, approval workflows, audit logging, RBAC.
- **Connectors** -- bi-directional integration with enterprise systems across PPM, ERP, HRIS, collaboration, and GRC categories. For the full connector catalog, see [Readme](connectors/README.md).

#### Out of Scope

- Development of custom hardware or proprietary IoT devices beyond the platform's standard IoT connector.
- Changes to source-of-record systems (Planview, Jira, SAP, etc.) that the connectors integrate with.
- Custom ERP or HRIS configuration in client environments.

### Implementation Alignment

The repository contains a working implementation of the core execution stack: API gateway, orchestration service, workflow service, agent runtime, 14 FastAPI Python microservices, a React 18 web console with methodology navigation and assistant panel, and a React Native mobile application. The platform runs on PostgreSQL 15 and Redis 7, with Azure OpenAI providing LLM capabilities via LangChain.

For architecture details, see [Readme](architecture/README.md). For the cross-cutting solution index, see [Solution Index](solution-index.md). Validate any feature claims in commercial collateral against these references before using them in delivery commitments.

### Core Value Proposition

**For Delivery Teams:** Delivery teams spend less time on administrative work and more time on actual delivery. The platform's agents draft the documents, track the risks, reconcile the budgets and send the status updates that used to consume project managers' days. The methodology map makes clear what is expected at each stage. The AI assistant provides guidance on demand. The result is faster, more consistent delivery with less rework.

**For Portfolio Leaders:** Portfolio leaders gain real-time visibility across all initiatives without having to chase status reports. They can see which projects need intervention, where the portfolio is over-committed on resources, and whether the portfolio as a whole is aligned with organisational strategy. Scenario modelling allows them to evaluate trade-offs and communicate investment decisions with confidence.

**For Executives:** Executives see a portfolio health dashboard that gives them a clear, current, data-driven picture of the organisation's project investments. They can drill down into any initiative, see the latest financial performance, and understand the risk profile -- without needing to attend every steering committee or read every status report.

**For the Organisation:** At the organisational level, the platform creates a shared standard for how projects are delivered. Best practices are embedded in the methodology map. Governance is consistently enforced. Lessons learned are captured and made accessible. Over time, the platform's continuous improvement agents help the organisation become genuinely better at delivery -- not just more efficient at managing the same problems.

### Unique Differentiators

**Methodology as Navigation:** Unlike generic PPM tools that rely on static menus, this platform turns the methodology itself into the navigation mechanism. Users always know what step they are on and what deliverables are required. See [User Journeys and Stage Gates](#user-journeys-and-stage-gates) for the operational detail.

**AI-Native Architecture:** The AI assistant is not a bolt-on; it is the primary interface. Agents use large language models and machine-learning algorithms to interpret intent, generate content, optimise portfolios and predict outcomes. See [Readme](architecture/README.md) for technical depth.

**Modular Agents and Connector Marketplace:** Organisations can enable only the agents they need and connect to their existing tools. New agents can be added to support emerging use cases without rewriting core code. See [Readme](README.md) and [Readme](connectors/README.md).

**Embedded Governance and Compliance:** The platform embeds stage-gates, approval workflows, RBAC, audit trails and compliance checks into every process. It is designed to satisfy regulatory requirements such as Privacy Act 1988 (APPs), Australian ISM/PSPF and APRA CPS 234. See [Readme](README.md) for controls mapping and evidence guides.

**Continuous Improvement:** Built-in process mining and lessons-learned capture enable organisations to refine their methodologies over time and increase project success rates.

### Why This, Why Now

AI is transforming every knowledge-intensive profession, and project and portfolio management is no exception. The question is not whether AI will change the way organisations manage their investments and programmes -- it is whether organisations will lead that change or be overtaken by it.

The Multi-Agent PPM Platform represents a considered, production-ready answer to that question. It is not a single AI feature bolted onto an existing tool. It is an architecture built from the ground up around the idea that AI agents, working together and in concert with human judgement, can transform the quality and efficiency of project delivery.

For market data and research supporting this positioning, see [Platform Commercials](platform-commercials.md).

---

## Requirements Specification

This section defines the functional and non-functional requirements for the Multi-Agent PPM Platform. It serves as a source of truth for designers, developers, testers and stakeholders.

### Background and Context

The PPM software market is experiencing double-digit growth, and AI adoption in project management is accelerating but uneven. For full market data, research citations, and AI adoption statistics, see [Platform Commercials](platform-commercials.md).

The Multi-Agent PPM Platform addresses these challenges by orchestrating 25 specialised agents via a conversational AI assistant, embedding governance into methodology maps and integrating seamlessly with existing systems of record. The platform aims to reduce manual effort, improve decision-making and increase project success rates.

### Functional Requirements

#### 1. Demand Management and Intake

**Multi-Channel Intake:** The system shall capture new project requests via web forms, email, Slack/Teams bots and API submissions. It must support attachments and metadata such as requestor, business unit, and desired completion date. The Demand and Intake agent will classify requests by type (e.g., strategic initiative, operational improvement) using NLP and route them to appropriate reviewers.

**Duplicate Detection and Triage:** The agent shall detect duplicate or similar requests using semantic similarity and highlight them to reviewers for consolidation. It shall assess complexity and urgency to triage requests into fast-track or normal review queues.

**Pipeline Visualisation:** Users shall have a dashboard showing all pending requests by stage (e.g., draft, under review, approved, rejected). Filters by business unit, type, priority and methodology must be available.

**Methodology Recommendation:** Based on request attributes (size, complexity, risk), the agent shall recommend a suitable delivery methodology (Adaptive, Predictive, hybrid). Users can override the recommendation but must provide justification.

#### 2. Business Case and Investment Analysis

**Automated Business Case Generation:** Upon approval of an intake request, the system shall gather relevant data (e.g., scope, objectives, cost estimates, benefits, risks) and generate a draft business case document. Templates must be customisable by organisation.

**Cost-Benefit and ROI Modelling:** The agent shall perform financial analysis, including Net Present Value (NPV), Internal Rate of Return (IRR), payback period and benefit-cost ratio. It shall allow scenario modelling (best case, worst case, most likely) and Monte Carlo simulations to assess uncertainty.

**Investment Recommendation:** The system shall score each business case based on strategic fit, financial return and risk level, and recommend whether to proceed. It shall present a summary view to decision makers with recommended funding options.

**Approval Workflow Integration:** Business case approval shall integrate with the Approval Workflow agent, supporting multi-level approvals, delegation, escalation and audit logging.

#### 3. Portfolio Strategy and Optimisation

**Strategic Alignment Scoring:** The system shall map each initiative to strategic objectives and calculate alignment scores. Weightings for objectives (e.g., revenue growth, cost reduction, compliance) must be configurable.

**Prioritisation and Ranking:** The agent shall implement multi-criteria decision analysis algorithms (e.g., Analytic Hierarchy Process, weighted scoring) and constraint-based optimisation to rank projects based on benefits, costs, risks and capacity constraints.

**Capacity-Constrained Portfolio Optimisation:** The system shall solve capacity-constrained selection problems using genetic algorithms or multi-objective optimisation to recommend an optimal portfolio mix under budget and resource limits.

**Scenario Planning:** Users shall create what-if scenarios by adjusting budgets, constraints or strategic priorities. The system shall show how changes affect portfolio composition and performance metrics.

**Portfolio Health Dashboard:** Provide real-time analytics on portfolio value delivered, benefits realisation, budget utilisation, risk exposure and resource capacity.

#### 4. Program Management

**Program Definition:** Users shall create programs with associated vision statements, objectives, scope, benefits and KPIs. Programs group related projects for coordinated delivery.

**Cross-Project Dependency Management:** The agent shall visualise dependencies across projects within a program and alert program managers to potential conflicts and schedule impacts.

**Benefits Aggregation:** The system shall aggregate benefits across projects and track them against program-level goals, providing variance analysis when benefits slip.

**Program Roadmap and Milestones:** Visualise a high-level roadmap showing program phases, major milestones and key deliverables. Allow program managers to adjust schedules and reallocate resources based on changes.

**Synergy and Impact Analysis:** Identify opportunities for shared resources, consolidated procurement and process synergies across projects. Provide change impact analysis when altering program scope or timelines.

#### 5. Project Definition and Scope Management

**Project Charter Generation:** The system shall generate project charters capturing objectives, scope, stakeholders, assumptions, constraints and success criteria. Users can select templates and the agent shall pre-populate sections based on intake data.

**Scope and Requirements Management:** Provide tools to capture, categorise and prioritise requirements. Support change control processes for scope changes, including impact analysis on schedule, cost and resources.

**Work Breakdown Structure (WBS) Creation:** Automatically generate WBS from requirements or user inputs. Visualise WBS as hierarchical trees and allow drag-and-drop editing.

**Stakeholder and RACI Analysis:** Identify stakeholders and map responsibilities (Responsible, Accountable, Consulted, Informed). Provide conflict detection and send notifications to stakeholders for sign-off.

**Baseline Management:** Allow users to establish scope and WBS baselines, version them and compare actual progress against baselines.

#### 6. Project Lifecycle and Governance

**Lifecycle Models and Methodology Map:** The platform shall support multiple lifecycle models (Predictive phases, Adaptive sprints, hybrid) and render them as interactive maps in the UI. Each stage or sprint includes required tasks and documentation.

**Stage-Gate Enforcement:** The system shall enforce stage-gate criteria, preventing transitions to the next phase until required artefacts are completed and approvals obtained. Criteria are configurable per methodology and organisation.

**Health Scoring and Alerts:** Calculate project health scores based on schedule, cost, risk and resource indicators. Provide early-warning alerts when metrics fall below thresholds and recommendations for corrective actions.

**Lifecycle Dashboard:** Display a timeline of phases or sprints, stage-gate status, health metrics and outstanding tasks. Allow filtering by program, methodology and status.

#### 7. Schedule and Planning

**Schedule Generation:** Generate project schedules from WBS elements, estimate durations using historical data and machine-learning models, and assign resources. Support both Predictive Gantt charts and Adaptive sprint plans.

**Dependency and Critical Path Analysis:** Visualise task dependencies and highlight critical paths. Provide what-if analysis to assess the impact of changes on project end dates.

**Resource-Constrained Scheduling:** Incorporate resource availability and skill profiles when producing schedules. Identify resource over-allocations and recommend adjustments.

**Schedule Risk Analysis:** Run Monte Carlo simulations or advanced risk models to estimate schedule risk and generate confidence intervals for completion dates.

**Baseline and Variance Reporting:** Establish schedule baselines and track actual progress. Display variances and provide reasons (e.g., scope change, resource bottleneck).

#### 8. Resource and Capacity Management

**Resource Catalogue and Profiles:** Maintain a central repository of resources (people, equipment) with attributes such as skills, roles, cost rates and availability. Integrate with HRIS systems (e.g., Workday) to synchronise data.

**Demand vs. Capacity Planning:** Compare project resource demand against available capacity across teams and time periods. Identify bottlenecks and propose hiring or training plans.

**Allocation and Balancing:** Allow managers to allocate resources to tasks at the project, program and portfolio levels. Provide algorithms to suggest optimal allocations based on skills, availability and priority.

**Utilisation Reporting:** Display utilisation metrics by person, team and role. Highlight under-utilised or over-allocated resources and suggest corrective actions.

**Skills Development and Forecasting:** Forecast future skill shortages based on upcoming projects and recommend training or recruiting strategies.

#### 9. Financial Management

**Budgeting and Forecasting:** Define budgets at portfolio, program and project levels. Allocate funds across cost categories (labour, materials, overhead) and time periods. Use predictive models to forecast costs and cash flows.

**Cost Tracking and Variance Analysis:** Integrate with ERP systems (e.g., SAP, Oracle) to import actual costs and compare them against budgets. Provide variance analysis and explanations (e.g., scope change, rate increase).

**Financial Approvals and Controls:** Implement approval workflows for budget changes, expense approvals and contract authorisations. Enforce spending limits and segregation of duties with role-based permissions and audit trails.

**Multi-Currency and Tax Handling:** Support multiple currencies, conversion rates and tax rules. Provide roll-up views in the organisation's base currency.

**ROI and Benefits Realisation:** Track actual benefits realised against projected benefits in business cases. Provide dashboards showing ROI, NPV and other financial KPIs.

#### 10. Vendor and Procurement Management

**Vendor Catalogue and Contract Repository:** Store information about approved vendors, contracts, service-level agreements (SLAs) and pricing. Link contracts to projects and resources.

**Procurement Workflow:** Automate procurement processes including request for proposal (RFP), bid evaluation, vendor selection, contract negotiation and purchase order issuance. Integrate with procurement systems (e.g., Coupa, Ariba).

**Spend Management and Invoice Processing:** Track purchase orders, invoices and payments. Match invoices to purchase orders and contracts. Integrate with finance systems for payment processing.

**Vendor Performance Evaluation:** Collect performance data (delivery quality, timeliness, cost compliance) and calculate vendor scores. Use this data to inform vendor selection decisions and contract renewals.

**Risk and Compliance Checks:** Perform due diligence on vendors (e.g., financial health, sustainability, regulatory compliance) and enforce compliance with organisational policies.

#### 11. Quality Management

**Quality Planning:** Define quality standards, acceptance criteria and metrics for deliverables. Integrate templates for quality plans and checklists.

**Quality Assurance and Control:** Automate quality checks at predefined gates (e.g., code reviews, design reviews, inspections). Capture defects, assign remediation actions and track resolution.

**Continuous Improvement:** Analyse defect trends and process quality metrics to identify systemic issues. Recommend process improvements and training.

**Compliance and Certification:** Ensure that deliverables meet standards such as ISO 9001 or industry-specific regulations. Provide evidence and audit trails for certification.

#### 12. Risk and Issue Management

**Risk Identification and Assessment:** Provide tools to log risks with descriptions, probability, impact, triggers and mitigation actions. Use AI to suggest risk categories and generate similar risks based on historical data.

**Risk Quantification and Exposure:** Calculate risk exposure (e.g., Expected Monetary Value) and support Monte Carlo simulations for risk analysis. Prioritise risks based on exposure and highlight those requiring urgent action.

**Issue Tracking and Escalation:** Capture project issues, assign owners, set severity levels and track resolution progress. Integrate with ticketing systems if required.

**Risk and Issue Dashboard:** Provide a consolidated view of risks and issues across portfolios, programs and projects. Offer heat maps, bubble charts and trends.

**Alerts and Predictive Warnings:** Use machine-learning models to forecast potential risks (e.g., schedule slippage due to resource shortage) and send proactive alerts to stakeholders.

#### 13. Compliance and Regulatory Management

**Policy Catalogue and Controls:** Maintain a repository of regulatory and policy requirements (e.g., GDPR, Australian ISM/PSPF, Sarbanes-Oxley). Map requirements to processes and deliverables.

**Control Checks and Audit Trails:** Embed automated checks at stage-gates to ensure compliance. Capture evidence (e.g., approvals, testing results) and store audit trails.

**Data Classification and Access Controls:** Enforce classification levels (Public, Internal, Confidential, Restricted) and apply role-based access control (RBAC) and data-level security accordingly.

**Privacy and DLP:** Implement data loss prevention (DLP) rules to detect and prevent sensitive data exfiltration. Provide features to support data subject requests (access, erasure, portability).

**Compliance Reporting:** Generate reports for auditors and regulators, showing policy compliance status, audit logs and remediation actions.

**Specialised Industry Regulations:** Support HIPAA and FDA CFR 21 Part 11 compliance modules, including configurable audit trails, electronic signatures, and evidence capture aligned to each regulation.

#### 14. Change and Configuration Management

**Template and Methodology Management:** Store templates for charters, plans, reports and generate them on demand. Version control for methodologies (Adaptive, Predictive, hybrid) to accommodate organisational changes. Track usage and update history.

**Configuration Item (CI) Repository:** Maintain a catalogue of configuration items (workflows, connectors, agent configurations) with version numbers and dependencies.

**Impact Analysis and Assessment:** When a change is proposed (e.g., updating a workflow or template), the system shall identify affected agents, data flows and schedules. Provide simulation of the change impact before implementation.

**Change Approval and Deployment:** Use approval workflows to manage changes. Support staged rollouts (development, test, production) and rollback in case of issues. Integrate with release and deployment pipelines.

#### 15. Release and Deployment Management

**Release Planning and Scheduling:** Plan releases across agents and connectors. Create release calendars with cut-off dates, environments and stakeholders.

**Automated Build and Deployment:** Integrate with CI/CD pipelines to build, test and deploy agent packages and connectors. Support blue/green or canary deployments to minimise downtime.

**Rollback and Contingency Plans:** Provide mechanisms to roll back deployments in case of failures. Capture deployment logs and metrics for analysis.

**Release Readiness Checks:** Ensure that all quality, security and compliance gates are passed before promoting changes to production.

#### 16. Knowledge and Document Management

**Central Repository:** Provide a secure document repository for storing project charters, business cases, contracts, test plans, lessons learned, meeting notes and other artefacts. Support version control and search.

**Metadata and Classification:** Tag documents with metadata (project, program, category, confidentiality level) to enable filtering and retention rules. Integrate with data classification policies.

**In-Context Access:** Surface relevant documents directly within the canvas (e.g., show project charter in the charter generation view) and allow users to link documents to tasks and stage-gates.

**Lessons Learned and Knowledge Base:** Capture lessons learned at the end of stages or sprints. Categorise them by topic and make them searchable. Provide AI-powered recommendation of relevant lessons when similar situations arise.

**Document Retention and Disposal:** Enforce retention schedules based on classification. Support archival and secure disposal of documents.

**Real-Time Collaborative Editing:** Enable multiple users to co-edit documents simultaneously with live cursors, presence indicators and change tracking, using Operational Transform (OT) or CRDT-style merging strategies.

#### 17. Governance, Knowledge and Audit Pages

The following pages extend the product specification for governance-heavy workflows and knowledge retrieval. Each page aligns with the methodology-first navigation model and reuses the standard three-panel layout.

**Approvals Page:** A single workspace for pending approvals across portfolios, programs, projects and operational workflows. Consolidates items requiring review, shows required artefacts and stage-gate criteria, surfaces approval history, and provides contextual risk and impact summaries.

**Workflow Monitoring Page:** Monitors automated workflow executions across agents, connectors and approval pipelines with near-real-time status, bottleneck detection and intervention controls.

**Document Search Page:** Federated search across the knowledge repository, project artefacts and connected systems with AI-assisted semantic search, compliance tagging, and saved searches.

**Lessons Learned Page:** Structured capture, curation and application of lessons learned across projects and programs, with AI-driven recommendations for new initiatives.

**Audit Log Page:** Tamper-evident audit log for approvals, workflow runs, data changes and access events with exportable evidence packs and cryptographic hash verification.

#### 18. Integration and Device Data

**Connector Coverage:** Provide production-ready connectors for core enterprise systems (Planview, Jira, SAP, Workday, ServiceNow, Salesforce) and an IoT connector that ingests telemetry for asset-linked projects.

**Secure Data Exchange:** Support token-based authentication, scoped API credentials and event-driven sync for integrations, aligning with the platform's RBAC and audit logging standards.

#### 19. Continuous Improvement and Process Mining

**Process Mining and Discovery:** Analyse execution logs and user interactions to discover actual process flows. Compare them with prescribed methodologies and identify deviations or bottlenecks.

**Performance Metrics and Dashboards:** Provide KPIs for process efficiency (cycle time, lead time, rework), stage-gate compliance, and agent utilisation. Display trends over time.

**Recommendations and Action Plans:** Suggest corrective actions based on process analysis. Assign actions to stakeholders and track completion.

**Continuous Learning:** Incorporate lessons learned, audit findings and process mining insights into methodology updates and templates.

#### 20. Communications and Stakeholder Management

**Stakeholder Directory:** Maintain a directory of stakeholders with contact information, roles, interests and communication preferences. Integrate with identity systems.

**Communication Plans:** Define communication plans for projects and programs, specifying audiences, frequency, channels (email, Slack, Teams) and content templates.

**Notification and Alerts:** Provide automated notifications for upcoming stage-gates, overdue approvals, risk escalations and other events. Allow users to configure notification preferences.

**Meeting and Reporting Tools:** Integrate with calendar systems to schedule meetings. Generate status reports summarising progress, risks and financials.

**Stakeholder Sentiment Analysis:** Use natural language processing to analyse feedback from surveys or communications and detect sentiment trends.

#### 21. Analytics and Insights

**Dashboards and Reports:** Provide a library of dashboards (portfolio, program, project, resource, financial, risk) and allow custom report creation with interactive drill-down.

**Predictive Analytics and Forecasting:** Use machine-learning models to forecast schedule slippage, cost overruns, resource bottlenecks and risk events. Provide confidence intervals and scenario outputs.

**Benchmarking and KPIs:** Define standard KPIs and allow comparison across portfolios, industries and time periods.

**Data Visualisation and Export:** Offer charts (Gantt, burndown, histograms), tables and graphs. Allow export to Excel, PDF or other formats.

**Natural Language Insights:** Allow users to ask the AI assistant questions and generate narrative summaries explaining trends and anomalies.

#### 22. Data Synchronisation and Quality

**Bi-Directional Synchronisation:** Agents shall support reading from and writing to systems of record via connectors. Synchronisation modes (real-time, near-real-time, batch) must be configurable. Conflict resolution rules must be defined per data type.

**Data Quality Validation:** Implement validation rules (referential integrity, business rules, completeness, accuracy, consistency, timeliness) and quality metrics.

**Data Lineage and Auditing:** Track lineage of data from source systems through transformations to reports. Provide audit trails for CRUD operations.

**Caching and Performance Optimisation:** Use cache-aside strategies with TTL to improve performance and reduce API calls.

#### 23. Workflow and Process Engine

**Visual Workflow Designer:** Provide a drag-and-drop interface to design custom workflows. Users can define triggers, actions, conditions and tasks. Workflows can call agents and external APIs.

**Event-Driven Orchestration:** Support event-driven patterns. Events from systems of record or user actions trigger workflows and agent operations.

**State Management:** Maintain stateful information for long-running processes using durable storage. Ensure idempotency and error recovery.

**Monitoring and Logging:** Provide dashboards showing workflow executions, success/failure rates and latency. Allow users to replay, resume or roll back workflows.

#### 24. System Health and Monitoring

**Operational Metrics:** Collect and display metrics such as request rates, agent response times, error rates, resource utilisation and throughput.

**Distributed Tracing and Logging:** Implement distributed tracing to track request flows across agents and connectors. Centralise logs and enforce retention periods.

**Health Dashboards:** Provide dashboards for system health (uptime, memory usage, queue length) and business health (project success rates, cost variance).

**Self-Healing and Resilience:** Incorporate circuit breakers, retries and timeouts. Use horizontal auto-scaling to handle load spikes and maintain high availability.

**Incident Management and SLA:** Define incident categories, severity levels and response SLAs. Provide runbooks and automate notifications.

### Non-Functional Requirements

**Performance and Scalability:** The platform shall support thousands of concurrent users and manage hundreds of portfolios, programs and projects. Responses must be rendered within 2 seconds for UI interactions and 10 seconds for complex AI operations. The architecture shall scale horizontally.

**Availability and Resilience:** Ensure 99.9% uptime for critical services. Use redundancy across availability zones, load balancing and automatic failover.

**Security and Compliance:** Enforce SSO using SAML/OAuth, mutual TLS for agent-to-agent communication, and secret management via Vault. Apply RBAC, encryption in transit (TLS 1.3) and at rest (AES-256), WAF rules and DLP policies. Comply with GDPR, SOC 2, ISO 27001, Australian ISM/PSPF and industry-specific standards. Support audit logging and retention for at least 7 years.

**Extensibility and Modularity:** Design the platform as a collection of loosely coupled microservices and agents with well-defined interfaces. New agents or connectors can be added without affecting existing services.

**Usability and Accessibility:** Provide an intuitive, responsive web interface following WCAG 2.1. Support keyboard navigation and screen readers.

**Internationalisation and Localisation:** Support multiple languages and region-specific date/currency formats. Allow customisation of terminology.

### Success Metrics and Acceptance Criteria

**Adoption and Usage:** Target at least 70% of projects managed through the platform within the first year.

**User Satisfaction:** Target NPS > +40 and SUS > 80.

**Efficiency Gains:** Target 50% reduction in administrative work for project managers after six months.

**Portfolio Performance:** Target 20% increase in projects delivered on time and on budget.

**Integration and Data Quality:** Sync success rate >99%, data freshness <15 minutes, data quality scores >95%.

**Security and Compliance:** Zero critical incidents; all compliance reports passed without material findings.

### Dependencies and Assumptions

The platform relies on existing systems of record being available and accessible via APIs. Clients will provide necessary credentials and API access. Stakeholders will allocate time for requirements workshops, user testing and training. Regulatory requirements may vary by jurisdiction and compliance features will need to be configured accordingly.

---

## Personas and UX Guidelines

This section defines the platform's user personas, interaction patterns, and UI/UX design standards.

### Layout and Navigation

**Left Navigation Pane:** Displays the hierarchical methodology map (phases for Predictive or sprints for Adaptive) and provides quick access to major modules (Dashboard, Portfolio, Programs, Projects, Reports, Settings). The map highlights the current phase and upcoming stages. Collapsible sections allow users to focus on specific areas.

**Central Canvas:** The main workspace where users interact with agents and data. The canvas dynamically changes based on the selected phase or agent: for example, WBS tree with drag-and-drop for project definition, schedule Gantt chart, or business-case form. Users can add, resize or reorder cards. The canvas supports multi-select actions and context menus.

**Right Contextual Panel:** Shows details for the currently selected card or entity and hosts the conversational assistant. It surfaces hints, recommended actions, analytics and cross-references.

**Header:** Includes global search, notifications, user profile, and environment selection. Breadcrumbs indicate the current location.

#### Navigation Patterns

**Methodology Navigation:** Clicking on a stage in the methodology map updates the canvas and context panel. Stage gates require specific criteria before proceeding; the UI displays gate status (Not started, In progress, Complete) with tooltips explaining required artefacts.

**Universal Search:** Accessible via the header, it allows users to search across projects, tasks, documents and agents. Results are grouped by entity type with quick actions.

**Contextual Commands:** Right-click menus and action bars provide contextual commands relative to the selected card or entity.

### Visual Style and Branding

**Colour Palette:** Neutral base with accent colours aligned to the client's brand. Consistent colours for statuses (green for complete, amber for warning, red for overdue). Avoid using red and green together to support colour-blind accessibility.

**Typography:** Sans-serif font for clarity and readability with clear hierarchy through size, weight and colour.

**Spacing and Alignment:** Consistent margins and padding (8pt grid) for balanced layouts.

**Iconography:** Vector icons used sparingly for common actions. Simple and recognisable.

**Responsiveness:** Layouts adapt to different screen sizes. Left navigation collapses to a hamburger menu on narrow screens; cards rearrange into vertical stacks.

**Accessibility:** WCAG 2.1 guidelines: sufficient colour contrast, keyboard navigation, ARIA labels, and accessible tab order.

### Component Specifications

**Cards:** Primary visual container for discrete information. Each card includes title and status, key metrics with sparklines, contextual action buttons, and badge indicators.

**Tables and Lists:** Column sorting, filters, pagination, inline editing, sticky headers, and bulk action capability.

**Gantt and Timeline Views:** Interactive charts with drag-and-drop adjustments, critical path highlighting, grouping by resource or phase, zoom controls and baseline overlays. Adaptive mode switches to a sprint board.

**Forms and Wizards:** Multi-step wizards with progress indicators, real-time validation, contextual help, and dynamic fields.

**Dashboards and Reports:** Preconfigured dashboards for key personas with interactive charts and KPIs. Customisable layouts with drill-downs and export to Excel/PDF.

### Interaction with Agents

**Conversational Assistant:** Accessible via the context panel or a floating button. Accepts natural-language queries, suggests clarifying questions, summarises results, and triggers multi-agent workflows. Conversation history remains visible.

**Agent Notifications:** Proactive notifications for approval requests, risk alerts, and data quality issues. Notification centre with filtering and unread counts.

**Inline Recommendations:** Domain agents provide inline guidance (e.g., risk agent highlighting high-risk tasks, quality agent recommending additional tests). Recommendations include tooltips and accept/dismiss controls.

### Style Guide Reference

| Element | Specification |
|---|---|
| Primary Font | Open Sans (fallback: Arial, sans-serif) |
| Base Font Size | 14pt for body text |
| Heading Levels | H1: 24pt, H2: 20pt, H3: 16pt |
| Accent Colour | #0066CC (hyperlinks, call-to-action) |
| Neutral Colour | #F5F5F5 background, #333333 text |
| Border Radius | 4px for cards, inputs and buttons |
| Shadow | Subtle drop shadow (2px y, 4px blur) |

---

## User Journeys and Stage Gates

This section describes how the platform embeds Adaptive, Predictive and Hybrid methodologies into the user interface to guide users through stage-gate workflows and enforce governance.

### 1. Adaptive Process Flow

The Adaptive process is iterative, emphasising incremental delivery, sprint ceremonies and continuous refinement. The methodology map shows current and future sprints and allows users to navigate through initiation, release planning, sprint cycles and release delivery.

**Demand and Ideation:** A stakeholder submits a demand/proposal. The Demand and Intake Agent classifies the request and recommends the Adaptive methodology based on factors such as uncertainty and stakeholder expectations.

**Business Case and Approval:** The Business Case Agent crafts a lean business case emphasising iterative value delivery and minimum viable product (MVP). Approval is typically streamlined.

**Project Definition (Initiation):** The Project Definition Agent generates the Adaptive project charter and initial backlog. The methodology map highlights initiation with tasks such as product vision, initial backlog creation and team formation.

**Release Planning:** Users plan releases at a high level. Release goal definition, feature prioritisation and release roadmap are surfaced as discrete activities.

**Sprint Cycles:** Each sprint appears as an expandable node with sub-activities: sprint planning, daily development, sprint review and sprint retrospective. The Schedule and Planning Agent aids in sprint planning while the Approval Workflow Agent records acceptance via definition of done.

**Continuous Activities:** Backlog refinement, impediment tracking, stakeholder feedback and sprint dashboards are always accessible.

**Release and Deployment:** Release testing, deployment and release retrospective activities coordinate testing, deployment, and feedback for the next iterations.

**Closure and Lessons Learned:** Once releases meet stakeholder acceptance criteria, the project transitions to maintenance or closure. Knowledge is stored for continuous improvement.

#### Governance in Adaptive

- **Definition of Done (DoD) gates:** Each story or feature must meet agreed acceptance criteria. The Quality Management Agent validates DoD, test coverage and defect metrics.
- **Release readiness checks:** Before deploying, the platform verifies all planned sprints are completed, critical defects are resolved and stakeholder approvals are recorded.
- **Continuous Monitoring:** Velocity, burndown, defect density and risk exposure are monitored continuously with health dashboards and alerts.

### 2. Predictive Process Flow

The Predictive process is linear with discrete phases separated by formal stage gates: Initiating, Planning, Executing and Closing. Monitoring and controlling activities operate continuously.

**Demand and Business Case:** A demand triggers a comprehensive business case with total project ROI, cost-benefit analysis and long-term value. Multi-level approvals are coordinated by the Approval Workflow Agent.

**Initiating Phase:** Project charter, stakeholder register and preliminary scope baseline are created.

**Stage Gate 1 -- Charter Approval:** Formal gate reviewing the charter for completeness and alignment. Sign-offs from sponsors and the PMO are coordinated. If criteria are unmet, progression is blocked.

**Planning Phase:** Scope definition, WBS development, schedule development, resource and budget planning, quality planning, risk management plan and procurement plan. Domain agents generate detailed plans and baseline estimates.

**Stage Gate 2 -- Planning Approval:** All baseline plans must be approved. Criteria include scope completeness, cost and schedule baseline approval, risk register completeness and procurement approvals.

**Executing Phase:** Deliverable development, quality assurance and procurement execution. Agents monitor progress and update schedules, track testing and acceptance, and manage vendor engagements.

**Stage Gate 3 -- Execution Review (optional):** For large projects, additional gates may be configured for mid-project review.

**Closing Phase:** Final deliverable acceptance, contract closeout, lessons learned and project archive. The project cannot close until all deliverables are accepted, contracts settled and documentation archived.

**Monitoring and Controlling (Continuous):** Performance tracking, change control, risk monitoring and stakeholder management activities run in parallel throughout the lifecycle.

#### Governance in Predictive

Stage gates are evaluated by checking criteria and preventing phase transitions if conditions are not met. Users may either complete missing work, check status, or request an override requiring senior approval.

### 3. Hybrid Process Flow

Hybrid methodologies combine Adaptive and Predictive elements, allowing stage gates at major milestones while operating iteratively within phases.

**Methodology Selection:** The platform analyses the business case and recommends a hybrid approach when uncertainty exists alongside regulatory constraints.

**Initiation and Charter:** Formal charter and stakeholder analysis are prepared and approved through a stage gate.

**Planning and Release Framing:** High-level scope, budget and schedule are defined. Release planning outlines milestones and delivers value incrementally via sprints within each release.

**Iterative Development within Phases:** Each release is executed through sprints nested under the corresponding phase.

**Milestone Reviews:** Phase and release gates require validation of deliverables, stakeholder acceptance, and updated risk and financial assessments.

**Continuous Monitoring:** Both sprint-level metrics (velocity, burnup) and phase-level metrics (schedule variance, budget variance) are tracked.

**Closing and Hand-over:** Formal closing activities occur once all iterations and milestones are complete.

#### Governance in Hybrid

Gates exist at both the phase/release level and the sprint level. Sprint-level gates use DoD compliance; milestone gates use formal approval workflows. The assistant adapts prompts based on context.

### Best Practice Enforcement

Across all methodologies, the platform enforces governance through:

- **Interactive Methodology Map:** Both navigation and checklist. Steps cannot be arbitrarily skipped.
- **Agent-Driven Validation:** Continuous readiness validation for transitions. Missing approvals, incomplete registers and outstanding issues block progression.
- **Conversational Guidance:** Just-in-time recommendations based on the current step.
- **Monitoring Dashboards:** Composite health scores with root cause identification and corrective action proposals.
- **Publishing Workflow:** Agent outputs are reviewed and approved in canvases before writing back to systems of record.

---

## Templates and Methodology Catalog

This section provides a cross-methodology catalog of project management templates and the agents that produce or consume them.

### Shared Template Library

| Artefact | Purpose | Agent | Template Path |
|---|---|---|---|
| Demand intake request | Capture intake data for triage | Demand Intake | [Readme](templates/README.md) |
| Business case | Document investment rationale | Business Case | [Readme](templates/README.md) |
| Business case update report | Compare actuals vs plan | Business Case | [Readme](templates/README.md) |
| Product strategy canvas | Vision, market context, roadmap | Portfolio Optimisation | [Readme](templates/README.md) |
| ROI/NPV worksheet | Calculate ROI and NPV assumptions | Business Case | [Readme](templates/README.md) |
| Assumption log | Track project assumptions | Business Case, Risk Management | [Readme](templates/README.md) |
| Variance report | Track schedule/cost variance | Schedule Planning | [Readme](templates/README.md) |
| Executive dashboard status report | Health, decisions, value summary | Stakeholder Communications | [Readme](templates/README.md) |
| Milestone review | Formal gate or go/no-go review | Lifecycle Governance | [Readme](templates/README.md) |
| Risk report | Top risks and exposure trends | Risk Management | [Readme](templates/README.md) |
| Schedule risk analysis | Quantify schedule risk | Schedule Planning, Risk Management | [Readme](templates/README.md) |
| Quality report | Quality performance and defects | Quality Management | [Readme](templates/README.md) |
| Change request | Submit changes for approval | Change Control | [Readme](templates/README.md) |
| Change impact assessment | Analyse change impacts | Change Control | [Readme](templates/README.md) |
| Lessons learned register | Outcomes, root causes, recommendations | Continuous Improvement | [Readme](templates/README.md) |
| Scope baseline | Scope statement, WBS, dictionary | Scope Definition | [Readme](templates/README.md) |
| Project management plan | Integrate subsidiary plans | Lifecycle Governance | [Readme](templates/README.md) |
| Resource management plan | Resource estimation and acquisition | Resource Management | [Readme](templates/README.md) |
| Risk management plan | Risk governance and analysis | Risk Management | [Readme](templates/README.md) |
| Procurement management plan | Sourcing strategy and contracts | Vendor Procurement | [Readme](templates/README.md) |
| RACI matrix | Responsibilities and decision rights | Resource Management | [Readme](templates/README.md) |
| Communications plan | Stakeholder communications | Stakeholder Communications | [Readme](templates/README.md) |
| Stakeholder analysis and mapping | Identify and analyse stakeholders | Stakeholder Communications | [Readme](templates/README.md) |

### Methodology Variants

| Artefact | Adaptive | Predictive | Hybrid |
|---|---|---|---|
| Charter | | Project charter | Hybrid charter |
| Roles and responsibilities | Adaptive roles | Predictive roles | Hybrid roles |
| User story mapping | Yes | | |
| Backlog | Yes | | |
| Sprint plan | Yes | | Yes |
| Release plan | Yes | | Yes |
| Burndown | Yes | | |
| WBS | | Yes | |
| Schedule baseline | | Yes | |
| Risk register | | Yes | Yes |
| Milestone plan | | | Yes |
| Governance pack | | | Yes |
| Decision log | | | Yes |
| Closure report | | Yes | Yes |

For the complete set of template files, see [Readme](templates/README.md).

---

## Document Control

| Field | Details |
|---|---|
| Owner | Product Management |
| Review cycle | Quarterly |
| Last reviewed | 2026-03-01 |
| Status | Active |
