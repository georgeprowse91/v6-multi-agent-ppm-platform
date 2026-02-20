> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 20 — Continuous Improvement and Process Mining

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

The agent ingests event logs from the platform's audit trail, workflow engine, and domain agents. It applies process mining algorithms to build process models and perform conformance analysis. Waiting time analysis identifies bottleneck stages. Correlation analysis links process characteristics to outcomes. The improvement backlog is persisted and managed as a structured data store, with priority scoring that combines benefit size, implementation effort, and strategic alignment.

A test suite verifies the event ingestion logic, the accuracy of process discovery, the conformance checking algorithm, and the compliance rate calculation methodology.

---

## What It Uses

- Event logs from the platform's audit trail and workflow engine
- Process events from all domain agents
- Analytics reports from Agent 22 — Analytics and Insights
- The knowledge base from Agent 19 — Knowledge and Document Management for best practice recommendations
- Process mining algorithms for model discovery and conformance checking
- Waiting time analysis for bottleneck detection
- Correlation analysis for root cause identification
- Industry benchmark data for performance comparison
- Agent 24 — Workflow Process Engine for improvement workflow automation

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

The Continuous Improvement agent ingests data from virtually every other agent via the audit log and event streams. It draws on knowledge from **Agent 19** for best practice comparisons and recommendations. Its findings feed into **Agent 22 — Analytics and Insights** for portfolio-level improvement reporting. Improvement workflow automation is handled by **Agent 24 — Workflow Process Engine**. Process improvement insights may trigger updates to methodology definitions, which are reflected in **Agent 09 — Lifecycle and Governance**.
