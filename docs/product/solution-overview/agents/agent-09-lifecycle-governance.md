> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 09 — Project Lifecycle and Governance

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

Governance decisions — particularly gate approvals where a manual review is required — are routed through **Agent 03 — Approval Workflow**, ensuring that stage transitions are formally authorised and recorded.

---

## What It Uses

- Project records, charter, scope baseline, and artefacts from the platform's data store
- Methodology definitions for each project type (Predictive, Adaptive, Hybrid)
- Stage-gate criteria definitions configured per methodology and organisation
- A machine learning readiness scoring model trained on historical project data
- Health dimension data: schedule performance from Agent 10, financial performance from Agent 12, risk status from Agent 15, quality data from Agent 14
- External tool synchronisation: Planview, Clarity, Jira, Azure DevOps
- Agent 03 — Approval Workflow for gate governance
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

The Lifecycle and Governance agent draws health data from **Agents 10, 12, 14 and 15** (Schedule, Financial, Quality, and Risk) to calculate its composite health score. It uses **Agent 03 — Approval Workflow** for gate governance. Its lifecycle stage data drives the methodology map navigation visible to users, and its outputs feed into **Agent 22 — Analytics and Insights** for portfolio-level governance reporting. When it detects a methodology mismatch, it can engage **Agent 08 — Project Definition and Scope** to update the project definition accordingly.
