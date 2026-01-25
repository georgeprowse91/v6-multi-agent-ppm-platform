# Agent 9: Project Lifecycle & Governance Agent Specification

## Purpose

The Project Lifecycle & Governance Agent manages the progression of projects through their lifecycle stages, enforces methodology‑specific governance gates and continuously monitors project health. It ensures compliance with selected methodologies (Agile, Waterfall or Hybrid), provides phase transition approvals and presents a unified health dashboard for each project.

## Key Capabilities

**Project phase management:** Controls transitions through lifecycle phases (Initiate → Plan → Execute → Monitor → Close) and sprints or iterations.

**Methodology selection & adaptation:** Configures lifecycle stages based on project methodology and adapts navigation, gating and documentation accordingly.

**Phase gate definition & enforcement:** Defines criteria for each phase gate and ensures required artefacts and approvals are complete before allowing transition.

**Project health scoring:** Aggregates metrics from schedule, financial, resource, risk and quality agents to compute composite health scores and identify at‑risk projects.

**State transitions & approvals:** Automates state changes upon meeting gate criteria and routes approvals to appropriate stakeholders.

**Governance compliance monitoring:** Continuously checks compliance with organisational policies and regulatory requirements across phases.

**Project dashboard generation:** Presents comprehensive dashboards showing lifecycle stage, health indicators, pending actions and upcoming gates.

## AI Technologies

**Adaptive methodology recommendation:** Suggests the most appropriate methodology (Agile, Waterfall or Hybrid) based on project characteristics and historical outcomes.

**Phase transition readiness scoring:** Utilises machine‑learning models to predict success probability of transitioning to the next phase, highlighting readiness gaps.

**Predictive project success analysis:** Forecasts likelihood of on‑time and on‑budget delivery by analysing historical project data and current metrics.

**Automated health dashboard generation:** Creates dashboards with anomaly detection and trending insights across multiple data sources.

**Pattern recognition:** Detects early warning signals such as declining velocity or budget burn anomalies.

## Methodology Adaptations

**Agile:** Manages sprint cycles, iteration reviews, release planning and daily stand‑ups. Supports continuous health monitoring and flexible phase transitions.

**Waterfall:** Manages sequential phases with formal gates; requires baseline approvals and formal sign‑off at each stage.

**Hybrid:** Combines iterative and sequential phases, balancing agility with stage‑gate governance.

## Dependencies & Interactions

**Project Definition & Scope Agent (Agent 8):** Supplies charters, WBS and requirements; receives requests to generate missing artefacts during phase transitions.

**Schedule & Planning Agent (Agent 10):** Provides schedule baselines, critical path status and variance metrics; receives triggers for schedule creation during planning.

**Resource & Capacity Management Agent (Agent 11):** Supplies utilisation and allocation metrics for health scoring.

**Financial Management Agent (Agent 12):** Provides cost baselines, actuals and variance for health scoring.

**Risk Management Agent (Agent 15):** Supplies risk scores and mitigation status for health scoring.

**Quality Assurance Agent (Agent 14):** Provides quality metrics, defect density and gate readiness for transitions.

**Approval Workflow Agent (Agent 3):** Orchestrates approvals for phase gates and overrides.

**Compliance & Security Agent (Agent 16):** Provides compliance gap status before transitions.

## Integration Responsibilities

**Planview/Clarity PPM:** Read and update project metadata, lifecycle state and methodology configuration.

**Jira/Azure DevOps:** Retrieve sprint data, sprint burndown and release information for Agile projects.

**Task & Workflow Tools:** Integrate with Monday.com or Asana for task-level status and gating criteria.

**Event Bus:** Subscribe to events from domain agents and publish transitions (project.transitioned, phase.gate.blocked).

## Data Ownership

**Project lifecycle states & history:** Maintains current phase, history of transitions and reasons for delays or overrides.

**Phase gate criteria & results:** Stores criteria definitions and evaluation outcomes for each phase.

**Project health metrics & scores:** Calculates and stores composite health scores and underlying metrics.

**Methodology configurations:** Holds configuration for selected methodology (stages, sprints, gates).

**Dashboard configurations:** Defines which metrics appear on dashboards and custom thresholds.

## Key Workflows

**Project Initiation:** When the portfolio approves a project for initiation, this agent creates the project record, sets the initial state to “Initiating”, selects the recommended methodology and loads the corresponding methodology map into the UI. It triggers the Project Definition Agent to generate the charter and monitors for charter approval.

**Phase Gate Enforcement:** When a user attempts to transition between phases, the agent checks gate criteria (e.g., scope baseline approved, schedule baselined, budget approved, risk register complete). If criteria are unmet, it blocks the transition and provides specific guidance and options such as completing missing activities, checking approval status or requesting an override.

**Project Health Monitoring:** Continuously collects metrics from domain agents (schedule SPI, financial CPI, risk scores, quality metrics and resource utilisation). It calculates composite health scores, identifies primary concerns and alerts users with recommended corrective actions. Users can request what‑if analyses (e.g., adding resources, descope features) directly via the assistant.

**Methodology Adjustment:** Periodically analyses project performance and suggests adjustments (e.g., switching from Waterfall to Hybrid for projects experiencing requirement volatility). Updates the methodology configuration accordingly and triggers appropriate agent activations or deactivations.

## UI/UX Design

**Lifecycle Map:** Displays the selected methodology as a navigable map in the left panel. Each stage is colour‑coded by status (e.g., completed, in progress, blocked). Clicking a stage reveals gating criteria and associated artefacts.

**Gate Checklist Panel:** When a user attempts a phase transition, a modal or side panel shows the gate criteria and their status (✓ met, ✗ missing). Users can click links to complete missing tasks or request an override.

**Health Dashboard:** Presents a composite health score with sub‑metrics (schedule, cost, risk, quality, resource). Visual indicators (green, yellow, red) quickly convey health. Drill‑down links allow users to view underlying data and recommended actions.

**Alert Feed:** Alerts for blocked gates, health concerns or methodology recommendations appear in the assistant panel. Users can take action (e.g., assign tasks, schedule meetings) directly from the alert.

## Configuration Parameters

**Gate Criteria Definitions:** Configurable checklists for each phase by project type and methodology, including required documents and approval signatories.

**Health Score Weights:** Weighting of schedule, cost, risk, quality and resource metrics in composite health calculation.

**Monitoring Frequency:** Frequency of health monitoring (e.g., hourly, daily) and thresholds for triggering alerts.

**Override Policies:** Rules for when PMO or executive override is permitted (e.g., risk tolerance levels, budget thresholds).

**Methodology Selection Rules:** Criteria for recommending Agile vs. Waterfall vs. Hybrid based on project size, complexity and stakeholder engagement.

## Azure Implementation Guidance

**Compute:** Use Azure Durable Functions to manage stateful workflows for project initiation, phase transitions and health monitoring. Maintain project state in Azure durable entities.

**Data Storage:** Store lifecycle states, gate criteria, health scores and methodology configuration in Azure Cosmos DB or Azure Table Storage for scalable, low‑latency access.

**AI Models:** Host readiness scoring and success prediction models in Azure Machine Learning. Use Azure Cognitive Services for summarising health insights.

**Integration:** Connect to Planview, Jira/Azure DevOps, Monday.com and other systems via Logic Apps or custom API connectors. Use Event Grid to publish and listen for lifecycle events.

**Security:** Implement role‑based access to lifecycle controls and ensure that phase transitions cannot be performed by unauthorised users. Store secrets in Key Vault.

**Monitoring:** Use Application Insights for function telemetry and integrate with the System Health & Monitoring Agent for end‑to‑end observability.

## Security & Compliance

Enforce segregation of duties by requiring specific roles (e.g., Project Manager, PMO Director) for approvals and overrides.

Maintain audit logs of all state transitions, gate evaluations and overrides for governance and regulatory compliance.

Integrate with the Compliance & Security Agent to ensure that required controls (e.g., compliance gaps) are addressed before transitions.

Handle personally identifiable information (PII) and sensitive project data in accordance with data privacy regulations, encrypting at rest and in transit.

## Performance & Scalability

Use event‑driven architecture to process updates asynchronously and avoid blocking user interactions.

Cache gate criteria and health calculation results to reduce repeated computation when data has not changed.

Scale out monitoring functions to handle large portfolios of concurrent projects.

## Logging & Monitoring

Log every phase transition attempt, gate evaluation result and health score calculation. Include user identity and timestamps.

Track performance metrics (latency of gate checks, health score computation) and error rates via Application Insights and System Health Agent.

Provide aggregated logs and dashboards for auditors and PMO via the Analytics Agent and System Health Agent.
