> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 11 — Resource and Capacity Management

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

Capacity forecasting draws on the scheduled demand from Agent 10 — Schedule and Planning across all active projects, combined with the available supply from the resource pool, to produce forward-looking supply-demand views at the portfolio level.

---

## What It Uses

- HR and workforce system integrations: Workday, SAP SuccessFactors
- Resource pool definitions with skills, roles, cost rates, and calendars
- Schedule demand data from Agent 10 — Schedule and Planning
- Portfolio-level resource demand from Agent 06 — Portfolio Strategy and Optimisation
- Skill matching and ranking algorithm
- Constraint rule definitions configured per organisation
- Agent 03 — Approval Workflow for resource allocation approvals
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

The Resource and Capacity Management agent is a dependency for multiple other agents. **Agent 06 — Portfolio Strategy and Optimisation** uses its capacity data for portfolio optimisation. **Agent 07 — Programme Management** uses it for cross-project resource coordination. **Agent 10 — Schedule and Planning** uses it for resource-constrained scheduling. **Agent 12 — Financial Management** uses resource cost rate data for budget modelling. Resource utilisation data also feeds into **Agent 22 — Analytics and Insights** for portfolio health reporting.
