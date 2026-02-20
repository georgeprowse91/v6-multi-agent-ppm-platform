> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 10 — Schedule and Planning

**Category:** Delivery Management
**Role:** Schedule Builder and Milestone Manager

---

## What This Agent Is

The Schedule and Planning agent transforms a project's scope definition into a working schedule. It takes the Work Breakdown Structure produced during project definition, estimates how long each element will take, maps out the dependencies between tasks, identifies the critical path, and produces a baselined schedule that the project team can deliver against.

It is also the agent that keeps the schedule current throughout delivery — updating progress, identifying delays, forecasting completion dates, and alerting the team when the schedule is under threat. For agile projects, it handles sprint planning and backlog management rather than waterfall scheduling, adapting its approach to match the delivery methodology.

---

## What It Does

**It converts the WBS into a schedule.** Working from the Work Breakdown Structure provided by Agent 08, the agent creates a task list with durations, dependencies, assigned resources, and scheduled dates. Duration estimates are generated using a combination of AI-based estimation (drawing on historical data from similar projects) and any estimates provided directly by the project team.

**It maps dependencies.** The agent supports all standard task dependency types — finish-to-start, start-to-start, finish-to-finish, and start-to-finish — and maps them across the schedule to create a dependency network. This network is used for critical path analysis and schedule risk assessment.

**It runs Critical Path Method analysis.** The agent identifies the critical path through the schedule — the sequence of tasks that determines the minimum possible project duration. Any delay to a task on the critical path will delay the project. Understanding the critical path allows project managers to focus their attention where it matters most.

**It performs resource-constrained scheduling.** An unconstrained schedule assumes that every task can be resourced whenever it is needed. A realistic schedule reflects the fact that resources are limited. The agent applies resource constraints from Agent 11 to produce a schedule that reflects actual availability — delaying tasks or extending durations when the required resources are not available.

**It runs Monte Carlo risk simulations.** Schedule estimates are inherently uncertain. The agent can run probabilistic simulations — testing the schedule against thousands of possible combinations of task duration variations — to produce a probability distribution of completion dates rather than a single deterministic end date. This gives project managers an honest picture of schedule risk: not just the plan, but the confidence interval around it.

**It manages milestones and baselines.** Key milestones are tracked separately and displayed prominently — both in the schedule and in the Timeline Canvas. Once the schedule is approved, it is baselined: the approved plan is stored as a reference, and all subsequent schedule performance is measured against this baseline. Baseline changes require formal approval through the change management process.

**It supports agile sprint planning.** For agile projects, the agent shifts from a task network to a sprint-based view. It supports backlog management, sprint capacity planning, sprint commitment, and sprint progress tracking. The schedule picture for an agile project is sprint velocity and burn-down rather than Gantt charts and critical path analysis.

**It flags schedule risks and delays.** As the schedule progresses, the agent monitors actual completion dates against planned dates, calculates schedule variance, and raises alerts when tasks are late, when the critical path is threatened, or when the forecast completion date has slipped beyond the baselined end date.

---

## How It Works

The agent takes the WBS from Agent 08 and resource availability from Agent 11 as its primary inputs. Duration estimates are generated using a hybrid approach: an AI model trained on historical project data produces initial estimates, which can be overridden or supplemented by team input. The dependency network is built from the task structure and any dependency relationships defined in the WBS.

Schedule data is synchronised bidirectionally with connected project management tools — Azure DevOps, Jira, and Microsoft Project — so that the schedule in the platform reflects the current state of work as tracked in the tools the delivery team uses.

---

## What It Uses

- WBS from Agent 08 — Project Definition and Scope
- Resource availability data from Agent 11 — Resource and Capacity Management
- Historical project data for AI-based duration estimation
- Dependency type definitions (FS, SS, FF, SF)
- Critical Path Method algorithm
- Monte Carlo simulation engine
- Azure DevOps, Jira, and Microsoft Project connectors for bidirectional synchronisation
- Agent 03 — Approval Workflow for baseline change approvals
- Agent 09 — Project Lifecycle and Governance as a consumer of schedule performance data

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

The Schedule and Planning agent receives its WBS input from **Agent 08** and resource constraints from **Agent 11**. Its schedule performance data feeds into **Agent 09 — Lifecycle and Governance** for health scoring and **Agent 22 — Analytics and Insights** for portfolio-level schedule reporting. Baseline change requests are processed by **Agent 17 — Change and Configuration Management**. For agile projects, sprint data connects to **Agent 14 — Quality Management** for definition-of-done tracking.
