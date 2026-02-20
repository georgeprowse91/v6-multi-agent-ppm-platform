> **Deprecated — 2026-02-20:** This document has been migrated to [`01-product-definition/user-journeys-and-stage-gates.md`](01-product-definition/user-journeys-and-stage-gates.md). This file will be removed after the transition period. Please update all bookmarks and links.

---

# Methodology‑Embedded Process Flows

This document describes how the multi‑agent PPM platform embeds Adaptive, Predictive and Hybrid methodologies into the user interface to guide users through stage‑gate workflows and enforce governance. The platform presents each methodology as an interactive map; the project management methodology becomes the navigation mechanism. This map guides users through stages and activities, while the conversational assistant and specialist agents execute tasks and enforce gate criteria. The objective is to provide clear user journeys, ensure compliance with best practices and allow continuous monitoring and governance.

## 1. Adaptive Process Flow

The Adaptive process is iterative and adaptive, emphasising incremental delivery, sprint ceremonies and continuous refinement. The platform’s Adaptive methodology map, presented in the left panel, shows current and future sprints and allows users to navigate through initiation, release planning, sprint cycles and release delivery. Continuous activities like backlog refinement and impediment tracking remain accessible throughout.

### 1.1 User Journey

**Demand & Ideation:** A stakeholder submits a demand/proposal. The Demand & Intake Agent classifies the request and recommends the Adaptive methodology based on factors such as uncertainty and stakeholder expectations.

**Business Case & Approval:** The Business Case Agent crafts a lean business case emphasising iterative value delivery and minimum viable product (MVP). Approval is typically streamlined; a product owner or program manager can approve the case.

**Project Definition (Initiation):** The Project Definition Agent generates the Adaptive project charter and initial backlog. The methodology map highlights the initiation stage, with tasks such as product vision, initial backlog creation and team formation.

**Release Planning:** Users plan releases at a high level. The Release Goal Definition, feature prioritisation and release roadmap are surfaced as discrete activities on the map. Agents assist in prioritising features and estimating release cadence.

**Sprint Cycles:** Each sprint appears as an expandable node (e.g., “Sprint 1 (Jan 6‑19)”) with sub‑activities: sprint planning, daily development, sprint review and sprint retrospective. Users can drill down to current sprints to see tasks, track progress and update status. The Schedule & Planning Agent aids in sprint planning and generates a sprint backlog, while the Approval Workflow Agent records acceptance of stories via definition of done. Continuous monitoring dashboards remain available.

**Continuous Activities:** Backlog refinement, impediment tracking, stakeholder feedback and sprint dashboards are always accessible. The Knowledge Management Agent stores lessons learned and documentation.

**Release & Deployment:** At the end of a release cycle, Release Testing, Deployment and Release Retrospective activities appear. Agents coordinate testing, deployment, and gather feedback for the next iterations.

**Closure & Lessons Learned:** Once releases meet stakeholder acceptance criteria, the project may transition to maintenance or closure. The knowledge gained is stored for continuous improvement.

### 1.2 Stage‑Gate Governance in Adaptive

Adaptive projects rely on sprint ceremonies rather than formal gates. The platform enforces governance through:

**Definition of Done (DoD) gates:** Each user story or feature must meet agreed acceptance criteria before being marked complete. The Quality Management Agent validates DoD, test coverage and defect metrics. The agent can block completion if criteria are not met and prompt the user to update tests or remediate defects.

**Release readiness checks:** Before deploying a release, the platform verifies that all planned sprints for the release are completed, critical defects are resolved and stakeholder approvals are recorded. If not, the Release & Deployment Agent prompts users to address outstanding items.

**Continuous Monitoring:** The Project Lifecycle Agent monitors metrics such as velocity, burndown, defect density and risk exposure to surface early warnings. Health dashboards and alerts show whether the project is on track and propose corrective actions.

### 1.3 UI & Navigation

The methodology map functions as a timeline and checklist. Completed activities are ticked, the current sprint is highlighted and future sprints are collapsed for clarity. Users can click any activity to open the corresponding canvas (e.g., backlog board, sprint plan). The assistant uses context from the map to guide users to the next logical action and can jump between sprints or release‑level views. Monitoring widgets remain pinned in the workspace to ensure continuous oversight.

## 2. Predictive Process Flow

**The Predictive process is linear and predictive, with discrete phases separated by formal stage gates. The platform’s Predictive methodology map displays the phases:** Initiating, Planning, Executing and Closing – with stage gates between them. Monitoring and controlling activities operate continuously.

### 2.1 User Journey

**Demand & Business Case:** A demand triggers the creation of a comprehensive business case emphasising total project ROI, cost‑benefit analysis and long‑term value. The Approval Workflow Agent routes the case through multi‑level approvals.

**Initiating Phase:** Upon approval, the Project Definition & Scope Agent creates the project charter, stakeholder register and preliminary scope baseline. The methodology map lists activities such as Business Case, Project Charter and Stakeholder Analysis.

**Stage Gate 1: Charter Approval:** A formal gate reviews the charter for completeness and alignment. The Approval Workflow Agent coordinates sign‑offs from sponsors and the PMO. If criteria are unmet, the Project Lifecycle Agent blocks progression.

**Planning Phase:** Detailed planning tasks are executed: Scope Definition, Work Breakdown Structure (WBS) Development, Schedule Development, Resource and Budget Planning, Quality Planning, Risk Management Plan and Procurement Plan. Domain agents generate detailed plans and baseline estimates. Each deliverable appears as a checklist item on the map.

**Stage Gate 2: Planning Approval:** The platform requires approval of all baseline plans. Criteria may include scope completeness, cost and schedule baseline approval, risk register completeness and procurement approvals. The Project Lifecycle Agent evaluates readiness and either allows progression or provides detailed feedback if the gate is not met.

**Executing Phase:** The project team executes deliverables. The methodology map shows activities like Deliverable Development, Quality Assurance and Procurement Execution. The Schedule & Planning Agent monitors progress and updates the schedule; the Quality Management Agent tracks testing and acceptance; the Procurement Agent manages vendor engagements.

**Stage Gate 3: Execution Review (optional):** For large projects, additional gates may be configured (e.g., mid‑project review) to reassess scope, budget and risk.

**Closing Phase:** Final Deliverable Acceptance, Contract Closeout, Lessons Learned and Project Archive tasks appear on the map. The project cannot close until all deliverables are accepted, contracts settled and documentation archived. The Knowledge Management Agent captures lessons learned.

**Monitoring & Controlling (Continuous):** Throughout the lifecycle, performance tracking, change control, risk monitoring and stakeholder management activities run in parallel. The Project Lifecycle Agent synthesises metrics from other domain agents to calculate a composite health score and surface risks and variances.

### 2.2 Stage‑Gate Governance

The Predictive methodology relies heavily on stage gates. The platform enforces gates by evaluating criteria and preventing phase transitions if conditions are not met. For example, if a user attempts to transition from Planning to Executing without required approvals or risk identification, the agent presents an error message and directs the user to complete outstanding tasks. Users may either complete missing work, check status (e.g., CFO approval), or request an override requiring senior approval.

### 2.3 UI & Navigation

The methodology map uses clearly delineated phases and gates. Each gate is rendered as a horizontal separator with descriptive text (e.g., “STAGE GATE 2: Planning Approval”). Completed activities display check marks; in‑progress activities show progress indicators; future activities are greyed out. When a user hovers over a gate, a tooltip summarises criteria. Attempting to move ahead triggers the Project Lifecycle Agent to validate compliance and either approve or block the transition.

## 3. Hybrid Process Flow

Hybrid methodologies combine elements of Adaptive and Predictive to suit complex projects with both predictive and adaptive components. The platform supports hybrid approaches by allowing teams to configure stage gates at major milestones while operating iteratively within phases. Methodology selection is dynamic: the platform chooses a default methodology based on business case recommendations and activates the relevant agents. Users may adjust the mix of phases and sprints to align with organisational standards.

### 3.1 User Journey

**Methodology Selection:** When a demand is received, the platform analyses the business case and recommends a hybrid approach if uncertainty exists alongside regulatory constraints. The Project Lifecycle Agent loads a hybrid methodology map combining Predictive phases and Adaptive iterations.

**Initiation & Charter:** Similar to Predictive, a formal charter and stakeholder analysis are prepared and approved through a stage gate.

**Planning & Release Framing:** The team defines high‑level scope, budget and schedule. The Release Planning Agent outlines milestones (e.g., release 1, release 2) and chooses to deliver value incrementally via sprints within each release. The stage gate for planning ensures baseline approvals.

**Iterative Development within Phases:** Each release is executed through a series of sprints. The methodology map nests sprints under the corresponding phase; for example, within the “Execution” phase there may be “Sprint 1”, “Sprint 2”, etc. Teams perform sprint planning, daily work, review and retrospectives while still maintaining overall phase objectives and deliverables.

**Milestone Reviews:** At the end of each release or phase, the platform enforces milestone gates requiring validation of deliverables, acceptance from stakeholders, and updated risk and financial assessments. These gates combine Adaptive acceptance criteria (DoD) with Predictive governance (formal sign‑offs).

**Continuous Monitoring:** The Project Lifecycle Agent monitors both sprint‑level metrics (velocity, burnup) and phase‑level metrics (schedule variance, budget variance). This dual view ensures that iterative progress does not diverge from strategic objectives.

**Closing & Hand‑over:** As with Predictive, formal closing activities occur once all iterations and milestones are complete, including lessons learned and documentation archiving.

### 3.2 Governance & Gates

In hybrid projects, gates exist at both the phase/release level and at the sprint level. For sprint‑level gates, the Quality Management Agent checks DoD compliance; for milestone gates, the Approval Workflow Agent ensures deliverables, budgets and risks meet criteria before moving forward. Users can request overrides but these require higher‑level approvals. The platform also ensures that monitoring and controlling activities remain visible across both iterative and linear parts of the project.

### 3.3 UI & Navigation

The hybrid methodology map visually nests sprints within phases. Stage gates appear between major milestones (e.g., “Planning → Execution”, “Release 1 → Release 2”). The assistant adapts prompts according to context: when the user is in a sprint, suggestions relate to story completion and sprint reviews; at milestones, prompts focus on approval checklists and integration with external systems (e.g., Planview, SAP). Users can collapse or expand sprints and phases to focus on the desired level of granularity.

## 4. Best Practice Enforcement via UI

Across all methodologies, the platform enforces governance and best practice through:

**Interactive Methodology Map:** The map is both navigation and checklist. It guides users through required steps, reflects current progress and provides visual status. Users cannot arbitrarily skip steps without meeting gate criteria..

**Agent‑Driven Validation:** The Project Lifecycle Agent and domain agents continuously validate readiness for transitions. They check for missing approvals, incomplete registers and outstanding issues, and block progression until resolved.

**Conversational Guidance:** The assistant provides just‑in‑time recommendations based on the current step. It helps users navigate to relevant canvases, summarises outstanding tasks and provides context‑aware suggestions. The assistant’s context includes methodology, phase and active agents, ensuring guidance is specific.

**Monitoring Dashboards:** Health dashboards summarise schedule, cost, risk, quality and resource metrics. When a composite score indicates risk, the platform identifies root causes and proposes corrective actions.

**Publishing Workflow:** Before writing back to systems of record, users review and approve agent outputs in canvases. This ensures data quality, alignment with governance and prevents unintended changes.

## Conclusion

By embedding Adaptive, Predictive and Hybrid methodologies directly into the user interface, the multi‑agent PPM platform guides teams through appropriate workflows and enforces governance. The methodology map provides a visual representation of the project lifecycle, while agents validate stage‑gate criteria, manage approvals and surface performance insights. Continuous monitoring and conversational guidance ensure that best practices are followed and deviations are quickly addressed.
