# Agent 7: Program Management Agent Specification

## Purpose

The Program Management Agent coordinates groups of related projects (programs) to achieve shared strategic objectives and realise synergies. It manages inter‑project dependencies, plans integrated roadmaps and monitors program health, ensuring that benefits across multiple projects are delivered coherently.

## Key Capabilities

**Program definition & roadmap planning:** Creates and maintains program structures, defining constituent projects, milestones and overarching goals.

**Inter‑project dependency tracking:** Identifies and manages dependencies among projects within a program (e.g., shared components, prerequisite deliverables).

**Benefits aggregation:** Aggregates benefits across projects to understand overall program value and track benefit realisation at the program level.

**Cross‑project resource coordination:** Coordinates resource allocation across projects to avoid conflicts and optimise utilisation.

**Synergy identification:** Detects opportunities for re‑use of components, shared services, vendors or infrastructure across projects, reducing duplication and cost.

**Program‑level change impact analysis:** Evaluates how changes in one project affect other projects and the overall program schedule and benefits.

**Program governance & reporting:** Provides status dashboards, consolidated reports and risk escalations for program managers and executives.

## AI Technologies

**Dependency graph analysis:** Uses graph algorithms to map and analyse inter‑project dependencies, identify critical paths across the program and assess cascading effects of delays.

**Synergy detection:** Applies similarity algorithms to identify shared components, technologies or resources across projects, recommending consolidation opportunities.

**Cross‑project optimisation:** Optimises shared resource allocation to minimise bottlenecks and maximise utilisation.

**Program health prediction:** Uses machine‑learning models to predict program outcomes based on constituent project health indicators.

**Natural language generation (NLG):** Generates program status reports and executive summaries in clear, concise language.

## Methodology Adaptations

**Agile Programs:** Coordinates release trains and cross‑team dependencies; emphasises iteration alignment and program increment planning.

**Waterfall Programs:** Manages phase alignment, integrated master schedules and formal gate reviews across projects.

**Hybrid Programs:** Combines iterative releases for some components with phase‑based schedules for others; tracks benefits realisation continuously.

## Dependencies & Interactions

**Portfolio Strategy & Optimization Agent (Agent 6):** Receives program definitions and provides strategic context and prioritisation.

**Project Definition & Scope Agent (Agent 8):** Supplies project charters, scope statements and WBS for each constituent project.

**Schedule & Planning Agent (Agent 10):** Provides individual project schedules and critical paths; receives updates when program‑wide rescheduling is required.

**Resource & Capacity Management Agent (Agent 11):** Supplies resource availability and receives coordination directives for cross‑project allocations.

**Financial Management Agent (Agent 12):** Provides budget status for each project and aggregates program financials.

**Risk & Quality Agents (Agents 14‑15):** Provide risk and quality metrics for program health prediction.

**Stakeholder Communication Agent (Agent 21):** Disseminates program status reports to stakeholders.

## Integration Responsibilities

**Planview/Clarity PPM:** Sync program structures, milestones and dependencies.

**Jira/Azure DevOps:** Map epics and features to program initiatives and retrieve progress information.

**BI & Reporting Platforms:** Feed program dashboards and KPIs for executive reporting.

**Event Bus:** Subscribe to events from project‑level agents (schedule.delay, scope.changed) and publish program‑level events (program.roadmap.updated, program.risk.alert).

## Data Ownership

**Program structures & relationships:** Defines which projects belong to each program and their interdependencies.

**Program roadmaps:** Integrated schedules showing milestones, releases and dependencies across projects.

**Cross‑project dependencies:** Maintains data on dependencies and shared components.

**Program benefits & outcomes:** Stores aggregated benefits, cost savings and realised outcomes.

## Key Workflows

**Program Roadmap Creation:** Upon request, the agent identifies constituent projects, queries each project's schedule and dependencies from the Schedule & Planning Agent and constructs an integrated program roadmap with milestones, dependency arrows and shared components highlighted. The roadmap is presented in a visual canvas where users can modify alignment and share synergy notes.

**Cross‑Project Dependency Management:** When a delay or change occurs in one project (e.g., schedule.delay event), the agent analyses cascading effects across dependent projects. It proposes mitigation options (parallelise tasks, crash schedules, accept delay) and routes decisions to program managers via the assistant.

**Synergy & Benefit Analysis:** Periodically scans projects within the program to identify opportunities for shared components or vendor consolidation. Generates recommendations to reuse services or coordinate procurement, quantifying potential cost savings.

**Program Health Monitoring:** Aggregates health metrics from project lifecycle, schedule, financial and risk agents to produce a composite program health score. Alerts program managers to trends requiring intervention (e.g., declining velocity across projects).

## UI/UX Design

**Program Dashboard:** A central dashboard presents the program roadmap, highlighting timelines, dependencies and benefits. Users can drill into constituent project details or adjust scheduling directly on the timeline.

**Dependency Graph View:** Visualises inter‑project dependencies using a graph layout. Users can highlight critical paths, filter by dependency type (technical, resource, deliverable) and explore impact scenarios.

**Synergy Insights Panel:** Displays identified synergies and recommended actions, including shared components and combined vendor contracts.

**Health & Benefits Cards:** Summarises program health (schedule, budget, risk) and aggregated benefits, with indicators for attention required.

## Configuration Parameters

**Dependency Types & Weights:** Define types of dependencies (finish‑to‑start, shared resource, technical) and their impact weighting on schedule risk.

**Benefit Aggregation Rules:** Configure how individual project benefits roll up to program‑level benefits (sum, average, weighted by strategic value).

**Resource Coordination Policies:** Set priorities for resource allocation across projects and escalation rules for conflicts.

**Synergy Detection Thresholds:** Minimum similarity or shared component usage required to trigger synergy recommendations.

**Health Score Formula:** Weighting of schedule, budget, risk and quality metrics in composite program health score.

## Azure Implementation Guidance

**Compute & Orchestration:** Implement program logic as Azure Durable Functions to coordinate long‑running operations (e.g., roadmap generation, dependency analysis). Use Azure Functions for event handlers reacting to schedule or scope changes.

**Data Storage:** Store program structures, roadmaps and dependencies in Azure Cosmos DB (graph API) to enable efficient queries. Benefits and aggregated metrics can be stored in Azure SQL Database or Synapse.

**AI & Analytics:** Use Azure ML to train and run program health prediction models; use Cognitive Services for summarising program status reports.

**Integration:** Connect to Planview, Jira and Azure DevOps via Logic Apps or custom connectors to fetch schedules and update program data. Use Event Grid to subscribe to project events and publish program updates.

**Visualization:** Render interactive dashboards via front‑end frameworks hosted in Azure App Service or integrated with existing UI components. Use Power BI Embedded for program analytics.

**Security:** Secure program data using RBAC and row‑level security; store credentials in Azure Key Vault; ensure encryption at rest and in transit.

**Monitoring:** Track function executions, latency and error rates using Application Insights. Stream logs to the System Health & Monitoring Agent for consolidated observability.

## Security & Compliance

Enforce access controls so that only program managers and authorised stakeholders can view cross‑project data and benefits.

Record all changes to program structures, dependencies and roadmaps; maintain audit trails for compliance and governance.

Ensure that shared resource allocations respect organisational segregation of duties and HR policies.

Collaborate with the Compliance & Security Agent to confirm that program processes adhere to regulatory requirements.

## Performance & Scalability

Pre‑compute baseline dependency graphs and roadmaps to reduce computation time during interactive sessions.

Use asynchronous, event‑driven architecture to handle updates from multiple projects concurrently without blocking user interactions.

Employ caching of program health scores and synergy suggestions for quick retrieval.

Scale out Durable Functions across multiple instances when managing numerous programs; partition program data by portfolio or business unit.

## Logging & Monitoring

Log all program events (roadmap creation, dependency changes, mitigation decisions) to the central logging system.

Capture execution metrics for dependency analysis and synergy detection algorithms to tune performance.

Provide real‑time monitoring of program health and resource conflicts via integration with the System Health & Monitoring Agent.
