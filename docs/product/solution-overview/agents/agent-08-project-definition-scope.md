> **Deprecated — 2026-02-20:** This document has been migrated to [`02-solution-design/agent-system-design.md`](../../02-solution-design/agent-system-design.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Agent 08 — Project Definition and Scope

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

- Approved business case from Agent 05 as the primary input
- Demand record from Agent 04 for context
- Document templates for charters, scope statements, WBS, and RACI matrices
- The platform's LLM gateway for narrative generation
- External research capability for supplementary scope context
- The document canvas for storing all outputs
- Agent 03 — Approval Workflow for charter and scope baseline sign-off
- Agent 10 — Schedule and Planning as the consumer of the WBS

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

The project charter and scope baseline produced by this agent feed directly into **Agent 09 — Project Lifecycle and Governance**, which uses them as the reference for gate assessments. The WBS is consumed by **Agent 10 — Schedule and Planning** to build the project schedule. Scope change requests are processed by **Agent 17 — Change and Configuration Management**, which assesses their impact against the baselined scope. The stakeholder register is used by **Agent 21 — Stakeholder Communications** to plan and execute project communications.
