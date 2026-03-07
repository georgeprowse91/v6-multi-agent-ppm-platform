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

## Summary Matrix

| # | Enhancement | Current Status | Primary Persona | Remaining Effort | Impact | Revenue Lever |
|---|------------|---------------|----------------|-----------------|--------|---------------|
| 1 | What-If Scenario Engine | ~60% — backend engines done, UI and NLP missing | CFO, PMO Director | Medium | High | Upsell to Enterprise tier |
| 2 | Predictive Health Scoring | ~55% — dashboard and alerts done, composite index and ML missing | PMO Director, PM | Medium | High | Core value prop |
| 3 | Collection Search Pages | ~25% — basic card list done, backend search and filtering missing | All users | Low-Medium | Critical | Table stakes |
| 4 | Agent Marketplace | ~15% — BaseAgent abstraction done, everything else missing | CIO, Partners | High | Very High | New revenue stream |
| 5 | Cross-System Search | ~40% — local search UI done, federated connector search missing | PM, PMO Analyst | Medium | High | Orchestration differentiator |
| 6 | Interactive Gantt + AI | ~45% — components and algorithms exist separately, unification missing | PM, Scheduler | Medium-High | High | Win predictive-methodology deals |
| 7 | Executive Briefing Generator | ~65% — generation UI and API done, scheduled delivery and PDF export missing | C-suite, PMO Director | Low-Medium | Very High | Premium feature |
| 8 | AI Capacity Planning | ~75% — planning and matching engines done, taxonomy and HR sync missing | CIO, Resource Manager | Low-Medium | High | Enterprise upsell |
| 9 | Intake-to-Project Automation | ~45% — individual pieces exist, end-to-end linking missing | PM, PMO Director | Low-Medium | High | Demo showpiece |
| 10 | Mobile-First Experience | ~35% — basic screens done, advanced UX features missing | Executives, PM | Medium | High | Competitive differentiator |
| 11 | Methodology Tailoring | ~60% — editor and engine done, tenant isolation and Data Service integration missing | PMO Admin, CIO | Medium | Critical | Deployment prerequisite + services revenue |

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
