> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 17 — Change and Configuration Management

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
- Agent 03 — Approval Workflow for change approval routing
- Agent 08 — Project Definition and Scope for scope baseline updates
- Agent 10 — Schedule and Planning for schedule baseline updates
- Agent 12 — Financial Management for budget baseline updates
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

The Change and Configuration agent coordinates with **Agents 08, 10, and 12** to update scope, schedule, and budget baselines when changes are approved. It works closely with **Agent 09 — Lifecycle and Governance** to assess whether approved changes require a gate review. **Agent 18 — Release and Deployment** relies on its configuration record for deployment readiness assessments. **Agent 07 — Programme Management** uses it for programme-level change impact analysis.
