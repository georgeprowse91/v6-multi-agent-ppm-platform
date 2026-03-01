# Templates and Methodology Catalog

**Purpose:** Canonical cross-methodology catalog of project management templates and the agents that produce or consume them. Remove repeated template references from other docs and link here instead.
**Audience:** Project managers, PMO practitioners, product management, and engineering teams configuring agent template outputs.
**Owner:** PMO Lead / Product Management
**Last reviewed:** 2026-02-20
**Related docs:** [requirements-specification.md](requirements-specification.md) · [user-journeys-and-stage-gates.md](user-journeys-and-stage-gates.md) · [../02-solution-design/agent-system-design.md](../02-solution-design/agent-system-design.md)

> **Migration note:** Lifted and shifted from `templates-catalog.md` on 2026-02-20. All template cross-references in other documents should link here as the single source of truth.

---

# Template Catalog

## Purpose
Provide a cross-methodology catalog of project management templates and the agents that produce
or consume them. The catalog aligns with PMBOK focus areas such as integration, scope, schedule,
cost, quality, resource, communications, risk, procurement, and stakeholder management.

## Methodology Template Index
- Templates are organized by discipline under [docs/templates](../../templates/README.md). Methodology
  variants are labeled with `-adaptive`, `-hybrid`, or `-predictive` in the filename.

## Shared Template Library
| Artefact | Purpose | Used by (agent) | Template Path |
| --- | --- | --- | --- |
| Demand intake request | Capture intake data for triage and prioritization. | the Demand Intake agent (Demand Intake) | [docs/templates/portfolio-program/demand-intake-request-template-cross.md](../../templates/README.md) |
| Demand intake schema | Structured schema for intake data. | the Demand Intake agent (Demand Intake) | [docs/templates/portfolio-program/demand-intake-schema-cross.yaml](../../templates/README.md) |
| Business case | Document investment rationale and options. | the Business Case agent/12 (Business Case & Investment) | [docs/templates/portfolio-program/business-case-var3-template-cross.md](../../templates/README.md) |
| Business case update report | Compare actuals vs plan to validate continued investment. | the Business Case agent/12 (Business Case & Investment) | [docs/templates/portfolio-program/business-case-update-template-cross.md](../../templates/README.md) |
| Product strategy canvas | Consolidate product vision, market context, and roadmap strategy. | the Portfolio Optimisation agent/07 (Portfolio/Program Strategy) | [docs/templates/product/product-strategy-canvas-var1-template-cross.md](../../templates/README.md) |
| Product vision template | Define product vision, mission, and success metrics. | the Portfolio Optimisation agent/07 (Portfolio/Program Strategy) | [docs/templates/product/product-vision-var1-template-cross.md](../../templates/README.md) |
| ROI/NPV worksheet | Calculate ROI and NPV assumptions. | the Business Case agent/12 (Business Case & Investment) | [docs/templates/finance/roi-npv-worksheet-cross.xlsx](../../templates/README.md) |
| Assumption log | Track key project assumptions and validation. | the Business Case agent/12 (Business Case & Investment), the Risk Management agent (Risk & Issue) | [docs/templates/risk/assumption-log-template-cross.md](../../templates/README.md) |
| Variance report | Track schedule/cost variance. | the Schedule Planning agent (Schedule & Planning) | [docs/templates/finance/variance-report-template-cross.md](../../templates/README.md) |
| Executive dashboard status report | Executive-ready health, decisions, and value summary. | the Stakeholder Communications agent (Stakeholder Comms) | [docs/templates/governance/status-report-var1-template-cross.md](../../templates/README.md) |
| Milestone review | Formal milestone, phase gate, or go/no-go review. | the Lifecycle Governance agent (Lifecycle & Governance) | [docs/templates/governance/milestone-review-var1-template-cross.md](../../templates/README.md) |
| Risk report | Report top risks and exposure trends. | the Risk Management agent (Risk & Issue Management) | [docs/templates/risk/risk-report-template-cross.md](../../templates/README.md) |
| Schedule risk analysis | Quantify schedule risk exposure and confidence-based completion dates. | the Schedule Planning agent (Schedule & Planning), the Risk Management agent (Risk & Issue Management) | [docs/templates/risk/schedule-risk-analysis-var1-template-cross.md](../../templates/README.md) |
| Quality report | Report quality performance and defects. | the Quality Management agent (Quality Assurance) | [docs/templates/quality/quality-report-template-cross.md](../../templates/README.md) |
| Quality checklist | Standardize quality reviews and acceptance criteria. | the Quality Management agent (Quality Assurance) | [docs/templates/quality/quality-checklist-var1-template-cross.md](../../templates/README.md) |
| Change request | Submit changes for approval. | the Change Control agent (Change & Configuration) | [docs/templates/change/change-request-var1-template-cross.md](../../templates/README.md) |
| Change impact assessment | Analyze change impacts. | the Change Control agent (Change & Configuration) | [docs/templates/change/change-impact-assessment-template-cross.md](../../templates/README.md) |
| Change log | Track approved and pending changes. | the Change Control agent (Change & Configuration) | [docs/templates/change/change-log-template-cross.md](../../templates/README.md) |
| Issue log | Track and resolve issues. | the Risk Management agent (Risk & Issue Management) | [docs/templates/risk/issue-log-var1-template-cross.md](../../templates/README.md) |
| Lessons learned register | Capture outcomes, root causes, and recommendations. | the Continuous Improvement agent (Continuous Improvement) | [docs/templates/governance/lessons-learned-var1-template-cross.md](../../templates/README.md) |
| Scope baseline | Combine scope statement, WBS, and dictionary. | the Scope Definition agent (Project Definition) | [docs/templates/requirements/scope-baseline-template-cross.md](../../templates/README.md) |
| Project scope statement | Define the approved project scope, boundaries, and acceptance criteria. | the Scope Definition agent (Project Definition) | [docs/templates/requirements/project-scope-statement-template-cross.md](../../templates/README.md) |
| Project management plan | Integrate subsidiary management plans. | the Lifecycle Governance agent (Lifecycle & Governance) | [docs/templates/governance/project-management-plan-template-cross.md](../../templates/README.md) |
| Scope management plan | Define scope definition, validation, and control. | the Scope Definition agent (Project Definition) | [docs/templates/requirements/scope-management-plan-template-cross.md](../../templates/README.md) |
| Business requirements document | Capture business goals, requirements, and success metrics. | the Scope Definition agent (Project Definition) | [docs/templates/requirements/business-requirements-document-template-cross.md](../../templates/README.md) |
| Software requirements specification | Define detailed functional and non-functional requirements. | the Scope Definition agent (Project Definition) | [docs/templates/requirements/requirements-specification-template-cross.md](../../templates/README.md) |
| Requirements traceability matrix | Map requirements to design, build, and test artifacts. | the Scope Definition agent (Project Definition) | [docs/templates/requirements/requirements-traceability-matrix-template-cross.md](../../templates/README.md) |
| Schedule management plan | Define schedule development and control. | the Schedule Planning agent (Schedule & Planning) | [docs/templates/schedule/schedule-management-plan-template-cross.md](../../templates/README.md) |
| Project schedule template | Capture activity-level schedule detail, milestones, and baselines. | the Schedule Planning agent (Schedule & Planning) | [docs/templates/schedule/project-schedule-var2-template-cross.md](../../templates/README.md) |
| Release management workflow | Execute and validate releases end-to-end. | the Quality Management agent (Release Management) | [docs/templates/schedule/release-management-workflow-template-cross.md](../../templates/README.md) |
| Cost management plan | Define cost estimation, baseline, and control. | the Financial Management agent (Financial Management) | [docs/templates/finance/cost-management-plan-template-cross.md](../../templates/README.md) |
| Financial risk management plan | Define financial risk identification, assessment, and response. | the Financial Management agent (Financial Management), the Risk Management agent (Risk & Issue Management) | [docs/templates/finance/financial-risk-management-plan-template-cross.md](../../templates/README.md) |
| Quality management plan | Define QA/QC standards and processes. | the Quality Management agent (Quality Assurance) | [docs/templates/quality/quality-management-plan-template-cross.md](../../templates/README.md) |
| Resource management plan | Define resource estimation and acquisition. | the Resource Management agent (Resource & Capacity) | [docs/templates/resources/resource-management-plan-template-cross.md](../../templates/README.md) |
| Risk management plan | Define risk governance and analysis methods. | the Risk Management agent (Risk & Issue Management) | [docs/templates/risk/risk-management-plan-template-cross.md](../../templates/README.md) |
| Procurement management plan | Define sourcing strategy and contract approach. | the Vendor Procurement agent (Vendor Procurement) | [docs/templates/finance/procurement-management-plan-template-cross.md](../../templates/README.md) |
| Resource assignment matrix | Track RACI assignments per task. | the Resource Management agent (Resource & Capacity) | [docs/templates/resources/resource-assignment-matrix-cross.csv](../../templates/README.md) |
| RACI matrix | Define responsibilities, accountability, and decision rights. | the Resource Management agent (Resource & Capacity) | [docs/templates/governance/raci-matrix-var1-template-cross.md](../../templates/README.md) |
| Activity list | Define activities aligned to WBS items. | the Schedule Planning agent (Schedule & Planning) | [docs/templates/schedule/activity-list-template-cross.csv](../../templates/README.md) |
| Project calendar | Track working days, holidays, and events. | the Schedule Planning agent (Schedule & Planning) | [docs/templates/schedule/project-calendar-cross.csv](../../templates/README.md) |
| Risk breakdown structure | Categorize risks for consistent analysis. | the Risk Management agent (Risk & Issue Management) | [docs/templates/risk/risk-breakdown-structure-template-cross.yaml](../../templates/README.md) |
| Product breakdown structure | Decompose product components and features. | the Scope Definition agent (Project Definition) | [docs/templates/product/product-breakdown-structure-template-cross.yaml](../../templates/README.md) |
| Communications plan | Plan stakeholder communications. | the Stakeholder Communications agent (Stakeholder Comms) | [docs/templates/communications/communications-plan-template-cross.md](../../templates/README.md) |
| Stakeholder analysis & mapping | Identify, map, and analyze stakeholders with engagement strategies. | the Stakeholder Communications agent (Stakeholder Comms) | [docs/templates/stakeholders/stakeholder-analysis-and-mapping-template-cross.md](../../templates/README.md) |
| Template customization guide | Guide consistent tailoring and governance of templates. | the Lifecycle Governance agent (Lifecycle & Governance) | [docs/templates/governance/customization-guide-template-cross.md](../../templates/README.md) |
| Stakeholder register | Track stakeholder influence and engagement. | the Stakeholder Communications agent (Stakeholder Comms) | [docs/templates/stakeholders/stakeholder-register-cross.xlsx](../../templates/README.md) |
| RFP template | Request vendor proposals. | the Vendor Procurement agent (Vendor Procurement) | [docs/templates/finance/rfp-template-cross.md](../../templates/README.md) |
| Vendor evaluation scorecard | Score vendors consistently. | the Vendor Procurement agent (Vendor Procurement) | [docs/templates/finance/vendor-evaluation-scorecard-cross.xlsx](../../templates/README.md) |
| Contract summary | Summarize contract terms and obligations. | the Vendor Procurement agent (Vendor Procurement) | [docs/templates/finance/contract-summary-template-cross.md](../../templates/README.md) |
| Supplier risk assessment | Assess supplier risk factors and mitigations. | the Vendor Procurement agent (Vendor Procurement) | [docs/templates/finance/supplier-risk-assessment-template-cross.md](../../templates/README.md) |
| Portfolio prioritization report | Document prioritization results. | the Portfolio Optimisation agent/07 (Portfolio/Program Strategy) | [docs/templates/portfolio-program/portfolio-prioritization-report-template-cross.md](../../templates/README.md) |
| Program roadmap | Track program initiatives and milestones. | the Portfolio Optimisation agent/07 (Portfolio/Program Strategy) | [docs/templates/portfolio-program/program-roadmap-cross.xlsx](../../templates/README.md) |
| Executive real-time dashboard specification | Define real-time executive KPIs, panels, and refresh cadence. | the Analytics Insights agent (Performance & Insights) | [docs/templates/governance/kpi-dashboard-spec-template-cross.md](../../templates/README.md) |
| SLO/alert definition | Define SLOs and alerting thresholds. | the System Health agent (System Health Monitoring) | [docs/templates/quality/slo-alert-definition-cross.yaml](../../templates/README.md) |
| Skills matrix | Assess team capabilities, gaps, and development needs. | the Resource Management agent (Resource & Capacity) | [docs/templates/resources/skills-matrix-template-cross.md](../../templates/README.md) |
| Cost baseline | Time-phased budget baseline (spreadsheet). | the Financial Management agent (Financial Management) | [docs/templates/finance/cost-baseline-cross.xlsx](../../templates/README.md) |

> **Note:** Spreadsheet templates (e.g., cost baseline, risk register, stakeholder register) are stored in the repository but cannot be rendered directly in Markdown previews. Open them in Excel or Google Sheets for full functionality.

## Methodology Variants
| Artefact | Adaptive | Predictive | Hybrid |
| --- | --- | --- | --- |
| Charter |  | [Project charter](../../templates/README.md) | [Hybrid charter](../../templates/README.md) |
| Roles & responsibilities matrix | [Roles & responsibilities](../../templates/README.md) — Defines the key roles and responsibilities for Adaptive projects (Product Owner, Scrum Master, Team, Stakeholders, etc.). | [Roles & responsibilities](../../templates/README.md) — Defines the key roles and responsibilities for Predictive projects (Sponsor, PM, BA, Functional Leads, etc.). | [Roles & responsibilities](../../templates/README.md) — Defines hybrid roles and shared responsibilities where governance and Adaptive delivery overlap. |
| User story mapping | [User story mapping](../../templates/README.md) |  |  |
| User story template | [User story template](../../templates/README.md) |  |  |
| Backlog | [Backlog](../../templates/README.md) |  |  |
| Backlog management | [Backlog management](../../templates/README.md) |  |  |
| Backlog refinement | [Backlog refinement](../../templates/README.md) |  |  |
| Risk-adjusted backlog | [Risk-adjusted backlog](../../templates/README.md) |  |  |
| Adaptive risk board | [Adaptive risk board](../../templates/README.md) |  |  |
| Sprint plan | [Sprint plan](../../templates/README.md) |  | [Sprint plan](../../templates/README.md) |
| Iteration plan | [Iteration plan](../../templates/README.md) |  |  |
| Release plan | [Release plan](../../templates/README.md) |  | [Release plan](../../templates/README.md) |
| Burndown | [Burndown](../../templates/README.md) |  |  |
| WBS |  | [WBS](../../templates/README.md) |  |
| Schedule baseline |  | [Schedule baseline](../../templates/README.md) |  |
| Risk register |  | [Risk register](../../templates/README.md) | [Integrated risk register](../../templates/README.md) |
| Integrated risk register |  |  | [Integrated risk register](../../templates/README.md) |
| Risk breakdown structure |  | [RBS](../../templates/README.md) |  |
| QA checklist |  | [QA checklist](../../templates/README.md) |  |
| Milestone plan |  |  | [Milestone plan](../../templates/README.md) |
| Governance pack |  |  | [Governance pack](../../templates/README.md) |
| Decision log |  |  | [Decision log](../../templates/README.md) |
| Hybrid team management |  |  | [Hybrid team management](../../templates/README.md) |
| Hybrid resource plan |  |  | [Hybrid resource plan](../../templates/README.md) |
| Closure report |  | [Closure report](../../templates/README.md) | [Closure report](../../templates/README.md) |
| Project management plan |  | [Project management plan](../../templates/README.md) |  |
| Scope management plan |  | [Scope management plan](../../templates/README.md) |  |
| Schedule management plan |  | [Schedule management plan](../../templates/README.md) |  |
| Cost management plan |  | [Cost management plan](../../templates/README.md) |  |
| Quality management plan |  | [Quality management plan](../../templates/README.md) |  |
| Resource management plan |  | [Resource management plan](../../templates/README.md) |  |
| Risk management plan |  | [Risk management plan](../../templates/README.md) |  |
| Procurement management plan |  | [Procurement management plan](../../templates/README.md) |  |

## Related Compliance Template
- DPIA template: [docs/compliance/privacy-dpia-template.md](../../compliance/privacy-dpia-template.md)
