# Proposed Enhancements — 11 High-Impact Improvements

**Author:** AI Analysis
**Date:** 2026-03-07
**Scope:** Customer-facing enhancements to increase platform appeal, based on a full codebase review.

---

## 1. Natural-Language Portfolio What-If Scenario Engine

**Current implementation: ~60% complete**

| Capability | Status | Detail |
|---|---|---|
| Schedule what-if analysis | Done | `schedule_actions/what_if.py` — duration changes, multipliers, cost/resource impact |
| Portfolio scenario comparison | Done | `portfolio_actions/scenario_actions.py` — budget/capacity/priority multipliers, trade-off identification, DB persistence |
| Business case scenario analysis | Done | `business_case_actions/roi_actions.py` — Monte Carlo (1000+ iterations), sensitivity analysis, NPV/IRR/payback |
| Financial variants generation | Done | `financial_actions/forecast_actions.py` — budget deltas/multipliers, CPI/SPI adjustments |
| Scenario data model | Done | `data/schemas/scenario.schema.json` — baseline reference, deltas array, status lifecycle |
| Natural-language input layer | Missing | No NLP parser for "what if" queries; users must call agents with structured JSON |
| Cross-project cascade impact | Missing | Each scenario analysed in isolation; no downstream ripple effect across projects |
| Web UI what-if controls | Missing | `AnalyticsDashboard.tsx` has placeholder text but no functional controls |

**What remains:** Wire the existing backend scenario engines to the UI, add a natural-language front-end via the Intent Router, and implement cross-project financial cascade logic.

---

## 2. Predictive Project Health Scoring with Early-Warning Alerts

**Current implementation: ~55% complete**

| Capability | Status | Detail |
|---|---|---|
| System health score calculation | Done | `health_actions/check_health.py` — calculates `(total - unhealthy) / total` |
| Predictive health forecasting | Done | `apps/analytics-service/src/predictive_models.py` — trend-based prediction with confidence intervals |
| Predictive dashboard UI | Done | `PredictiveDashboardPage.tsx` — current/predicted scores (30/60/90d), colour-coded badges, risk heatmap, resource bottleneck predictions |
| Predictive alert notifications | Done | `POST /v1/notifications/predictive-alerts` — severity, rationale, mitigations; feature-flagged; multi-channel delivery |
| Analytics insights agent prediction | Done | `run_prediction.py` — supports health_score model type |
| Composite project health index | Missing | Current score is infrastructure-only (healthy services ratio), not a composite of schedule + budget + risk + resource health |
| ML-based early warning | Missing | Prediction is linear trend extrapolation only; no anomaly detection or ML model |
| Root cause analysis | Missing | Alerts don't explain why health is declining; mitigations are hardcoded placeholders |
| Cross-project health correlation | Missing | Each project scored independently; no portfolio-level aggregation or inter-project impact |

**What remains:** Build a composite PHI aggregating signals from multiple agents, replace linear prediction with ML-based anomaly detection, and add root cause explanations to alerts.

---

## 3. Searchable Portfolio, Program, and Project Collection Pages

**Current implementation: ~25% complete**

| Capability | Status | Detail |
|---|---|---|
| Routes defined | Done | `/portfolios`, `/programs`, `/projects` routes wired to `WorkspaceDirectoryPage` |
| Basic card list UI | Done | `WorkspaceDirectoryPage.tsx` — generic component showing cards with name, owner, status |
| Client-side search | Done | Simple case-insensitive string matching on ID/name/owner/status |
| Backend search/filter endpoints | Missing | Data Service has no search endpoints; only basic entity listing with skip/limit |
| Faceted filtering | Missing | No filtering by status, methodology, owner, date range, health score, or tags |
| Table/grid view option | Missing | Card layout only; no sortable table view |
| Saved filter presets | Missing | No persistence of user filter preferences |
| Bulk actions | Missing | No export, reassign, or archive capabilities |
| Deep-link support | Missing | No bookmarkable filtered views |

**What remains:** Implement backend search/filter query endpoints in the Data Service, add faceted filtering and table view to the UI, and add bulk operations.

---

## 4. Agent Marketplace with Custom Agent SDK

**Current implementation: ~15% complete**

| Capability | Status | Detail |
|---|---|---|
| BaseAgent abstraction | Done | Well-designed abstract class with clear extension points (`validate_input`, `process`, `cleanup`) |
| Agent configuration system | Done | Config injection, readiness checks, cost tracking, policy evaluation, audit logging |
| Agent gallery (built-in) | Done | `AgentGallery.tsx` — displays 25 hardcoded agents with enable/disable toggles and parameter config |
| Agent catalog | Done | `agent_catalog.py` — static tuple of 25 entries; lookup functions |
| Public SDK package | Missing | No published SDK, no extension documentation |
| Dynamic agent registration | Missing | Catalog is hardcoded; no `register_agent()` or runtime registration API |
| Marketplace UI | Missing | No browse/install/configure flow for third-party agents |
| Packaging format | Missing | No manifest, Docker image, or schema declaration standard for external agents |
| Sandbox testing | Missing | No isolated environment for testing custom agents |
| Third-party RBAC | Missing | No permissions model for externally provided agents |

**What remains:** Extract a public SDK interface from BaseAgent, add dynamic registration to the catalog and orchestrator, define a packaging format, and build the marketplace UI.

---

## 5. Unified Cross-System Search with AI-Powered Summarisation

**Current implementation: ~40% complete**

| Capability | Status | Detail |
|---|---|---|
| Global search page | Done | `GlobalSearch.tsx` — type filtering (documents, projects, knowledge, approvals, workflows), date range, project filter, pagination, highlighted excerpts |
| Header search integration | Done | `Header.tsx` — Cmd+K shortcut, recent searches (localStorage), quick navigation, inline preview with 300ms debounce |
| Local document/knowledge search | Done | `search_service.py` — searches documents, lessons, spreadsheet items, projects, approvals, workflows |
| Backend search endpoint | Done | `GET /api/search?q=...&types=...&project_ids=...&offset=...&limit=...` |
| Vector store infrastructure | Done | `packages/vector_store/faiss_store.py` — FAISS-based with sharding, TTL, batch search (not wired into search path) |
| Connector search interface | Missing | `BaseConnector` has no `search()` method; no standard search interface across connectors |
| Multi-system fan-out | Missing | Search queries only local stores; no parallel invocation of connector searches |
| LLM-powered ranking/summarisation | Missing | No LLM Gateway integration for relevance scoring or result summarisation |
| Cross-system deduplication | Missing | Vector store exists but is not integrated into the search pipeline |
| RBAC/ABAC on search results | Missing | Search filters by tenant_id only; no field-level access policy enforcement |

**What remains:** Add a standard `search()` method to BaseConnector, build a federated search orchestrator, integrate the vector store for deduplication, and add LLM-powered ranking.

---

## 6. Interactive Gantt Chart with AI-Assisted Schedule Optimisation

**Current implementation: ~45% complete**

| Capability | Status | Detail |
|---|---|---|
| Gantt canvas component | Done | `GanttCanvas.tsx` — tabular CRUD for tasks (name, dates, dependencies, baseline); no visual timeline bars |
| Timeline canvas with drag-and-drop | Done | `TimelineCanvas.tsx` — visual bars with drag-to-reschedule, milestone detection, gate status |
| Critical Path Method | Done | `critical_path.py` — calculates early/late start/finish |
| Resource levelling algorithm | Done | `resource_scheduling.py` — RCPSP with serial schedule generation, resource utilisation metrics |
| Schedule optimisation recommendations | Done | `optimize.py` — identifies parallelisation, fast-track, crashing opportunities (returns text recommendations only) |
| Baseline data model | Done | Tasks track `baselineStart`/`baselineEnd` dates |
| Realtime co-edit infrastructure | Done | WebSocket hub with cursor tracking and content updates (generic, not Gantt-specific) |
| Unified interactive Gantt | Missing | GanttCanvas (tabular) and TimelineCanvas (visual bars) are separate; neither is a complete interactive Gantt |
| Dependency cascade on drag | Missing | Dragging a task doesn't recalculate dependent task dates |
| AI optimisation UI | Missing | No "Suggest optimal schedule" button; recommendations not actionable from UI |
| Resource levelling visualisation | Missing | Algorithm exists but results not pushed to UI |
| Gantt-specific collaboration events | Missing | Realtime service uses generic content updates; no task-level event protocol |
| Baseline comparison overlay | Missing | Data model supports it but no visual overlay implemented |

**What remains:** Merge GanttCanvas visuals with TimelineCanvas drag logic, add dependency cascade, build AI optimisation UI flow, and add Gantt-specific realtime event types.

---

## 7. Executive AI Briefing Generator

**Current implementation: ~65% complete**

| Capability | Status | Detail |
|---|---|---|
| Briefing page UI | Done | `ExecutiveBriefingPage.tsx` — audience selector (board/c-suite/PMO/delivery), tone, section checkboxes, format, generate/copy/regenerate, live preview, history |
| Backend generation API | Done | `POST /api/briefings/generate` — LLM-powered with audience-specific system prompts, section parsing, request validation |
| Briefing history | Done | `GET /api/briefings/history` — retrieves last 20 briefings |
| Unit tests | Done | Full test coverage for all audience types, section combinations, metadata formatting |
| Executive report templates | Done | `docs/templates/Executive-Report-Templates.md` — formal status report structure |
| Multi-channel notification delivery | Done | Notification Service supports Teams, Slack, Email, ACS (text/template rendering) |
| Cross-agent data aggregation | Missing | Briefing uses portfolio data passed to LLM but does not aggregate from Financial, Risk, Resource, Analytics agents |
| Scheduled delivery | Missing | No periodic delivery (weekly/fortnightly/monthly); Stakeholder Communications agent has scheduling capability but briefings are not connected to it |
| PDF/PPTX export | Missing | No rich-format document generation; notification service only supports text/template rendering |
| Template rendering engine | Missing | Document Service handles encryption/DLP only; no report template rendering to branded PDF/PowerPoint |

**What remains:** Connect briefing generation to cross-agent data aggregation, integrate scheduled delivery via the Stakeholder Communications agent, and add PDF/PPTX rendering capability.

---

## 8. Intelligent Resource Capacity Planning with Skill Matching

**Current implementation: ~75% complete**

| Capability | Status | Detail |
|---|---|---|
| Capacity planning engine | Done | `resource_capacity_agent.py` — `plan_capacity`, `forecast_capacity`, `scenario_analysis` actions with gap identification and mitigation strategies |
| Skill matching engine | Done | Weighted scoring (skills 0.6, availability 0.2, cost 0.1, performance 0.1), configurable threshold (0.70), Azure Search + embedding integration |
| ML-based forecasting | Done | Azure ML integration with AutoML, TimeSeriesForecaster, Synapse analytics |
| Hiring/training recommendations | Done | Plan includes hiring, training, and reallocation recommendations |
| LMS integration | Done | Training client for Moodle and Coursera Business with skill development tracking |
| Resource schema | Partial | `data/schemas/resource.schema.json` has `skills` (array of strings), `capacity_hours_per_week`, `allocation_pct`, `availability_pct` — but no structured taxonomy |
| HR connector sync | Partial | Workday syncs workers/positions; SAP SuccessFactors syncs users/jobs — neither syncs skill profiles |
| Skills taxonomy | Missing | No structured skill categories, levels, or standard framework (ESCO, SFIA, O*NET); skills are free-text only |
| HR skill data sync | Missing | No implementation to extract skills from HRIS systems and populate resource records |
| Portfolio-level demand aggregation | Missing | Forecast works per-project; no roll-up of planned demand by skill/role across the portfolio |
| Supply vs demand visualisation | Missing | No frontend for capacity curves or supply/demand graphs with drill-down by skill |

**What remains:** Define a structured skills taxonomy, implement skill data sync from HR connectors, add portfolio-level demand aggregation, and build a capacity planning dashboard.

---

## 9. End-to-End Intake-to-Project Automation with Guided Setup

**Current implementation: ~45% complete**

| Capability | Status | Detail |
|---|---|---|
| Intake form UI | Done | `IntakeFormPage.tsx` — multi-step form (sponsor, business, success, attachments), submits to `/api/intake` |
| Intake status page | Done | `IntakeStatusPage.tsx` — shows pending/approved/rejected status with sponsor, reviewers, decision card |
| Approval workflow agent | Done | Full approval chain orchestration with role-based routing, multi-level chains, delegation, escalation, event publishing |
| Workspace Setup agent | Done | `initialise_workspace`, `select_methodology`, `validate_connectors`, `provision_external_workspace`, event emission |
| Project Setup Wizard page | Done | `ProjectSetupWizardPage.tsx` — 4-step wizard (profile, methodology recommendation, template selection, configure & launch) |
| Intake workflow definition | Done | `project-intake.workflow.yaml` — submit → strategic alignment → PMO triage → notify |
| Post-approval project creation | Missing | No hook in approval agent to auto-create a project entity when intake is approved |
| Approval-to-setup routing | Missing | `IntakeStatusPage.tsx` shows decision status but has no "Create Project" button or redirect to `ProjectSetupWizardPage` |
| Linked workflow | Missing | Intake workflow terminates at `notify_requester`; no `create_project` or `provision_workspace` step |
| Connector toggle in setup wizard | Missing | Setup wizard recommends methodology and templates but has no connector category browser with per-project toggle |
| Team member assignment in wizard | Missing | No team/role assignment step in the existing setup wizard |

**What remains:** Add a post-approval hook to create the project entity, link the intake status page to the setup wizard on approval, extend the setup wizard with connector toggle and team assignment steps, and add a `create_project` step to the intake workflow.

---

## 10. Mobile-First Approval and Status Update Experience

**Current implementation: ~35% complete**

| Capability | Status | Detail |
|---|---|---|
| Approvals screen | Done | `ApprovalsScreen.tsx` — FlatList with approve/reject buttons, pull-to-refresh |
| Status update queue | Done | `statusQueue.ts` — offline persistence via SecureStore with enqueue/replay/clear (status updates only, not approvals) |
| Deep-link URL scheme | Partial | `notifications.ts` — `extractApprovalDeepLink()` generates `ppm://approvals/{id}`, `subscribeToApprovalDeepLinks()` listener; but `registerForApprovalNotifications()` is a stub |
| Secure session | Done | `secureSession.ts` — token persistence via SecureStore with restore/persist/clear |
| Dashboard | Done | `DashboardScreen.tsx` — portfolio summary, health status, risks, blockers, KPIs (plain text only) |
| AI assistant chat | Done | `AssistantScreen.tsx` — text-based chat with message history |
| Swipe-to-approve gestures | Missing | No gesture handler imports; approvals use standard Pressable buttons only |
| Offline approval queue | Missing | `statusQueue.ts` handles status updates only; no offline buffering for approve/reject actions |
| Biometric authentication | Missing | No `react-native-biometrics` or platform biometric API integration |
| Health badges and sparklines | Missing | Dashboard renders health as plain text; no charting library integrated |
| Voice-to-status | Missing | No speech recognition or voice input in AssistantScreen; text input only |
| Native push notifications | Missing | Notification registration is a stub (`Promise.resolve()`); no FCM/APNs setup |

**What remains:** Add swipe gesture handling, implement offline approval queue, integrate biometric auth, add charting library for health badges/sparklines, and add voice input capability.

---

## 11. Organisational Methodology Tailoring

**Current implementation: ~60% complete**

| Capability | Status | Detail |
|---|---|---|
| Methodology Editor UI | Done | `MethodologyEditor.tsx` — edit stages (add/remove/reorder), activities (with prerequisites, categories), gates and gate criteria; permission-gated on `methodology.edit` |
| Methodology Engine (Python) | Done | `methodology_engine.py` — built-in templates (Waterfall, Agile, PRINCE2, SAFe, Hybrid, Lean, Kanban), runtime `register_template()`, `recommend_methodology()` |
| Editor API routes | Done | `GET/POST /api/methodology/editor` — load and save customised definitions |
| Runtime lifecycle actions | Done | Generate, review, approve, publish actions with approval workflow; SoR read/publish endpoints |
| Methodology map discovery | Done | Auto-discovery from `docs/methodology/*/map.yaml`; override support via `METHODOLOGY_STORAGE_PATH` |
| Methodology workspace components | Done | `MethodologyWorkspaceSurface`, `MethodologyMapCanvas`, `MethodologyNav`, `ActivityDetailPanel` — activity locking, prerequisite enforcement, review queues |
| Methodology persistence | Partial | Stored in flat JSON file (`apps/web/storage/methodologies.json`); not integrated with Data Service |
| Tenant-level storage isolation | Missing | Storage is global; no per-tenant scoping of customised methodologies |
| Tenant-level policy enforcement | Missing | No org-level methodology restrictions (e.g. "this tenant only uses Hybrid and Adaptive") |
| Canonical schema and versioning | Missing | No JSON Schema in `data/schemas/` for methodology definitions; no Alembic migration |
| Data Service integration | Missing | Methodologies not persisted in the canonical data layer |
| Organisation settings UI | Missing | No admin page to configure allowed methodologies, org-level defaults, or department-specific policies |
| Change impact analysis | Missing | No detection of which active workspaces use a methodology being edited |
| Methodology version history | Missing | Audit events logged but not tied to methodology versions |

**What remains:** Migrate methodology storage to the Data Service with tenant scoping, add a canonical schema with versioning, build an organisation settings admin page, and implement change impact analysis.

---

## Summary Matrix — Remaining Work by Enhancement

### #1 — What-If Scenario Engine (~60% complete)

| Work Item | Type | Files to Update/Create |
|-----------|------|----------------------|
| Wire what-if controls to backend scenario APIs | UI (React) | `apps/web/frontend/src/pages/AnalyticsDashboard.tsx` |
| Build scenario builder UI (parameter sliders, side-by-side comparison) | UI (React, new) | `apps/web/frontend/src/components/analytics/ScenarioBuilder.tsx` (new) |
| Add natural-language scenario parsing via Intent Router | Agent action | `agents/core-orchestration/intent-router-agent/src/intent_router_agent.py` — add "what_if" intent classification |
| Add cross-project cascade impact calculation | Agent action | `agents/delivery-management/financial-management-agent/src/financial_actions/forecast_actions.py` — add `cascade_impact` handler |
| Add scenario template presets (cost reduction, aggressive growth, etc.) | Agent action | `agents/portfolio-management/portfolio-optimisation-agent/src/portfolio_actions/scenario_actions.py` — add template factory |
| Create API endpoint for UI-initiated scenario runs | API route | `apps/web/src/routes/analytics.py` or new `routes/scenarios.py` |

### #2 — Predictive Health Scoring (~55% complete)

| Work Item | Type | Files to Update/Create |
|-----------|------|----------------------|
| Build composite Project Health Index aggregating schedule, budget, risk, resource signals | Agent action | `agents/operations-management/analytics-insights-agent/src/analytics_actions/run_prediction.py` — add `compute_health_index` action |
| Collect signals from delivery agents | Agent orchestration | `agents/runtime/src/orchestrator.py` — add cross-agent data collection task for PHI |
| Replace linear trend prediction with ML-based anomaly detection | Service (Python) | `apps/analytics-service/src/predictive_models.py` — upgrade prediction algorithm |
| Add root cause analysis to alerts | Service (Python) | `apps/analytics-service/src/predictive_models.py` — add `root_cause` field with contributing factors |
| Add alert threshold rules engine | Service endpoint | `services/notification-service/src/main.py` — add configurable threshold-based alert triggers |
| Add health badge component to project cards | UI (React) | `apps/web/frontend/src/components/project/HealthBadge.tsx` (new) |
| Add health badge to mobile dashboard | UI (React Native) | `apps/mobile/src/screens/DashboardScreen.tsx` — replace plain-text health with badge component |
| Add portfolio-level health aggregation | Agent action | `agents/operations-management/analytics-insights-agent/src/analytics_actions/` — add `aggregate_portfolio_health` action |

### #3 — Collection Search Pages (~25% complete)

| Work Item | Type | Files to Update/Create |
|-----------|------|----------------------|
| Add search/filter query endpoints to Data Service | Service endpoint | `services/data-service/src/main.py` — add `GET /v1/entities/{schema}/search` with full-text, faceted filtering |
| Build faceted filter component (status, methodology, owner, date, tags) | UI (React, new) | `apps/web/frontend/src/components/collections/FacetedFilter.tsx` (new) |
| Add sortable table view alongside existing card view | UI (React, new) | `apps/web/frontend/src/components/collections/EntityTable.tsx` (new) |
| Upgrade WorkspaceDirectoryPage with server-side search, facets, view toggle | UI (React) | `apps/web/frontend/src/pages/WorkspaceDirectoryPage.tsx` |
| Add saved filter presets (per user) | UI (React) + API | `apps/web/frontend/src/pages/WorkspaceDirectoryPage.tsx` + `apps/web/src/routes/` (new preferences endpoint) |
| Add bulk actions (export, reassign, archive) | UI (React) | `apps/web/frontend/src/components/collections/BulkActions.tsx` (new) |
| Add deep-link support for bookmarkable filtered views | UI (React) | `apps/web/frontend/src/pages/WorkspaceDirectoryPage.tsx` — sync filter state with URL query params |

### #4 — Agent Marketplace (~15% complete)

| Work Item | Type | Files to Update/Create |
|-----------|------|----------------------|
| Extract public SDK interface from BaseAgent | Package (Python, new) | `agents/runtime/src/base_agent.py` — extract interface; new `packages/agent-sdk/` package |
| Define agent packaging format (manifest schema, Docker, prompts, schemas) | Schema + docs | `data/schemas/agent-manifest.schema.json` (new); `docs/connectors/` or new `docs/agent-sdk/` |
| Add dynamic agent registration to catalog | Agent runtime | `agents/runtime/src/agent_catalog.py` — add `register_agent()`, `unregister_agent()`, persistent store |
| Allow dynamically registered agents in task graphs | Agent runtime | `agents/runtime/src/orchestrator.py` — resolve agent references from dynamic catalog |
| Build agent registration API | API route (new) | `apps/api-gateway/src/api/routes/marketplace.py` (new) — `POST/DELETE /v1/agents/register` |
| Build marketplace UI (browse, install, configure, monitor) | UI (React, new) | `apps/web/frontend/src/pages/AgentMarketplacePage.tsx` (new) |
| Build agent sandbox execution environment | Service (new) | New sandboxed runner service or extend `services/agent-runtime/` |
| Add third-party agent RBAC permissions | Config | `config/rbac/roles.yaml`, `config/rbac/permissions.yaml` — add marketplace permissions |

### #5 — Cross-System Search (~40% complete)

| Work Item | Type | Files to Update/Create |
|-----------|------|----------------------|
| Add standard `search()` method to BaseConnector | Connector SDK | `connectors/sdk/src/base_connector.py` — add abstract `search(query, limit)` method |
| Implement `search()` in key connectors | Connector implementations | `connectors/jira/src/jira_connector.py`, `connectors/confluence/src/`, `connectors/sharepoint/src/`, `connectors/sap/src/` (and others) |
| Build federated search orchestrator (parallel fan-out, aggregation) | Service (Python, new) | `apps/web/src/search_service.py` — add `federated_search()` alongside existing local search |
| Integrate vector store for semantic deduplication | Package integration | `apps/web/src/search_service.py` — wire `packages/vector_store/faiss_store.py` into search pipeline |
| Add LLM-powered ranking and summarisation | Service (Python) | `apps/web/src/search_service.py` — call `packages/llm/src/llm/client.py` for result ranking/summarisation |
| Add source system attribution badges to results | UI (React) | `apps/web/frontend/src/pages/GlobalSearch.tsx` — add source system icons and labels per result |
| Enforce RBAC/ABAC on cross-system results | Service (Python) | `apps/web/src/search_service.py` — integrate `config/rbac/field-level.yaml` and `config/abac/policies.yaml` filtering |

### #6 — Interactive Gantt + AI (~45% complete)

| Work Item | Type | Files to Update/Create |
|-----------|------|----------------------|
| Merge GanttCanvas (tabular) with TimelineCanvas (visual bars + drag) into unified component | UI (React) | `packages/canvas-engine/src/components/GanttCanvas/GanttCanvas.tsx` — integrate TimelineCanvas drag logic and visual bar rendering |
| Add dependency cascade recalculation on task drag | UI (React) + Algorithm | `packages/canvas-engine/src/components/GanttCanvas/GanttCanvas.tsx` — call CPM recalculation on drag end |
| Add visual dependency connector lines between tasks | UI (React) | `packages/canvas-engine/src/components/GanttCanvas/GanttCanvas.tsx` — render SVG connector lines |
| Build "Suggest optimal schedule" button invoking Schedule Planning agent | UI (React) + API | `packages/canvas-engine/src/components/GanttCanvas/GanttCanvas.tsx` + `apps/web/src/routes/methodology.py` — add optimisation endpoint |
| Make schedule optimisation recommendations actionable (accept/reject/modify) | Agent action | `agents/delivery-management/schedule-planning-agent/src/schedule_actions/optimize.py` — add `apply_optimization` handler |
| Add resource levelling visualisation | UI (React, new) | `packages/canvas-engine/src/components/GanttCanvas/ResourceLevelChart.tsx` (new) |
| Add Gantt-specific realtime collaboration event types | Service (Python) | `services/realtime-coedit-service/src/main.py` — add task-level event protocol (task_moved, dependency_changed) |
| Add baseline comparison overlay | UI (React) | `packages/canvas-engine/src/components/GanttCanvas/GanttCanvas.tsx` — render planned vs actual vs baseline bars |

### #7 — Executive Briefing Generator (~65% complete)

| Work Item | Type | Files to Update/Create |
|-----------|------|----------------------|
| Connect briefing generation to cross-agent data (Financial, Risk, Resource, Analytics) | API route | `apps/web/src/routes/briefings.py` — aggregate data from multiple agent endpoints before LLM generation |
| Integrate scheduled delivery via Stakeholder Communications agent | Agent action | `agents/operations-management/stakeholder-communications-agent/src/` — add `schedule_briefing` action connecting to briefing API |
| Add scheduling configuration UI (frequency, recipients, channels) | UI (React) | `apps/web/frontend/src/pages/ExecutiveBriefingPage.tsx` — add schedule configuration panel |
| Add PDF rendering capability | Service (Python, new) | `apps/document-service/src/` — add PDF generation (e.g. WeasyPrint or ReportLab) from briefing content |
| Add PPTX rendering capability | Service (Python, new) | `apps/document-service/src/` — add PowerPoint generation (e.g. python-pptx) from briefing sections |
| Add rich-format attachment delivery to notification service | Service endpoint | `services/notification-service/src/main.py` — add attachment support for email/Teams/Slack delivery |

### #8 — AI Capacity Planning (~75% complete)

| Work Item | Type | Files to Update/Create |
|-----------|------|----------------------|
| Define structured skills taxonomy (categories, levels, framework) | Data schema | `data/schemas/resource.schema.json` — extend `skills` from free-text array to structured objects with category/level/framework |
| Add Alembic migration for skills schema change | Migration | `data/migrations/versions/0010_skills_taxonomy.py` (new) |
| Implement skill data sync from Workday | Connector | `connectors/workday/src/workday_connector.py` — add skill profile extraction to `read()` |
| Implement skill data sync from SAP SuccessFactors | Connector | `connectors/sap_successfactors/src/sap_successfactors_connector.py` — add skill/competency extraction |
| Add portfolio-level demand aggregation by skill/role | Agent action | `agents/delivery-management/resource-management-agent/src/resource_capacity_agent.py` — add `aggregate_portfolio_demand` action |
| Build capacity planning dashboard (supply vs demand curves, drill-down) | UI (React, new) | `apps/web/frontend/src/pages/CapacityPlanningPage.tsx` (new) |
| Add route for capacity planning page | UI (React) | `apps/web/frontend/src/App.tsx` — add route |
| Integrate recommendations with HR workflow (optional) | Agent action | `agents/delivery-management/resource-management-agent/src/resource_capacity_agent.py` — add `route_recommendation` action connecting to HR connectors |

### #9 — Intake-to-Project Automation (~45% complete)

| Work Item | Type | Files to Update/Create |
|-----------|------|----------------------|
| Add post-approval hook to create project entity in Data Service | Agent action | `agents/core-orchestration/approval-workflow-agent/src/decision_actions.py` — add project creation logic on `approval.approved` event for intake type |
| Add `create_project` step to intake workflow definition | Workflow config | `ops/config/demo-workflows/project-intake.workflow.yaml` — add step after `notify_requester` |
| Add approval-to-setup-wizard routing on intake status page | UI (React) | `apps/web/frontend/src/pages/IntakeStatusPage.tsx` — add "Configure Project" button/redirect on approval |
| Add connector category browser with per-project toggle to setup wizard | UI (React) | `apps/web/frontend/src/pages/ProjectSetupWizardPage.tsx` — add connector selection step pulling from `connectors/registry/connectors.json` |
| Add team member and role assignment step to setup wizard | UI (React) | `apps/web/frontend/src/pages/ProjectSetupWizardPage.tsx` — add team assignment step with RBAC role picker |
| Wire setup wizard confirmation to Workspace Setup agent | API route | `apps/web/src/routes/` — ensure `/api/project-setup/configure-workspace` passes connector and team selections to workspace agent |
| Emit real-time notification on project creation | Service (Python) | `agents/core-orchestration/approval-workflow-agent/src/decision_actions.py` — emit WebSocket event for `useRealtimeConsole` |

### #10 — Mobile-First Experience (~35% complete)

| Work Item | Type | Files to Update/Create |
|-----------|------|----------------------|
| Add swipe-to-approve/reject gestures | UI (React Native) | `apps/mobile/src/screens/ApprovalsScreen.tsx` — add `react-native-gesture-handler` swipe actions |
| Add offline approval queue | Service (React Native) | `apps/mobile/src/services/approvalQueue.ts` (new) — mirror `statusQueue.ts` pattern for approval actions |
| Implement native push notification registration (FCM/APNs) | Service (React Native) | `apps/mobile/src/services/notifications.ts` — replace stub `registerForApprovalNotifications()` with Expo Notifications setup |
| Add deep-link routing from push notifications to specific screens | Service (React Native) | `apps/mobile/src/services/notifications.ts` — add notification response handler with screen navigation |
| Add biometric authentication for sensitive approvals | Service (React Native) | `apps/mobile/src/services/secureSession.ts` — integrate `expo-local-authentication` for fingerprint/Face ID |
| Add health badge and sparkline components to dashboard | UI (React Native) | `apps/mobile/src/screens/DashboardScreen.tsx` — add charting library (e.g. `react-native-svg` + `victory-native`) |
| Add voice-to-status via speech recognition | UI (React Native) | `apps/mobile/src/screens/AssistantScreen.tsx` — integrate `expo-speech` or `@react-native-voice/voice` for dictation |
| Add package dependencies | Config | `apps/mobile/package.json` — add `react-native-gesture-handler`, `expo-local-authentication`, charting/voice libraries |

### #11 — Methodology Tailoring (~60% complete)

| Work Item | Type | Files to Update/Create |
|-----------|------|----------------------|
| Add tenant-scoped methodology storage | Service (Python) | `apps/web/src/methodologies.py` — scope `_load_methodology_storage()` and `_write_json()` by `tenant_id` |
| Migrate methodology persistence to Data Service | Service endpoint | `services/data-service/src/main.py` — add methodology CRUD endpoints with tenant isolation |
| Create canonical methodology JSON Schema | Data schema (new) | `data/schemas/methodology.schema.json` (new) |
| Add Alembic migration for methodology definitions | Migration (new) | `data/migrations/versions/0010_methodology_definitions.py` (new) |
| Add methodology versioning (immutable versions, new projects use latest) | Service (Python) | `services/data-service/src/main.py` — add version tracking; `apps/web/src/methodologies.py` — version on save |
| Build organisation settings admin page | UI (React, new) | `apps/web/frontend/src/pages/OrganisationMethodologySettings.tsx` (new) — configure allowed methodologies, defaults per department |
| Add route for organisation settings page | UI (React) | `apps/web/frontend/src/App.tsx` — add admin route |
| Add tenant-level policy enforcement on workspace creation | Agent action | `agents/core-orchestration/workspace-setup-agent/src/workspace_setup_agent.py` — validate methodology selection against tenant policy |
| Add change impact analysis before methodology edits | API route | `apps/web/src/routes/methodology.py` — add endpoint returning active workspaces using the methodology being edited |
| Document methodology tailoring workflow | Documentation | `docs/methodology/customisation-guide.md` (new) |

---

## Summary Matrix

| # | Enhancement | Done | Files to Update/Create | Primary Persona | Effort | Impact |
|---|------------|------|----------------------|----------------|--------|--------|
| 1 | What-If Scenario Engine | ~60% | `apps/web/frontend/src/pages/AnalyticsDashboard.tsx`, `apps/web/frontend/src/components/analytics/ScenarioBuilder.tsx` (new), `agents/core-orchestration/intent-router-agent/src/intent_router_agent.py`, `agents/delivery-management/financial-management-agent/src/financial_actions/forecast_actions.py`, `agents/portfolio-management/portfolio-optimisation-agent/src/portfolio_actions/scenario_actions.py`, `apps/web/src/routes/scenarios.py` (new) | CFO, PMO Director | Medium | High |
| 2 | Predictive Health Scoring | ~55% | `agents/operations-management/analytics-insights-agent/src/analytics_actions/run_prediction.py`, `agents/runtime/src/orchestrator.py`, `apps/analytics-service/src/predictive_models.py`, `services/notification-service/src/main.py`, `apps/web/frontend/src/components/project/HealthBadge.tsx` (new), `apps/mobile/src/screens/DashboardScreen.tsx` | PMO Director, PM | Medium | High |
| 3 | Collection Search Pages | ~25% | `services/data-service/src/main.py`, `apps/web/frontend/src/components/collections/FacetedFilter.tsx` (new), `apps/web/frontend/src/components/collections/EntityTable.tsx` (new), `apps/web/frontend/src/components/collections/BulkActions.tsx` (new), `apps/web/frontend/src/pages/WorkspaceDirectoryPage.tsx` | All users | Low-Med | Critical |
| 4 | Agent Marketplace | ~15% | `agents/runtime/src/base_agent.py`, `packages/agent-sdk/` (new), `data/schemas/agent-manifest.schema.json` (new), `agents/runtime/src/agent_catalog.py`, `agents/runtime/src/orchestrator.py`, `apps/api-gateway/src/api/routes/marketplace.py` (new), `apps/web/frontend/src/pages/AgentMarketplacePage.tsx` (new), `config/rbac/roles.yaml`, `config/rbac/permissions.yaml` | CIO, Partners | High | Very High |
| 5 | Cross-System Search | ~40% | `connectors/sdk/src/base_connector.py`, `connectors/jira/src/jira_connector.py`, `connectors/confluence/src/`, `connectors/sharepoint/src/`, `connectors/sap/src/`, `apps/web/src/search_service.py`, `packages/vector_store/faiss_store.py`, `apps/web/frontend/src/pages/GlobalSearch.tsx`, `config/rbac/field-level.yaml` | PM, PMO Analyst | Medium | High |
| 6 | Interactive Gantt + AI | ~45% | `packages/canvas-engine/src/components/GanttCanvas/GanttCanvas.tsx`, `packages/canvas-engine/src/components/GanttCanvas/ResourceLevelChart.tsx` (new), `agents/delivery-management/schedule-planning-agent/src/schedule_actions/optimize.py`, `apps/web/src/routes/methodology.py`, `services/realtime-coedit-service/src/main.py` | PM, Scheduler | Med-High | High |
| 7 | Executive Briefing Generator | ~65% | `apps/web/src/routes/briefings.py`, `agents/operations-management/stakeholder-communications-agent/src/`, `apps/web/frontend/src/pages/ExecutiveBriefingPage.tsx`, `apps/document-service/src/` (PDF + PPTX), `services/notification-service/src/main.py` | C-suite, PMO Dir | Low-Med | Very High |
| 8 | AI Capacity Planning | ~75% | `data/schemas/resource.schema.json`, `data/migrations/versions/0010_skills_taxonomy.py` (new), `connectors/workday/src/workday_connector.py`, `connectors/sap_successfactors/src/sap_successfactors_connector.py`, `agents/delivery-management/resource-management-agent/src/resource_capacity_agent.py`, `apps/web/frontend/src/pages/CapacityPlanningPage.tsx` (new), `apps/web/frontend/src/App.tsx` | CIO, Resource Mgr | Low-Med | High |
| 9 | Intake-to-Project Automation | ~45% | `agents/core-orchestration/approval-workflow-agent/src/decision_actions.py`, `ops/config/demo-workflows/project-intake.workflow.yaml`, `apps/web/frontend/src/pages/IntakeStatusPage.tsx`, `apps/web/frontend/src/pages/ProjectSetupWizardPage.tsx`, `apps/web/src/routes/` (workspace config endpoint) | PM, PMO Director | Low-Med | High |
| 10 | Mobile-First Experience | ~35% | `apps/mobile/src/screens/ApprovalsScreen.tsx`, `apps/mobile/src/services/approvalQueue.ts` (new), `apps/mobile/src/services/notifications.ts`, `apps/mobile/src/services/secureSession.ts`, `apps/mobile/src/screens/DashboardScreen.tsx`, `apps/mobile/src/screens/AssistantScreen.tsx`, `apps/mobile/package.json` | Executives, PM | Medium | High |
| 11 | Methodology Tailoring | ~60% | `apps/web/src/methodologies.py`, `services/data-service/src/main.py`, `data/schemas/methodology.schema.json` (new), `data/migrations/versions/0010_methodology_definitions.py` (new), `apps/web/frontend/src/pages/OrganisationMethodologySettings.tsx` (new), `apps/web/frontend/src/App.tsx`, `agents/core-orchestration/workspace-setup-agent/src/workspace_setup_agent.py`, `apps/web/src/routes/methodology.py`, `docs/methodology/customisation-guide.md` (new) | PMO Admin, CIO | Medium | Critical |

### Recommended Priority Order

1. **#11 Organisational Methodology Tailoring** — Deployment prerequisite; editor functional but needs tenant isolation
2. **#3 Collection Search Pages** — Table stakes; basic UI exists but backend search missing
3. **#9 Intake-to-Project Automation** — Individual pieces exist; needs end-to-end linking (depends on #11)
4. **#7 Executive Briefing Generator** — Generation MVP works; needs scheduled delivery and export
5. **#8 AI Capacity Planning** — Engine is mature; needs taxonomy and visualisation
6. **#2 Predictive Health Scoring** — Dashboard exists; needs composite index and ML upgrade
7. **#1 What-If Scenario Engine** — Backend engines complete; needs UI wiring and NLP layer
8. **#5 Cross-System Search** — Local search works well; federated layer is a new build
9. **#6 Interactive Gantt + AI** — Strong components exist; unification effort
10. **#10 Mobile-First Experience** — Basic app works; advanced UX is incremental
11. **#4 Agent Marketplace** — Highest long-term value, mostly greenfield
