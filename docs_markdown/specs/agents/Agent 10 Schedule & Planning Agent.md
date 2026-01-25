# Agent 10: Schedule & Planning Agent Specification

## Purpose

The Schedule & Planning Agent constructs and manages project timelines, transforms work breakdown structures (WBS) into schedules, maps task dependencies and performs critical path analysis. It supports both predictive (Waterfall) and adaptive (Agile) planning by estimating task durations, identifying risks and generating what‑if scenarios to optimise delivery.

## Key Capabilities

**WBS to schedule conversion:** Translates hierarchical WBS into detailed schedules with start/end dates and dependencies.

**Task duration estimation:** Estimates task durations using historical data, AI models and team velocity, adjusting for complexity and skill levels.

**Dependency mapping:** Captures finish‑to‑start (FS), start‑to‑start (SS), finish‑to‑finish (FF) and start‑to‑finish (SF) dependencies between tasks.

**Critical path method (CPM) analysis:** Calculates the critical path, float and total project duration.

**Resource‑constrained scheduling:** Plans schedules that respect resource availability and skill constraints.

**Schedule risk analysis:** Performs Monte Carlo simulations to assess schedule risk and generate probabilistic completion dates.

**Milestone tracking & deadline management:** Tracks key milestones and deadlines, highlighting upcoming dates and potential delays.

**Schedule optimisation & what‑if scenarios:** Recommends adjustments (parallelising tasks, adding resources) to minimise delays and provides what‑if scenario analysis.

**Baseline management & variance tracking:** Locks schedules as baselines and measures variances against actuals.

## AI Technologies

**AI‑based duration estimation:** Utilises machine‑learning models trained on historical task performance to predict durations, factoring in team experience and complexity.

**Predictive delay detection:** Monitors progress and uses trend analysis to predict delays before they fully materialise.

**Schedule optimisation algorithms:** Applies genetic algorithms and resource‑constrained project scheduling (RCPSP) to optimise schedules.

**Monte Carlo simulation:** Generates probabilistic forecasts for completion dates and risk analysis.

**Integration with AI predictive models:** Incorporates data on resource availability, risk factors and past performance to refine predictions and recommendations.

## Methodology Adaptations

**Agile:** Supports sprint planning, capacity planning and velocity‑based forecasting. Produces burndown charts and recommends sprint backlog composition.

**Waterfall:** Generates Gantt charts and critical path diagrams, performs resource leveling and manages phase‑based baselines.

**Hybrid:** Combines sprint‑level planning within phase‑based frameworks; supports fixed milestones with iterative delivery.

## Dependencies & Interactions

**Project Definition & Scope Agent (Agent 8):** Receives approved WBS and requirements to convert into a schedule.

**Resource & Capacity Management Agent (Agent 11):** Supplies resource calendars, skills and availability to inform scheduling and resource‑constrained planning.

**Financial Management Agent (Agent 12):** Provides cost rates for activities and monitors schedule variance impacts on budget.

**Risk Management Agent (Agent 15):** Provides risk data used in Monte Carlo simulations and delay predictions.

**Program Management Agent (Agent 7):** Receives schedule information to build program roadmaps and identifies cross‑project dependencies.

**Approval Workflow Agent (Agent 3):** Manages baseline approval and schedule change approvals.

**Stakeholder Communication Agent (Agent 21):** Disseminates schedule reports and updates to stakeholders.

## Integration Responsibilities

**Project Scheduling Tools:** Sync schedules with Microsoft Project, Smartsheet or similar tools; import and export Gantt charts.

**Jira/Azure DevOps:** For Agile projects, pull sprint data (backlog, story points) and update sprint commitments.

**Planview/Clarity PPM:** Maintain master schedules and portfolio timelines; propagate baseline updates.

**Calendar Systems:** Sync milestone dates and resource calendars with Outlook or Google Calendar for visibility.

**Event Bus:** Publish events like schedule.baseline.locked, schedule.delay and subscribe to changes (scope.updated, resource.reallocated).

## Data Ownership

**Project schedules & timelines:** Maintains start/end dates, durations and sequencing of tasks.

**Task dependencies:** Stores relationship types and dependency logic.

**Critical path data:** Holds computed critical paths and slack times.

**Schedule baselines & forecasts:** Owns baseline versions and forecasted completion dates.

**Task effort estimates & actuals:** Collects estimates, actual durations and variances for continuous improvement.

## Key Workflows

**Schedule Creation from WBS (Waterfall):** When a schedule is requested, the agent retrieves the WBS, estimates durations using AI models and team velocity, prompts users to define dependencies and generates a network diagram. It runs critical path analysis to calculate project duration and baseline dates and produces a Gantt chart for user review and approval.

**Sprint Planning (Agile):** At the start of each sprint, the agent collects backlog items, team velocity and capacity, recommends a set of user stories that fit within capacity and displays the proposed sprint backlog for adjustment. It generates a burndown chart and tracks progress daily.

**Delay Prediction & Early Warning:** The agent monitors task progress and compares actual completion against expected durations. Using predictive models, it identifies tasks that are behind and estimates potential delays, alerting the user with recommended corrective actions (adding resources, descope tasks, etc.).

**What‑If Analysis:** Users can ask “What if I add another developer?” or “What if we shift these tasks?”; the agent recalculates the schedule under new assumptions and displays differences in completion dates and resource usage.

**Baseline Management:** After approval, the agent locks the schedule as a baseline and tracks variances. Change requests to schedule (e.g., adding new tasks) trigger baseline updates and require approval via the Change & Configuration Agent.

## UI/UX Design

**Timeline Canvas:** A Gantt-style interactive timeline displays tasks, dependencies and milestones. Users can drag tasks to adjust dates, link dependencies visually and zoom in/out for different time horizons. Critical path tasks are highlighted in red.

**Schedule Builder Panel:** Guides users through WBS import, duration estimation and dependency definition with conversational prompts and forms. Presents AI‑estimated durations with confidence intervals and allows user overrides.

**Sprint Planning Board:** For Agile projects, a planning board shows backlog items with story points. Users can drag items into the sprint, and the board displays capacity usage and velocity trends.

**Early Warning Alerts:** Alert cards in the assistant notify users of predicted delays or schedule risks, with recommended mitigation actions and links to run what‑if analyses.

**Baseline Indicator:** A badge on the schedule indicates whether it is in baseline mode. When changes occur, unsaved changes are marked, and users are prompted to re‑baseline through approval.

## Configuration Parameters

**Estimation Model Parameters:** Configuration of the duration estimation model (e.g., training data range, feature weights) and default adjustment factors for new teams or technologies.

**Dependency Types & Defaults:** Define allowable dependency types and default lags/leads for certain task categories.

**Scheduling Constraints:** Maximum working hours per day, allowable resource over‑allocation thresholds, non‑working days/holidays calendars.

**Risk Thresholds:** Trigger levels for early warnings (e.g., tasks >70% of duration with <50% completion).

**Baseline Approval Rules:** Conditions under which baseline changes require formal approval vs. auto‑accept.

## Azure Implementation Guidance

**Compute & Orchestration:** Implement scheduling logic as Azure Functions for on‑demand operations (e.g., creating schedules) and Azure Durable Functions for long‑running monitoring and early warning workflows.

**Data Storage:** Store schedule data, dependencies and baselines in Azure SQL Database or Cosmos DB (for hierarchical task structures). Use Azure Cache for Redis to cache frequently accessed schedules.

**AI Services:** Train duration estimation and delay prediction models in Azure Machine Learning or Azure Databricks. Use Azure Synapse Analytics to analyse historical project performance data.

**Integration:** Connect to Microsoft Project, Jira, Smartsheet and calendar systems via Logic Apps and connectors. Use Event Grid for event‑driven updates.

**Visualization:** Host interactive timeline and board components as web modules in the UI layer; use Power BI Embedded for schedule reporting and dashboards.

**Security:** Use Managed Identities to access external systems; store credentials in Key Vault. Implement RBAC to control who can create, edit or approve schedules.

**Monitoring:** Instrument functions with Application Insights and stream metrics to the System Health & Monitoring Agent. Monitor resource utilisation and schedule creation durations.

## Security & Compliance

Enforce access control so only authorised project managers and schedulers can modify schedules or baselines.

Maintain an immutable record of baseline versions and changes for audit and governance. Integrate with the Compliance & Security Agent for retention policies.

Protect sensitive calendar data (e.g., employee availability) by encrypting in transit and at rest.

## Performance & Scalability

**Data Caching:** Cache AI estimation results for similar tasks to reduce repeated computation.

**Parallel Processing:** Use parallelism in schedule optimisation and Monte Carlo simulation to accelerate scenario analysis.

**Event‑Driven Scaling:** Trigger early warning evaluations only when progress updates occur or at defined intervals to avoid unnecessary computation.

**Load Balancing:** Scale out functions across multiple instances when processing multiple project schedules concurrently.

## Logging & Monitoring

Log each schedule creation, update, baseline locking and variance calculation. Include user actions and timestamps for traceability.

Monitor prediction accuracy of duration estimates and early warning models; retrain as necessary based on feedback.

Expose metrics (e.g., number of schedules created, average estimation error, number of alerts generated) to the Analytics & System Health Agents.
