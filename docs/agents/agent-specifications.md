# Agent System Design

**Purpose:** Canonical catalog of all 25 specialised AI agents in the platform. Replaces the individual per-agent files in `solution-overview/agents/` as the single reference for agent purpose, behaviour, interfaces, and connections.
**Audience:** Product management, solution architects, AI/ML engineers, integration engineers, and reviewers.
**Owner:** Architecture Lead / Product Management
**Last reviewed:** 2026-02-20
**Related docs:** [platform-architecture-overview.md](platform-architecture-overview.md) · [../01-product-definition/requirements-specification.md](../01-product-definition/requirements-specification.md) · [../03-delivery-and-quality/acceptance-and-test-strategy.md](../03-delivery-and-quality/acceptance-and-test-strategy.md)

> **Migration note:** Consolidates all 25 individual agent files from `solution-overview/agents/` on 2026-02-20. The individual files are deprecated (see deprecation banners added to each). Use this document as the single authoring surface for agent specifications.

---

## Agent Summary Table

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

## Why this design

Two deliberate architectural changes shape the current agent catalog:

### The Approval Workflow agent as unified orchestration authority

Approvals are a specialised workflow pattern — a human decision step with routing, deadlines, escalation, and an immutable outcome record. The Approval Workflow agent is the platform's single canonical orchestration authority for long-running workflows. Every multi-step process — including approvals, automated task sequences, retry/compensation flows, and event-driven process automation — is defined and executed through one agent with a unified execution record and audit trail. Approval steps are represented as a first-class workflow step type (`approval_gate`) within the `ppm.workflow/v1` specification.

**Operational benefits:**
- One workflow definition language and one execution engine for all structured processes.
- One task inbox for human tasks and approvals, reducing context switching for users.
- One monitoring view for all workflow and approval activity.
- One audit trail covering the full lifecycle of every process, including embedded approvals.
- Simplified governance: every process (including approvals) follows the same versioning, retry, and compensation policies.

### Adding the Workspace Setup agent

Before any delivery agent can write to a system of record (Jira, Planview, SAP, SharePoint, Teams), a project workspace must exist and be correctly configured. Without a governed setup phase, downstream agents encounter connectivity failures, permission errors, and missing field mappings that disrupt delivery.

The Workspace Setup agent introduces a mandatory "setup wizard" phase between the portfolio decision and the start of project delivery. It ensures that:
- An internal workspace exists with the correct folder structure and canvas views.
- All required connectors are enabled, authenticated, and have validated permissions.
- External artefacts (Teams channels, SharePoint sites, Jira projects, Planview shells) are provisioned or linked.
- The selected methodology lifecycle map and organisational template defaults are applied.

The agent publishes a `workspace.setup.completed` event that the Lifecycle Governance agent uses as a gate — no project can progress past initiation until workspace setup is complete. This eliminates a class of downstream failures and gives project teams confidence that their tools are ready before they begin work.

### Integration service taxonomy

Agents interact with external systems through a set of shared integration services defined in `agents/common/connector_integration.py`. The taxonomy below reflects the corrected classification following the Agent-Connector Usage Analysis review:

| Service | Responsibility | Connectors |
| --- | --- | --- |
| **DocumentManagementService** | Document CRUD, metadata, publishing (SharePoint, Confluence) | SharePoint, Confluence |
| **DocumentationPublishingService** | Thin facade over DocumentManagementService adding Confluence-first publish with SharePoint fallback | Confluence (primary), SharePoint (fallback) |
| **ERPFinanceService** (alias `ERPIntegrationService`) | Financial data sync — GL, cost centres, journal entries | SAP, Oracle, NetSuite, Dynamics 365 |
| **HRISService** | HR data sync — employees, org structure, resource capacity | Workday, SuccessFactors, ADP |
| **ProjectManagementService** | Project/task CRUD, schedule sync | Planview, MS Project, Jira, Azure DevOps, Smartsheet |
| **ITSMIntegrationService** | Incident, change, and service request management | ServiceNow, Jira Service Management, BMC Remedy |
| **GRCIntegrationService** | Governance, risk, and compliance record management | ServiceNow GRC, RSA Archer |
| **NotificationService** | Multi-channel notifications — email, Teams, Slack, SMS, push | SMTP/SendGrid, Teams, Slack, Twilio, Azure Notification Hubs |
| **CalendarIntegrationService** | Calendar event CRUD and availability checks | Outlook, Google Calendar |
| **DatabaseStorageService** | Persistent agent data storage | Azure SQL, Cosmos DB, local JSON |
| **MLPredictionService** | Classification, forecasting, anomaly detection | Azure ML |

**Key changes from the original taxonomy:**
- **Workday reclassified:** Moved from `ERPIntegrationService` to the new `HRISService`. The ERP service now covers finance-only systems (SAP, Oracle, NetSuite, Dynamics 365).
- **DocumentationPublishingService marked as facade:** It delegates to `DocumentManagementService` and adds Confluence as a primary publishing target. It is not a separate storage layer.
- **ConnectorWriteGate added:** All services should check the write gate before external writes. The gate enforces: connector configured + connected, approval present if policy requires, dry-run passed if required, idempotency key generated, and audit entry emitted.
- **Governed connector runtime for Data Synchronisation:** The Data Synchronisation agent now exposes a `governed_connector_write()` method that routes all writes through `ConnectorWriteGate` rather than directly instantiating connectors.

#### Agent-to-service usage

| Agent | Primary services | Optional services |
| --- | --- | --- |
| workspace-setup-agent | DocumentManagementService, ProjectManagementService, NotificationService, DatabaseStorageService | CalendarIntegrationService |
| approval-workflow-agent | NotificationService, DatabaseStorageService | CalendarIntegrationService |
| data-synchronisation-agent | DatabaseStorageService, ConnectorWriteGate (governed runtime) | — |
| financial-management-agent | ERPFinanceService, DatabaseStorageService, NotificationService | — |
| resource-management-agent | HRISService, DatabaseStorageService | CalendarIntegrationService |
| risk-management-agent | GRCIntegrationService, DocumentManagementService, DocumentationPublishingService, MLPredictionService, DatabaseStorageService | — |
| release-deployment-agent | DocumentationPublishingService, DatabaseStorageService, CalendarIntegrationService | — |

---

## Agent Specifications


---

# the Intent Router agent — Intent Router

**Category:** Core Orchestration
**Role:** Platform Dispatcher

---

## What This Agent Is

The Intent Router is the first point of contact for every user interaction in the platform. It sits at the front of the agent network and acts as an intelligent dispatcher — reading what a user has asked for, working out what they actually mean, and directing that request to the right combination of specialist agents to handle it.

It operates invisibly. Users never interact with the Intent Router directly. They type a message or trigger an action in the workspace, and the Intent Router processes that input before anything else happens. The quality of the whole platform experience depends on this agent doing its job well: if it misreads the user's intent, the wrong agents respond. If it reads it correctly, the right expertise is assembled in seconds.

---

## What It Does

When a user submits a request — whether typed in the assistant panel, submitted through a form, or triggered by a workflow event — the Intent Router receives that input and performs three things:

**It classifies the intent.** It reads the text and identifies what the user is trying to accomplish. Is this a request to create a new project? A question about portfolio health? A risk that needs to be logged? A budget that needs reviewing? The agent has been trained to recognise a wide range of project and portfolio management intents, from straightforward document creation tasks through to complex portfolio optimisation queries.

**It extracts the relevant parameters.** Beyond understanding the intent, the agent picks out the specific details embedded in the request: the project ID being referenced, the portfolio in scope, the currency or financial amount mentioned, the type of entity being asked about, the timeframe in question. These parameters are passed downstream so that the agents that respond have the context they need without the user having to repeat themselves.

**It determines which agents should respond.** Based on the classified intent and extracted parameters, the Intent Router produces a routing plan — a structured list of which domain agents need to be invoked, in what order, and with what inputs. This plan is handed to the Response Orchestration agent, which executes it.

---

## How It Works

The Intent Router uses a language model to interpret user input. It sends the user's message to the platform's LLM gateway and receives back a classification of the intent along with a confidence score. If the confidence is high, that classification is used. If the language model is unavailable or returns a low-confidence result, the agent falls back to a keyword-based classifier that uses pattern matching to make a best-effort determination without relying on the LLM.

The agent is also capable of detecting when a single request contains more than one intent — for example, a user asking to "create a project and generate a risk register" is really asking for two things at once. In those cases, the Intent Router identifies both intents and constructs a routing plan that addresses each of them.

Every classification decision is recorded in the platform's audit log, including which method was used (LLM or fallback), the confidence score assigned, and the routing plan produced. This creates a complete, traceable record of how the system interpreted every user request.

---

## What It Uses

- The platform's LLM gateway to perform intent classification
- A fine-tuned transformer model for natural language understanding
- spaCy for named entity recognition, used to extract parameters such as project names, financial figures and entity types
- A keyword-based fallback classifier for resilience when the LLM is unavailable
- The audit log service to record every classification decision

---

## What It Produces

The Intent Router produces a **routing plan**: a structured document that specifies which agents should be called, with what parameters, and in what sequence. This plan is consumed by the Response Orchestration agent and drives everything that happens next.

It also emits an audit event for every request it processes, capturing the intent classification result, the confidence level, and whether the LLM or fallback method was used.

---

## How It Appears in the Platform

The Intent Router itself has no visible presence in the user interface. Its work happens behind the scenes the moment a user submits any input to the assistant panel or triggers an action. The speed with which the platform responds — and the relevance of that response — reflects the Intent Router's performance.

In the platform's administration console, operators can view agent execution logs that show how requests were classified and routed. This is useful for diagnosing unexpected behaviour or tuning the routing configuration.

---

## The Value It Adds

The Intent Router is what makes the platform feel intelligent rather than mechanical. Without it, users would need to navigate menus, select specific functions and fill in structured forms to get anything done. With it, they can describe what they need in plain language and the platform works out the rest.

It also provides resilience: by maintaining a fallback classifier alongside the LLM-based approach, the agent ensures that the platform continues to function and route requests correctly even when the language model is temporarily unavailable.

---

## How It Connects to Other Agents

The Intent Router feeds its output directly into **The Response Orchestration agent — Response Orchestration**, which takes the routing plan and executes it by calling the relevant domain agents. Every request that enters the platform flows through the Intent Router agent first. It does not communicate directly with domain agents; that is the responsibility of the orchestration layer.


---

# the Response Orchestration agent — Response Orchestration

**Category:** Core Orchestration
**Role:** Execution Coordinator

---

## What This Agent Is

The Response Orchestration agent is the engine that makes multi-agent collaboration work. Once the Intent Router has classified a user's request and produced a routing plan, it is the Response Orchestration agent that picks up that plan and carries it through to completion — calling the right agents, in the right order, managing failures, caching results, and assembling everything into a single coherent response for the user.

It is the most operationally complex agent in the platform, responsible for coordinating the work of every other agent and ensuring that the user always receives a useful, well-structured answer regardless of how many underlying systems were involved in producing it.

---

## What It Does

**It executes the routing plan.** The agent receives a plan containing a set of tasks — each task specifying which domain agent should be called, what action it should perform, and what inputs it needs. The Response Orchestration agent works through this plan, calling each agent as directed.

**It manages parallel and sequential execution.** Not all tasks need to happen one after another. When tasks are independent of each other, the agent runs them simultaneously, which significantly reduces the time the user waits for a response. When one task depends on the output of another — for example, a financial forecast that depends on a schedule first being generated — the agent sequences those correctly, ensuring data flows in the right order.

**It handles failures gracefully.** If an agent call fails, the Response Orchestration agent retries it automatically using an exponential backoff strategy, giving the downstream system time to recover. If an agent consistently fails, a circuit breaker kicks in and prevents the system from continuing to flood a struggling service with requests. The user receives a partial response where possible, with a clear indication of what could not be completed.

**It caches results.** For tasks that are expensive to compute and are likely to be repeated — portfolio health summaries, resource utilisation snapshots — the agent caches the results for a configurable window (fifteen minutes by default). Repeat requests within that window are served from cache rather than re-invoking downstream agents, which improves response speed and reduces load on connected systems.

**It enriches responses with external research.** When configured, the agent can supplement the outputs of domain agents with information retrieved from external sources — market data, industry benchmarks, publicly available regulatory guidance — to provide richer, more contextually grounded responses.

**It aggregates and synthesises.** Once all agent calls in a plan have been completed, the Response Orchestration agent combines their outputs into a single, structured response. It resolves any conflicts between agent outputs, applies a consistent format, and presents the result to the user through the assistant panel.

---

## How It Works

The agent analyses the routing plan to build a dependency graph — a map of which tasks can run concurrently and which must wait for others to complete. It uses cycle detection to identify and handle any circular dependencies before execution begins.

Agent calls are made over HTTP to the individual agent services, with fallback options via the internal service registry or the event bus for agents that cannot be reached directly. The agent tracks the status of each task throughout execution and maintains a plan status that transitions from pending through to approved, in-progress, and completed.

All activity is recorded in the platform's observability layer, including per-task latency, cache hit and miss rates, retry counts, and failure reasons. This data feeds into the platform's performance dashboards and supports ongoing operational monitoring.

---

## What It Uses

- The routing plan produced by the Intent Router agent — Intent Router
- HTTP connections to each domain agent service
- An internal service registry for agent discovery
- The platform's event bus as a fallback communication channel
- A result cache with configurable time-to-live
- An external research integration for supplementary enrichment
- The platform's observability and metrics system
- The audit log service

---

## What It Produces

The Response Orchestration agent produces the **final response** that is returned to the user through the assistant panel. This may be a generated document, a summary report, a structured data table, a recommendation, or a confirmation that an action has been completed — depending on what was requested.

It also produces plan execution records showing the status, duration and outcome of every task in the routing plan, which are available to platform administrators through the agent runs monitoring view.

---

## How It Appears in the Platform

Like the Intent Router, the Response Orchestration agent operates entirely behind the scenes. Users see its output — the response that appears in the assistant panel — but not the coordination work that produced it.

In the administration console, the **Agent Runs** page shows a history of orchestration plans that have been executed, including the tasks they contained, the agents involved, the time taken, and any failures or retries that occurred. This gives operators a clear view of how the platform is performing and where bottlenecks exist.

---

## The Value It Adds

The Response Orchestration agent is what allows the platform to behave as a unified intelligent system rather than a collection of disconnected tools. A single user request can trigger five or six agent calls, each pulling data from a different system, and the user receives a single coherent answer in seconds. Without this coordination layer, users would have to navigate to each agent individually, interpret separate outputs, and assemble the picture themselves.

The caching mechanism also means that the platform is operationally efficient: heavily used views and reports are not recomputed from scratch on every request, and the connected source systems are not hammered with redundant queries.

---

## How It Connects to Other Agents

The Response Orchestration agent connects to every domain agent in the platform. It receives its instructions from **The Intent Router agent — Intent Router** and calls any combination of agents 03 through 25 depending on what the routing plan requires. It is the central coordination hub of the entire agent network.


---

# the Approval Workflow agent — Approval Workflow

**Category:** Core Orchestration
**Role:** Workflow Orchestration and Governance

---

## What This Agent Is

The Approval Workflow agent is the platform's unified workflow and approval engine — the single canonical orchestration authority for all long-running, multi-step processes. It manages the definition, execution, monitoring, and auditing of every structured process in the platform: approval chains, automated task sequences, event-driven process automation, retry and compensation flows, and governed business workflows.

Approvals are represented as a workflow pattern (`approval_gate` step type) within the workflow specification (`ppm.workflow/v1`). This unified representation ensures that approval steps are executed with the same state persistence, monitoring, and audit infrastructure as every other workflow step. The result is one workflow definition language, one execution engine, one task inbox, one monitoring view, and one audit trail for all structured processes.

---

## What It Does

### Workflow engine capabilities

**It defines workflows as structured specifications.** Workflow definitions are created using a structured YAML or JSON format — the platform's workflow specification language (`ppm.workflow/v1`). Each workflow definition describes its steps, the type of each step (`human_task`, `automated_action`, `approval_gate`, `notification`, `decision`, `parallel`, `loop`), the conditions that govern transitions between steps, retry policies for steps that might fail, and the metadata needed to identify and version the workflow. BPMN 2.0 format is also supported for organisations that already model their processes in standard BPMN tools.

**It starts and manages workflow instances.** When a workflow is triggered — by a user action, by an event from another agent, or by a scheduled trigger — the engine creates a new instance of the workflow. Each instance has its own state, tracking which steps have been completed, what data has been passed between steps, and what the current execution status is. Instances can be paused, resumed, cancelled, or retried depending on the circumstances.

**It executes parallel and conditional logic.** Workflows can contain parallel branches — multiple steps that execute simultaneously — and decision points where the path taken depends on the result of a previous step. The engine evaluates decision conditions (equality, comparison, containment, existence checks) against the current workflow data and routes execution accordingly. Parallel branches are collected at a join point before the workflow continues, ensuring that all concurrent steps are complete before the process advances.

**It manages human task inboxes.** When a workflow reaches a step that requires human action — a review, a decision, a data entry task — the engine creates a task in the assigned user's inbox and waits for them to complete it. The task includes all the context the user needs to act, a deadline, and any relevant data from previous workflow steps. Users can view and complete their pending tasks from the platform's Task Inbox.

**It handles retries and compensation.** When a workflow step fails — because a system is unavailable, a validation check fails, or an automated action produces an error — the engine applies the configured retry policy: retrying after a delay, with exponential backoff for repeated failures. If a workflow fails in a way that cannot be retried, compensation workflows can be triggered to reverse the actions already taken, ensuring that the system is not left in an inconsistent state.

**It responds to events.** Workflows can be triggered or continued by events from other agents and systems. The engine monitors configured event subscriptions and, when a matching event arrives, triggers the appropriate workflow action — starting a new instance, advancing a waiting step, or branching based on the event data. Event criteria can match on specific field values, allowing fine-grained control over which events trigger which workflow responses.

**It supports workflow versioning.** As business processes evolve, workflow definitions are updated and versioned. The engine maintains a version history for each workflow definition, ensuring that in-flight instances continue on the version they were started with while new instances use the current version.

**It provides monitoring and reporting.** For each workflow definition, the engine tracks instance counts, success rates, average execution time, step-level performance metrics, backlog depth, and failure rates. This data is accessible through the Workflow Monitoring view and feeds into the Continuous Improvement agent's process analysis.

### Approval workflow capabilities

**It creates and manages approval chains.** When an action in the platform requires human sign-off, the agent creates a structured approval chain — sequential or parallel — with configurable chain types and deadlines. The agent assesses the nature of the request, its risk level, its financial value, and the organisational context to determine the correct chain structure.

**It routes requests to the right people.** Rather than sending every approval to a fixed list of names, the agent routes dynamically. A low-value procurement request goes to a project manager. A high-value contract goes to a finance lead and a program director. An approval with regulatory implications involves the compliance team. The routing rules are configurable and can be adapted to match any organisation's governance structure.

**It supports delegation.** If a designated approver is unavailable — on leave, outside working hours, or overloaded — the agent supports delegation rules that redirect the approval to an appropriate substitute. Delegation can be configured in advance by the approver or applied automatically based on calendar availability.

**It sends notifications through multiple channels.** When an approval task is created, modified, or overdue, the agent notifies the relevant people. It sends notifications by email, Microsoft Teams, Slack, and push notification — whichever channel the recipient has configured as their preference. Notifications are formatted clearly, include the context needed to make a decision, and contain deep links ("View request") to the approval task in the platform.

**It escalates automatically.** Every approval task has a deadline. If a decision is not made within the required timeframe, the agent automatically escalates — notifying a senior approver, sending a reminder, or triggering a governance alert. The escalation timeline is calculated dynamically based on the urgency and risk level of the request.

**It records decisions permanently.** Every approval decision — approved, rejected, or deferred — is recorded as an immutable decision record with the identity of the approver, the timestamp, any comments provided, and the outcome. This record cannot be altered and is retained according to the platform's data retention policy.

**It supports the "My approvals" queue.** Approvers can list, filter, open, and decide on their pending approvals from a personal queue view. For approvers who handle high volumes, the agent can batch pending items into a digest notification.

### How approvals fit inside workflows

Approvals are represented as a workflow pattern using the `approval_gate` step type within the `ppm.workflow/v1` specification:

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

---

## How It Works

Workflow definitions are loaded from the platform's workflow definition store and from a library of pre-built workflow templates. The engine uses a task-dependency graph to determine the execution order for each workflow instance, applying cycle detection to prevent invalid workflow definitions from causing infinite loops. State is persisted using either JSON file storage or a PostgreSQL database backend, depending on the deployment configuration. For task queuing, either an in-process queue (for simple deployments) or RabbitMQ (for scaled deployments) is used.

For approval-specific processing, the agent assesses each incoming approval request to determine its risk level and criticality, then uses those assessments to calculate the appropriate escalation timeline and select the correct approval chain. Notifications are generated from localised templates (English and French, with the structure to add further languages). Accessibility is addressed: notifications can be delivered in plain text or HTML with alt text depending on the recipient's preferences.

The agent integrates with Microsoft Graph to create calendar entries and tasks for approvers, so that approval deadlines appear alongside their other commitments. The event subscription system uses deterministic criteria matching — evaluating field conditions against incoming event data — ensuring consistent, predictable behaviour regardless of event volume.

---

## What It Uses

- Workflow definitions in YAML, JSON, or BPMN 2.0 format
- A workflow specification schema (`ppm.workflow/v1`) for validation
- PostgreSQL or JSON file-backed state store for workflow instance persistence
- RabbitMQ or in-process task queue for task message passing
- Role-based routing rules configured per tenant
- Risk and criticality assessment logic to determine escalation timelines
- Notification templates in multiple languages
- Email, Microsoft Teams, Slack, and push notification channels
- Microsoft Graph for calendar and task integration
- Azure Monitor and Azure Event Grid for event integration
- Azure Service Bus for event publishing
- Task dependency graph with cycle detection
- The platform's audit log for permanent decision and state transition recording
- An approval store for persistence of approval state
- the Change Control agent — Change and Configuration Management for change-triggered workflows
- the Continuous Improvement agent — Continuous Improvement for process performance analysis
- the Data Synchronisation agent — Data Synchronisation and Quality for sync retry workflows

---

## What It Produces

- **Workflow definitions**: versioned, structured specifications of business processes
- **Workflow instances**: running and completed process executions with full state history
- **Task inbox items**: human tasks created for workflow participants with context and deadlines
- **Approval tasks** routed to the relevant approvers with full context
- **Execution logs**: step-by-step records of every workflow execution with outcomes and timestamps
- **Compensation records**: documentation of rollback actions taken when workflows fail
- **Notification messages** across the configured channels, formatted and localised
- **Escalation alerts** when decisions are not made within the required timeframe
- **Immutable decision records** in the audit log for every approval outcome
- **Event subscription records**: configured triggers and their matching criteria
- **Workflow performance metrics**: execution time, success rate, step-level performance, backlog depth, and failure rates by workflow type
- **Workflow monitoring dashboard**: real-time view of active instances, failure rates, and backlogs
- **Approval status updates** visible in the platform's Approvals page

---

## How It Appears in the Platform

The **Workflow Designer** page allows authorised users to create and configure workflow definitions through a structured interface. Workflow definitions can be imported and exported in YAML or BPMN format.

The **Workflow Monitoring** page provides a real-time operations view — showing how many instances of each workflow are currently running, how many have completed or failed, average execution times, and any instances that are stuck or in a failed state. Operators can inspect individual instances, view their execution history, retry failed steps, or cancel stalled instances from this view.

The **Approvals** page provides a complete view of all pending and completed approval tasks. Approvers see a queue of items awaiting their decision, with the relevant context — what is being approved, who raised it, what supporting information is available, and what the deadline is. They can approve, reject or comment from within this view without needing to navigate elsewhere.

Users with pending workflow tasks or approval decisions see them in the **Task Inbox**, accessible from the platform's notification centre. Each item shows what action is required, the deadline, and the relevant context from the workflow.

The platform also surfaces approval status inline within the relevant workflow context — for example, a project that is waiting for a business case approval will show the pending approval status on its lifecycle stage in the methodology map.

---

## The Value It Adds

The Approval Workflow agent provides two categories of operational value:

**Process automation.** It enables organisations to automate the routine, multi-step processes that consume significant administrative time — approvals, notifications, escalations, data updates — and execute them consistently, at scale, without manual coordination. The event-driven architecture means workflows respond intelligently to platform events rather than running on fixed schedules.

**Governance confidence.** It replaces informal, unreliable approval processes — emails that get lost, decisions made in meetings with no record, approvals that never happen because nobody followed up. Every decision is made by the right person, within the right timeframe, with a permanent record. For regulated industries, the combination of automated routing, escalation, and immutable audit records means organisations can demonstrate their governance processes to auditors and regulators with confidence.

The unified design — one engine for both workflows and approvals — means organisations manage one set of definitions, one task inbox, and one monitoring view for all structured processes. This reduces complexity for administrators and improves the experience for users who no longer need to check multiple inboxes or navigate between separate workflow and approval interfaces.

---

## How It Connects to Other Agents

The Approval Workflow agent is used by virtually every other agent in the platform to automate multi-step processes and human authorisation steps. Requests that originate from the **Business Case and Investment** agent, the **Vendor Procurement** agent, the **Change and Configuration** agent, the **Project Definition and Scope** agent, and many others are routed through the Approval Workflow agent when they reach a decision gate or need a governed workflow. The **Change Control agent** triggers change workflows through it. The **Data Synchronisation agent** uses it to manage sync retry workflows. The **Continuous Improvement agent** analyses its execution data for process mining. The **Release Deployment agent** uses it to orchestrate deployment workflows. The **Workspace Setup agent** routes governed provisioning actions through it for approval. It feeds its outputs — approval decisions, workflow status updates, and task assignments — back to the requesting agent so that the downstream process can continue.


---

# the Demand Intake agent — Demand and Intake

**Category:** Portfolio Management
**Role:** Project Request Handler

---

## What This Agent Is

The Demand and Intake agent is where every project begins. It is the front door through which ideas, requests, and proposals enter the platform — regardless of which channel they come from or who is submitting them. Its job is to ensure that no request gets lost, that every submission is consistently captured and classified, and that the right people are notified so that the review process can begin promptly.

Before this agent, organisations typically manage demand through email threads, spreadsheets, or manual entry into a PPM tool — processes that are inconsistent, hard to track, and impossible to report on reliably. The Demand and Intake agent replaces all of that with a structured, automated, multi-channel intake process.

---

## What It Does

**It receives requests from multiple channels.** A project request can arrive as a submission through the platform's intake form, a message sent to a connected Slack workspace, an email to a configured address, or a notification from Microsoft Teams. The agent monitors all configured channels and captures submissions from any of them, applying the same processing logic regardless of source.

**It classifies each request automatically.** Once a request is received, the agent analyses its content and assigns it a category — is this a capital project, a technology initiative, a regulatory compliance programme, a change request, or something else? It also estimates the complexity and scale of the request based on the description provided. These classifications feed into the routing and prioritisation logic that determines how the request is handled next.

**It checks for duplicates.** The agent uses semantic similarity analysis to compare each new request against existing demands in the system. If a similar request has already been submitted — perhaps from a different team or through a different channel — the agent flags the potential duplicate so that reviewers can consider whether to consolidate or keep them separate. This prevents the portfolio from filling up with overlapping initiatives.

**It enriches the submission.** Where the submitted information is incomplete, the agent prompts the submitter for missing details or supplements the record with information it can derive from context — the submitting business unit, the relevant portfolio or programme, suggested categorisation, and similar historical projects. This reduces the administrative burden on the intake team and ensures that demand records are complete enough to be usefully reviewed.

**It routes requests for review.** Once a submission has been validated and enriched, the agent triggers a notification to the appropriate reviewers and creates an intake record that appears in the platform's intake queue. Reviewers can see all pending requests, their classifications, and their status from a single view.

**It maintains a pipeline view.** The agent tracks the status of every demand item — submitted, under review, approved for further development, rejected, or converted into a project — and provides a pipeline visualisation that shows where each request sits in the process. This gives portfolio managers visibility into the incoming workload and helps them plan capacity for the review and business case process.

---

## How It Works

The agent uses natural language processing to interpret and classify the text of each submission. It applies a set of validation rules to check that the required fields are present and that the submission meets the minimum information standards needed for a meaningful review. Vector-based embedding is used for duplicate detection — the agent converts each new request into a numerical representation and compares it against the embedded representations of existing demands to find semantically similar submissions.

Event publishing ensures that other parts of the platform — the notification service, the intake approval queue, the portfolio management views — are kept informed as the status of each demand item changes.

---

## What It Uses

- Intake form submissions from the platform's web interface
- Connected Slack, Teams and email channels for multi-channel capture
- Natural language processing for classification and entity extraction
- Semantic embedding and vector search for duplicate detection
- Validation rules to enforce minimum submission standards
- The notification service to alert reviewers of new submissions
- The platform's event bus to publish status changes
- A canonical demand schema to ensure consistent data structure

---

## What It Produces

- **Demand records** in the platform's data store, consistently structured regardless of the channel of origin
- **Classification labels** identifying the request type and estimated complexity
- **Duplicate flags** where semantically similar requests already exist
- **Intake notifications** to configured reviewers
- **Pipeline status updates** as requests move through the review process
- **Enriched submission data** supplementing incomplete requests with inferred context

---

## How It Appears in the Platform

The **Intake Form** page provides a structured submission experience for users raising new project requests. The form collects the key information the platform needs: a description of the initiative, the business problem being addressed, the expected benefits, the requesting business unit, the estimated scale, and any supporting materials.

The **Intake Queue** page gives portfolio managers and reviewers a consolidated view of all submitted requests, organised by status and classification. Each item shows a summary of the request, its classification, its submission date, and any flags raised by the agent (such as duplicate detection). Reviewers can approve, reject, request more information, or convert a request into a full business case from this view.

The **Intake Status** page allows submitters to track the progress of their own requests through the review process without needing to contact the portfolio team.

---

## The Value It Adds

Organisations that manage demand informally typically find that only a fraction of submitted project ideas are properly evaluated — many are lost in email, deprioritised without communication, or never formally reviewed at all. The Demand and Intake agent ensures that every request is captured, every submitter receives a response, and every decision is traceable.

For portfolio managers, having a structured, classified, deduplicated demand pipeline is essential for planning and forecasting. They can see how many requests are in progress, what types of initiative are being proposed, and whether the incoming pipeline aligns with the organisation's strategic priorities — all from a single view.

---

## How It Connects to Other Agents

Once a demand item has been approved for development, the Demand and Intake agent hands off to **The Business Case agent — Business Case and Investment Analysis**, which takes the enriched demand record and builds out the financial and strategic case for the initiative. The agent also works with **The Approval Workflow agent — Approval Workflow** to manage the review and approval of intake submissions, and surfaces its outputs in the portfolio-level views managed by **The Portfolio Optimisation agent — Portfolio Strategy and Optimisation**.


---

# the Business Case agent — Business Case and Investment Analysis

**Category:** Portfolio Management
**Role:** Financial Justification and Investment Advisor

---

## What This Agent Is

The Business Case and Investment Analysis agent turns a project idea into a structured investment proposition. It takes the information captured during demand intake and builds out a complete financial and strategic analysis — including cost modelling, benefit quantification, return on investment calculations, scenario comparisons, and a recommendation on whether to proceed.

This is the agent that makes the case for or against investing in a project. It does the analytical heavy lifting that project teams and finance functions would otherwise spend days or weeks doing manually — producing a document-ready business case with rigorous financial modelling in a fraction of the time.

---

## What It Does

**It generates business cases from structured templates.** The agent uses the platform's business case template library — tailored to different project types such as capital investment, technology delivery, regulatory compliance, or operational improvement — to produce a properly structured document. The template ensures that every business case contains the sections expected by the organisation's governance process: strategic alignment, problem statement, options analysis, cost-benefit analysis, risk summary, and recommendation.

**It performs cost-benefit analysis.** The agent models the expected costs of the initiative across its full lifecycle — capital costs, implementation costs, ongoing operational costs, and decommissioning costs — and quantifies the expected benefits: efficiency savings, revenue generation, risk reduction, regulatory compliance value, or strategic positioning gains. It calculates the net benefit and presents a clear picture of whether the investment is financially justified.

**It calculates key financial metrics.** For each business case, the agent calculates Net Present Value (NPV), Internal Rate of Return (IRR), payback period, and Total Cost of Ownership (TCO). These metrics are calculated using configurable discount rates and inflation assumptions, and support multi-currency scenarios for organisations operating across multiple markets.

**It models scenarios and sensitivity.** Rather than presenting a single set of numbers, the agent models multiple scenarios — a base case, an optimistic case, and a conservative case — showing how the financial outcome changes under different assumptions. It also runs sensitivity analysis, identifying which assumptions have the greatest impact on the result and presenting the range of outcomes if those assumptions prove incorrect.

**It runs Monte Carlo simulation.** For more complex investment decisions, the agent can run probabilistic simulations — testing the business case against thousands of randomly sampled combinations of cost and benefit assumptions — to produce a probability distribution of outcomes rather than a single point estimate. This gives decision-makers a realistic sense of the uncertainty in the numbers rather than a false precision.

**It benchmarks against historical projects.** The agent compares the proposed investment against a library of historical projects to assess whether the cost and benefit estimates are realistic, whether similar initiatives have delivered as expected, and what lessons from past experience should inform the current decision.

**It produces an investment recommendation.** Drawing on the financial analysis, the scenario modelling, the risk assessment and the historical comparison, the agent produces a clear recommendation — proceed, do not proceed, or proceed with conditions — along with the confidence level of that recommendation and the key factors driving it.

---

## How It Works

The agent draws on the enriched demand record produced by the Demand Intake agent as its starting point. It uses the platform's LLM gateway to generate narrative sections of the business case from structured data inputs, and applies financial calculation libraries to produce the quantitative analysis. Where external market data is available — such as benchmark costs for a particular type of technology project — the agent can retrieve and incorporate that information to ground the estimates in real-world comparisons.

The generated business case is stored in the platform's document canvas as a versioned document, allowing it to be reviewed, commented on, and revised through the platform's document editing workflow. Changes to assumptions trigger a recalculation of the financial metrics so that the document always reflects the most current analysis.

---

## What It Uses

- The demand record from the Demand Intake agent as the starting input
- Business case document templates from the platform's template library
- Financial calculation logic for NPV, IRR, payback period, TCO and multi-currency conversion
- Monte Carlo simulation for probabilistic analysis
- Sensitivity analysis across configurable assumption dimensions
- A library of historical project data for benchmarking
- External market data for grounding cost and benefit estimates
- The platform's LLM gateway for narrative generation
- The document canvas for storing and presenting the business case
- the Approval Workflow agent — Approval Workflow for routing the completed business case for sign-off

---

## What It Produces

- A **complete business case document** stored in the document canvas, structured according to the organisation's template and containing all required sections
- **Financial metrics**: NPV, IRR, payback period, TCO for each scenario
- **Scenario comparisons**: base, optimistic and conservative cases side by side
- **Sensitivity analysis**: identification of the key assumptions and their range of impact
- **Monte Carlo results**: probability distribution of outcomes for complex investments
- **Investment recommendation** with confidence level and supporting rationale
- **Benchmark comparison** against historical similar projects

---

## How It Appears in the Platform

When a business case is generated, it appears in the **Document Canvas** of the relevant project workspace, pre-populated with all the sections the platform's template defines. The financial metrics are presented in formatted tables, and the scenario analysis is shown as a comparison view that allows reviewers to see the optimistic, base and conservative cases side by side.

The business case document can be edited directly within the document canvas. As assumptions are changed, the financial metrics update automatically. Comments and review notes can be added inline, and the document passes through the Approvals workflow before it is formally signed off.

On the portfolio analytics dashboard, approved business cases contribute their NPV and strategic alignment scores to the portfolio-level investment view.

---

## The Value It Adds

Building a rigorous business case is time-consuming work that requires financial skills, structured thinking, and access to historical data that most project teams do not have readily at hand. The Business Case and Investment Analysis agent compresses this work from days to minutes, produces a consistently structured output that meets governance standards, and applies analytical rigour — Monte Carlo simulation, sensitivity analysis, historical benchmarking — that goes beyond what most organisations manage in practice.

For investment committees and portfolio boards, the consistency of the output means that every business case they review is structured the same way, uses the same financial methodology, and can be compared directly against others in the portfolio — making investment decisions significantly easier and more defensible.

---

## How It Connects to Other Agents

The Business Case and Investment Analysis agent receives its input from **The Demand Intake agent — Demand and Intake** and routes completed business cases to **The Approval Workflow agent — Approval Workflow** for sign-off. Approved business cases feed into **The Portfolio Optimisation agent — Portfolio Strategy and Optimisation**, which uses the financial metrics and strategic alignment scores to rank and prioritise the portfolio. The financial baseline established in the business case also forms the starting point for **The Financial Management agent — Financial Management** once the project is approved and enters delivery.


---

# the Portfolio Optimisation agent — Portfolio Strategy and Optimisation

**Category:** Portfolio Management
**Role:** Investment Prioritisation and Portfolio Advisor

---

## What This Agent Is

The Portfolio Strategy and Optimisation agent is the strategic brain of the platform at the portfolio level. It looks across all active and proposed projects simultaneously — weighing their strategic value, their costs, their risks, their resource demands, and the organisation's capacity constraints — and produces a prioritised, optimised view of the portfolio that tells decision-makers where to invest, where to hold, and where to stop.

This is the agent that answers the hardest questions in portfolio management: "Given everything on our plate and everything in our pipeline, what should we focus on?" It replaces intuition-led portfolio reviews with evidence-based, multi-criteria analysis.

---

## What It Does

**It scores and ranks projects across multiple dimensions.** The agent evaluates every project and proposal in the portfolio against a consistent set of criteria: strategic alignment with the organisation's objectives, expected return on investment, risk level, urgency, dependency on other initiatives, and resource intensity. Each dimension is weighted according to the organisation's configured priorities, and every project receives a composite score that reflects its overall value relative to others in the portfolio.

**It performs capacity-constrained optimisation.** Scoring projects is only half the challenge. The other half is working out which combination of projects the organisation can actually deliver given its available budget, people, and time. The agent applies optimisation algorithms to find the portfolio mix that maximises total strategic value subject to the actual constraints in play. It does not just recommend what is most valuable in isolation — it recommends what is most valuable given what is realistically achievable.

**It supports multiple optimisation approaches.** Depending on the complexity of the portfolio and the preferences of the investment committee, the agent can apply different approaches: integer programming for mathematically optimal solutions under strict constraints, mean-variance analysis for balancing return against risk, the Analytic Hierarchy Process for structured multi-criteria comparison, or multi-objective optimisation for scenarios where trade-offs between competing priorities need to be explicitly surfaced.

**It runs what-if scenario analysis.** The agent allows portfolio managers and executives to model the impact of portfolio changes before they are made. What happens to total portfolio value if this programme is deferred by a quarter? What if the budget is cut by fifteen percent — which projects should be deprioritised? What if a new strategic priority emerges — how should the portfolio be rebalanced? Each scenario is modelled quickly, and the results are presented as a comparison against the current portfolio state.

**It evaluates policy guardrails.** Portfolio decisions are not made in a vacuum. The agent checks proposed portfolio configurations against the organisation's investment policies — minimum diversification requirements, maximum concentration in any single domain, mandatory compliance investments that cannot be deferred — and flags any configuration that would breach these guardrails.

**It produces rebalancing recommendations.** When the portfolio has drifted from its optimal configuration — because new priorities have emerged, projects have been delayed, or resource capacity has changed — the agent analyses the gap and produces a set of specific rebalancing actions: projects to accelerate, projects to pause, proposals to promote into delivery, and initiatives to close.

---

## How It Works

The agent ingests the scored outputs of individual business cases from the Business Case agent, the resource capacity picture from the Resource Management agent, and the current portfolio status from the platform's data store. It applies its optimisation algorithms to this combined dataset and produces both a portfolio health assessment and a set of recommendations.

The agent's scoring model is configurable per tenant: the weight given to strategic alignment versus financial return versus risk versus urgency can be adjusted to match the organisation's current priorities. This means the same platform can serve an organisation that prioritises financial return above all else and one that prioritises regulatory compliance, without requiring any code changes.

All recommendations are versioned and auditable — the agent records the inputs, the scoring weights, the algorithm used, and the resulting recommendation for every optimisation run, so that the basis for portfolio decisions can be reviewed and challenged at any point.

---

## What It Uses

- Business case data and financial metrics from the Business Case agent
- Resource capacity and constraint data from the Resource Management agent
- Current portfolio status from the platform's data store
- Configurable scoring weights and strategic objective definitions
- Multiple optimisation algorithms: integer programming, mean-variance, AHP, multi-objective
- Policy guardrail definitions
- the Approval Workflow agent — Approval Workflow for routing portfolio recommendations for executive sign-off
- The platform's event bus for publishing portfolio change events

---

## What It Produces

- A **scored and ranked portfolio view** showing every active and proposed project with its composite strategic value score
- A **capacity-constrained optimised portfolio**: the recommended portfolio given actual resource and budget constraints
- **What-if scenario results**: modelled comparisons of alternative portfolio configurations
- **Policy guardrail assessments**: flags for any configurations that would breach investment policies
- **Rebalancing recommendations**: specific, actionable changes to bring the portfolio back into alignment with strategic priorities
- **Portfolio health summary** showing overall alignment, resource utilisation, and risk distribution

---

## How It Appears in the Platform

The portfolio-level **Dashboard Canvas** presents the optimised portfolio as a visual scorecard — each project shown with its strategic alignment score, financial value, risk level, and status. The colour coding makes it immediately clear which projects are performing well, which are at risk, and which are misaligned with the current strategy.

The scenario modelling capability is accessible through the assistant panel: a portfolio manager can ask the platform to model a specific change — "what happens if we defer Project X?" — and receive a before-and-after comparison directly in the canvas. Formal portfolio reviews and rebalancing decisions are routed through the Approvals workflow so that they are properly governed and recorded.

---

## The Value It Adds

Most organisations make portfolio investment decisions through a combination of gut feeling, political influence, and a spreadsheet that somebody spent three weeks building. The output is a portfolio that reflects who argued most persuasively in the last investment committee meeting, not what actually creates the most value.

The Portfolio Strategy and Optimisation agent replaces that process with evidence-based multi-criteria analysis that is transparent, consistent, and auditable. Every project is evaluated on the same criteria. The constraints are real. The scenarios are modelled, not guessed. And the basis for every recommendation is recorded, so that when the investment committee is challenged on a decision six months later, the reasoning is available.

---

## How It Connects to Other Agents

The Portfolio Strategy and Optimisation agent draws on business case data from **The Business Case agent** and resource capacity data from **The Resource Management agent**. Its outputs inform the programme structure that **The Program Management agent — Programme Management** creates and the financial baselines that **The Financial Management agent — Financial Management** tracks. Portfolio decisions approved through this agent are surfaced in the analytics dashboards managed by **The Analytics Insights agent — Analytics and Insights**.


---

# the Program Management agent — Programme Management

**Category:** Portfolio Management
**Role:** Programme Coordinator and Benefits Tracker

---

## What This Agent Is

The Programme Management agent provides the organisational layer between individual projects and the portfolio. When a group of related projects needs to be managed together — because they share objectives, depend on each other, draw on the same resources, or are expected to deliver a combined set of benefits — this agent creates and manages the programme that holds them together.

It is the agent that ensures related initiatives are treated as a coherent whole rather than a collection of independent efforts, and that the combined benefits they are expected to deliver are tracked, measured, and reported at the right level.

---

## What It Does

**It defines and creates programmes.** When the portfolio optimisation process identifies a group of related projects — or when a strategic initiative is large enough to require multiple workstreams — the agent creates a programme record that formally groups them. It generates programme documentation including a programme mandate, objectives, benefit realisation plan, and governance structure.

**It builds and maintains integrated roadmaps.** The agent creates a programme-level roadmap that shows all the constituent projects, their key milestones, their sequencing, and the dependencies between them. This roadmap is not a static document — it is a live view that updates as project schedules change, keeping the programme-level picture current without requiring manual maintenance.

**It manages inter-project dependencies.** One of the most complex challenges in programme management is managing the web of dependencies between projects. Project A cannot start until Project B delivers a particular output. Project C shares a critical resource with Project D and cannot run at the same time. The agent maps these dependencies, monitors them continuously, and raises alerts when a change to one project creates a knock-on risk for others.

**It aggregates and tracks benefits.** Each project in a programme may deliver its own benefits, but the programme's value case is typically about the combined benefit: the integrated capability, the organisation-wide efficiency gain, the strategic position achieved by delivering all the projects together. The agent aggregates benefit commitments across the programme, tracks realisation progress as projects deliver, and reports on whether the programme is on track to achieve the expected combined value.

**It coordinates resources across projects.** When multiple projects within a programme are competing for the same people or capabilities, the agent provides a cross-project resource view and identifies conflicts. It works with the Resource and Capacity agent to recommend resolutions — whether that means adjusting sequencing, requesting additional capacity, or accepting a trade-off between programme schedule and resource cost.

**It identifies synergies.** Sometimes projects within a programme can create value by working together more closely than originally planned — sharing a component, reusing an artefact, or combining a delivery activity. The agent analyses the programme's projects for these opportunities and surfaces them as recommendations.

**It monitors programme health.** The agent calculates an overall health score for the programme based on the combined performance of its constituent projects: their schedule performance, financial performance, risk status, and benefits delivery progress. It surfaces this as a programme-level health dashboard and provides a narrative summary of the programme's current status and outlook.

**It analyses change impact at the programme level.** When a scope or schedule change is proposed for one project, the agent assesses the impact of that change across the entire programme — identifying which other projects are affected, what the programme-level implications are for benefits, schedule and budget, and what governance decisions are needed before the change can be approved.

---

## How It Works

The agent is one of the most substantial in the platform, with implementation that spans programme creation, roadmap generation, dependency analysis, benefit tracking, resource coordination, synergy identification, health monitoring, and change impact analysis. It uses the platform's LLM gateway to generate narrative content — programme mandates, health summaries, change impact reports — and applies its own analytical logic to the quantitative aspects of programme management.

The agent persists all programme data to the platform's database, and publishes events as programme status changes so that the analytics, stakeholder communications, and governance agents can respond appropriately.

---

## What It Uses

- Portfolio optimisation outputs from the Portfolio Optimisation agent to identify groupings of related projects
- Project records from the platform's data store for each constituent project
- Schedule and milestone data from the Schedule Planning agent — Schedule and Planning
- Resource capacity data from the Resource Management agent — Resource and Capacity Management
- Financial data from the Financial Management agent — Financial Management
- The platform's LLM gateway for narrative generation
- the Approval Workflow agent — Approval Workflow for programme governance decisions
- The event bus for publishing programme status updates

---

## What It Produces

- **Programme record**: a structured definition of the programme with mandate, objectives, and governance structure
- **Benefits realisation plan**: a document mapping expected benefits to the projects that will deliver them, with delivery milestones
- **Integrated roadmap**: a live, cross-project timeline showing all milestones, dependencies, and sequencing
- **Dependency map**: a visualisation of inter-project dependencies with status and risk indicators
- **Benefits tracking report**: current status of benefit realisation against plan
- **Resource conflict report**: cross-project resource conflicts with resolution options
- **Synergy recommendations**: identified opportunities for projects to work more closely together
- **Programme health dashboard**: composite health score with narrative summary
- **Change impact assessments**: programme-level analysis of the impact of proposed project changes

---

## How It Appears in the Platform

Programme data is surfaced in the platform's **Dashboard Canvas** at the programme level, showing the integrated roadmap, benefits realisation progress, health score, and resource picture. The programme roadmap timeline gives a visual representation of all constituent projects and their interdependencies.

The dependency map is accessible from the Tree Canvas, where the hierarchical relationship between the programme and its projects can be explored alongside the dependency links between them.

Health summaries are available through the assistant panel — a programme manager can ask for a status update and receive a structured narrative covering schedule, benefits, risk and resource position across the programme.

---

## The Value It Adds

Programmes that are managed as collections of independent projects consistently underperform. Dependencies are not managed, benefits are not tracked, resources are not coordinated, and the combined value case — the reason the programme was created in the first place — drifts out of focus. The Programme Management agent addresses every one of these failure modes by providing active, continuous coordination at the programme level.

For organisations running large transformation programmes — technology modernisation, regulatory compliance, operational restructuring — having a live, integrated view of the whole programme rather than a spreadsheet of individual project status reports is a significant operational improvement.

---

## How It Connects to Other Agents

The Programme Management agent draws on portfolio decisions from **The Portfolio Optimisation agent**, schedule data from **The Schedule Planning agent**, resource data from **The Resource Management agent**, and financial data from **The Financial Management agent**. It coordinates with **The Approval Workflow agent — Approval Workflow** for programme governance, and its outputs — health dashboards, benefits reports, roadmap views — feed into **The Analytics Insights agent — Analytics and Insights** for portfolio-level reporting. Change impact assessments are produced in coordination with **The Change Control agent — Change and Configuration Management**.


---

# the Scope Definition agent — Project Definition and Scope

**Category:** Delivery Management
**Role:** Project Charter and Scope Baseline Manager

---

## What This Agent Is

The Project Definition and Scope agent is responsible for establishing the formal foundation of a project. Before any delivery work begins, every project needs a clear and agreed definition: what it is trying to achieve, what is in scope and what is not, who is responsible for what, and what the key deliverables look like. This agent creates all of that.

It is the agent that turns an approved idea into a properly defined project — one with a signed charter, a documented scope baseline, a Work Breakdown Structure, a requirements register, and a stakeholder and responsibility map. These documents are not just administrative formalities; they are the reference point against which everything that happens during delivery is measured.

---

## What It Does

**It generates project charters.** The agent produces a complete project charter — the formal document that authorises the project, defines its objectives, establishes the authority of the project manager, and captures the high-level scope, constraints, assumptions, and risks. The charter is generated from the approved business case and demand record, so that the agreed case for the project is directly reflected in the project's founding document.

**It defines and baselines scope.** Working from the charter and requirements, the agent produces a detailed scope statement that defines precisely what the project will and will not deliver. This scope statement is stored as a formally baselined document — a signed-off, version-controlled record that serves as the definitive reference for all future scope discussions. Any subsequent change to scope is assessed against this baseline, not against the latest working version.

**It builds Work Breakdown Structures.** The agent decomposes the project's deliverables into a hierarchical Work Breakdown Structure (WBS) — breaking the overall scope into progressively smaller, manageable work packages. Each element of the WBS is defined clearly enough to be scheduled, assigned, and tracked. The WBS becomes the input to the Schedule and Planning agent, which converts it into a project schedule.

**It manages requirements and traceability.** The agent maintains a requirements register, capturing each requirement with its source, priority, status, and acceptance criteria. It builds a traceability matrix that links each requirement to the WBS element and deliverable that addresses it — ensuring that nothing in the scope has been missed and that every requirement can be tracked through to delivery.

**It produces stakeholder analysis and RACI matrices.** The agent identifies the key stakeholders for the project — who is affected, who has influence, who needs to be informed — and produces a RACI matrix that maps each stakeholder's role to each work package: who is Responsible, who is Accountable, who needs to be Consulted, and who needs to be Informed.

**It detects scope creep.** Throughout delivery, the agent monitors changes to the project's scope and flags any additions, modifications or deletions that have not been formally approved through the change management process. When undocumented scope changes are detected, it raises an alert and creates a change request so that the change can be properly assessed and governed.

**It supports external scope research.** Where useful, the agent can search external sources — market intelligence, regulatory guidance, industry standards — to supplement the scope definition with relevant context that may not be available from internal sources alone.

---

## How It Works

The agent takes the approved business case, the demand record, and any additional input from the project team as its starting point. It uses the platform's LLM gateway to generate the narrative sections of the charter and scope statement, and applies structured logic to build the WBS hierarchy, the requirements register, and the RACI matrix. All generated documents are stored in the document canvas as versioned records.

The scope baseline is stored separately from the working scope documents, ensuring that the original baseline remains intact and unchanged even as working documents are updated during delivery. The traceability matrix is maintained as a living record that is updated whenever requirements or WBS elements change.

---

## What It Uses

- Approved business case from the Business Case agent as the primary input
- Demand record from the Demand Intake agent for context
- Document templates for charters, scope statements, WBS, and RACI matrices
- The platform's LLM gateway for narrative generation
- External research capability for supplementary scope context
- The document canvas for storing all outputs
- the Approval Workflow agent — Approval Workflow for charter and scope baseline sign-off
- the Schedule Planning agent — Schedule and Planning as the consumer of the WBS

---

## What It Produces

- **Project charter**: a complete, structured document authorising the project and defining its objectives, authority, and constraints
- **Scope baseline**: a formally signed-off scope statement stored as a permanent reference document
- **Work Breakdown Structure**: a hierarchical decomposition of project deliverables into manageable work packages
- **Requirements register**: a tracked list of all project requirements with source, priority, status and acceptance criteria
- **Traceability matrix**: a mapping of requirements to WBS elements and deliverables
- **Stakeholder register**: identification and classification of all project stakeholders
- **RACI matrix**: responsibility assignments for each work package and deliverable
- **Scope creep alerts**: flags for changes to scope that have not been formally approved

---

## How It Appears in the Platform

All documents produced by the Project Definition and Scope agent appear in the **Document Canvas** of the project workspace. The charter and scope baseline are presented as formatted documents that can be reviewed, commented on, and approved through the platform's document workflow. Once approved, the scope baseline is marked as locked — clearly distinguishing it from the working scope documents.

The WBS is available as both a document in the Document Canvas and a hierarchical view in the **Tree Canvas**, where the structure of the project's deliverables can be explored and navigated. The requirements register and traceability matrix are presented in the **Spreadsheet Canvas**, where individual entries can be reviewed and updated.

Scope creep alerts surface in the **Methodology Map** navigation panel on the left, where the relevant stage and activity is highlighted when an unapproved scope change is detected.

---

## The Value It Adds

Projects that start without clear, agreed, documented scope definitions are extremely difficult to deliver successfully. Scope discussions recur throughout delivery. Disagreements arise about what was and was not committed. Change requests accumulate without a clear baseline to assess them against.

The Project Definition and Scope agent addresses this by producing a comprehensive, consistent, approved scope definition at the start of every project — regardless of the project manager's experience level or the time pressure they are under. The scope baseline becomes the contract between the delivery team and the business, and the traceability matrix ensures that every requirement is visible and tracked from definition through to delivery.

---

## How It Connects to Other Agents

The project charter and scope baseline produced by this agent feed directly into **The Lifecycle Governance agent — Project Lifecycle and Governance**, which uses them as the reference for gate assessments. The WBS is consumed by **The Schedule Planning agent — Schedule and Planning** to build the project schedule. Scope change requests are processed by **The Change Control agent — Change and Configuration Management**, which assesses their impact against the baselined scope. The stakeholder register is used by **The Stakeholder Communications agent — Stakeholder Communications** to plan and execute project communications.


---

# the Lifecycle Governance agent — Project Lifecycle and Governance

**Category:** Delivery Management
**Role:** Stage-Gate Enforcer and Project Health Monitor

---

## What This Agent Is

The Project Lifecycle and Governance agent is the platform's governance enforcer at the project level. It manages every project's journey through its defined lifecycle — tracking which stage the project is in, assessing whether the criteria to advance to the next stage have been met, and ensuring that no project skips the governance checkpoints that keep delivery quality and organisational risk under control.

It also acts as the project's ongoing health monitor — continuously assessing the project against a set of health indicators and raising alerts when performance is deteriorating so that intervention can happen before problems become crises.

---

## What It Does

**It manages project lifecycle stages.** Each project moves through a defined set of phases determined by its chosen methodology — Initiation, Planning, Execution, Monitoring and Controlling, and Closing for predictive projects; Sprint Planning, Sprint Execution, Sprint Review, and Sprint Retrospective for agile projects. The agent tracks which stage each project is currently in, records the date of each stage transition, and maintains the full lifecycle history.

**It enforces stage-gate criteria.** Before a project can advance from one stage to the next, specific criteria must be met. The gate criteria are defined by the project's methodology and configured by the organisation: a signed charter to leave Initiation, an approved schedule and risk register to leave Planning, a quality-assured product to leave Execution. The agent evaluates whether each criterion has been satisfied before allowing the transition. If criteria are not met, the gate remains closed and the agent explains which items still need to be addressed.

**It calculates project health scores.** The agent continuously evaluates each project against a set of health dimensions — schedule performance, financial performance, risk status, governance compliance, and quality of deliverables — and produces a composite health score. This score is updated regularly and provides an objective, data-driven assessment of how well the project is performing.

**It recommends methodology adaptations.** If a project's circumstances change significantly — for example, a predictive project encountering high levels of scope uncertainty — the agent can assess whether a methodology change might better serve the project's needs and recommend the appropriate adaptation.

**It monitors gates with machine learning readiness scoring.** Beyond the binary pass/fail of gate criteria, the agent uses a machine learning model to predict how likely a project is to pass an upcoming gate based on its current trajectory. This readiness score allows project managers to identify and address issues proactively — before they result in a gate failure — rather than discovering problems only at the formal gate review.

**It integrates with project delivery tools.** The agent synchronises project lifecycle status with the external project management tools connected to the platform — Planview, Clarity, Jira, Azure DevOps — ensuring that the governance picture in the platform reflects the actual state of delivery in the tools teams use day to day.

---

## How It Works

The agent maintains a persistent record of each project's lifecycle state — current stage, gate assessment history, health scores over time, and methodology configuration — stored in the platform's database. Gate evaluations are triggered at defined intervals and whenever a project's data changes significantly. The machine learning readiness model is trained on historical project data and provides probability estimates for gate outcomes.

Stage transitions initiate a set of downstream actions: notifying stakeholders, updating the methodology map view in the UI, triggering the appropriate document and artefact checklist for the new stage, and publishing a lifecycle event to the event bus so that other agents can respond.

Governance decisions — particularly gate approvals where a manual review is required — are routed through **The Approval Workflow agent — Approval Workflow**, ensuring that stage transitions are formally authorised and recorded.

---

## What It Uses

- Project records, charter, scope baseline, and artefacts from the platform's data store
- Methodology definitions for each project type (Predictive, Adaptive, Hybrid)
- Stage-gate criteria definitions configured per methodology and organisation
- A machine learning readiness scoring model trained on historical project data
- Health dimension data: schedule performance from the Schedule Planning agent, financial performance from the Financial Management agent, risk status from the Risk Management agent, quality data from the Quality Management agent
- External tool synchronisation: Planview, Clarity, Jira, Azure DevOps
- the Approval Workflow agent — Approval Workflow for gate governance
- Azure Monitor for operational monitoring and alerting

---

## What It Produces

- **Current lifecycle stage** for each project, with transition history
- **Gate assessment results**: pass/fail evaluation of each stage-gate criterion with explanatory detail
- **Health score**: a composite, continuously updated assessment of project performance
- **Readiness predictions**: ML-based probability estimates for upcoming gate outcomes
- **Health dashboard**: a visual representation of the project's health across all dimensions
- **Governance alerts**: notifications when health deteriorates or gate criteria are at risk
- **Methodology recommendations**: suggestions to adapt the delivery approach when circumstances change
- **Stage transition records**: a complete history of every lifecycle transition with dates and authorisation details

---

## How It Appears in the Platform

The lifecycle stage is the primary driver of the **Methodology Map** navigation panel on the left side of the workspace. The map shows the current stage highlighted, with completed stages marked and upcoming stages visible ahead. Stage-gate requirements are shown as a checklist on the relevant stage node — the user can see at a glance which criteria are met and which are still open.

The **health score** is displayed prominently in the project dashboard view, with colour coding indicating overall status: green for healthy, amber for at risk, red for critical. Clicking through shows the breakdown of the score across each dimension.

When a project is approaching a gate, the platform surfaces the readiness prediction in the assistant panel — a project manager can ask "are we ready for the planning gate review?" and receive a structured assessment of the current position.

---

## The Value It Adds

The most expensive governance failures are the ones that are caught late — when a project has been running for six months with a scope that was never properly approved, or has spent through its budget contingency without anyone noticing. The Project Lifecycle and Governance agent catches these situations early by continuously monitoring project health and enforcing gate criteria before transitions happen.

The readiness scoring adds a layer of proactive intelligence that most governance frameworks lack. Rather than waiting for the gate review to discover that three critical artefacts are missing, the agent predicts this situation two weeks earlier and gives the project team time to address it.

---

## How It Connects to Other Agents

The Lifecycle and Governance agent draws health data from **Agents 10, 12, 14 and 15** (Schedule, Financial, Quality, and Risk) to calculate its composite health score. It uses **The Approval Workflow agent — Approval Workflow** for gate governance. Its lifecycle stage data drives the methodology map navigation visible to users, and its outputs feed into **The Analytics Insights agent — Analytics and Insights** for portfolio-level governance reporting. When it detects a methodology mismatch, it can engage **The Scope Definition agent — Project Definition and Scope** to update the project definition accordingly.


---

# the Schedule Planning agent — Schedule and Planning

**Category:** Delivery Management
**Role:** Schedule Builder and Milestone Manager

---

## What This Agent Is

The Schedule and Planning agent transforms a project's scope definition into a working schedule. It takes the Work Breakdown Structure produced during project definition, estimates how long each element will take, maps out the dependencies between tasks, identifies the critical path, and produces a baselined schedule that the project team can deliver against.

It is also the agent that keeps the schedule current throughout delivery — updating progress, identifying delays, forecasting completion dates, and alerting the team when the schedule is under threat. For agile projects, it handles sprint planning and backlog management rather than waterfall scheduling, adapting its approach to match the delivery methodology.

---

## What It Does

**It converts the WBS into a schedule.** Working from the Work Breakdown Structure provided by the Scope Definition agent, the agent creates a task list with durations, dependencies, assigned resources, and scheduled dates. Duration estimates are generated using a combination of AI-based estimation (drawing on historical data from similar projects) and any estimates provided directly by the project team.

**It maps dependencies.** The agent supports all standard task dependency types — finish-to-start, start-to-start, finish-to-finish, and start-to-finish — and maps them across the schedule to create a dependency network. This network is used for critical path analysis and schedule risk assessment.

**It runs Critical Path Method analysis.** The agent identifies the critical path through the schedule — the sequence of tasks that determines the minimum possible project duration. Any delay to a task on the critical path will delay the project. Understanding the critical path allows project managers to focus their attention where it matters most.

**It performs resource-constrained scheduling.** An unconstrained schedule assumes that every task can be resourced whenever it is needed. A realistic schedule reflects the fact that resources are limited. The agent applies resource constraints from the Resource Management agent to produce a schedule that reflects actual availability — delaying tasks or extending durations when the required resources are not available.

**It runs Monte Carlo risk simulations.** Schedule estimates are inherently uncertain. The agent can run probabilistic simulations — testing the schedule against thousands of possible combinations of task duration variations — to produce a probability distribution of completion dates rather than a single deterministic end date. This gives project managers an honest picture of schedule risk: not just the plan, but the confidence interval around it.

**It manages milestones and baselines.** Key milestones are tracked separately and displayed prominently — both in the schedule and in the Timeline Canvas. Once the schedule is approved, it is baselined: the approved plan is stored as a reference, and all subsequent schedule performance is measured against this baseline. Baseline changes require formal approval through the change management process.

**It supports agile sprint planning.** For agile projects, the agent shifts from a task network to a sprint-based view. It supports backlog management, sprint capacity planning, sprint commitment, and sprint progress tracking. The schedule picture for an agile project is sprint velocity and burn-down rather than Gantt charts and critical path analysis.

**It flags schedule risks and delays.** As the schedule progresses, the agent monitors actual completion dates against planned dates, calculates schedule variance, and raises alerts when tasks are late, when the critical path is threatened, or when the forecast completion date has slipped beyond the baselined end date.

---

## How It Works

The agent takes the WBS from the Scope Definition agent and resource availability from the Resource Management agent as its primary inputs. Duration estimates are generated using a hybrid approach: an AI model trained on historical project data produces initial estimates, which can be overridden or supplemented by team input. The dependency network is built from the task structure and any dependency relationships defined in the WBS.

Schedule data is synchronised bidirectionally with connected project management tools — Azure DevOps, Jira, and Microsoft Project — so that the schedule in the platform reflects the current state of work as tracked in the tools the delivery team uses.

---

## What It Uses

- WBS from the Scope Definition agent — Project Definition and Scope
- Resource availability data from the Resource Management agent — Resource and Capacity Management
- Historical project data for AI-based duration estimation
- Dependency type definitions (FS, SS, FF, SF)
- Critical Path Method algorithm
- Monte Carlo simulation engine
- Azure DevOps, Jira, and Microsoft Project connectors for bidirectional synchronisation
- the Approval Workflow agent — Approval Workflow for baseline change approvals
- the Lifecycle Governance agent — Project Lifecycle and Governance as a consumer of schedule performance data

---

## What It Produces

- **Project schedule**: a complete task list with durations, dependencies, resources, and dates
- **Critical path analysis**: identification of the critical path and float available on non-critical tasks
- **Resource-constrained schedule**: an adjusted schedule reflecting actual resource availability
- **Monte Carlo simulation results**: probability distribution of forecast completion dates
- **Milestone register**: a tracked list of key milestones with planned and forecast dates
- **Schedule baseline**: the approved plan stored as a permanent reference
- **Schedule variance report**: comparison of actual progress against the baseline
- **Sprint plans** (for agile projects): sprint capacity, commitment, and burn-down data
- **Schedule risk alerts**: notifications when the critical path or milestone dates are threatened

---

## How It Appears in the Platform

Schedule data is presented primarily through the **Timeline Canvas**, which provides a visual milestone and schedule view. Key milestones are displayed as dated markers on the timeline, with colour coding indicating their status — on track, at risk, or delayed. The timeline can be zoomed to show the full project duration or focused on the current period.

The Gantt-style task view is accessible from the schedule section of the Document Canvas, where the full task list with dependencies and resource assignments can be reviewed. Sprint boards and burn-down charts are displayed in the agile project view.

The assistant panel can be used to ask scheduling questions: "When is the next milestone?" "What is our current schedule variance?" "Which tasks are on the critical path?" — and the agent responds with current data.

---

## The Value It Adds

Producing a realistic, resource-constrained schedule with critical path analysis and Monte Carlo risk simulation is sophisticated work that takes experienced planners significant time. The Schedule and Planning agent does this automatically from the WBS, and keeps it current as the project progresses — eliminating one of the most time-consuming aspects of project management.

The Monte Carlo capability, in particular, adds a level of honesty to schedule reporting that most organisations lack: instead of a single completion date that everyone knows is optimistic, the platform shows the range of likely outcomes and the confidence level associated with the plan date. This helps executives set realistic expectations and make better contingency decisions.

---

## How It Connects to Other Agents

The Schedule and Planning agent receives its WBS input from **The Scope Definition agent** and resource constraints from **The Resource Management agent**. Its schedule performance data feeds into **The Lifecycle Governance agent — Lifecycle and Governance** for health scoring and **The Analytics Insights agent — Analytics and Insights** for portfolio-level schedule reporting. Baseline change requests are processed by **The Change Control agent — Change and Configuration Management**. For agile projects, sprint data connects to **The Quality Management agent — Quality Management** for definition-of-done tracking.


---

# the Resource Management agent — Resource and Capacity Management

**Category:** Delivery Management
**Role:** Resource Allocator and Capacity Planner

---

## What This Agent Is

The Resource and Capacity Management agent manages the people side of project delivery. It maintains a picture of who is available, what skills they have, how much of their time is committed to existing work, and whether the organisation has the capacity to take on new initiatives. It makes resource allocation decisions and helps the organisation avoid the chronic problem of over-committing the same people across too many projects at once.

---

## What It Does

**It maintains a resource pool.** The agent holds a live register of available resources — people, skills, roles, and their allocated working time. Resource profiles include their skills, experience, cost rates, working calendars (including leave and non-working time), and current allocation commitments. This pool is synchronised from the organisation's HR and workforce management systems so that it reflects actual availability rather than an out-of-date spreadsheet.

**It manages resource requests.** When a project needs people, the team creates a resource request specifying the required skills, effort, and timing. The agent receives this request, evaluates the available resource pool, identifies candidates who have the right skills and sufficient availability, and ranks them by fit. The recommended allocation is then routed for approval before the resource is formally committed.

**It validates allocations and detects conflicts.** Before confirming any resource allocation, the agent checks for conflicts — is the proposed resource already committed to another project for the same period? Would the allocation exceed their available capacity? Does it respect any constraint rules — for example, maximum utilisation thresholds or restrictions on splitting a resource across too many concurrent projects? Conflicts are flagged clearly, with the specific clashing commitments identified.

**It forecasts capacity.** Looking ahead, the agent projects how resource demand from the current portfolio and pipeline will develop over the coming weeks and months, and compares that demand against available supply. Where demand is expected to exceed supply — creating a capacity crunch — the agent surfaces this as a portfolio-level risk and recommends options: adjusting project timings, acquiring additional capacity, or renegotiating commitments.

**It tracks utilisation.** The agent monitors actual resource utilisation across the portfolio — how much time each person is actually spending on project work versus their committed allocation — and produces utilisation reports. Both under-utilisation (capacity being wasted) and over-utilisation (people at risk of burnout or delivery degradation) are flagged.

**It integrates with HR and workforce systems.** Resource data is synchronised from Workday, SAP SuccessFactors, and other connected HR systems, ensuring that the resource pool reflects the actual organisational workforce: current employees, contractors, real skill profiles, and live availability calendars.

**It enforces allocation constraints.** Configurable rules govern how resources can be allocated: maximum utilisation percentages, minimum notice periods, restrictions on roles that require specialised access or clearances. The agent applies these rules automatically, preventing allocations that would violate organisational policy.

---

## How It Works

The agent maintains a tenant-scoped resource pool that is updated through scheduled synchronisation with connected HR systems and through manual updates where direct integration is not available. When a resource request is received, the agent runs a skill-matching algorithm to score and rank available candidates, applies constraint checks to eliminate invalid options, and presents a ranked shortlist for review.

Capacity forecasting draws on the scheduled demand from the Schedule Planning agent — Schedule and Planning across all active projects, combined with the available supply from the resource pool, to produce forward-looking supply-demand views at the portfolio level.

---

## What It Uses

- HR and workforce system integrations: Workday, SAP SuccessFactors
- Resource pool definitions with skills, roles, cost rates, and calendars
- Schedule demand data from the Schedule Planning agent — Schedule and Planning
- Portfolio-level resource demand from the Portfolio Optimisation agent — Portfolio Strategy and Optimisation
- Skill matching and ranking algorithm
- Constraint rule definitions configured per organisation
- the Approval Workflow agent — Approval Workflow for resource allocation approvals
- The platform's event bus for publishing allocation and capacity events

---

## What It Produces

- **Resource pool**: a live, synchronised register of available resources with skills, availability, and cost
- **Ranked candidate shortlists**: recommendations for resource requests based on skill fit and availability
- **Allocation records**: confirmed resource commitments with validated capacity checks
- **Conflict reports**: identification of over-allocation or scheduling conflicts
- **Capacity forecast**: forward-looking supply-demand view at project and portfolio level
- **Utilisation report**: actual versus committed utilisation for each resource
- **Constraint violation alerts**: flags for allocations that would breach organisational policy

---

## How It Appears in the Platform

Resource data is accessible through the **Dashboard Canvas**, which shows a portfolio-level resource utilisation view — which roles are over-committed, which projects have unresourced demand, and how capacity is distributed across the portfolio.

At the project level, the resource picture is visible in the project workspace, where allocated resources are shown against each work package in the WBS view. The assistant panel can answer resource questions directly: "Who is available for a business analyst role in Q3?" or "Which projects are competing for the same architect?"

Capacity conflict alerts surface in the methodology map and in the platform's notification centre, drawing attention to situations that need to be addressed.

---

## The Value It Adds

Resource over-allocation is one of the most common and most damaging problems in project delivery. When the same people are committed to too many things, everything runs late and quality suffers — but the problem is often invisible until it has already caused significant impact. The Resource and Capacity Management agent makes the capacity picture transparent and keeps it current, enabling portfolio leaders to make allocation decisions based on facts rather than optimistic assumptions.

The integration with HR systems means that the resource picture always reflects reality: annual leave, internal transfers, new hires, and leavers are all reflected in the capacity view without manual updating.

---

## How It Connects to Other Agents

The Resource and Capacity Management agent is a dependency for multiple other agents. **The Portfolio Optimisation agent — Portfolio Strategy and Optimisation** uses its capacity data for portfolio optimisation. **The Program Management agent — Programme Management** uses it for cross-project resource coordination. **The Schedule Planning agent — Schedule and Planning** uses it for resource-constrained scheduling. **The Financial Management agent — Financial Management** uses resource cost rate data for budget modelling. Resource utilisation data also feeds into **The Analytics Insights agent — Analytics and Insights** for portfolio health reporting.


---

# the Financial Management agent — Financial Management

**Category:** Delivery Management
**Role:** Budget Tracker and Financial Controller

---

## What This Agent Is

The Financial Management agent is the platform's financial intelligence layer for project and portfolio delivery. It tracks budgets, records costs, forecasts spending, analyses variances, and produces the financial reports that project managers, finance teams, and portfolio leaders need to keep investments under control.

It replaces the manual reconciliation processes that consume so much time in most project management offices — the monthly cycle of pulling actuals from the finance system, updating the spreadsheet, recalculating the forecast, and producing the report — with a continuous, automated financial monitoring capability that keeps the financial picture current at all times.

---

## What It Does

**It creates and manages budgets.** When a project is approved, the agent establishes a financial baseline from the cost estimates in the approved business case. This baseline defines the total approved budget, allocated across cost categories — labour, third-party services, licences, hardware, travel, and contingency — and distributed across the project timeline. The baseline is stored as a reference against which all subsequent financial performance is measured.

**It tracks and accrues costs.** As delivery progresses, the agent records actual costs as they are incurred — pulling transaction data from connected ERP systems (SAP, Oracle, NetSuite) and supplemented by cost entries from the project team. Accruals are applied where costs have been incurred but not yet invoiced, giving a more accurate picture of the true cost-to-date than a simple cash-basis view.

**It forecasts spending.** The agent produces an Estimate at Completion (EAC) — a forecast of the total project cost based on actual spending to date and the estimated cost of the remaining work. The forecast is recalculated whenever new actuals are received or the project scope and schedule change. Multiple forecasting methods are available, including top-down percentage adjustment, bottom-up re-estimation, and EVM-based projection.

**It analyses variances.** The agent calculates cost variance — the difference between what was planned to be spent and what has actually been spent — at every level of the project: by cost category, by work package, and at the total project level. It identifies which areas are running over or under budget, analyses the reasons for variances, and flags situations where the variance is approaching or exceeding the approved tolerance.

**It applies Earned Value Management.** For projects where EVM is required, the agent calculates the full suite of earned value metrics: Schedule Variance (SV), Cost Variance (CV), Schedule Performance Index (SPI), Cost Performance Index (CPI), and Estimate to Complete (ETC). These metrics provide an objective, integrated view of both schedule and cost performance.

**It handles multi-currency.** For projects that span multiple countries or involve international suppliers, the agent manages currency conversion, applying configurable exchange rates to produce consistent reporting in the organisation's base currency while preserving the original transaction currency for audit purposes.

**It analyses profitability.** For client-delivery organisations, the agent can track revenue alongside cost to produce profitability analysis at the project level, including ROI tracking against the business case investment commitment and IRR recalculation as actual costs emerge.

**It produces financial reports and dashboards.** The agent generates structured financial reports — cost summaries, variance analyses, forecast comparisons, EVM reports — and populates the financial sections of project and portfolio dashboards.

---

## How It Works

The agent's financial baseline is derived from the business case approved through the Business Case agent, adjusted for any changes approved through the Change Control agent — Change and Configuration Management. Actual cost data flows in from connected ERP systems on a scheduled synchronisation cycle and through manual cost entry in the platform. The agent applies accrual logic, performs currency conversion, and recalculates all financial metrics whenever new data is received.

Budget threshold rules can be configured to trigger alerts automatically — for example, alerting the project manager when actuals reach 80% of the approved budget, or alerting the programme director when the forecast exceeds the baseline by more than 10%.

---

## What It Uses

- Approved business case cost estimates from the Business Case agent as the financial baseline
- ERP system integrations: SAP, Oracle, NetSuite for actual cost data
- Workday and ADP for labour cost data
- Change records from the Change Control agent for budget adjustments
- Schedule data from the Schedule Planning agent for earned value calculations
- Resource cost rate data from the Resource Management agent
- Configurable exchange rates for multi-currency handling
- Budget threshold and alert rules
- the Approval Workflow agent — Approval Workflow for budget change approvals

---

## What It Produces

- **Financial baseline**: the approved budget stored as a permanent reference
- **Cost tracking register**: actual costs recorded against each cost category and work package
- **Forecast (EAC/ETC)**: current estimate of total and remaining project cost
- **Variance analysis**: cost variance at project, work package, and cost category level
- **EVM metrics**: SV, CV, SPI, CPI, and related schedule and cost performance indices
- **Budget threshold alerts**: notifications when spending approaches or exceeds defined thresholds
- **Financial dashboard**: real-time financial summary for the project and portfolio
- **Profitability analysis**: ROI and IRR tracking against the business case commitment
- **Financial reports**: structured period-end reports for governance and finance review

---

## How It Appears in the Platform

The financial picture is surfaced primarily through the **Dashboard Canvas**, where a financial summary panel shows the budget, actuals to date, forecast at completion, and variance percentage. The colour coding gives an immediate health indication — green for on-budget, amber for approaching tolerance, red for exceeding tolerance.

The detailed financial breakdown — cost category analysis, work package costs, EVM metrics — is accessible from the financial section of the project workspace, presented as a structured dashboard with drill-down capability. The Spreadsheet Canvas is available for teams that prefer to review financial data in a tabular format.

The assistant panel can answer financial questions directly: "What is our current cost variance?" "How much budget do we have remaining?" "What is our forecast at completion?" — returning current figures in a conversational format.

---

## The Value It Adds

Financial overruns are one of the most common failure modes in project delivery, and they almost always involve a period of wilful ignorance — the project team knowing the numbers are bad but not having a mechanism to surface and address the issue before it escalates. The Financial Management agent eliminates this by providing continuous, automated financial monitoring that makes variances visible in real time and alerts the right people before thresholds are breached.

For portfolio leaders, the aggregated financial view across all projects — budget versus actuals versus forecast — is essential for managing the organisation's investment effectively. This view is typically only available at month-end in most organisations. The platform makes it available continuously.

---

## How It Connects to Other Agents

The Financial Management agent receives its baseline from **The Business Case agent** (business case) and adjustments from **The Change Control agent** (change management). It provides financial performance data to **The Lifecycle Governance agent — Lifecycle and Governance** for health scoring and to **The Analytics Insights agent — Analytics and Insights** for portfolio financial reporting. Budget overrun risks are surfaced to **The Risk Management agent — Risk and Issue Management** as financial risks. **The Program Management agent — Programme Management** uses it for programme-level financial consolidation.


---

# the Vendor Procurement agent — Vendor and Procurement Management

**Category:** Delivery Management
**Role:** Vendor Lifecycle and Procurement Coordinator

---

## What This Agent Is

The Vendor and Procurement Management agent handles every aspect of the supplier and procurement relationship within a project or programme — from identifying a need for external capability through to contract management, purchase order processing, invoice reconciliation, and ongoing vendor performance tracking.

It is one of the most comprehensive agents in the platform, managing a process that in most organisations spans multiple teams (project management, procurement, legal, finance) and multiple systems (sourcing tools, contract management, ERP). The agent unifies this fragmented process into a single, governed, transparent workflow.

---

## What It Does

**It onboards vendors.** When a new supplier needs to be engaged, the agent manages the onboarding process: capturing vendor details, running risk assessments (including credit checks and sanctions screening), validating that the vendor meets the organisation's procurement standards, and creating a vendor record in the platform and connected procurement systems. It uses Azure Form Recognizer to extract structured data from submitted vendor documents, reducing manual data entry.

**It manages procurement requests.** When a project needs to buy something — a service, a product, a licence, a consultancy engagement — the project team raises a procurement request through the platform. The agent classifies the request by category and complexity, validates it against the available budget (checking with the Financial Management agent), and routes it through the appropriate procurement pathway: a simple purchase for small items, a competitive quotation for medium-value purchases, or a formal RFP process for significant engagements.

**It generates Requests for Proposal.** For competitive procurement, the agent drafts a Request for Proposal (RFP) document, drawing on the project's scope definition and the procurement request to specify the requirement clearly. The RFP is stored in the document canvas and can be reviewed and edited before being issued to shortlisted suppliers.

**It manages proposal evaluation.** When proposals are received from vendors, the agent coordinates the evaluation process — scoring each proposal against predefined criteria (technical capability, commercial terms, delivery approach, risk profile) and consolidating the scores into a comparative evaluation matrix. It uses ML-based vendor scoring to supplement the structured evaluation with a broader capability and risk assessment based on the vendor's historical performance and market data.

**It manages contracts.** Once a vendor is selected, the agent manages the contract lifecycle: creating the contract record from negotiated terms, tracking key dates (commencement, renewal, expiry), managing variations to contract terms, and maintaining a complete contract history. It uses Azure Form Recognizer to extract structured fields from contract documents, reducing the risk of important terms being missed.

**It creates and tracks purchase orders.** Approved procurement commitments result in purchase orders that are created in the platform and synchronised to connected ERP systems (SAP, Oracle, NetSuite). The agent tracks the status of each purchase order — raised, acknowledged, delivered, and closed — and links purchase orders to the corresponding contracts and budget allocations.

**It processes invoices.** As vendor invoices are received, the agent performs three-way matching — verifying that the invoice amount, quantity, and supplier details match the corresponding purchase order and delivery receipt. Matched invoices are routed for payment approval; mismatched invoices are flagged for review with the specific discrepancy identified.

**It tracks vendor performance.** Throughout the engagement, the agent monitors vendor performance against contractual commitments — delivery timescales, quality standards, SLA compliance. It produces vendor scorecards that can be used in future procurement evaluation and maintains a performance history that informs decisions about whether to re-engage a vendor on future work.

---

## How It Works

The agent integrates with enterprise procurement systems — SAP Ariba, Coupa, Oracle Procurement, Microsoft Dynamics — for bidirectional data flow, as well as with the platform's financial management and approval workflow agents. A machine learning-based vendor scoring model supplements structured evaluation criteria with pattern-based assessments of vendor capability and risk.

---

## What It Uses

- The project's budget from the Financial Management agent for financial validation of procurement requests
- The project's scope definition from the Scope Definition agent for RFP drafting
- Integrations with SAP Ariba, Coupa, Oracle Procurement, Microsoft Dynamics 365
- Azure Form Recognizer for document data extraction
- ML-based vendor scoring model for capability and risk assessment
- Risk database client for credit and sanctions screening
- the Approval Workflow agent — Approval Workflow for procurement approvals and contract sign-off
- The event bus for publishing procurement lifecycle events
- ERP integrations (SAP, Oracle, NetSuite) for purchase order synchronisation

---

## What It Produces

- **Vendor records**: onboarded, validated supplier profiles with risk assessment results
- **Procurement requests**: categorised, budget-validated requirements ready for sourcing
- **RFP documents**: structured requests for proposal ready for issue
- **Proposal evaluation matrix**: scored comparison of vendor proposals
- **Contract records**: structured contract data with key dates, terms, and variation history
- **Purchase orders**: approved commitments synchronised to ERP systems
- **Invoice matching results**: three-way match outcomes with discrepancy flags
- **Vendor scorecards**: performance assessments against contractual commitments
- **Procurement dashboard**: pipeline view of all active procurement activities

---

## How It Appears in the Platform

Procurement activity is accessible from the relevant stage of the methodology map — the Procurement or Execution stage, depending on the project type. The **Document Canvas** holds RFP documents, evaluation matrices, and contracts. Purchase orders and invoice status are tracked in the **Spreadsheet Canvas**, providing a tabular view of all commitments and their payment status.

The vendor scorecard is visible from the vendor record in the platform, and can be surfaced in the assistant panel: "How has Vendor X performed on this project?" The procurement pipeline — all active sourcing activities with their current status — is accessible from the project dashboard.

Approval requests for procurement decisions — vendor selection, contract sign-off, invoice approval — appear in the **Approvals** page, routed by the Approval Workflow agent to the appropriate reviewers.

---

## The Value It Adds

Procurement processes in project environments are often poorly governed — RFPs drafted informally, vendor selection decisions poorly documented, contracts filed and forgotten, invoices paid without proper matching. The Vendor and Procurement Management agent applies consistent process governance to every procurement activity, regardless of scale.

For organisations with significant third-party spend, the combination of automated three-way invoice matching, structured vendor performance tracking, and integration with ERP systems delivers meaningful financial control — reducing the risk of overpayment, duplicate payment, and contract non-compliance.

---

## How It Connects to Other Agents

The Vendor and Procurement agent draws on budget data from **The Financial Management agent** and scope context from **The Scope Definition agent**. All approval decisions are managed by **The Approval Workflow agent — Approval Workflow**. Vendor performance data feeds into **The Analytics Insights agent — Analytics and Insights** for portfolio-level supplier reporting. Contracts and procurement records contribute to the compliance evidence tracked by **The Compliance Governance agent — Compliance and Regulatory**.


---

# the Quality Management agent — Quality Management

**Category:** Delivery Management
**Role:** Quality Planner and Test Coordinator

---

## What This Agent Is

The Quality Management agent embeds quality assurance into the project delivery process rather than treating it as an end-of-cycle activity. It plans how quality will be measured and assured, manages the test process, tracks defects, enforces quality gate criteria, and provides the quality data that feeds into project health scoring and stage-gate assessments.

Its presence means that quality does not depend on a single person remembering to run tests or complete a review. It is a systematic, tracked, continuously monitored dimension of every project on the platform.

---

## What It Does

**It creates quality plans.** At the start of a project, the agent produces a quality management plan that defines the quality objectives, the standards that will be applied, the metrics that will be tracked, the review activities that will be conducted, and the gate criteria that must be satisfied before each stage transition. The plan is tailored to the project type and methodology — a quality plan for a software delivery project looks different from one for a capital infrastructure project.

**It manages test cases and test suites.** For technology delivery projects, the agent creates and organises test cases linked directly to the project's requirements register. Each test case specifies the scenario being tested, the expected outcome, the preconditions, and the acceptance criteria. Test cases are grouped into test suites that can be executed together. Test case generation uses the project's requirements as inputs, ensuring comprehensive coverage without requiring the test team to start from scratch.

**It tracks test execution and results.** As tests are run — whether manually or through automated test frameworks — the agent records the results: pass, fail, or blocked. It calculates pass rates, coverage percentages, and defect densities, and tracks these metrics against the quality gate thresholds defined in the quality plan.

**It manages the defect lifecycle.** When a test fails and a defect is identified, the agent creates a defect record with the relevant context: severity, priority, which requirement or test case it relates to, and the environment in which it was found. It tracks defects through their lifecycle — identified, assigned, in progress, resolved, verified — and applies configurable workflows to ensure that defects are not closed without proper verification. It integrates with Azure DevOps and Jira for teams that manage defects in those tools.

**It schedules and tracks reviews and audits.** Quality assurance involves more than testing. The agent schedules formal reviews — design reviews, code reviews, documentation reviews, security audits — tracks whether they have taken place, and records their outcomes. These review records contribute to the evidence base for stage-gate assessments.

**It enforces quality gate criteria.** Before a project can advance past a stage gate, the quality data must meet the defined thresholds: test pass rate above a configured minimum (commonly 95%), defect density below a threshold (commonly 0.05 defects per function point), code coverage above a minimum (commonly 80%), and all critical and high-severity defects resolved. The agent evaluates these criteria and provides a clear pass/fail assessment to the Lifecycle and Governance agent.

**It performs defect trend analysis.** The agent analyses defect patterns over time — identifying which components or requirements are generating the most defects, whether defect rates are improving or worsening as delivery progresses, and whether specific defect categories are recurring — and produces recommendations for targeted quality improvement.

**It integrates with test automation.** For organisations using Playwright or other automated testing frameworks, the agent can ingest automated test results and incorporate them into the quality picture alongside manually executed tests.

---

## How It Works

The agent creates its quality plan from the project's requirements register (from the Scope Definition agent) and methodology configuration. Test case generation uses the requirements as inputs, applying the platform's LLM to produce test scenarios from requirement descriptions. Defect prediction uses an Azure ML model to identify areas of the project most likely to generate defects based on historical patterns — allowing the test effort to be directed where it is most needed.

---

## What It Uses

- Requirements register from the Scope Definition agent — Project Definition and Scope
- Methodology configuration for quality gate thresholds
- Azure DevOps and Jira integrations for bidirectional defect synchronisation
- Playwright automation integration for automated test result ingestion
- Azure ML model for defect prediction and test prioritisation
- TestRail integration for test management
- Code coverage metrics from connected code repositories
- the Lifecycle Governance agent — Project Lifecycle and Governance as the consumer of quality gate assessments
- the Approval Workflow agent — Approval Workflow for formal review and audit approvals

---

## What It Produces

- **Quality management plan**: objectives, standards, metrics, review schedule, and gate criteria
- **Test cases and test suites**: structured test scenarios linked to requirements
- **Test execution results**: pass/fail outcomes with coverage and pass rate metrics
- **Defect register**: tracked defect records with severity, priority, status, and lifecycle history
- **Quality gate assessment**: pass/fail evaluation of quality criteria for each stage gate
- **Defect trend analysis**: patterns and recommendations for quality improvement
- **Review and audit records**: evidence of completed quality activities
- **Quality dashboard**: real-time view of test coverage, pass rates, defect density, and quality gate status

---

## How It Appears in the Platform

Quality data is surfaced in the project workspace in two primary ways. The quality gate status is visible in the **Methodology Map** — the relevant stage shows a quality gate indicator that reflects whether the quality criteria have been met. The detailed quality dashboard — test pass rates, defect density, open defect count by severity — is available in the **Dashboard Canvas**.

Defect records and test cases are managed through the **Spreadsheet Canvas**, where they can be filtered, sorted, and updated. Review schedules appear in the project timeline in the **Timeline Canvas**.

The assistant panel supports quality queries: "How many critical defects are currently open?" "What is our test pass rate?" "Are we on track to pass the quality gate?" — returning current data in conversational format.

---

## The Value It Adds

Quality problems discovered late are vastly more expensive to fix than problems discovered early. The Quality Management agent shifts the quality conversation from a last-minute gate check to a continuous monitoring activity — tracking quality metrics throughout delivery and alerting the team when trends suggest the quality gate will not be met before they actually reach it.

For organisations operating in regulated sectors where quality evidence is required for audit purposes, the combination of structured quality plans, traceable test records, and formal review documentation provides a ready-made evidence base for compliance and assurance reviews.

---

## How It Connects to Other Agents

The Quality Management agent receives requirements from **The Scope Definition agent** and provides quality gate assessments to **The Lifecycle Governance agent — Lifecycle and Governance**. For agile projects, it connects to **The Schedule Planning agent — Schedule and Planning** for sprint definition-of-done tracking. Quality metrics feed into **The Analytics Insights agent — Analytics and Insights** for portfolio-level quality reporting. Release readiness assessments for **The Release Deployment agent — Release and Deployment** depend on quality gate status from this agent.


---

# the Risk Management agent — Risk and Issue Management

**Category:** Delivery Management
**Role:** Risk Identifier, Assessor, and Issue Tracker

---

## What This Agent Is

The Risk and Issue Management agent provides the platform's early warning system for project delivery. It helps teams systematically identify, assess and respond to risks before they become problems, and tracks issues that have already materialised to ensure they are resolved before they escalate into crises.

Risk and issue management is one of the disciplines that most distinguishes experienced project delivery from undisciplined delivery. Done well, it prevents problems. Done poorly — or not at all — it means problems are discovered late, responses are reactive, and the impact on cost, schedule, and quality is far greater than it needed to be. This agent institutionalises the discipline.

---

## What It Does

**It supports risk identification.** The agent prompts the project team to think systematically about risks using structured techniques: reviewing the project's scope, schedule, budget, resources, dependencies, and external environment for things that could go wrong. It also uses a natural language processing model — fine-tuned on risk terminology — to extract potential risks from project documents and meeting notes where they have been described informally but not formally registered.

**It assesses risks quantitatively and qualitatively.** For each identified risk, the agent supports both qualitative assessment (likelihood and impact ratings on a configurable scale) and quantitative analysis. The quantitative analysis uses an Azure ML model to predict probability and impact scores based on historical risk data from similar projects. The combined assessment places each risk in the appropriate cell of the risk matrix.

**It prioritises risks.** The agent calculates a risk exposure score for each risk — combining probability, impact, and urgency — and ranks all risks accordingly. This prioritisation guides where the project team should focus their risk response efforts. The top risks are surfaced prominently in the risk dashboard.

**It runs Monte Carlo simulation for quantitative schedule and cost risk.** For projects where quantitative risk analysis is required, the agent can run Monte Carlo simulations that model the combined effect of all identified risks on the project's schedule and budget. The output is a probability distribution of project outcomes — showing, for example, the probability of completing within budget or the range of likely completion dates — rather than a single optimistic plan.

**It creates and tracks mitigation plans.** For each risk that warrants a response, the agent helps define a mitigation plan: the actions that will be taken to reduce the probability or impact of the risk, who is responsible, and when the actions should be completed. These actions are tracked as tasks within the platform, ensuring that risk responses actually happen rather than being defined and then forgotten.

**It monitors risk triggers.** Many risks have early warning indicators — precursor events that suggest the risk is becoming more likely. The agent monitors configured trigger conditions and raises an alert when a trigger event is detected, prompting the team to review the risk response before the risk fully materialises.

**It manages the issue log.** When a risk materialises — or when a new problem arises that was not previously identified as a risk — it is logged as an issue. The agent tracks issues through their resolution lifecycle: identified, assigned, in progress, resolved. It applies escalation rules to ensure that unresolved issues are escalated to the appropriate level of management before they breach their resolution deadline.

**It generates a risk matrix and dashboard.** The risk matrix provides a visual heat map of the project's risk exposure — plotting each risk by likelihood and impact to give an immediate visual representation of the risk profile. The risk dashboard summarises the top risks, their current status, and the overall risk exposure trend.

**It integrates with GRC systems.** For organisations that manage enterprise risk through ServiceNow or RSA Archer, the agent synchronises project risk data with these systems — ensuring that project-level risks are visible in the enterprise risk picture and that the project benefits from any enterprise-level risk intelligence.

---

## How It Works

The agent uses a BERT-based natural language model, fine-tuned on risk language, to extract potential risks from unstructured project text. The Azure ML model provides probability and impact predictions calibrated against historical project risk data. Monte Carlo simulation applies statistical sampling to model the combined schedule and cost impact of the risk portfolio. The agent stores the risk register in the platform's database and synchronises it with connected GRC and project management tools.

---

## What It Uses

- Project scope, schedule, and budget data from Agents 08, 10, and 12
- A fine-tuned BERT model for risk extraction from project documents
- Azure ML for risk probability and impact prediction
- Azure Cognitive Search for accessing a knowledge base of mitigation guidance
- Monte Carlo simulation engine for quantitative risk analysis
- GRC system integrations: ServiceNow, RSA Archer
- PM tool integrations: Planview, Microsoft Project, Jira, Azure DevOps
- the Approval Workflow agent — Approval Workflow for escalation decisions
- the Lifecycle Governance agent — Lifecycle and Governance as a consumer of risk status data
- Azure Synapse and Data Lake for risk dataset storage

---

## What It Produces

- **Risk register**: a structured record of all identified risks with probability, impact, priority, owner, and response plan
- **Risk matrix**: a heat map visualisation of risk exposure across the project
- **Risk prioritisation**: ranked list of risks by exposure score
- **Monte Carlo simulation results**: probability distribution of schedule and cost outcomes
- **Mitigation plans**: defined actions, owners, and timelines for each prioritised risk response
- **Trigger monitoring alerts**: notifications when risk trigger conditions are detected
- **Issue log**: tracked issues with status, owner, and resolution timeline
- **Risk dashboard**: top risks, exposure trend, and overall risk health indicator
- **Risk report**: structured narrative report suitable for governance review

---

## How It Appears in the Platform

The risk register is accessible from the risk management stage in the **Methodology Map** navigation, and the content is presented in the **Spreadsheet Canvas** where individual risks can be reviewed, updated, and filtered. The risk matrix heat map is displayed in the **Dashboard Canvas**, with colour coding indicating the concentration of risk in each likelihood/impact zone.

The risk dashboard — top risks, exposure trend, open issues — is available both in the project dashboard and as a summary in the portfolio-level dashboard managed by the Analytics Insights agent. The assistant panel supports risk queries: "What are our top five risks?" "Are there any escalated issues?" "What is our current risk exposure trend?"

---

## The Value It Adds

Projects that manage risk proactively experience significantly better outcomes than those that manage it reactively. The Risk and Issue Management agent provides the structure, the prompts, and the tooling to make systematic risk management achievable without requiring the project team to have deep specialist expertise in risk methodology.

The quantitative analysis capabilities — ML-based probability estimation and Monte Carlo simulation — go well beyond what most project teams can do with a spreadsheet, providing an evidence-based, statistically grounded view of project risk exposure that supports better-informed decisions at both the project and portfolio level.

---

## How It Connects to Other Agents

The Risk and Issue Management agent draws on scope, schedule, and financial data from **Agents 08, 10, and 12**. Risk status feeds into **The Lifecycle Governance agent — Lifecycle and Governance** for project health scoring and stage-gate assessments. The risk portfolio feeds into **The Analytics Insights agent — Analytics and Insights** for portfolio risk reporting. Risk-related compliance implications are surfaced to **The Compliance Governance agent — Compliance and Regulatory**. Budget risk data connects to **The Financial Management agent — Financial Management**.


---

# the Compliance Governance agent — Compliance and Regulatory

**Category:** Delivery Management
**Role:** Regulatory Framework Manager and Compliance Monitor

---

## What This Agent Is

The Compliance and Regulatory agent ensures that every project on the platform is managed in accordance with the regulatory frameworks and internal policies that apply to it. It translates abstract compliance obligations into concrete, project-specific requirements; monitors adherence throughout delivery; maintains the evidence needed to demonstrate compliance; and prepares for and supports audit processes.

For organisations operating in regulated sectors — financial services, government, healthcare, defence — compliance is not an optional feature. It is a condition of operation. This agent makes compliance systematic and demonstrable rather than sporadic and anecdotal.

---

## What It Does

**It manages regulatory frameworks.** The agent holds a library of regulatory and policy frameworks relevant to the organisation's operations. Built-in frameworks include the Australian Privacy Act 1988 (APPs), APRA CPS 234, ISO 27001, the Australian Government's Information Security Manual (ASD ISM), and the Protective Security Policy Framework (PSPF). Additional frameworks can be configured by the organisation. Each framework is broken down into its constituent control requirements, which the agent can map to individual projects.

**It defines and maps controls.** For each regulatory requirement, the agent defines the specific control that must be implemented — who must do what, by when, and with what evidence — and maps those controls to the relevant projects, workstreams, or activities. This mapping ensures that each project team knows precisely which compliance obligations apply to their work and what they need to do to satisfy them.

**It conducts compliance assessments.** Periodically, or at governance gate points, the agent assesses each project against its mapped control requirements. The assessment evaluates whether each control has been implemented, whether the required evidence exists, and whether the control has been tested. The result is a compliance scorecard that shows which obligations are met, which are partially met, and which are outstanding.

**It tests controls.** Beyond assessment, the agent supports formal control testing — verifying that a control not only exists in policy but is operating effectively in practice. It records the test approach, the evidence reviewed, the testing outcome, and any exceptions identified.

**It manages the evidence store.** For each control, the agent maintains a collection of evidence snapshots — documents, records, screenshots, or other artefacts that demonstrate the control is in place and operating. Evidence is timestamped, version-controlled, and linked to the specific control and project it relates to. This evidence store is the primary resource for audit preparation.

**It prepares for and supports audits.** When an audit is approaching, the agent prepares an audit readiness package — a structured collection of the evidence, assessments, and control test results that the auditor will need. It tracks the status of audit preparation activity and identifies any evidence gaps that need to be addressed before the audit. During the audit, it provides a structured record of audit queries and responses.

**It monitors regulatory changes.** Regulations change. The agent is designed to monitor for changes to the regulatory frameworks it manages and flag updates that may require new controls to be implemented or existing ones to be revised. This ensures that the compliance picture remains current as the regulatory environment evolves.

**It verifies release compliance.** For technology projects, the agent performs a compliance verification before release — checking that all relevant security scans have been completed, data privacy requirements have been addressed, audit logging is in place, deployment checks have passed, and quality testing is sufficient — providing a compliance clearance for the release to proceed.

---

## How It Works

The agent maintains its control catalogue in a structured internal registry. A simple rules engine evaluates compliance evidence against the defined criteria for each control: whether required documents exist, whether evidence has been uploaded, whether controls have been tested, whether audit logs are present, whether risk mitigations are documented. The rules engine produces a compliance score that is used in the compliance dashboard and stage-gate assessments.

The agent integrates with GRC systems — ServiceNow and RSA Archer — for organisations that manage enterprise compliance programmes through those platforms, ensuring project-level compliance data is visible in the broader enterprise governance picture.

---

## What It Uses

- Built-in regulatory framework library: Privacy Act 1988, APRA CPS 234, ISO 27001, ASD ISM, PSPF
- Configurable additional frameworks and control definitions
- A compliance rule engine for automated assessment against evidence
- GRC system integrations: ServiceNow, RSA Archer
- Document management integration: SharePoint for evidence storage
- the Approval Workflow agent — Approval Workflow for audit preparation and compliance approvals
- the Lifecycle Governance agent — Lifecycle and Governance for gate compliance assessments
- The platform's immutable audit log as a compliance evidence source
- The platform's event bus for compliance status events

---

## What It Produces

- **Regulatory framework register**: the library of applicable frameworks and their control requirements
- **Control mapping**: the specific controls mapped to each project and their obligations
- **Compliance assessment reports**: scored assessments of each project against its controls
- **Control test records**: evidence of formal control testing with outcomes and exceptions
- **Evidence snapshots**: timestamped, version-controlled evidence linked to specific controls
- **Audit readiness package**: structured evidence collection for audit preparation
- **Regulatory change alerts**: notifications when monitored frameworks are updated
- **Release compliance clearance**: pre-release verification that compliance requirements are satisfied
- **Compliance dashboard**: real-time view of overall compliance posture across the project

---

## How It Appears in the Platform

The compliance view is accessible from the Compliance activity in the **Methodology Map** navigation. The compliance dashboard in the **Dashboard Canvas** shows the overall compliance posture — which frameworks apply, what percentage of controls are satisfied, and which items require attention. The evidence store and control mapping are available in the **Spreadsheet Canvas** for detailed review.

Compliance gate assessments are surfaced at the relevant stage gates in the methodology map — a project cannot advance past a compliance gate without the agent confirming that the required controls have been satisfied.

The assistant panel supports compliance queries: "Are we compliant with APRA CPS 234?" "What evidence is missing for our next audit?" "Which controls apply to this project?"

---

## The Value It Adds

Compliance failures in regulated industries carry serious consequences — regulatory sanctions, financial penalties, reputational damage, and operational disruption. Most organisations manage compliance reactively, discovering gaps when audits uncover them. The Compliance and Regulatory agent shifts this to a proactive posture: controls are mapped at the start of the project, evidence is collected continuously, gaps are identified in advance, and audit preparation is a structured, evidence-backed process rather than a last-minute scramble.

For PwC-delivered programmes, this agent provides a ready-made compliance evidence framework that can be configured to the client's regulatory context and used as the basis for regulatory assurance reporting.

---

## How It Connects to Other Agents

The Compliance and Regulatory agent draws evidence from the platform's immutable audit log, from quality test records from **The Quality Management agent**, and from risk registers from **The Risk Management agent**. Compliance gate assessments are provided to **The Lifecycle Governance agent — Lifecycle and Governance**. Release compliance clearance is provided to **The Release Deployment agent — Release and Deployment**. Compliance posture data feeds into **The Analytics Insights agent — Analytics and Insights** for portfolio-level compliance reporting.


---

# the Change Control agent — Change and Configuration Management

**Category:** Operations Management
**Role:** Change Controller and Configuration Authority

---

## What This Agent Is

The Change and Configuration Management agent governs the controlled evolution of a project's scope, schedule, budget, and technical baseline. Every significant change — to what is being built, how it is being built, what it is expected to cost, or when it is expected to complete — passes through this agent to be assessed, approved, and recorded before it takes effect.

Without formal change control, projects drift. Scope expands without budget adjustment. Technical decisions are made informally without assessing their downstream impact. Baselines become meaningless because nobody knows what has and has not changed. This agent prevents that drift by providing the governance structure within which change happens in a controlled and transparent way.

---

## What It Does

**It captures and classifies change requests.** When anyone wants to change something about a project — adding a requirement, removing a deliverable, adjusting a milestone, modifying a technical architecture decision — they raise a change request through the platform. The agent captures the request, classifies it by type and category using natural language analysis (infrastructure, application, process, governance, scope, schedule, budget), and assigns it an initial priority based on urgency and criticality.

**It assesses the impact of changes.** For each change request, the agent analyses the potential impact across multiple dimensions: which other work packages or deliverables are affected, what the schedule implications are, what the cost implications are, and what compliance or security considerations arise. For technical changes, it parses the infrastructure-as-code files in connected repositories — Terraform templates, ARM templates, Bicep files — to identify specific resources and configurations that would be affected.

**It manages the dependency graph.** The agent uses a dependency graph to understand the relationships between components, services, and projects. When a change affects a component, it can trace downstream impacts through the dependency network, identifying everything that depends on the component being changed. This ensures that impact assessments are comprehensive rather than limited to the obvious first-order effects.

**It routes changes for approval.** Based on the impact assessment and the change category, the agent determines the appropriate approval authority and routes the change request through the platform's approval workflow. Minor changes may be approved by the project manager alone. Changes with significant scope, cost, or schedule implications require a change control board. Emergency changes may follow an expedited approval path with post-hoc review.

**It orchestrates change workflows.** Once approved, the agent orchestrates the implementation of the change through a configured workflow — updating the relevant baselines, notifying affected parties, creating implementation tasks, and scheduling verification activities. For technical changes, it integrates with Azure Durable Functions and Logic Apps to orchestrate the deployment workflow.

**It maintains the configuration record.** Beyond managing individual changes, the agent maintains a running record of the current authorised configuration of the project — what is in scope, what the approved schedule and budget are, and what the current technical baseline looks like. This configuration record is always up to date, reflecting every approved change.

**It tracks change metrics.** The agent monitors change activity over time — volume of changes by category, approval rates, time to approval, frequency of emergency changes — and surfaces trends that may indicate underlying scope or delivery management issues.

---

## How It Works

The agent uses a text classification model (NaiveBayesTextClassifier) to categorise incoming change requests without requiring the submitter to select a category manually. The IaC change parser analyses Terraform, ARM, and Bicep files in connected code repositories to extract specific resource-level changes for impact assessment. The dependency graph service uses Neo4j to model and query the network of interdependencies between components.

Change workflows are persisted through Durable Functions or Logic Apps, ensuring that multi-step change processes survive system restarts and that every step is recorded with its outcome and timestamp.

---

## What It Uses

- Change request submissions from the platform interface
- Text classification model for automatic change categorisation
- IaC change parsers for Terraform, ARM, and Bicep files
- Repository integrations: GitHub, GitLab, Azure Repos
- Neo4j dependency graph for impact propagation analysis
- Impact model using linear regression trained on historical change data
- Durable Functions and Logic Apps for workflow orchestration
- the Approval Workflow agent — Approval Workflow for change approval routing
- the Scope Definition agent — Project Definition and Scope for scope baseline updates
- the Schedule Planning agent — Schedule and Planning for schedule baseline updates
- the Financial Management agent — Financial Management for budget baseline updates
- Azure Service Bus for change event publishing

---

## What It Produces

- **Change request records**: structured change submissions with category, classification, and impact assessment
- **Impact assessments**: multi-dimensional analysis of a change's effects on scope, schedule, cost, and dependencies
- **Change approval records**: routed decisions with approver identity, reasoning, and outcome
- **Updated baselines**: revised scope, schedule, and budget baselines reflecting approved changes
- **Configuration record**: current authorised state of the project at any point in time
- **Change log**: complete history of all change requests and their outcomes
- **Change trend metrics**: volume, approval rate, and category breakdown over time
- **Emergency change records**: expedited approvals with post-hoc review tracking

---

## How It Appears in the Platform

Change requests are accessible from the Change Management stage in the **Methodology Map** and appear in the **Approvals** page for reviewers. The change log — a complete history of all requests and decisions — is accessible from the project workspace and presented in the **Spreadsheet Canvas** for review and filtering.

The dependency impact visualisation is shown in the **Tree Canvas**, where the dependency graph can be explored to understand which components are affected by a proposed change. Updated baselines are reflected immediately in the document canvas versions of the scope statement, schedule, and budget documents.

The assistant panel supports change queries: "What changes have been approved this month?" "What is the current status of change request CR-045?" "What would be the impact of removing this requirement?"

---

## The Value It Adds

The most common reason projects overrun their budgets and schedules is uncontrolled change. Scope creep — the gradual accumulation of additions that were never formally approved and never attracted budget or schedule adjustment — is endemic in project delivery. The Change and Configuration Management agent makes scope creep visible and gives the governance structures to control it.

The IaC change analysis capability is particularly valuable for technology programmes where infrastructure changes can have complex, non-obvious downstream effects. By automatically parsing infrastructure code and tracing dependencies, the agent surfaces impacts that a human reviewer might miss.

---

## How It Connects to Other Agents

The Change and Configuration agent coordinates with **Agents 08, 10, and 12** to update scope, schedule, and budget baselines when changes are approved. It works closely with **The Lifecycle Governance agent — Lifecycle and Governance** to assess whether approved changes require a gate review. **The Release Deployment agent — Release and Deployment** relies on its configuration record for deployment readiness assessments. **The Program Management agent — Programme Management** uses it for programme-level change impact analysis.


---

# the Release Deployment agent — Release and Deployment

**Category:** Operations Management
**Role:** Release Coordinator and Deployment Orchestrator

---

## What This Agent Is

The Release and Deployment agent coordinates the controlled movement of project outputs — software releases, infrastructure changes, process updates, or any other deliverable — from the delivery environment into production. It manages release planning, readiness assessment, deployment orchestration, and rollback procedures, ensuring that releases are planned, approved, monitored, and recorded.

For technology delivery programmes in particular, the release process is where months of delivery work either succeeds or fails in its final step. This agent ensures that step is taken carefully, with the right information, at the right time, with a clear path back if things go wrong.

---

## What It Does

**It plans releases.** The agent manages a release calendar, coordinating multiple planned releases across projects and environments. It considers scheduling constraints — maintenance windows, blackout periods, dependencies on other releases — and recommends optimal deployment windows that minimise risk and disruption. Calendar integration ensures that release windows appear alongside other commitments.

**It assesses release readiness.** Before a release can proceed, the agent performs a structured readiness assessment. It checks that all quality gate criteria have been met (from the Quality Management agent), that all relevant change requests have been approved and incorporated (from the Change Control agent), that compliance clearance has been obtained (from the Compliance Governance agent), that the target environment is available and correctly provisioned, and that the deployment plan has been reviewed and approved. Only when all readiness criteria are satisfied — a go/no-go decision — does the agent authorise the deployment to proceed.

**It orchestrates deployments.** Once a deployment is approved to proceed, the agent manages its execution through a structured deployment plan. The plan defines the sequence of deployment steps, the verification checks at each step, the parties responsible for each action, and the conditions that would trigger a rollback. The agent monitors execution against the plan in real time, recording the outcome of each step.

**It manages environment provisioning.** The agent tracks the configuration and availability of each deployment environment — development, test, staging, and production — ensuring that environments are correctly provisioned before a deployment is attempted and that environment configuration drift (where an environment has diverged from its expected configuration) is detected and addressed.

**It performs configuration drift checking.** Environments that have drifted from their approved configuration are a common source of deployment failures. The agent periodically checks each environment against its baseline configuration and flags any drift before a deployment is attempted, giving the team the opportunity to remediate the discrepancy rather than discovering it during deployment.

**It manages rollback procedures.** Every deployment plan includes a defined rollback procedure that specifies how to reverse the deployment if it fails or causes unacceptable issues. The agent manages rollback execution — triggering the rollback steps, monitoring their progress, and confirming when the environment has been successfully restored to its pre-deployment state.

**It generates release notes.** After a successful deployment, the agent produces release notes that summarise what was included in the release, what issues were resolved, what new capabilities were delivered, and any known limitations. Release notes are stored in the document canvas and can be distributed to stakeholders through the communications agent.

**It tracks deployment metrics.** The agent monitors deployment success rates, mean time to recovery, lead time from approval to deployment, and change failure rates. These metrics feed into the continuous improvement process and contribute to the organisation's DevOps maturity assessment.

---

## How It Works

The agent integrates with version control systems (GitHub, GitLab, Azure Repos) to access release artefacts and change sets, and with CI/CD pipeline tools (Azure DevOps, Jenkins) to trigger and monitor deployments. Environment management leverages Azure infrastructure tools. The readiness assessment is a structured gate that aggregates signals from multiple other agents before producing a go/no-go recommendation.

---

## What It Uses

- Quality gate status from the Quality Management agent — Quality Management
- Change approval records from the Change Control agent — Change and Configuration Management
- Compliance clearance from the Compliance Governance agent — Compliance and Regulatory
- Repository integrations: GitHub, GitLab, Azure Repos
- CI/CD pipeline integrations: Azure DevOps
- Environment configuration and drift checking
- Release calendar with maintenance window and blackout period rules
- the Approval Workflow agent — Approval Workflow for deployment authorisation
- the System Health agent — System Health and Monitoring for post-deployment health checks

---

## What It Produces

- **Release plan**: a scheduled, prioritised list of upcoming releases with readiness status
- **Release readiness assessment**: a go/no-go evaluation summarising the status of all readiness criteria
- **Deployment plan**: a step-by-step execution plan with verification checks and rollback procedures
- **Deployment record**: a complete log of each deployment with step-by-step outcomes and timestamps
- **Rollback record**: a log of rollback executions with cause and resolution
- **Environment configuration record**: current state of each environment with drift indicators
- **Release notes**: a summary of each deployment's contents for stakeholder communication
- **Deployment metrics**: success rate, lead time, change failure rate, and mean time to recovery

---

## How It Appears in the Platform

Release planning is accessible from the Release Management stage in the **Methodology Map** and from the **Timeline Canvas**, where upcoming releases are shown as dated milestones. The release readiness dashboard — showing the status of each readiness criterion — is available in the **Dashboard Canvas**.

Deployment approval requests appear in the **Approvals** page. The deployment log and release notes are stored in the **Document Canvas**. The assistant panel can answer deployment questions: "Are we ready to release?" "What was included in last week's deployment?" "Has the production environment drifted from its baseline?"

---

## The Value It Adds

Deployment failures and post-release incidents are expensive — in remediation cost, in business disruption, and in the erosion of confidence in the delivery team. The Release and Deployment agent reduces the risk of deployment failures by enforcing a structured readiness gate, ensuring that releases only proceed when all the conditions for success are in place.

The rollback capability provides a safety net that gives teams the confidence to deploy more frequently — knowing that if something goes wrong, the path back is well-defined and tested.

---

## How It Connects to Other Agents

The Release and Deployment agent is a consumer of quality, compliance, and change data from **Agents 14, 16, and 17**. Deployment success is monitored by **The System Health agent — System Health and Monitoring** post-deployment. Deployment events are recorded in the change log maintained by **The Change Control agent**. Release metrics feed into **The Continuous Improvement agent — Continuous Improvement** for DevOps maturity analysis, and into **The Analytics Insights agent — Analytics and Insights** for portfolio-level delivery reporting.


---

# the Knowledge Management agent — Knowledge and Document Management

**Category:** Operations Management
**Role:** Document Librarian and Knowledge Curator

---

## What This Agent Is

The Knowledge and Document Management agent is the platform's institutional memory. It manages the lifecycle of every document and knowledge artefact in the system — ingesting, classifying, indexing, and curating content so that the right information is findable and accessible to the right people at the right time.

Beyond simple document storage, it builds a knowledge graph that connects related documents, extracts and links concepts and entities across the document library, and enables intelligent search that understands meaning rather than just keywords. Over time, it becomes an organisational intelligence asset — capturing what the organisation knows about how to deliver projects, and making that knowledge available to every team that needs it.

---

## What It Does

**It ingests documents from multiple sources.** The agent accepts documents from many origins: directly through the platform's document canvas, uploaded by users, pulled from connected repositories (GitHub, SharePoint, Confluence, Google Drive), or generated by other platform agents. Each document is processed on ingestion — classified, indexed, and stored in the knowledge base.

**It classifies and tags documents.** Using entity extraction and document classification logic, the agent assigns each document to a category (project charter, risk register, status report, technical specification, lessons learned, policy, and so on) and extracts key entities — project names, organisations, technologies, dates, people — that are used to build the searchable index. This classification happens automatically on ingestion, without requiring the submitter to manually tag documents.

**It enables semantic search.** The agent provides a search capability that understands meaning rather than relying purely on keyword matching. It uses sentence-transformer models to create vector embeddings of document content and queries, enabling it to find conceptually relevant documents even when they do not contain the exact words in the search query. Results are ranked by semantic relevance and presented with contextual excerpts that show why each result matched the query.

**It builds and maintains a knowledge graph.** Beyond indexing individual documents, the agent builds a network of relationships between them: this risk register relates to that project charter; this lessons learned document is relevant to that type of initiative; this technical specification supersedes an earlier version. The knowledge graph makes it possible to navigate related content and to understand the connections between documents rather than treating each one in isolation.

**It manages document versioning and curation.** Documents in the platform are versioned — every change creates a new version, and the full version history is preserved. The agent manages a curation workflow through which documents can be annotated, reviewed, and formally approved, with the approval status visible to all users. Curated, approved documents are distinguished from working drafts in the search results.

**It captures lessons learned.** After each project, or at any point during delivery when a significant learning emerges, the agent supports the structured capture of lessons learned: what happened, what the impact was, what should be done differently, and which project types and contexts the lesson is most relevant to. Captured lessons are indexed and searchable, making institutional learning accessible to future project teams.

**It produces document summaries.** For long documents, the agent can generate a concise summary — an executive overview of the key points — that allows readers to quickly assess the relevance of a document before reading it in full. Summaries are generated on request and displayed alongside search results.

---

## How It Works

The agent uses spaCy and regex-based entity extraction to identify and extract key information from document content. Sentence-transformer models produce the vector embeddings used for semantic search. SQLite-backed database storage manages the document registry, version history, tags, and knowledge graph nodes and edges. The knowledge graph is built incrementally as documents are ingested and updated.

A test suite for this agent verifies the accuracy of entity extraction, the quality of semantic search ranking, the correctness of the knowledge graph relationship structure, and the behaviour of the curation workflow.

---

## What It Uses

- Documents from the platform's document canvas, uploads, and connected repositories
- GitHub repository integration for code and documentation ingestion
- SharePoint and Confluence connectors for enterprise knowledge base ingestion
- spaCy and regex for entity extraction
- Sentence-transformer models for semantic embedding
- Vector-based similarity search for semantic search ranking
- SQLite knowledge database for document storage and indexing
- A curation workflow for formal document review and approval
- the Stakeholder Communications agent — Stakeholder Communications as a consumer of document content for communications
- the Analytics Insights agent — Analytics and Insights for knowledge base analytics

---

## What It Produces

- **Indexed document library**: a classified, tagged, searchable collection of all project knowledge
- **Semantic search results**: relevance-ranked results with contextual excerpts, understanding meaning not just keywords
- **Knowledge graph**: a network of relationships between documents and the entities they reference
- **Document summaries**: AI-generated executive overviews of document content
- **Lessons learned register**: a searchable library of structured lessons captured from project experience
- **Version history**: a complete record of every change to every document
- **Curation records**: a log of document review and approval decisions
- **Entity extraction results**: structured data identifying key concepts, organisations, and people across the document library

---

## How It Appears in the Platform

The document library is accessible through the **Document Search** page, which provides a full-text and semantic search interface across all platform documents. Search results are presented with relevance scoring, document type indicators, and contextual excerpts. Filters allow results to be narrowed by document type, project, date, or author.

Within the project workspace, documents are navigable through the **Tree Canvas**, which shows the hierarchical structure of the project's document library with folder organisation and cross-links between related documents. The **Document Canvas** provides the authoring and editing environment for individual documents.

The lessons learned library is accessible from the **Lessons Learned** page, where captured insights can be searched and browsed by project type, phase, and topic. The assistant panel can answer knowledge queries: "Are there any lessons learned relevant to vendor onboarding?" "What documents relate to this project's security architecture?"

---

## The Value It Adds

Organisational knowledge accumulated through project delivery is one of the most valuable — and most underutilised — assets in any enterprise. Most of it is locked in documents that live in siloed systems, are poorly indexed, and are effectively invisible to teams working on related problems. The Knowledge and Document Management agent unlocks this value by making every document semantically searchable and by surfacing relevant prior knowledge to teams that need it.

The lessons learned capability in particular addresses a chronic weakness in project delivery: lessons are often captured at the end of a project but never actually applied to future work because the mechanism for doing so does not exist. By indexing lessons and making them searchable and accessible in context, the agent creates a feedback loop between past experience and future delivery.

---

## How It Connects to Other Agents

The Knowledge and Document Management agent receives documents from every other agent in the platform — charters from **The Scope Definition agent**, risk registers from **The Risk Management agent**, quality plans from **The Quality Management agent**, procurement records from **The Vendor Procurement agent**, and so on. It provides document content to **The Stakeholder Communications agent — Stakeholder Communications** for communications drafting and to **The Response Orchestration agent — Response Orchestration** for context enrichment. Its knowledge base feeds **The Continuous Improvement agent — Continuous Improvement** with the lessons and process data needed for improvement analysis.


---

# the Continuous Improvement agent — Continuous Improvement and Process Mining

**Category:** Operations Management
**Role:** Process Analyst and Improvement Engine

---

## What This Agent Is

The Continuous Improvement and Process Mining agent analyses how the organisation's projects are actually being delivered — not how the methodology says they should be delivered, but what the data shows about what really happens. It identifies where processes are slow, where steps are being skipped, where the same problems recur, and what changes would have the most meaningful impact on delivery performance.

It turns the accumulated data from every project on the platform into actionable intelligence about how to improve. This is the agent that creates the feedback loop between delivery experience and methodology evolution — ensuring that the organisation gets progressively better at project delivery, not just faster at repeating the same mistakes.

---

## What It Does

**It ingests and analyses event logs.** Every action taken in the platform generates an event: a task completed, a gate passed, a risk raised, a document approved, a deployment executed. The agent ingests these event streams and builds process traces — timelines showing the actual sequence of activities for each project. This creates an empirical record of how processes are actually executed.

**It discovers process models.** Using process mining algorithms, the agent derives actual process models from the event data — BPMN diagrams and Petri nets that represent the typical flow of activities as they actually occur. These discovered models can be compared against the intended methodology to identify where practice diverges from policy.

**It performs conformance checking.** The agent checks each project's actual process trace against the expected process model, identifying deviations: steps taken out of sequence, mandatory activities skipped, gates passed without required evidence, activities that are being repeated when they should happen once. These deviations are categorised by severity and frequency.

**It detects bottlenecks.** By analysing waiting time at each stage of each process, the agent identifies where work is getting stuck — the handoffs that take longest, the approval queues that are consistently backed up, the activities that take far longer than they should. Bottleneck detection reveals the process constraints that have the greatest impact on overall delivery speed.

**It analyses root causes.** When a pattern of problems is identified, the agent attempts to find the underlying cause. It applies correlation analysis to identify which project characteristics, team attributes, or process choices are statistically associated with poor outcomes — whether certain types of project consistently overrun, whether certain approval chains consistently cause delays, whether certain teams consistently skip documentation steps.

**It manages an improvement backlog.** The agent creates and maintains an improvement backlog — a prioritised list of process improvement opportunities, each with an assessment of the benefit it would deliver and the effort required to implement it. This backlog is visible to the improvement team and can be used to plan and track improvement initiatives.

**It tracks benefit realisation.** When improvement initiatives are implemented, the agent monitors subsequent process performance to assess whether the improvement has delivered the expected benefit. This closes the loop between improvement action and outcome measurement, ensuring that improvement efforts are evidence-based rather than aspirational.

**It benchmarks against best practices.** The agent can compare the organisation's process performance against industry benchmarks and the platform's library of best practices — identifying where the organisation's delivery performance lags behind the sector and providing specific recommendations for closing the gap.

---

## How It Works

The agent ingests event logs from the platform's audit trail, orchestration services, and domain agents. It applies process mining algorithms to build process models and perform conformance analysis. Waiting time analysis identifies bottleneck stages. Correlation analysis links process characteristics to outcomes. The improvement backlog is persisted and managed as a structured data store, with priority scoring that combines benefit size, implementation effort, and strategic alignment.

A test suite verifies the event ingestion logic, the accuracy of process discovery, the conformance checking algorithm, and the compliance rate calculation methodology.

---

## What It Uses

- Event logs from the platform's audit trail and orchestration services
- Process events from all domain agents
- Analytics reports from the Analytics Insights agent — Analytics and Insights
- The knowledge base from the Knowledge Management agent — Knowledge and Document Management for best practice recommendations
- Process mining algorithms for model discovery and conformance checking
- Waiting time analysis for bottleneck detection
- Correlation analysis for root cause identification
- Industry benchmark data for performance comparison
- the Approval Workflow agent — Approval Workflow for improvement workflow automation

---

## What It Produces

- **Discovered process models**: BPMN and Petri net representations of how processes actually flow
- **Conformance reports**: assessments of where actual practice deviates from intended methodology
- **Bottleneck analysis**: identification of the stages with the greatest waiting time and delay
- **Root cause assessments**: analysis of the factors most correlated with delivery problems
- **Improvement backlog**: a prioritised list of improvement opportunities with benefit and effort estimates
- **Benefit realisation tracking**: measurement of the impact of implemented improvements
- **Benchmark comparison**: performance relative to industry standards and best practices
- **Process performance KPIs**: throughput time, cycle time, deviation frequency, and improvement trend over time

---

## How It Appears in the Platform

The continuous improvement view is accessible from the Closing stage of the methodology map — the natural home for retrospective analysis — and from the portfolio analytics view. The process conformance report is presented as a visualisation showing the discovered process model with deviations highlighted in a distinctive colour.

The improvement backlog is managed in the **Spreadsheet Canvas**, where improvement items can be filtered, prioritised, assigned, and tracked. The bottleneck analysis is presented as a process flow diagram showing relative waiting times at each step.

The assistant panel supports improvement queries: "Where are our biggest process bottlenecks?" "Which projects are showing the most conformance deviations?" "What improvements have we implemented this quarter and what impact have they had?"

---

## The Value It Adds

Most organisations conduct end-of-project retrospectives but rarely convert the insights into systematic process improvements. The Continuous Improvement and Process Mining agent automates the analysis that a retrospective should produce — finding the actual patterns in delivery data rather than relying on what people remember and choose to share in a meeting — and creates the structured improvement backlog needed to act on those insights.

The process mining capability, in particular, provides a level of organisational self-knowledge that most enterprises simply do not have. Organisations typically know what their process is supposed to look like. They rarely know what it actually looks like in practice — which steps are consistently skipped, which sequences never actually happen, which controls are bypassed informally. This agent makes the invisible visible.

---

## How It Connects to Other Agents

The Continuous Improvement agent ingests data from virtually every other agent via the audit log and event streams. It draws on knowledge from **The Knowledge Management agent** for best practice comparisons and recommendations. Its findings feed into **The Analytics Insights agent — Analytics and Insights** for portfolio-level improvement reporting. Improvement workflow automation is handled by **The Approval Workflow agent — Approval Workflow**. Process improvement insights may trigger updates to methodology definitions, which are reflected in **The Lifecycle Governance agent — Lifecycle and Governance**.


---

# the Stakeholder Communications agent — Stakeholder Communications

**Category:** Operations Management
**Role:** Communications Planner and Engagement Manager

---

## What This Agent Is

The Stakeholder Communications agent manages the relationship between a project or programme and the people who have a stake in its outcome. It plans communications, drafts messages, coordinates delivery across multiple channels, tracks whether stakeholders are engaged, collects feedback, and ensures that the right people receive the right information at the right time.

Communication failure is one of the most frequently cited causes of project difficulty — stakeholders who feel uninformed, executives who are surprised by bad news, teams who lack the context they need to support delivery. This agent systematises communication so that it is consistent, timely, and appropriate to each audience.

---

## What It Does

**It maintains a stakeholder register.** The agent holds a structured register of all stakeholders for each project or programme: who they are, what their interest and influence levels are, how they prefer to receive communications, what their engagement level currently is, and what their history of interaction with the project looks like. The register is used to drive all communication planning and execution.

**It classifies stakeholders.** Using an influence/interest matrix, the agent classifies each stakeholder into a quadrant — high influence/high interest (key players to be managed closely), high influence/low interest (to be kept satisfied), low influence/high interest (to be kept informed), low influence/low interest (to be monitored). This classification drives the communication frequency, depth, and channel appropriate for each stakeholder.

**It creates communication plans.** Based on the stakeholder register and the project's communication requirements, the agent creates a communication plan that specifies what communications will be sent, to whom, through which channel, at what frequency, and for what purpose. The plan covers routine communications — weekly status reports, monthly portfolio updates — as well as event-driven communications — gate decisions, risk escalations, significant schedule changes.

**It drafts and personalises messages.** When a communication is due, the agent drafts it using the platform's LLM, drawing on current project data — status, health score, key milestones, recent decisions — to produce accurate, timely content. Messages are personalised to the recipient: an executive receives a high-level strategic summary; a project manager receives a detailed operational update; a workstream lead receives information specific to their area. Personalisation also covers tone, language, and level of technical detail.

**It delivers across multiple channels.** Messages are delivered through whichever channel each stakeholder prefers — email, Microsoft Teams, Slack, SMS, push notification, or the platform's notification centre. Consent is enforced: the agent only delivers to channels for which consent has been recorded. For stakeholders who receive high volumes of messages, digest batching consolidates multiple notifications into a single, organised summary.

**It supports multiple languages.** Notification templates are available in multiple languages. Messages are generated in the recipient's preferred language where configured, ensuring that international stakeholders receive communications in a language they can engage with easily.

**It schedules events and meetings.** The agent can schedule project meetings, review sessions, and governance events — creating calendar invitations through Microsoft Calendar integration and tracking attendance. It can also generate meeting agendas based on the current project status and the topics relevant to each meeting type.

**It collects feedback and tracks sentiment.** Following communications, the agent can collect structured feedback from stakeholders and analyse the sentiment of any informal comments or responses received. Sentiment tracking provides an ongoing indicator of stakeholder mood — identifying stakeholders who are becoming disengaged or concerned before those feelings become a project risk.

**It tracks engagement metrics.** The agent monitors engagement with each communication — whether emails are opened, whether meeting invitations are accepted, whether feedback is provided — and produces an engagement health score for each stakeholder. Low engagement triggers a prompt to review the communication approach for that individual.

**It synchronises with CRM systems.** For organisations that manage stakeholder relationships through Salesforce or other CRM platforms, the agent synchronises stakeholder profiles and communication history, ensuring consistency between the project communications record and the enterprise relationship management system.

---

## How It Works

The agent uses the platform's LLM gateway to generate message content from project data inputs. Template localisation ensures that messages are formatted correctly for each recipient's preferred language. Delivery is managed through the notification service, which handles routing to email, Teams, Slack, and other channels. Communication history is persisted to a database store that maintains the full record of every interaction with every stakeholder.

A test suite verifies channel resolution logic, digest queue behaviour, template localisation, and delivery metrics tracking.

---

## What It Uses

- Stakeholder register from the Scope Definition agent — Project Definition and Scope (initial population)
- Current project status data from multiple agents for message content
- The platform's LLM gateway for message drafting and personalisation
- Localised communication templates (English, French, and extensible to other languages)
- Email, Microsoft Teams, Slack, SMS, and push notification channels
- Microsoft Calendar integration for event scheduling
- Sentiment analysis for feedback processing
- Salesforce CRM integration for stakeholder profile synchronisation
- the Approval Workflow agent — Approval Workflow for communications that require sign-off before sending
- The notification service for outbound message delivery

---

## What It Produces

- **Stakeholder register**: classified, profiled record of all project stakeholders
- **Communication plan**: scheduled calendar of all planned project communications
- **Drafted messages**: LLM-generated, data-driven, personalised communications
- **Multi-channel delivery records**: confirmation of message delivery with timestamp and channel
- **Engagement metrics**: open rates, response rates, and engagement health scores per stakeholder
- **Sentiment analysis results**: mood indicators derived from stakeholder feedback and responses
- **Meeting schedules and agendas**: calendar invitations with structured agenda items
- **Communication history**: complete log of every interaction with every stakeholder
- **Digest notifications**: consolidated summary messages for high-volume recipients

---

## How It Appears in the Platform

The **Notification Centre** page in the platform provides a consolidated view of all outbound communications — what was sent, to whom, when, and through which channel. Stakeholders can view their own notification preferences and communication history.

The stakeholder register and communication plan are accessible from the Communications stage in the **Methodology Map** and are presented in the **Spreadsheet Canvas** for detailed management. The engagement metrics dashboard — showing stakeholder engagement levels and sentiment trends — is available in the **Dashboard Canvas**.

The assistant panel can generate communications on request: "Draft a status update for the executive steering committee" or "Send a milestone alert to the project sponsors" — producing a draft message that can be reviewed before sending.

---

## The Value It Adds

Poor stakeholder communication is a perennial project risk. The Stakeholder Communications agent ensures that communication is planned, consistent, personalised, and measured — rather than ad hoc, inconsistent, and unmeasured. For complex programmes with dozens of stakeholders across multiple organisations, this level of communication management would require dedicated resource without the agent.

The sentiment tracking and engagement metrics provide an early warning system for stakeholder problems. A disengaged executive or a stakeholder whose messages are consistently being ignored is a risk to project success. The agent makes these signals visible before they become crises.

---

## How It Connects to Other Agents

The Stakeholder Communications agent draws content from project data across the platform — health scores from **The Lifecycle Governance agent**, financial data from **The Financial Management agent**, risk updates from **The Risk Management agent**, milestone data from **The Schedule Planning agent**. It uses the knowledge base from **The Knowledge Management agent** for context. Formal communications requiring approval are routed through **The Approval Workflow agent — Approval Workflow**. Engagement and sentiment data feeds into **The Analytics Insights agent — Analytics and Insights** for stakeholder health reporting.


---

# the Analytics Insights agent — Analytics and Insights

**Category:** Operations Management
**Role:** Portfolio Intelligence and Reporting Engine

---

## What This Agent Is

The Analytics and Insights agent is the platform's intelligence layer — the capability that turns the raw data generated by every other agent and every connected system into meaningful, decision-ready information. It powers the dashboards, reports, and predictive insights that allow executives, portfolio managers, and programme leaders to understand what is happening across the portfolio and act on what they see.

It is the agent that answers the questions that matter most to leadership: which projects need attention, where is the portfolio over-committed, are we delivering value, and where are we heading if nothing changes.

---

## What It Does

**It aggregates data across the portfolio.** The agent continuously ingests data from every domain agent and every connected source system — project status, financial performance, schedule variance, risk exposure, quality metrics, resource utilisation, stakeholder engagement — and aggregates it into a consistent, portfolio-level picture. Events are ingested in real time through the platform's event bus, and historical data is loaded from Azure Synapse Analytics.

**It computes KPIs.** From the aggregated data, the agent calculates a comprehensive set of Key Performance Indicators at project, programme, and portfolio level. Schedule KPIs (milestone achievement rate, schedule performance index, days late per project), financial KPIs (budget variance, forecast accuracy, cost performance index), quality KPIs (defect density, test pass rate, technical debt ratio), resource KPIs (utilisation rate, capacity constraint frequency), and risk KPIs (risk exposure score, open issue count) are all calculated and maintained as time series, so that trends are visible alongside current values.

**It creates and manages dashboards.** The agent builds configurable dashboards for different audiences and purposes — an executive portfolio health dashboard, a programme manager delivery dashboard, a project-level operational dashboard, a financial management dashboard. Each dashboard is composed of appropriate visualisations: trend charts, scorecard tiles, heat maps, and tabular summaries. Dashboards can embed Power BI reports where deeper analytical drill-down is required.

**It runs predictive forecasting.** Using Azure ML models trained on historical delivery data, the agent predicts future project outcomes from current trajectory data. It forecasts the probability of completing on schedule and within budget, estimates the likely completion date range, and identifies projects that are trending towards an overrun before the overrun has actually occurred. These predictions are surfaced as alerts and as forecast indicators on project dashboards.

**It performs scenario analysis.** The agent supports what-if queries — allowing portfolio leaders to model the impact of portfolio changes on the overall delivery picture. What happens to portfolio completion dates if the top risk materialises? What is the financial impact if this programme is delayed? How does resource utilisation change if these two projects are merged?

**It generates narrative reports.** Beyond dashboards and charts, the agent generates written reports that interpret the data — executive summaries, monthly portfolio performance reports, programme health narratives. These reports are produced using the platform's LLM gateway, which combines structured data inputs with narrative generation to produce readable, accurate, context-appropriate documents.

**It delivers natural language query responses.** Users can ask questions about the portfolio in plain English through the assistant panel and receive data-driven answers: "Which projects are most at risk of overrunning?" "What is our portfolio-level cost variance this month?" "Which programme is furthest ahead of schedule?" The agent interprets the query, retrieves the relevant data, and returns a structured response.

**It tracks data lineage.** For every metric it reports, the agent maintains a record of where the underlying data came from, how it was transformed, and what quality score it has been assigned. This lineage record supports auditability and compliance — particularly important for regulated sectors where the provenance of reported data must be demonstrable.

**It orchestrates the analytics ETL pipeline.** The agent manages the Azure Data Factory pipelines that load, transform, and stage data for analytics — monitoring pipeline health, detecting failures, and triggering reruns when a pipeline job fails.

---

## How It Works

The agent is built on an Azure analytics stack: Azure Synapse Analytics for data warehousing, Azure Data Lake Storage for raw data, Azure Data Factory for ETL pipeline management, Azure Event Hub for real-time event ingestion, Azure ML for predictive modelling, and Power BI Embedded for rich analytical visualisation. The agent orchestrates all of these services and provides a unified interface for the rest of the platform to access analytics capabilities.

KPI computation is event-driven for real-time metrics and batch-processed for period-end summaries. The LLM gateway is used for narrative report generation and natural language query interpretation.

---

## What It Uses

- Event streams from all domain agents via the platform's event bus
- Historical data from Azure Synapse Analytics
- Azure Data Lake Storage for raw data
- Azure Data Factory for ETL pipeline management
- Azure Event Hub for real-time event ingestion
- Azure ML for predictive KPI models
- Power BI Embedded for rich dashboard visualisation
- The platform's LLM gateway for narrative generation and NL query
- the Lifecycle Governance agent — Lifecycle and Governance for project health data
- the Financial Management agent — Financial Management for financial performance data
- the System Health agent — System Health and Monitoring for platform operational data

---

## What It Produces

- **Portfolio health dashboard**: real-time scorecard of all active projects with health indicators
- **KPI time series**: tracked metrics at project, programme, and portfolio level, updated continuously
- **Predictive forecasts**: probability-based predictions of schedule and cost outcomes
- **Scenario analysis results**: modelled impact of portfolio changes
- **Narrative reports**: LLM-generated written reports with data-driven insights and interpretations
- **Natural language query responses**: conversational answers to portfolio questions
- **Embedded Power BI reports**: rich interactive analytics with full drill-down capability
- **Data lineage records**: provenance and quality information for every reported metric
- **KPI alerts**: notifications when key metrics breach configured thresholds

---

## How It Appears in the Platform

The Analytics and Insights agent powers the **Dashboard Canvas** — the primary analytics view for every project, programme, and portfolio in the platform. The dashboard is composed of configurable panels that can show whichever KPIs and visualisations are most relevant to the current user and context.

At the portfolio level, the executive dashboard provides a heat-map style overview of all active initiatives — colour-coded by health status, with click-through to any project for detail. At the project level, the dashboard shows the full set of project KPIs with trend lines and forecast indicators.

Reports generated by the agent are stored in the **Document Canvas** and can be distributed through the **Stakeholder Communications** agent. The assistant panel is the primary interface for natural language queries and ad hoc analytics requests.

---

## The Value It Adds

Decision quality is only as good as the information available. Most portfolio leaders operate with a monthly status report that is already two weeks out of date by the time they read it — and which shows them what happened rather than what is likely to happen. The Analytics and Insights agent provides continuous, real-time portfolio intelligence with forward-looking predictive capability, transforming the information available to leadership from a rearview mirror into a navigation system.

The natural language query capability means that executives do not need to learn how to operate BI tools or navigate complex dashboards. They can ask the question in plain English and receive a direct, data-grounded answer.

---

## How It Connects to Other Agents

The Analytics and Insights agent is a consumer of data from every other agent in the platform. It has a particularly close relationship with **The Lifecycle Governance agent** (project health), **The Financial Management agent** (financial performance), **The Risk Management agent** (risk exposure), and **The System Health agent** (platform operational health). It provides data and dashboards back to the platform's UI layer and supports **The Stakeholder Communications agent — Stakeholder Communications** with the performance data needed to produce communications.


---

# the Data Synchronisation agent — Data Synchronisation and Quality

**Category:** Operations Management
**Role:** Data Integrity Guardian and Sync Coordinator

---

## What This Agent Is

The Data Synchronisation and Quality agent is the platform's data steward. It governs the flow of data between the platform and every connected source system — ensuring that what the platform knows about projects, resources, finances, and risks accurately reflects what is recorded in the systems of record, and that the quality of that data meets the standards required for reliable analytics and decision-making.

Without this agent, the platform's value depends on the quality of data integration happening correctly and continuously. With it, data synchronisation is governed, monitored, and quality-assured — and the platform can be trusted to reflect the real state of the enterprise's projects.

---

## What It Does

**It orchestrates data synchronisation from connected systems.** The agent manages scheduled and triggered synchronisation jobs that pull data from connected source systems — Planview, SAP, Jira, Workday, and other connected platforms — and load it into the platform's canonical data model. Each sync job is configured with a source connector, a mapping definition, a quality threshold, and a conflict resolution strategy.

**It validates data against canonical schemas.** Every record ingested from a source system is validated against the platform's canonical schema for that entity type. The validation checks that required fields are present, that values are of the correct type and within acceptable ranges, and that relationships between entities are consistent. Records that fail validation are quarantined, the failure reason is recorded, and an alert is raised so that the issue can be investigated and resolved.

**It applies field and entity mapping.** Source systems rarely organise their data in the same way as the platform's canonical model. The agent applies configurable mapping rules that translate each source system's field names, data types, and value conventions into the platform's standard format. This mapping is defined in mapping rule files that can be updated without code changes when source systems change their data structures.

**It detects and resolves conflicts.** When the same entity appears differently in two connected sources — for example, a project's end date recorded differently in Planview and Jira — the agent detects the conflict and applies a configured resolution strategy: last-write-wins (the most recent update prevails), timestamp-based (the most recently modified record prevails), authoritative-source (one system is designated as the source of truth), prefer-existing (keep the platform's current value), or manual (flag the conflict for human resolution). The chosen strategy is configurable per entity type and per connector.

**It detects and merges duplicate records.** When the same real-world entity has been created multiple times — the same project appearing as two records, the same vendor registered twice — the agent uses fuzzy matching (with rapidfuzz) to identify likely duplicates and either merges them automatically or flags them for manual review. This prevents the fragmentation and inconsistency that accumulates when integration issues are not actively managed.

**It maintains data quality metrics.** For every data domain, the agent calculates quality scores across multiple dimensions: completeness (are required fields populated?), consistency (do related records agree?), timeliness (how recently was the data updated?), uniqueness (are there duplicate records?), schema compliance (does the data conform to the defined schema?), and auditability (is the lineage of each record traceable?). These scores are surfaced in the data quality dashboard.

**It manages the retry queue.** When a synchronisation job fails — because a source system is unavailable, or a record fails validation — the agent adds the failed record to a retry queue and reattempts the synchronisation after a configured delay. Failed records that cannot be resolved automatically are escalated for manual investigation.

**It emits data quality events.** Sync completions, quality threshold breaches, conflict detections, and duplicate identifications are all published as events on the platform's event bus, allowing other agents and monitoring systems to respond to data quality issues as they arise.

---

## How It Works

The agent is built around a set of connector-specific synchronisation pipelines, each defined by a manifest that specifies the source connector, the entity types being synced, the mapping rules, the quality thresholds, and the conflict resolution strategy. These pipelines are orchestrated by the agent on a configured schedule or triggered by events. Azure Data Factory is used for batch synchronisation; Azure Event Grid and Service Bus handle event-driven updates. Azure Key Vault manages the credentials needed to connect to each source system, accessed through a task-local secret context that prevents credential leakage.

The agent uses rapidfuzz for fuzzy matching in duplicate detection, providing probabilistic similarity scores rather than exact-match only.

---

## What It Uses

- Connector integrations: Planview, SAP, Jira, Workday (and all other connected systems)
- Mapping rule definitions for each connector and entity type
- Quality threshold rules per entity type and quality dimension
- Conflict resolution strategy definitions
- Azure Data Factory for batch ETL
- Azure Event Grid and Service Bus for event-driven sync
- Azure Key Vault for credential management
- Azure Cosmos DB and SQL for data storage
- Azure Log Analytics for sync monitoring and telemetry
- rapidfuzz for duplicate detection via fuzzy matching
- the Analytics Insights agent — Analytics and Insights for data quality reporting

---

## What It Produces

- **Synchronised data**: validated, mapped, quality-checked records loaded into the platform's canonical data store
- **Validation failure records**: quarantined records with detailed failure reasons
- **Conflict resolution records**: documentation of every conflict detected and how it was resolved
- **Duplicate detection reports**: identified duplicate records with similarity scores and resolution outcomes
- **Data quality scores**: per-entity, per-dimension quality metrics maintained as time series
- **Retry queue**: tracked list of failed sync records with retry status
- **Sync telemetry**: timing, volume, and success rate metrics for every sync job
- **Data quality dashboard**: real-time view of overall data quality posture across all connected systems
- **Data quality alerts**: notifications when quality scores fall below configured thresholds

---

## How It Appears in the Platform

The data quality picture is accessible from the **Connector Marketplace** in the administration console, where each connector's sync status, last sync time, success rate, and quality scores are displayed. Detailed data quality metrics are available in the **Dashboard Canvas** through a dedicated data quality panel.

Sync failures and quality alerts surface in the platform's **Notification Centre**, ensuring that data quality issues are visible to the teams responsible for resolving them. The retry queue can be managed from the connector detail view.

The assistant panel supports data quality queries: "When was the SAP data last synchronised?" "Are there any unresolved data conflicts?" "What is the current data quality score for project entities?"

---

## The Value It Adds

The value of the platform's analytics, reporting, and decision support capabilities depends entirely on the quality and currency of the underlying data. If the data is stale, incomplete, or inconsistent, every dashboard, every forecast, and every recommendation built on it is unreliable. The Data Synchronisation and Quality agent protects the data foundation that makes everything else trustworthy.

For organisations that have invested in multiple PPM, ERP, and collaboration systems, the data fragmentation problem is significant. Data about the same project may be held in three or four different systems, with no single source of truth. This agent resolves that fragmentation — maintaining a single, high-quality, continuously synchronised canonical record that all platform capabilities can depend on.

---

## How It Connects to Other Agents

The Data Synchronisation and Quality agent is a foundational service that supports every other agent in the platform by maintaining the data quality of the shared data store. It publishes quality metrics to **The Analytics Insights agent — Analytics and Insights** for reporting. Quality threshold breaches may trigger remediation workflows managed by **The Approval Workflow agent — Approval Workflow**. Lineage data maintained by this agent supports the compliance evidence managed by **The Compliance Governance agent — Compliance and Regulatory**.


---

# the Workspace Setup agent — Workspace Setup

**Category:** Core Orchestration
**Role:** Project Workspace Initialiser

---

## What This Agent Is

The Workspace Setup agent manages the initialisation and configuration of project workspaces before any data is written to systems of record. It acts as a governed "setup wizard" phase that ensures connectors are enabled, authentication is complete, field mappings are set, and all required external artefacts and containers exist before downstream delivery begins.

No write to a system of record is permitted until workspace setup is complete. This agent enforces that gate.

---

## What It Does

**It creates and configures internal project workspaces.** When a project is approved through the portfolio decision process, the Workspace Setup agent creates the internal workspace record, establishes the baseline artefact folder structure following organisational templates, and provisions default canvas tabs and views — a methodology map for lifecycle visualisation, a dashboard for project health summary, and registers for risk, issue, change, and decision tracking.

**It gates connector configuration.** Before a project can communicate with external systems, each required connector must progress through a validation sequence: Not configured → Configured → Connected → Permissions validated. The agent presents the required connectors by category — PPM tools (Planview, Clarity), PM tools (Jira, Azure DevOps), ERP systems (SAP, Oracle), document management (SharePoint, Confluence), collaboration (Teams, Slack), and GRC (ServiceNow GRC, Archer) — and validates each one. It supports "Test connection" checks to verify credentials and endpoint reachability, and "Dry-run mapping" checks to verify field mappings produce valid results without writing data. Connector selections and validation state are stored per project, with organisational defaults and project-level overrides.

**It provisions or links external workspace assets.** Based on organisational configuration and project requirements, the agent creates or links external assets: Teams teams and channels with standard channel structure, SharePoint sites with document libraries and folder structures, Jira projects and boards with templates applied, and Planview project shells with field mappings configured. Existing assets can be linked instead of created. Any provisioning or write action routes through the Approval Workflow agent for approval if organisational policy requires it.

**It bootstraps the delivery methodology.** The agent allows the project to select its delivery methodology — predictive, hybrid, or adaptive — and loads the corresponding lifecycle map. It applies the organisation's default stages, gates, artefact requirements, and review criteria for the selected methodology. The "Setup complete" status is marked as a prerequisite for any publishing actions to systems of record and for lifecycle progression beyond the initiation phase.

**It publishes setup status and events.** The agent produces a Setup Status checklist report showing pass/fail status for each setup item, a Provisioned Assets registry listing all created or linked external assets with their IDs and URLs, and publishes lifecycle events: `workspace.setup.started`, `workspace.setup.completed`, and `workspace.setup.failed`.

---

## How It Works

The agent is invoked after a portfolio decision (project approved for execution) and before any delivery agents begin work. It uses the platform's connector registry and connector runner to validate external system connectivity — the same infrastructure used by the Data Synchronisation agent for ongoing sync operations.

For external provisioning, the agent calls the relevant system APIs (Microsoft Graph for Teams/SharePoint, Jira REST API, Planview OData API) through the platform's connector framework. When organisational policy requires approval before provisioning (for example, creating a new Teams team or Jira project), the agent creates an approval request through the Approval Workflow agent and waits for the decision before executing the provisioning action.

The `workspace.setup.completed` event is consumed by the Lifecycle Governance agent as a gate condition — no project can progress past the initiation/setup phase until this event has been published.

---

## What It Uses

- The platform's connector registry and connector runner for connectivity validation
- Microsoft Graph API for Teams and SharePoint provisioning
- Jira REST API for project and board creation
- Planview OData API for project shell creation
- SAP APIs for ERP workspace configuration (as configured)
- Organisation configuration templates for methodology maps and default artefact structures
- The Approval Workflow agent for governed provisioning approvals
- Azure Service Bus for event publishing

---

## What It Produces

- **Internal workspace records** with folder structure and canvas tab configuration
- **Connector validation results** showing per-connector status for each project
- **Provisioned or linked external assets** with system IDs and URLs (Teams, SharePoint, Jira, Planview)
- **Setup Status checklist reports** with pass/fail per item and remediation guidance
- **Provisioned Assets registry** listing all external asset links
- **Setup lifecycle events**: `workspace.setup.started`, `workspace.setup.completed`, `workspace.setup.failed`

---

## How It Appears in the Platform

The **Workspace Setup** page presents a step-by-step setup wizard for new projects. Project managers see a checklist of required setup items — workspace creation, connector configuration, external asset provisioning, and methodology selection — with clear status indicators for each item. Connectors that require configuration show their current validation status and provide "Test connection" and "Dry-run mapping" buttons.

The **Provisioned Assets** panel shows all created or linked external workspace assets with direct links to each system (Teams channel, SharePoint site, Jira board, etc.).

Once all required items are complete, the setup page shows a "Setup complete" confirmation and the project becomes eligible for lifecycle progression.

---

## The Value It Adds

The Workspace Setup agent eliminates a class of downstream failures that occur when delivery agents attempt to interact with external systems that have not been properly configured. By enforcing a governed setup phase before any writes to systems of record, it ensures that:

- Connectors are authenticated and have the correct permissions before any agent tries to use them.
- External artefacts exist and are correctly configured before any agent tries to write to them.
- Field mappings are validated before any data synchronisation begins.
- The selected methodology and its lifecycle map are loaded before project governance begins.

This reduces support burden, increases first-time success rates for downstream agent operations, and gives project teams confidence that their tools are ready before they begin work.

---

## How It Connects to Other Agents

The Workspace Setup agent sits at a specific point in the platform lifecycle — after portfolio decision and before project delivery.

**Upstream:** The **Demand and Intake** agent, **Business Case and Investment** agent, and **Portfolio Strategy and Optimisation** agent handle the demand-to-decision pipeline. Once a project is approved, the Workspace Setup agent takes over.

**Peer:** The **Approval Workflow** agent handles any approval requests that the Workspace Setup agent raises for governed provisioning actions. The **Data Synchronisation agent** shares the connector registry and connector runner infrastructure.

**Downstream:** The **Lifecycle Governance** agent consumes the `workspace.setup.completed` event as a gate condition. The **Project Definition and Scope** agent begins work within the provisioned workspace. All delivery agents benefit from pre-validated connectors and provisioned external assets.


---

# the System Health agent — System Health and Monitoring

**Category:** Operations Management
**Role:** Platform Reliability Guardian

---

## What This Agent Is

The System Health and Monitoring agent is responsible for the operational reliability of the platform itself. It monitors every service, every integration, every infrastructure component, and every performance metric — detecting problems before they affect users, raising alerts when thresholds are breached, managing incidents, and providing the operational visibility that the teams running the platform need to keep it performing at the level the business expects.

Every capability the platform offers depends on its component services working correctly. The System Health and Monitoring agent is the layer that ensures they do.

---

## What It Does

**It monitors service health.** The agent continuously checks the health endpoints of every platform service — the API gateway, orchestration service, workflow service, document service, analytics service, identity and access service, and all others — at configured intervals. Each check records the response status, the response time, and whether the service is reporting healthy or degraded. Services that fail health checks are flagged immediately.

**It collects infrastructure metrics.** Beyond service-level health, the agent collects infrastructure metrics from the platform's compute and storage resources: CPU utilisation, memory utilisation, disk usage, network throughput, and queue depths. These metrics are ingested from Prometheus endpoints, parsed, and stored as time series for trend analysis and alerting.

**It collects application-level metrics.** In addition to infrastructure metrics, the agent monitors application performance: request latency (average and percentile), error rates, throughput, cache hit rates, agent execution times, and connector synchronisation success rates. These metrics provide a view of how the platform is performing from a user and business perspective, not just from an infrastructure perspective.

**It detects anomalies.** The agent uses statistical anomaly detection — analysing metric sequences to identify values that deviate significantly from historical norms — to surface unusual behaviour that might not trigger threshold-based alerts. An anomaly in request latency that does not breach the alert threshold may still indicate an emerging problem, and the anomaly detection capability surfaces it for investigation.

**It manages alerts.** When a metric breaches a configured threshold, the agent creates an alert with a severity level — critical, high, medium, or low — and routes it to the appropriate recipients. Alert routing integrates with PagerDuty and OpsGenie for on-call teams, ensuring that critical issues reach the right people through the right escalation path. Alerts for the same underlying problem are correlated rather than sent as a flood of individual notifications.

**It manages incidents.** When alerts indicate a significant service impact, the agent creates an incident record in ServiceNow — with the incident details, severity, affected services, and initial diagnostic information — and updates the incident as the situation evolves. Post-resolution, it generates a postmortem report summarising what happened, what the impact was, how it was resolved, and what changes should be made to prevent recurrence.

**It monitors SLOs.** Service Level Objectives (SLOs) define the performance targets that the platform is expected to meet — uptime, response time, error rate. The agent tracks actual performance against these targets continuously and raises a breach alert when performance is trending towards an SLO violation before the violation actually occurs, giving the operations team time to intervene.

**It triggers auto-scaling.** When resource metrics indicate that the platform is approaching capacity limits — CPU consistently high, queue depths growing, response times degrading — the agent can trigger auto-scaling webhooks to provision additional capacity. Scaling thresholds for CPU, memory, and queue depth are configurable, and scaling events are recorded with the metrics that triggered them.

**It generates Grafana dashboards.** The agent produces Grafana-compatible dashboard configurations that provide a comprehensive operational view of the platform — visualising service health, infrastructure metrics, application performance, alert history, and SLO tracking in a structured, navigable format accessible to the operations team.

**It performs pre-deployment environment checks.** Before a deployment is allowed to proceed, the agent evaluates the health of the target environment — checking that all services in that environment are healthy, that no active critical alerts exist, and that resource utilisation is within safe limits. If the environment is not in a suitable state for deployment, the check fails and the deployment is blocked until conditions are acceptable.

---

## How It Works

The agent integrates with Azure Monitor and Application Insights for metrics collection and alerting, and with Azure Log Analytics for log-based monitoring and querying. OpenTelemetry exporters send metrics to both Azure Monitor and Prometheus, providing flexibility in monitoring stack choice. Prometheus metric scraping handles infrastructure metrics. HTTP health probes check individual service health. The anomaly detection algorithm uses statistical analysis of metric time series — z-score and interquartile range analysis — to identify outliers without requiring a trained ML model.

A comprehensive test suite verifies Prometheus metrics parsing, application metrics collection, anomaly detection accuracy, alert threshold triggering, health status event publishing, environment health blocking, Grafana dashboard generation, and reporting summary generation.

---

## What It Uses

- Health endpoints of all platform services
- Prometheus metrics endpoints for infrastructure metrics
- Azure Monitor and Application Insights for metrics and logs
- Azure Log Analytics for query-based monitoring
- OpenTelemetry exporters for metrics distribution
- Azure Anomaly Detector service for advanced anomaly detection
- PagerDuty and OpsGenie webhooks for on-call alerting
- ServiceNow integration for incident creation and management
- Azure Logic Apps and Azure Automation for auto-scaling webhooks
- Azure Event Hub for health event publishing
- Grafana dashboard configuration generation

---

## What It Produces

- **Service health status**: real-time health assessment for every platform service
- **Infrastructure metrics**: time-series CPU, memory, disk, and network utilisation data
- **Application performance metrics**: latency, error rate, throughput, and agent execution times
- **Anomaly detections**: statistical outliers identified in metric time series
- **Alerts**: threshold-based notifications with severity levels and routing to on-call systems
- **Incident records**: structured ServiceNow incidents for significant service impacts
- **Postmortem reports**: post-resolution analysis of incidents with prevention recommendations
- **SLO compliance reports**: actual performance against defined service level targets
- **Grafana dashboards**: visual operational monitoring views for the operations team
- **Pre-deployment environment assessments**: go/no-go health checks before deployments
- **Scaling event records**: documentation of auto-scaling triggers and responses

---

## How It Appears in the Platform

The **Performance Dashboard** page in the platform provides the operations-facing view — showing service health status, key infrastructure metrics, active alerts, and SLO compliance. The Grafana dashboard provides a more detailed, interactive operations monitoring experience for the platform engineering team.

Alerts surface in the platform's **Notification Centre** and are pushed to the configured on-call channels (PagerDuty, OpsGenie). Incident status is visible through the platform's admin console.

The pre-deployment environment check integrates with **The Release Deployment agent — Release and Deployment**, appearing as a readiness criterion in the deployment approval workflow. A failed environment health check blocks the deployment and displays the specific issues that need to be resolved.

---

## The Value It Adds

A sophisticated platform that goes offline, runs slowly, or loses data is worse than no platform at all — it destroys confidence and sets back adoption. The System Health and Monitoring agent is the operational safety net that prevents this outcome by detecting problems early, routing them to the right people, and providing the operational visibility needed to diagnose and resolve them quickly.

The SLO monitoring capability, in particular, shifts the operations posture from reactive (responding to outages after they occur) to proactive (detecting trends that indicate an SLO breach is coming before it happens). This is the operational equivalent of the predictive forecasting that the Analytics and Insights agent provides for portfolio management — and it delivers the same benefit: earlier awareness, more time to act, better outcomes.

---

## How It Connects to Other Agents

The System Health and Monitoring agent is the operational guardian for the entire platform, so it connects to every other agent indirectly through its health monitoring. Directly, it provides pre-deployment environment health checks to **The Release Deployment agent — Release and Deployment**, publishes platform health data to **The Analytics Insights agent — Analytics and Insights** for operational reporting, and records incidents in ServiceNow alongside the compliance evidence managed by **The Compliance Governance agent — Compliance and Regulatory**. Operational metrics feed into the continuous improvement analysis managed by **The Continuous Improvement agent — Continuous Improvement and Process Mining**.
