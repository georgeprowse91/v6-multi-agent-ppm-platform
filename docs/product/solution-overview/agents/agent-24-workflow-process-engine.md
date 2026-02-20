> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 24 — Workflow and Process Engine

**Category:** Operations Management
**Role:** Process Automation Coordinator

---

## What This Agent Is

The Workflow and Process Engine agent is the platform's automation backbone. It manages the definition and execution of repeatable business processes — the multi-step workflows that coordinate human tasks, automated actions, notifications, approvals, and system integrations into a structured, governed sequence.

While the Approval Workflow agent manages the specific pattern of routing a decision to a human approver, the Workflow and Process Engine handles much broader and more varied process automation: the sequence of steps that constitute an onboarding workflow, a procurement process, a risk review cycle, a deployment pipeline, or any other structured process that the organisation wants to automate and govern.

---

## What It Does

**It defines workflows as structured specifications.** Workflow definitions are created using a structured YAML or JSON format — the platform's workflow specification language (`ppm.workflow/v1`). Each workflow definition describes its steps, the type of each step (human task, automated action, approval gate, notification, decision, parallel execution, or loop), the conditions that govern transitions between steps, retry policies for steps that might fail, and the metadata needed to identify and version the workflow. BPMN 2.0 format is also supported for organisations that already model their processes in standard BPMN tools.

**It starts and manages workflow instances.** When a workflow is triggered — by a user action, by an event from another agent, or by a scheduled trigger — the engine creates a new instance of the workflow. Each instance has its own state, tracking which steps have been completed, what data has been passed between steps, and what the current execution status is. Instances can be paused, resumed, cancelled, or retried depending on the circumstances.

**It executes parallel and conditional logic.** Workflows can contain parallel branches — multiple steps that execute simultaneously — and decision points where the path taken depends on the result of a previous step. The engine evaluates decision conditions (equality, comparison, containment, existence checks) against the current workflow data and routes execution accordingly. Parallel branches are collected at a join point before the workflow continues, ensuring that all concurrent steps are complete before the process advances.

**It manages human task inboxes.** When a workflow reaches a step that requires human action — a review, a decision, a data entry task — the engine creates a task in the assigned user's inbox and waits for them to complete it. The task includes all the context the user needs to act, a deadline, and any relevant data from previous workflow steps. Users can view and complete their pending tasks from the platform's task inbox.

**It handles retries and compensation.** When a workflow step fails — because a system is unavailable, a validation check fails, or an automated action produces an error — the engine applies the configured retry policy: retrying after a delay, with exponential backoff for repeated failures. If a workflow fails in a way that cannot be retried, compensation workflows can be triggered to reverse the actions already taken, ensuring that the system is not left in an inconsistent state.

**It responds to events.** Workflows can be triggered or continued by events from other agents and systems. The engine monitors configured event subscriptions and, when a matching event arrives, triggers the appropriate workflow action — starting a new instance, advancing a waiting step, or branching based on the event data. Event criteria can match on specific field values, allowing fine-grained control over which events trigger which workflow responses.

**It supports workflow versioning.** As business processes evolve, workflow definitions are updated and versioned. The engine maintains a version history for each workflow definition, ensuring that in-flight instances continue on the version they were started with while new instances use the current version.

**It provides monitoring and reporting.** For each workflow definition, the engine tracks instance counts, success rates, average execution time, and step-level performance metrics. This data is accessible through the workflow monitoring view and feeds into the continuous improvement analysis managed by Agent 20.

---

## How It Works

Workflow definitions are loaded from the platform's workflow definition store and from a library of pre-built workflow templates. The engine uses a task-dependency graph to determine the execution order for each workflow instance, applying cycle detection to prevent invalid workflow definitions from causing infinite loops. State is persisted using either JSON file storage or a PostgreSQL database backend, depending on the deployment configuration. For task queuing, either an in-process queue (for simple deployments) or RabbitMQ (for scaled deployments) is used.

The event subscription system uses deterministic criteria matching — evaluating field conditions against incoming event data — ensuring consistent, predictable behaviour regardless of event volume.

---

## What It Uses

- Workflow definitions in YAML, JSON, or BPMN 2.0 format
- A workflow specification schema (`ppm.workflow/v1`) for validation
- PostgreSQL or JSON file-backed state store for workflow instance persistence
- RabbitMQ or in-process task queue for task message passing
- Azure Monitor and Azure Event Grid for event integration
- Azure Service Bus for event publishing
- Task dependency graph with cycle detection
- Agent 03 — Approval Workflow for approval-type steps
- Agent 17 — Change and Configuration Management for change-triggered workflows
- Agent 20 — Continuous Improvement for process performance analysis
- Agent 23 — Data Synchronisation and Quality for sync retry workflows

---

## What It Produces

- **Workflow definitions**: versioned, structured specifications of business processes
- **Workflow instances**: running and completed process executions with full state history
- **Task inbox items**: human tasks created for workflow participants with context and deadlines
- **Execution logs**: step-by-step records of every workflow execution with outcomes and timestamps
- **Compensation records**: documentation of rollback actions taken when workflows fail
- **Event subscription records**: configured triggers and their matching criteria
- **Workflow performance metrics**: execution time, success rate, and step-level performance by workflow type
- **Workflow monitoring dashboard**: real-time view of active instances, failure rates, and backlogs

---

## How It Appears in the Platform

The **Workflow Designer** page allows authorised users to create and configure workflow definitions through a structured interface. Workflow definitions can be imported and exported in YAML or BPMN format.

The **Workflow Monitoring** page provides a real-time operations view — showing how many instances of each workflow are currently running, how many have completed or failed, average execution times, and any instances that are stuck or in a failed state. Operators can inspect individual instances, view their execution history, retry failed steps, or cancel stalled instances from this view.

Users with pending workflow tasks see them in the **Task Inbox**, accessible from the platform's notification centre. Each task shows what action is required, the deadline, and the relevant context from the workflow.

---

## The Value It Adds

Process automation is one of the most direct routes to operational efficiency in project management. The Workflow and Process Engine enables organisations to automate the routine, multi-step processes that consume significant administrative time — approvals, notifications, escalations, data updates — and execute them consistently, at scale, without manual coordination.

The event-driven architecture means that workflows respond intelligently to what is happening in the platform rather than running on fixed schedules. When a risk is escalated, the risk response workflow triggers automatically. When a sync job fails, the retry workflow starts. When a stage gate is passed, the next-stage preparation workflow begins. This responsiveness makes the platform feel like a genuinely intelligent operational system rather than a collection of manual processes.

---

## How It Connects to Other Agents

The Workflow and Process Engine is used by virtually every other agent in the platform to automate multi-step processes. **Agent 03 — Approval Workflow** uses it for complex approval chains. **Agent 17 — Change and Configuration Management** triggers change workflows through it. **Agent 23 — Data Synchronisation and Quality** uses it to manage sync retry workflows. **Agent 20 — Continuous Improvement** analyses its execution data for process mining. **Agent 18 — Release and Deployment** uses it to orchestrate deployment workflows.
