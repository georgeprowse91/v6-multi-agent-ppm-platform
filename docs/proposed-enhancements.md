# Proposed Enhancements — 11 High-Impact Improvements

**Author:** AI Analysis
**Date:** 2026-03-07
**Scope:** Customer-facing enhancements to increase platform appeal, based on a full codebase review.

---

## 1. Natural-Language Portfolio What-If Scenario Engine

**Problem:** The Analytics Dashboard has what-if controls in the UI but they are not wired to the backend (documented as Known Gap #4 in `docs/UI.md`). Portfolio leaders cannot interactively model "what happens if we delay Project X by 3 months?" or "what if we cut this program's budget by 20%?" — the exact kind of question that justifies a premium PPM tool.

**Enhancement:** Build a conversational what-if engine that lets users describe scenarios in plain English via the Assistant Panel. The system would:
- Parse the scenario using the Intent Router agent and route to the Portfolio Optimisation and Financial Management agents.
- Execute Monte Carlo simulations (infrastructure already exists in the Business Case agent at `agents/portfolio-management/business-case-agent/src/business_case_investment_agent.py`) across the affected portfolio.
- Return side-by-side comparison views (baseline vs. scenario) with impact on NPV, resource utilisation, schedule, and risk scores.
- Persist named scenarios for board-level comparison.

**Key files to extend:**
- `apps/web/frontend/src/pages/AnalyticsDashboard.tsx` — wire the existing what-if controls
- `agents/portfolio-management/portfolio-optimisation-agent/` — add scenario comparison action
- `agents/delivery-management/financial-management-agent/` — add cascade impact calculation

**Customer appeal:** Transforms the platform from a reporting tool into a strategic decision-support system. Directly addresses the CFO persona's "poor forecasting" pain point identified in `docs/platform-commercials.md`.

---

## 2. Predictive Project Health Scoring with Early-Warning Alerts

**Problem:** The System Health agent (`agents/operations-management/system-health-agent/`) monitors infrastructure but does not surface predictive project-level health signals to end users. The platform tracks telemetry and agent costs, but there is no unified "project health score" that aggregates schedule variance, budget burn rate, risk severity, resource contention, and scope creep into a single actionable indicator.

**Enhancement:** Introduce a composite Project Health Index (PHI) that:
- Aggregates signals from Schedule Planning, Financial Management, Risk Management, and Resource Management agents.
- Uses a time-series model to detect deteriorating trends before they become critical (leveraging the existing ML prediction service integration in the Risk Management agent).
- Pushes early-warning alerts through the Notification Service (`services/notification-service/`) to Slack, Teams, email, and mobile push (infrastructure already in the Stakeholder Communications agent).
- Displays a traffic-light health badge on every project card, portfolio dashboard, and the mobile app's Dashboard screen.

**Key files to extend:**
- `agents/operations-management/analytics-insights-agent/` — add PHI calculation action
- `services/notification-service/src/` — add alert-rule engine for threshold breaches
- `apps/mobile/src/screens/DashboardScreen.tsx` — add health badge component

**Customer appeal:** PMO Directors and executives get proactive warnings instead of retrospective reports. Directly addresses the documented success metric of ">40% manual reporting reduction" by surfacing issues automatically.

---

## 3. Searchable Portfolio, Program, and Project Collection Pages

**Problem:** This is documented as Known Gap #1 in `docs/UI.md` and affects capabilities 4, 5, 6, and 7. Currently, `/portfolios`, `/programs`, and `/projects` routes only redirect to a hardcoded fallback or the current selection — there is no way for users to browse, search, or filter their full portfolio of work. For enterprise customers with 500+ active projects, this is a critical navigation gap.

**Enhancement:** Implement dedicated collection pages with:
- Full-text search across project names, descriptions, and metadata.
- Faceted filtering by status, methodology, owner, date range, health score, and custom tags.
- Sortable table and card views with bulk actions (export, reassign, archive).
- Saved filter presets per user/role.
- Deep-link support for bookmarking filtered views.

**Key files to create/extend:**
- `apps/web/frontend/src/pages/` — new `PortfolioListPage.tsx`, `ProgramListPage.tsx`, `ProjectListPage.tsx`
- `apps/web/frontend/src/App.tsx` — replace `EntityCollectionRedirect` with real pages
- `services/data-service/src/` — add search/filter query endpoints

**Customer appeal:** Table-stakes for any enterprise PPM tool. Without this, the platform cannot credibly serve organisations with large portfolios. Every competitor (Planview, Smartsheet, Monday.com) offers this.

---

## 4. Agent Marketplace with Custom Agent SDK

**Problem:** The platform has 25 built-in agents but no mechanism for customers or partners to extend the agent ecosystem. The commercial docs (`docs/platform-commercials.md`) already envision "Model D — Agent Marketplace" as a future revenue stream, and the `BaseAgent` abstraction (`agents/runtime/src/base_agent.py`) is well-designed for extension — but no public SDK, packaging format, or marketplace UI exists.

**Enhancement:** Create a customer-facing Agent Marketplace:
- Publish a public Agent SDK based on the existing `BaseAgent` class with clear extension points (`validate_input`, `process`, `cleanup`).
- Define a packaging format (manifest + Docker image + prompt templates + schema declarations) aligned with the existing agent catalog structure.
- Build a marketplace UI in the web console where administrators can browse, install, configure, and monitor third-party agents.
- Include a sandbox environment for testing custom agents before production deployment.
- Revenue model: per-agent activation fees as already outlined in the pricing tiers.

**Key files to extend:**
- `agents/runtime/src/base_agent.py` — extract public SDK interface
- `agents/runtime/src/agent_catalog.py` — support dynamic registration
- `agents/runtime/src/orchestrator.py` — allow dynamically registered agents in task graphs

**Customer appeal:** Creates a network effect and ecosystem moat. Customers can build domain-specific agents (e.g., pharmaceutical regulatory, aerospace compliance) without forking the platform. Partners get a revenue channel.

---

## 5. Unified Cross-System Search with AI-Powered Summarisation

**Problem:** The platform connects to 40+ external systems through its connector ecosystem, but there is no unified search experience that lets users query across all connected systems simultaneously. A project manager looking for "the latest SAP cost report for Project Alpha" must know which system holds that data and navigate to it directly.

**Enhancement:** Build a federated search layer that:
- Accepts natural-language queries via the Header's global search trigger (already present in the UI but limited to local navigation).
- Fan-out searches across connected systems (Jira, Confluence, SharePoint, SAP, etc.) via the connector SDK's existing HTTP client infrastructure.
- Uses the LLM Gateway (`packages/llm/src/llm/client.py`) to rank and summarise results, collapsing duplicates using the vector similarity infrastructure already in the Demand Intake agent.
- Presents results in a unified panel with source attribution, relevance scores, and one-click navigation to the source system.
- Respects RBAC/ABAC policies so users only see results they are authorised to access.

**Key files to extend:**
- `connectors/sdk/src/base_connector.py` — add standard `search()` interface method
- `packages/vector_store/` — extend for cross-system indexing
- `apps/web/frontend/src/components/layout/Header.tsx` — upgrade global search

**Customer appeal:** Directly addresses the documented pain point that "PMO analysts spend up to 40% of time on manual aggregation across disconnected systems." Makes the platform the single pane of glass that the go-to-market positioning promises.

---

## 6. Interactive Gantt Chart with AI-Assisted Schedule Optimisation

**Problem:** The methodology workspace supports a `gantt` canvas type (documented in `docs/UI.md` component reference), but the current implementation is a read-only visualisation. Enterprise project managers expect interactive Gantt charts where they can drag tasks, adjust dependencies, and see the critical path recalculate in real time — capabilities that competitors like Microsoft Project and Planview offer natively.

**Enhancement:** Upgrade the Gantt canvas to a fully interactive experience:
- Drag-and-drop task rescheduling with automatic dependency cascade.
- Critical path highlighting and resource-levelling visualisation.
- AI-assisted optimisation: a "Suggest optimal schedule" button that invokes the Schedule Planning agent to propose resequencing based on resource availability, dependencies, and risk factors.
- Real-time collaborative editing via the existing Realtime Co-edit Service (`services/realtime-coedit/`).
- Baseline comparison overlay (planned vs. actual vs. AI-suggested).

**Key files to extend:**
- `apps/web/frontend/src/components/methodology/` — Gantt canvas renderer
- `agents/delivery-management/schedule-planning-agent/` — add optimisation action
- `services/realtime-coedit/src/` — add Gantt event types for collaborative editing

**Customer appeal:** Interactive Gantt is a must-have for predictive methodology customers (construction, aerospace, government). Combined with AI optimisation, it leapfrogs traditional tools that offer drag-and-drop but no intelligence.

---

## 7. Executive AI Briefing Generator

**Problem:** The platform collects rich data across portfolios, programmes, and projects but does not offer a one-click executive summary. Executives and board members — a key buyer persona — want concise, actionable briefings, not dashboards they must interpret themselves. The templates directory (`docs/templates/Executive-Report-Templates.md`) defines report formats, but no automated generation pipeline exists.

**Enhancement:** Build an AI-powered briefing generator that:
- Collects data from all relevant agents (Analytics Insights, Financial Management, Risk Management, Resource Management, Stakeholder Communications).
- Uses the LLM Gateway to generate a structured executive briefing covering: portfolio health summary, top 5 risks, budget variance highlights, resource bottlenecks, and recommended actions.
- Supports configurable frequency (weekly, fortnightly, monthly) and delivery channels (email, PDF, Teams/Slack post).
- Allows executives to ask follow-up questions via the Assistant Panel ("Why is Project X flagged red?").
- Produces branded, exportable PDF/PowerPoint reports using the executive report templates.

**Key files to extend:**
- `agents/operations-management/analytics-insights-agent/` — add briefing generation action
- `agents/operations-management/stakeholder-communications-agent/` — add scheduled delivery
- `services/notification-service/` — add rich-format delivery (PDF, PPTX attachments)
- `apps/document-service/` — add report template rendering

**Customer appeal:** Eliminates hours of manual report preparation. Directly addresses the PMO Director persona's pain point and the documented goal of "near-real-time dashboards." Provides a clear, tangible ROI that customers can calculate immediately.

---

## 8. Intelligent Resource Capacity Planning with Skill Matching

**Problem:** The Resource Management agent handles allocation and utilisation tracking, but the platform lacks forward-looking capacity planning with skill-based matching. Enterprise customers with hundreds of resources need to answer "Do we have enough cloud architects to staff next quarter's programmes?" — not just "Who is allocated where today?"

**Enhancement:** Build a capacity planning module that:
- Maintains a skills taxonomy and resource skill profiles (extending the `resource` schema in `data/schemas/`).
- Projects future demand by aggregating planned work from all active and pipeline projects.
- Identifies capacity gaps by skill, role, location, and time period.
- Recommends actions: internal reallocation, training investment, or contractor hiring — using the LLM Gateway for natural-language justifications.
- Integrates with HR connectors (Workday, SAP SuccessFactors, ADP) already in the connector ecosystem to pull real-time headcount and skill data.
- Visualises supply vs. demand curves with drill-down by skill category.

**Key files to extend:**
- `agents/delivery-management/resource-management-agent/` — add capacity planning actions
- `data/schemas/resource.json` — extend with skills taxonomy
- `connectors/workday/`, `connectors/sap_successfactors/` — add skill data sync

**Customer appeal:** Resource capacity planning is consistently ranked as a top PPM challenge by analysts. Combining it with AI-driven skill matching creates a differentiated offering that addresses the CIO's desire to "increase ROI on current tools."

---

## 9. End-to-End Intake-to-Project Automation with Guided Setup

**Problem:** Known Gap #2 in `docs/UI.md`: the intake creation flow routes to a status page, but the SPA does not automatically route users to a newly created project workspace when approval completes. The Demand Intake agent classifies and validates requests, and the Approval Workflow agent manages gates, but the handoff between "approved demand" and "active project" is a manual step.

**Enhancement:** Close the intake-to-project lifecycle with a two-phase approach:

### Phase 1 — Automatic project instance creation (on intake approval)

When an intake request is approved, the platform automatically:
- Creates a canonical project entity in the Data Service, pre-populated with metadata from the intake form and business case (name, sponsor, category, budget envelope, target dates, regulatory category).
- Sets the project status to `initiated`.
- Sends a real-time notification (via the existing WebSocket channel in `useRealtimeConsole`) deep-linking the creator and sponsor to the new project's setup wizard.
- Records the intake-to-project transition in the audit trail for governance traceability.

The project instance exists immediately so nothing falls through the cracks after approval, but it is not yet configured — that is a deliberate user-driven step.

### Phase 2 — User-driven project setup (via the setup wizard)

The user lands on the `ProjectSetupWizardPage` and completes configuration:

1. **Select methodology** — choose from the three organisationally tailored methodologies (predictive, adaptive, or hybrid) defined during platform deployment (see Enhancement #11).
2. **Toggle connectors** — browse the connector registry by category (PM, ERP, GRC, HR, Collaboration, etc.) and enable the specific connectors relevant to this project (e.g. Jira from PM, SAP from ERP, Slack from Collaboration).
3. **Assign team members and roles** — specify the PM, team members, and stakeholders with their project-level RBAC roles.

### Phase 3 — Automated workspace scaffolding (on setup confirmation)

Once the user confirms their choices, the Workspace Setup agent executes:
- **Scaffold the methodology map** — instantiate the selected organisational methodology's activity tree with the correct phases, stages, gates, and templates.
- **Provision toggled connectors** — create sync jobs in the Data Sync Service and authenticate against the external systems the user selected.
- **Configure RBAC** — apply project-level role assignments and field-level access rules from `config/rbac/field-level.yaml` for the assigned team members.
- **Activate real-time channels** — register the project's WebSocket channels in the Realtime Co-edit Service for collaborative editing.

Artefacts such as the project charter, risk register, and stakeholder map remain user-initiated — the PM creates them when ready, optionally using the AI assistant for drafting help.

**Key files to extend:**
- `agents/core-orchestration/approval-workflow-agent/` — add post-approval project creation hook
- `agents/core-orchestration/workspace-setup-agent/` — add user-configuration-driven setup
- `apps/web/frontend/src/pages/IntakeFormPage.tsx` — add redirect on approval event
- `apps/web/frontend/src/pages/ProjectSetupWizardPage.tsx` — embed methodology selection and connector toggle UI

**Customer appeal:** Reduces project setup time from days to minutes while keeping the PM in control of configuration decisions. Demonstrates the platform's end-to-end orchestration capability in a way that is immediately visible and impressive during sales demos.

---

## 10. Mobile-First Approval and Status Update Experience

**Problem:** The mobile app (`apps/mobile/`) has screens for approvals, status updates, dashboards, and an AI assistant, but the experience is basic compared to the web SPA. For executives and project managers on the go, mobile is often the primary interaction channel. The current mobile app has an `ApprovalsScreen`, `StatusUpdatesScreen`, and `AssistantScreen`, but lacks offline support, push notification deep-linking, and the rich methodology-aware context that the web console provides.

**Enhancement:** Upgrade the mobile experience to be a first-class client:
- Offline-first architecture: queue approvals and status updates locally (infrastructure exists in `services/statusQueue.ts`) and sync when connectivity returns.
- Push notification deep-linking: tap a notification to land directly on the relevant approval, project, or risk item (notification service already exists at `apps/mobile/src/services/notifications.ts`).
- Quick-action approval cards: swipe-to-approve/reject with one-tap confirmation for common gate approvals.
- Voice-to-status: use device speech recognition to dictate status updates that the AI assistant transcribes and routes to the correct project.
- Biometric authentication for sensitive approvals (extending the existing `secureSession.ts`).
- Rich dashboard widgets with the same health badges and trend sparklines as the web console.

**Key files to extend:**
- `apps/mobile/src/screens/ApprovalsScreen.tsx` — add swipe gestures and offline queue
- `apps/mobile/src/services/notifications.ts` — add deep-link routing
- `apps/mobile/src/services/statusQueue.ts` — add offline persistence
- `apps/mobile/src/screens/DashboardScreen.tsx` — add health badge widgets

**Customer appeal:** Executives approve budgets and review risks from their phone. This is a competitive differentiator against traditional PPM tools that are desktop-only. The "voice-to-status" feature is a showstopper for demos and directly leverages the platform's AI-native positioning.

---

## 11. Organisational Methodology Tailoring

**Problem:** The platform ships with three default methodology templates (predictive, adaptive, hybrid) defined in `docs/methodology/`. However, every enterprise has its own phase names, stage gates, approval requirements, and activity structures. A financial services firm's predictive methodology will have different phases and gate criteria than a defence contractor's. Without the ability to tailor these templates to organisational standards, customers must either work with generic defaults or request custom development.

**Enhancement:** Provide a methodology tailoring capability as part of platform deployment:

### What the PMO admin can customise

Using the existing `MethodologyEditor` page (already in the SPA at `/ops/config/methodologies`), the customer's PMO admin tailors each of the three methodology templates to match organisational standards:
- **Phases and stages** — rename, add, remove, or reorder phases and stages within each methodology.
- **Stage gate criteria** — define the gate conditions that must be met before progressing (e.g. required approvals, artefact completions, quality thresholds).
- **Prerequisite dependencies** — specify which activities must complete before others can begin.
- **Approval requirements** — configure which roles must approve at each gate and the escalation rules.
- **Templates and artefacts** — associate organisational document templates with each phase (e.g. the company's standard project charter template at initiation, their risk register format at planning).

### How it works

- Tailored methodologies are stored as tenant-level definitions in the Data Service, separate from the platform defaults.
- Each tenant gets its own set of three methodology templates that all projects within that organisation select from.
- The platform defaults serve as a starting point — customers can modify them incrementally rather than building from scratch.
- Validation rules prevent broken configurations (e.g. circular dependencies, gates referencing non-existent phases).
- Changes to methodology templates do not retroactively alter in-flight projects — only new projects pick up the latest version.

### When it happens

This is a **deployment-time activity**, not a per-project decision. It typically occurs during the implementation engagement (documented in `docs/platform-commercials.md` as the "Discovery and blueprinting" service) and is maintained by PMO admins thereafter.

**Key files to extend:**
- `apps/web/frontend/src/pages/MethodologyEditor.tsx` — enhance with full CRUD for phases, gates, dependencies, and template associations
- `services/data-service/src/` — persist tenant-level methodology definitions with versioning
- `packages/methodology-engine/` — add validation rules for methodology structure integrity
- `docs/methodology/` — document the tailoring workflow and provide examples

**Customer appeal:** Methodology alignment is a make-or-break requirement for enterprise PMO adoption. Customers will not use a platform whose methodology does not match their governance framework. This capability turns a potential objection ("it doesn't match how we work") into a selling point ("it adapts to exactly how you work"). It also creates implementation services revenue during deployment.

---

## Summary Matrix

| # | Enhancement | Primary Persona | Effort | Impact | Revenue Lever |
|---|------------|----------------|--------|--------|---------------|
| 1 | What-If Scenario Engine | CFO, PMO Director | Medium | High | Upsell to Enterprise tier |
| 2 | Predictive Health Scoring | PMO Director, PM | Medium | High | Core value prop |
| 3 | Collection Search Pages | All users | Low | Critical | Table stakes |
| 4 | Agent Marketplace | CIO, Partners | High | Very High | New revenue stream |
| 5 | Cross-System Search | PM, PMO Analyst | Medium | High | Orchestration differentiator |
| 6 | Interactive Gantt + AI | PM, Scheduler | High | High | Win predictive-methodology deals |
| 7 | Executive Briefing Generator | C-suite, PMO Director | Medium | Very High | Premium feature |
| 8 | AI Capacity Planning | CIO, Resource Manager | Medium | High | Enterprise upsell |
| 9 | Intake-to-Project Automation | PM, PMO Director | Low-Medium | High | Demo showpiece |
| 10 | Mobile-First Experience | Executives, PM | Medium | High | Competitive differentiator |
| 11 | Organisational Methodology Tailoring | PMO Admin, CIO | Medium | Critical | Deployment prerequisite + services revenue |

### Recommended Priority Order

1. **#11 Organisational Methodology Tailoring** — Deployment prerequisite; customers won't adopt without methodology alignment
2. **#3 Collection Search Pages** — Low effort, blocks basic usability at scale
3. **#9 Intake-to-Project Automation** — Closes a documented gap, high demo impact (depends on #11)
4. **#2 Predictive Health Scoring** — Core AI value proposition
5. **#7 Executive Briefing Generator** — Immediate ROI for buyer personas
6. **#1 What-If Scenario Engine** — Strategic decision support
7. **#5 Cross-System Search** — Fulfils the "single pane of glass" promise
8. **#10 Mobile-First Experience** — Competitive differentiator
9. **#8 AI Capacity Planning** — Enterprise upsell
10. **#6 Interactive Gantt + AI** — Wins predictive-methodology deals
11. **#4 Agent Marketplace** — Highest long-term value, highest effort
