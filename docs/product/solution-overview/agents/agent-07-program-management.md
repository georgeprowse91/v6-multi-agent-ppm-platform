# Agent 07 — Programme Management

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

- Portfolio optimisation outputs from Agent 06 to identify groupings of related projects
- Project records from the platform's data store for each constituent project
- Schedule and milestone data from Agent 10 — Schedule and Planning
- Resource capacity data from Agent 11 — Resource and Capacity Management
- Financial data from Agent 12 — Financial Management
- The platform's LLM gateway for narrative generation
- Agent 03 — Approval Workflow for programme governance decisions
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

The Programme Management agent draws on portfolio decisions from **Agent 06**, schedule data from **Agent 10**, resource data from **Agent 11**, and financial data from **Agent 12**. It coordinates with **Agent 03 — Approval Workflow** for programme governance, and its outputs — health dashboards, benefits reports, roadmap views — feed into **Agent 22 — Analytics and Insights** for portfolio-level reporting. Change impact assessments are produced in coordination with **Agent 17 — Change and Configuration Management**.
