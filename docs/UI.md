# UI

> This section documents the user-interface layer of the Multi-Agent PPM platform: a detailed reference for every component in the React SPA and Streamlit demo; a capability-by-capability coverage matrix mapping routes and backend endpoints to their implementation status; and an ordered backlog of known gaps with acceptance criteria for each item.

## Contents

- [Component Reference](#component-reference)
- [Connectors and System-of-Record Data Flow](#connectors-and-system-of-record-data-flow)
- [Coverage Matrix](#coverage-matrix)
- [Known Gaps](#known-gaps)

---

## Component Reference

> Last reviewed: 2026-02-23

This reference covers every UI component in the platform across two surfaces: the React SPA (`apps/web/frontend`) and the Streamlit standalone demo (`apps/demo_streamlit`). It is intended for developers extending either surface, QA engineers verifying component behaviour, and product stakeholders reading capability coverage.

### 1. SPA Shell Components

Source root: `apps/web/frontend/src/components/layout/`

#### `AppLayout`

**File:** `AppLayout.tsx`

Top-level authenticated layout wrapper rendered by every guarded route. Bootstraps feature flags and composes the three-panel shell.

| Responsibility | Detail |
|---|---|
| Feature flag bootstrap | Fetches `GET /v1/config` on mount; writes `feature_flags` into the global app store. Falls back to empty flags on error. |
| Realtime console | Activates `useRealtimeConsole()` for server-sent agent events. |
| Accessibility | Renders a visually-hidden "Skip to main content" anchor as the first focusable element. |
| Tour wrapping | Wraps all children in `TourProvider` so any page can activate the onboarding tour. |

**Children rendered (in order):**
```
TourProvider
  └── div.layout
        ├── <a> Skip link
        ├── Header
        └── div.body
              ├── LeftPanel
              ├── MainCanvas  ← page content via `children` prop
              └── AssistantPanel
```

**Props:**
| Prop | Type | Description |
|---|---|---|
| `children` | `React.ReactNode` | Page-level component rendered inside `MainCanvas`. |

---

#### `Header`

**File:** `Header.tsx`

Top application bar. Displays the platform wordmark, global search trigger, user avatar, and notification badge. Reads auth session from the app store.

---

#### `LeftPanel`

**File:** `LeftPanel.tsx`

Collapsible primary navigation sidebar. Switches between two modes depending on the current route:

| Mode | Trigger | Content |
|---|---|---|
| `hub` | Any route that is **not** a project workspace | Navigate / Work / Insights / Hub Admin sections |
| `project-workspace` | Route matches `/projects/:id` or `/project/:id` | Methodology block + project-scoped links |

**Hub nav sections:**

| Section | Links |
|---|---|
| Navigate | Home, Demo Run (25 Agents), Enterprise Uplift, My Portfolios, My Programs, My Projects |
| Work | New Intake, My Approvals, Intake Approvals |
| Insights | Analytics Dashboard, Documents, Lessons Learned |
| Hub Admin (collapsible) | Agents, Connectors, Workflows, Prompt Library, Workflow Monitor, Methodology Editor; + feature-flagged: Merge Review, Notification Center, Role Management, Role Assignments, Audit Logs, Agent Runs |

**Project-workspace nav sections:**

| Section | Links |
|---|---|
| Methodology | Methodology picker `<select>` + `MethodologyNav` tree |
| Project | Documents, Lessons Learned, Analytics, Performance Dashboard, My Approvals, Configuration (permission-gated) |

**Visibility rules (Hub Admin items):**

| Item | Gate |
|---|---|
| Merge Review | `featureFlags.duplicate_resolution === true` |
| Notification Center | `featureFlags.agent_async_notifications === true` |
| Role Management / Assignments | `hasPermission(permissions, 'roles.manage')` |
| Audit Logs | `canViewAuditLogs(permissions)` |
| Agent Runs | `featureFlags.agent_run_ui === true` |

**Keyboard navigation:** Arrow Up/Down, Home, End traverse `[data-nav-item="true"]` anchors within the `<nav>`.

**Collapsed state:** When `leftPanelCollapsed` is true, text labels are hidden; icon-only links expose `title` / `aria-label` attributes matching the full label.

---

#### `MainCanvas`

**File:** `MainCanvas.tsx`

Scrollable content region that hosts the active page component. Provides an `id="main-content"` skip-link target and applies `role="main"`.

---

### 2. Assistant Panel Components

Source root: `apps/web/frontend/src/components/assistant/`

#### `AssistantPanel`

**File:** `AssistantPanel.tsx`

The persistent right-hand conversational assistant. Always rendered by `AppLayout`; collapses to an icon-only rail when `rightPanelCollapsed` is true.

**Modes:**

| Mode | Route/trigger | Behaviour |
|---|---|---|
| `entry` | `/` (home) and non-workspace routes | Shows `ENTRY_ASSISTANT_CHIPS` quick-action chips |
| `intake` | `/intake/new` | Routes messages through `useIntakeAssistantAdapter`; patches apply to the intake form via `IntakeAssistantStore` |
| `workspace` | `/projects/:id` | Context-aware methodology chips generated by `useSuggestionEngine` |
| `demo` | `VITE_DEMO_MODE=true` | Replays scripted conversation scenarios; no live LLM calls |

**Sub-components composed:**

| Component | Role |
|---|---|
| `AssistantHeader` | Title bar with AI state indicator and collapse toggle |
| `ContextBar` | Collapsible breadcrumb showing project > stage > activity; pulsing sync chip when context changes |
| `MessageList` | Scrollable transcript of `user`, `assistant`, and `system` messages; renders `ActionChip` buttons inline |
| `QuickActions` | Chip rail for suggested actions (generated by `useSuggestionEngine`) |
| `ChatInput` | Textarea + send button; supports `/research` slash-command shortcut |

**LLM model selection:** Fetches `GET /v1/api/llm/models` to populate a provider/model `<select>`. Users with `config.manage` or `llm.manage` permission can save a project-scoped default via `POST /v1/api/llm/preferences`.

**Demo mode scripted scenarios:**

| Scenario ID | Label |
|---|---|
| `project_intake` | Project Intake |
| `resource_request` | Resource Request |
| `vendor_procurement` | Vendor Procurement |

Scripts are loaded from `GET /api/assistant/demo-conversations/:scenarioId`. The assistant matches user input against the expected script message and advances or branches accordingly.

**Action chip payload types (handled in `handleChipClick`):**

| `payload.type` | Effect |
|---|---|
| `open_activity` | Navigates to and opens the named activity canvas |
| `open_artifact` | Opens the current activity's artifact canvas |
| `open_dashboard` | Opens `act-dashboard` in `stage-monitoring` |
| `generate_template` | Queues a template generation notification |
| `show_prerequisites` | Lists incomplete prerequisite activity names |
| `complete_activity` | Sets activity status to `complete` via methodology store |
| `scope_research` | Sends `/research <objective>` to the chat backend |
| `custom` (various `actionKey` values) | See table below |

**Custom action keys:**

| `actionKey` | Effect |
|---|---|
| `navigate_intake` | Navigates to `/intake/new` |
| `open_workspace` | Navigates to `/<workspaceType>s` |
| `methodology_runtime_action` | Executes `executeNodeAction` then opens resulting artifact |
| `ask_question` | Focuses the `ChatInput` textarea |
| `intake_apply_field` | Enqueues an intake form field patch via `IntakeAssistantStore` |

---

#### `AssistantHeader`

**File:** `AssistantHeader.tsx`

Title row for the assistant panel. Displays the panel title, an AI state badge (`idle` / `thinking` / `streaming`), and the collapse toggle button.

---

#### `ContextBar`

**File:** `ContextBar.tsx`

Collapsible context breadcrumb rendered immediately below `AssistantHeader`. Shows a `stage > activity` breadcrumb, a sync-pulse chip that animates for 900 ms on each context change, and a stage-progress percentage badge. Expanded view reveals: Project name, Methodology name, Stage progress %, Activity lock state.

**Props:**
| Prop | Type | Description |
|---|---|---|
| `context` | `AssistantContext` | Current workspace context snapshot |
| `contextSyncLabel?` | `string` | Triggers a pulse animation when this string value changes |

---

#### `MessageList`

**File:** `MessageList.tsx`

Scrollable transcript. Renders each message as a bubble (user, assistant, or system). Assistant messages may include inline `ActionChip` buttons. Shows a typing indicator when `typingStatus` is active. Supports `aiState` to display a loading skeleton when streaming.

---

#### `QuickActions`

**File:** `QuickActions.tsx`

Horizontal chip rail rendered below `MessageList`. Each chip maps to an `ActionChip` from the assistant store. Disabled chips render visually muted and block the `handleChipClick` handler.

---

#### `ChatInput`

**File:** `ChatInput.tsx`

Textarea-based message input. Features:
- Auto-resize on content growth
- Submit on Enter (Shift+Enter inserts newline)
- `/research` scope button as a secondary CTA
- Displays an `error` string from `useAssistantChat` when the backend returns an error

---

### 3. Methodology Components

Source root: `apps/web/frontend/src/components/methodology/`

#### `MethodologyWorkspaceSurface`

**File:** `MethodologyWorkspaceSurface.tsx`

The main content area when a project workspace is active. Composes the methodology map (stage/activity navigation) with the activity detail panel.

**Canvas type mapping (`canvasMap`):**

| Canvas type string | Resolved `CanvasType` |
|---|---|
| `document`, `whiteboard` | `document` |
| `tree` | `tree` |
| `timeline` | `timeline` |
| `spreadsheet` | `spreadsheet` |
| `dashboard` | `dashboard` |
| `board`, `kanban` | `board` |
| `backlog` | `backlog` |
| `gantt` | `gantt` |
| `grid`, `risk_log`, `form` | `grid` |
| `financial` | `financial` |
| `dependency_map` | `dependency_map` |
| `roadmap` | `roadmap` |
| `approval`, `decision_log` | `approval` |

Backend reachability is checked on mount; when `backendReachable === false` the surface renders a read-only fallback notice.

**Lifecycle actions available:** `generate`, `update`, `review`, `approve`, `publish`, `view`. Each dispatches `POST /api/methodology/runtime/action`.

---

#### `MethodologyNav`

**File:** `MethodologyNav.tsx`

Tree-structured stage/activity navigator rendered inside `LeftPanel` when in `project-workspace` mode. Stages can be expanded/collapsed. Selecting an activity calls `setCurrentActivity` on the methodology store.

**Props:**
| Prop | Type | Description |
|---|---|---|
| `collapsed` | `boolean` | When true (panel is icon-only), renders icon-only stage nodes |

---

#### `MethodologyMapCanvas`

**File:** `MethodologyMapCanvas.tsx`

Full-canvas stage/activity grid rendered in the main workspace area. Each stage is a column; each activity is a card. Cards display status indicators (not started / in progress / complete / locked). Clicking a card sets it as the current activity.

---

#### `ActivityDetailPanel`

**File:** `ActivityDetailPanel.tsx`

Detail pane shown alongside `MethodologyMapCanvas` when an activity is selected. Displays activity name, stage label, status, description, missing prerequisite names (when locked), lock indicator, lifecycle action buttons, and an approvals inbox (`reviewQueue`) with accept/reject/modify decision controls.

**Props:**
| Prop | Type | Description |
|---|---|---|
| `activity` | `MethodologyActivity` | The selected activity object |
| `stageLabel` | `string` | Human-readable stage name |
| `isLocked` | `boolean` | Whether the activity's prerequisites are unmet |
| `missingPrerequisites` | `string[]` | Names of incomplete prerequisite activities |
| `runtimeActionsAvailable` | `string[]` | Lifecycle events the backend permits for this activity |
| `reviewQueue` | `ReviewItem[]` | Pending approval requests for this activity |
| `onLifecycleAction` | `(event) => void` | Called when a lifecycle button is clicked |
| `onReviewDecision` | `(approvalId, decision, notes?) => void` | Called when an approval decision is submitted |
| `actionsDisabled?` | `boolean` | Disables all action buttons (e.g. during backend call) |

---

### 4. Dashboard / Analytics Components

Source root: `apps/web/frontend/src/components/dashboard/`

#### `KpiWidget`

**File:** `KpiWidget.tsx`

Single-metric card for portfolio/project KPI display. Auto-detects delta tone from the `delta` string:

| Delta string prefix/symbol | Rendered tone |
|---|---|
| Starts with `+`, contains `▲` or `↑` | `positive` (green) |
| Starts with `-`, contains `▼` or `↓` | `negative` (red) |
| Anything else or absent | `neutral` |

**Props:**
| Prop | Type | Description |
|---|---|---|
| `label` | `string` | Metric label (e.g. "On-time delivery") |
| `value` | `string` | Primary metric value (e.g. "87%") |
| `delta?` | `string` | Period-over-period change (e.g. "+3%") |
| `description?` | `string` | Optional text appended after the delta |

---

#### `StatusIndicator`

**File:** `StatusIndicator.tsx`

Inline status badge used on pipeline cards and activity rows. Maps a status string to a colour-coded dot and label.

---

### 5. Primitive / Shared UI Components

Source root: `apps/web/frontend/src/components/ui/`

#### `EmptyState`

**File:** `EmptyState.tsx`

Centred placeholder shown when a list or canvas has no content. Wraps the content in `FadeIn` for a smooth mount animation.

**Props:**
| Prop | Type | Description |
|---|---|---|
| `icon` | `'dashboard' \| 'timeline' \| 'search' \| 'confirm' \| 'agents' \| 'connectors' \| 'workflow'` | Semantic icon key, resolved to a lucide icon via `iconSemanticMap` |
| `title` | `string` | Bold heading |
| `description` | `string` | Supporting text |
| `action?` | `{ label, onClick?, href? }` | Optional CTA — renders as `<button>` when `onClick` is provided, `<a>` when `href` is provided |
| `className?` | `string` | Optional CSS class override |

---

#### `Skeleton`

**File:** `Skeleton.tsx`

Animated loading placeholder. Accepts `width`, `height`, and `borderRadius` style overrides. Used by `WorkspacePage` and `AnalyticsDashboard` while entity data is loading.

---

#### `FadeIn`

**File:** `FadeIn.tsx`

Lightweight animation wrapper that applies a CSS keyframe fade from `opacity: 0` to `opacity: 1` on mount. Used by `EmptyState` and other components for perceived performance.

---

#### `OnboardingTour`

Source: `apps/web/frontend/src/components/tours/`

Step-by-step guided tour driven by `TourProvider` context. Tour steps are keyed to `data-tour` attributes on target elements (set by `LeftPanel` and `AssistantPanel`). Tour state (started, current step, dismissed) is persisted in `localStorage`.

---

### 6. Icon System

Source root: `apps/web/frontend/src/components/icon/`

#### `Icon`

**File:** `Icon.tsx`

The single icon primitive for the entire SPA. All icons must be addressed via semantic keys, never raw lucide component names.

**Props:**
| Prop | Type | Required | Description |
|---|---|---|---|
| `semantic` | `IconSemantic` | Yes | Semantic key resolved via `iconMap` (e.g. `'artifact.dashboard'`) |
| `decorative` | `true` | Conditional | Pass when the icon is purely visual; sets `aria-hidden="true"` and omits `role="img"` |
| `label` | `string` | Conditional (required when not decorative) | Accessible label; sets `aria-label` and `title` |
| `size?` | `'sm' \| 'md' \| 'lg' \| 'xl' \| '2xl' \| '3xl'` | No | Overrides the entry's default size token |
| `color?` | `IconColorKey` | No | Overrides the entry's default colour token |
| `className?` | `string` | No | Additional CSS classes |
| `style?` | `CSSProperties` | No | Inline style overrides |
| `title?` | `string` | No | Tooltip text (defaults to `label` when not decorative) |

**Size tokens:**

| Size key | Source token |
|---|---|
| `sm` | `tokens.iconography.sizePx.min` |
| `md` | `tokens.iconography.sizePx.default` |
| `lg` | `tokens.iconography.sizePx.max` |
| `xl` | `tokens.spacingPx.lg` |
| `2xl` | `tokens.spacingPx.xl` |
| `3xl` | `tokens.spacingPx['2xl']` |

**Semantic key namespaces (sample):**

| Namespace | Example keys | Lucide icons |
|---|---|---|
| `artifact.*` | `artifact.dashboard`, `artifact.document`, `artifact.timeline`, `artifact.tree` | `LayoutDashboard`, `FileText`, `Calendar`, `GitBranch` |
| `actions.*` | `actions.edit`, `actions.confirmApply`, `actions.settings` | `Edit3`, `Check`, `Settings` |
| `navigation.*` | `navigation.collapse`, `navigation.search` | `ChevronDown`, `Search` |
| `communication.*` | `communication.assistant`, `communication.message`, `communication.notifications` | `Sparkles`, `MessageSquare`, `Bell` |
| `ai.*` | `ai.automation`, `ai.explainability` | `Brain`, `Lightbulb` |
| `provenance.*` | `provenance.auditLog`, `provenance.link` | `History`, `Link2` |
| `connectors.*` | `connectors.cpuChip` | `Cpu` |

An unknown semantic key returns `null` and emits a `console.warn` in development mode.

---

### 7. Page Components

Source root: `apps/web/frontend/src/pages/`

All page components are lazy-loaded by `App.tsx` through `React.lazy` / `Suspense`.

| Component | Route(s) | Summary |
|---|---|---|
| `LoginPage` | `/login` | OIDC login launcher; calls `GET /session` pre-check |
| `HomePage` | `/` | Entry view with KPI summary cards, demo project launchers, and onboarding tour trigger |
| `WorkspacePage` | `/portfolio/:id`, `/program/:id`, `/project/:id` (and `/portfolios/:id`, `/programs/:id`, `/projects/:id` variants) | Unified entity workspace: loads pipeline board, KPI widgets, and drag-and-drop pipeline item management. `type` prop selects `portfolio`, `program`, or `project` context. |
| `IntakeFormPage` | `/intake/new` | Multi-step intake form. Steps: Concept → Details → Attachments → Submit. Optional `multimodal_intake` flag enables upload and extract endpoints. |
| `IntakeStatusPage` | `/intake/status/:requestId` | Polls intake status; shows approval state and "Open project workspace" CTA once `approved`. |
| `IntakeApprovalsPage` | `/intake/approvals` | Queue of pending intake decisions. |
| `MergeReviewPage` | `/intake/merge-review` | Feature-flagged (`duplicate_resolution`). Displays conflicting intake requests for de-duplication. |
| `ApprovalsPage` | `/approvals` | General approval queue. Supports approve/reject decisions. |
| `AnalyticsDashboard` | `/analytics/dashboard` | Trend charts, predictive alert badges (flag: `predictive_alerts`), KPI table. What-if controls and export pack are not yet wired to the API (see [Known Gaps](#known-gaps) #4). |
| `ConnectorMarketplacePage` | `/marketplace/connectors` | Paginated connector registry with category filter, enable/disable toggle, and test action. |
| `ConfigPage` | `/ops/config/agents`, `/ops/config/connectors`, `/ops/config/workflows` | Hub-level configuration tabs for agents, connectors, and workflow routing rules. |
| `PromptManager` | `/ops/config/prompts` | CRUD list of prompt templates used by agent invocations. |
| `ProjectConfigPage` | `/projects/:id/config`, `/projects/:id/ops/config/:tab` | Project-scoped agents and connectors configuration. |
| `WorkflowMonitoringPage` | `/workflows/monitoring` | Live workflow run list. |
| `WorkflowDesigner` | `/workflows/designer` | Visual workflow authoring canvas. |
| `AuditLogPage` | `/admin/audit` | Paginated audit event log. Requires `audit.view` permission. |
| `AgentRunsPage` | `/admin/agent-runs` | Feature-flagged (`agent_run_ui`). Lists agent execution records with duration and output artifact links. |
| `MethodologyEditor` | `/admin/methodology` | Admin-only methodology stage/activity editor. |
| `RoleManager` | `/admin/roles`, `/admin/roles/assignments` | CRUD for roles and user-role assignments. Requires `roles.manage` permission. |
| `NotificationCenterPage` | `/notifications` | Feature-flagged (`agent_async_notifications`). Real-time notification inbox. |
| `DocumentSearchPage` | `/knowledge/documents` | Full-text search over AI-indexed project documents. |
| `LessonsLearnedPage` | `/knowledge/lessons` | Lessons learned repository with filter/tag controls. |
| `GlobalSearch` | `/search` | Cross-entity search (projects, documents, agents). |
| `DemoRunPage` | `/demo-run` | Sequential 25-agent demo run ledger. |

---

### 8. Routing and Auth Guards

Source root: `apps/web/frontend/src/routing/`

| Guard | Behaviour |
|---|---|
| `RequireAuth` | Redirects unauthenticated users to `/login`. Preserves `return_to` query parameter so users land on their intended page after login. |
| `RequireTenantContext` | Checks that the session has a resolved tenant context. Renders a fallback spinner while the session is being hydrated. |
| `RequireAdminRole` | Restricts access to admin-only pages (`AuditLogPage`, `AgentRunsPage`, `MethodologyEditor`, `RoleManager`). Returns a `403 Forbidden` inline notice if the user lacks the required permission. |
| `EntityCollectionRedirect` | Handles bare collection routes (`/portfolios`, `/programs`, `/projects`). Redirects to the currently selected entity or a hardcoded `demo` fallback. This is a **known gap** (see [Known Gaps](#known-gaps) #1): a dedicated list/search page should replace this redirect. |

---

### 9. Streamlit Demo Panels

Source: `apps/demo_streamlit/app.py`

The Streamlit demo is a self-contained local mirror of the web console for offline and sales demos. It requires no backend services and makes no external calls. All writes go to `apps/demo_streamlit/storage/demo_outbox.json`.

#### Architecture

| Class / Function | Role |
|---|---|
| `DemoDataHub` | Central data access layer. Loads JSON fixtures on first access (cached); exposes `normalized_*` methods that merge and shape fixture data into display-ready rows. |
| `DemoOutbox` | Append-only JSON store for all write events emitted during the demo session (assistant actions, agent runs, audit events, artifact generation). |
| `DemoRunEngine` | Stateless step-sequencer for the 25-agent demo run playback. `progress(step)` slices completed vs queued agents; `play_step(step)` emits run and audit events to the outbox. |

#### Panel functions

| Function | Streamlit page | Description |
|---|---|---|
| `render_home(hub)` | Home | Portfolio KPI counts, parity status table vs web console. |
| `render_workspace(hub)` | Workspace | Project selector, methodology navigator table, stage/activity filter, activity detail, walkthrough completion tracker. |
| `render_dashboard(hub)` | Dashboard | KPI records metric, workflow run count, KPI and run tables; predictive alerts section when flag is enabled. |
| `render_approvals(hub)` | Approvals | Flat approval list from seed and approvals fixtures. |
| `render_approvals_advanced(hub)` | Approvals (advanced) | Approval type filter, decision detail pane with audit deep-link. |
| `render_artifact_lifecycle(hub)` | Artifact Lifecycle | Full artifact board with status filter; highlights artifacts blocking publish. |
| `render_intake(hub)` | Intake | Intake request list, JSON detail pane, "Open project workspace" button for approved requests. |
| `render_collections(hub)` | Collections | Segmented control for portfolio/program/project; search by id/name/status/owner. |
| `render_agent_gallery(hub, outbox)` | Agent Gallery | Metric count, filter, agent profile JSON, "Test agent" and "Run agent" actions. |
| `render_analytics_advanced(hub, outbox)` | Analytics What-If | KPI table, budget/scope delta sliders, "Run what-if scenario", "Export dashboard pack" download. |
| `render_connectors(hub)` | Connector Registry | Registered connector count, dataframe, connector detail JSON. |
| `render_audit(hub, outbox)` | Audit | Seed audit log merged with outbox `audit_events`. |
| `render_notifications(hub)` | Notifications | Seed and storage notification rows (visible when `agent_async_notifications` flag is enabled). |
| `render_demo_run(hub, engine, outbox)` | Demo Run | Run ID, progress bar, step playback controls, agent execution table, methodology walkthrough coverage, outbox event counts. |
| `render_agent_runs(hub, engine)` | Agent Runs | Completed/queued agent run counts and last-10 completed rows (visible when `agent_run_ui` flag is enabled). |

#### Shared sidebar panels

| Function | Description |
|---|---|
| `render_scenario_selectors_sidebar(hub)` | Selectboxes for Methodology, Stage, and Activity that drive the global context bar. |
| `render_feature_flags_panel()` | Checkboxes for each feature flag; changes are written back to `st.session_state['feature_flags']`. |
| `render_global_context_bar()` | Caption bar at page top showing current Project / Methodology / Stage / Activity / Outcome. |
| `render_provenance(hub, view_name)` | Data provenance table showing which JSON fixtures backed the current view. |

#### Data sources

All fixture paths are relative to the repo root:

| Key | File |
|---|---|
| `projects` | `apps/web/data/projects.json` |
| `demo_seed` | `apps/web/data/demo_seed.json` |
| `demo_run_log` | `apps/web/data/demo/demo_run_log.json` |
| `portfolio_health` | `examples/demo-scenarios/portfolio-health.json` |
| `lifecycle_metrics` | `examples/demo-scenarios/lifecycle-metrics.json` |
| `workflow_monitoring` | `examples/demo-scenarios/workflow-monitoring.json` |
| `approvals` | `examples/demo-scenarios/approvals.json` |
| `assistant_responses` | `examples/demo-scenarios/assistant-responses.json` |
| `feature_flags` | `apps/demo_streamlit/data/feature_flags_demo.json` |
| `storage_notifications` | `apps/web/storage/notifications.json` |
| `storage_scenarios` | `apps/web/storage/scenarios.json` |
| `dashboard_approvals` | `apps/web/data/demo_dashboards/approvals.json` |
| `dashboard_portfolio_health` | `apps/web/data/demo_dashboards/portfolio-health.json` |
| `dashboard_lifecycle` | `apps/web/data/demo_dashboards/lifecycle-metrics.json` |
| `dashboard_workflow` | `apps/web/data/demo_dashboards/workflow-monitoring.json` |
| `dashboard_executive` | `apps/web/data/demo_dashboards/executive_portfolio.json` |

Agent capability metadata is parsed from `agents/AGENT_CATALOG.md`. Connector metadata is parsed from `connectors/*/manifest.yaml`.

#### Outbox event types

| Bucket | Event type | Emitted by |
|---|---|---|
| `assistant_actions` | `activity.completed` | Complete activity chip |
| `assistant_actions` | `artifact.generated` | Generate artifact chip |
| `assistant_actions` | `assistant.agent_invocation` | Generate button |
| `assistant_actions` | `assistant.agent_invocation.bulk` | Run all 25 agents button |
| `assistant_actions` | `analytics.what_if` | Run what-if scenario button |
| `assistant_actions` | `analytics.export_pack` | Export dashboard pack button |
| `assistant_actions` | `agent.tested` | Test agent button |
| `assistant_actions` | `agent.run` | Run agent button |
| `demo_run_events` | _(run payload)_ | Demo Run play-step |
| `audit_events` | `demo.agent.executed` | Demo Run play-step |
| `audit_events` | `agent.run` | Run agent button |

---

## Connectors and System-of-Record Data Flow

> Last reviewed: 2026-03-07

The platform includes 40 integration connectors for external systems of record. Connectors enable a bidirectional data lifecycle: data is pulled from a system of record into the platform's canonical data model, surfaced in the canvas workspace where users and agents can view and modify it, and -- when ready -- written back to the system of record in the correct structure that mirrors that system's data configuration.

### How Data Flows Between Systems of Record and the Canvas

#### Inbound: System of Record --> Canonical Model --> Canvas

1. **Sync from source.** The Data Sync Service (`services/data-sync-service/`) runs scheduled or on-demand sync jobs for each configured connector. Each job (e.g. Jira tasks, Clarity projects, SAP financials) fetches records from the external system using the connector's REST API or MCP tool interface. Sync strategies include `source_of_truth` (external system always wins), `last_write_wins` (most recent timestamp wins), and `manual_required` (conflict queued for human resolution).

2. **Map to canonical schema.** The Data Synchronisation Agent (`agents/operations-management/data-synchronisation-agent/`) transforms inbound payloads using configurable field mappings defined in `mapping_rules.yaml` -- for example, Jira's `summary` maps to the canonical `task.title`, SAP's `ProjectID` maps to `project.id`. Validation rules (`validation_rules.yaml`) enforce data-quality thresholds before records enter the canonical store. Every transformation is recorded as a lineage event (source system, object type, record ID, field-level mappings), enabling full provenance tracking via `data/lineage/`.

3. **Surface in the canvas.** Canonical records materialise as canvas artifacts within project workspaces. The canvas engine (`packages/canvas-engine/`) supports 13 artifact types -- Document, Structured Tree (WBS), Timeline, Gantt, Board, Backlog, Grid, Spreadsheet, Financial, Dashboard, Dependency Map, Roadmap, and Approval -- each rendered in a purpose-built editor component. For example, Jira issues appear as cards on a Board canvas; Clarity WBS elements populate a Structured Tree canvas; SAP budget line items fill a Financial canvas. Artifacts carry provenance metadata (`sourceAgent`, `generatedAt`, `correlationId`) so users always know where the data originated.

#### Editing: Users and Agents Modify Canvas Artifacts

4. **Human edits.** Users edit artifacts directly in the canvas -- dragging cards between columns on a Board, adding nodes to a WBS tree, updating budget forecasts in a Financial canvas, or authoring documents in the rich-text Document canvas. Changes are tracked with version numbers, dirty-tab indicators, and edit history entries recording who changed what and when.

5. **Agent edits.** The platform's 25 specialised agents can also create and modify canvas artifacts. The Scope Definition Agent generates project charters as Document artifacts; the Schedule Planning Agent builds Gantt artifacts; the Risk Management Agent populates Grid artifacts with identified risks. Each agent-authored change is tagged with provenance metadata so that agent contributions are distinguishable from human edits. Artifacts move through a `draft` --> `published` lifecycle, with the Approval canvas type supporting formal approval workflows with evidence and decision history.

6. **Create from scratch.** Users and agents can also create new artifacts from scratch in any canvas type, using the `createArtifact` / `createEmptyContent` helpers in `packages/canvas-engine/src/types/artifact.ts`. For example, a user can create a new Financial canvas, enter budget line items manually, and later push those records to SAP -- the outbound sync pipeline handles the reverse field mapping to produce the SAP-native payload structure (e.g. `project.id` --> `ProjectID`, `project.name` --> `Description`, `project.status` --> `LifecycleStatus`).

#### Outbound: Canvas --> Canonical Model --> System of Record

7. **Save and publish.** When a user saves or publishes an artifact, the canvas store (`apps/web/frontend/src/store/useCanvasStore.ts`) persists the content to the platform's document repository (via the Knowledge Management API) with version tracking, edit history, and provenance metadata.

8. **Governed write-back.** All writes to external systems pass through the `ConnectorWriteGate` (`agents/common/connector_integration.py`), which enforces four controls before any data leaves the platform:
   - **Connector readiness** -- the connector must be configured and connected (status `connected` or `permissions_validated`)
   - **Approval** -- if organisational policy requires approval for the write, a valid approval must be present
   - **Dry-run** -- when configured, a dry run must succeed before the live write executes
   - **Idempotency and audit** -- every write attempt (pass or fail) generates an idempotency key and an audit log entry

   The Data Synchronisation Agent calls `governed_connector_write()` to push canonical records through the appropriate connector. The connector applies reverse field mappings to convert canonical schema fields to the target system's native field names and structure. Each connector exposes an outbound sync endpoint (e.g. `POST /connectors/sap/sync/outbound`, `POST /connectors/clarity/sync/outbound`) that accepts the mapped payload and writes to the external API.

9. **Conflict resolution.** When bidirectional sync detects that both the canonical store and the external system have changed the same record, the platform handles conflicts according to the configured strategy. For `manual_required` conflicts, the record appears in the Conflict Resolution Queue on the Connector Health Dashboard, where administrators compare source and canonical values side by side and choose which to keep. The sync registry also tracks write-back candidates -- records where the internal version is newer -- and offers them for outbound push.

### Connector Categories

| Category | Example Systems |
|----------|-----------------|
| PPM Tools | Clarity, Planview |
| PM Tools | Jira, Azure DevOps, Asana, Monday.com, SmartSheet |
| Document Management | SharePoint, Confluence, Google Drive |
| ERP | SAP, Oracle, NetSuite |
| HRIS | Workday, SAP SuccessFactors, ADP |
| Collaboration | Slack, Microsoft Teams, Zoom, Outlook, Google Calendar |
| CRM / Service Management | Salesforce, ServiceNow |
| GRC | Archer, LogicGate |

### MCP (Model Context Protocol) Connectors

MCP-enabled connectors are available for Jira, Asana, Clarity, Planview, SAP, Slack, Teams, and Workday. These provide structured tool-use interfaces that agents call directly, replacing REST polling with on-demand, scoped operations. Each MCP connector maps platform operations (e.g. `projects.read`, `resources.write`) to named MCP tools published by a managed MCP server. In the Project MCP Sidebar, administrators browse the available tool catalog, bind operations to tools, and save per-project MCP mappings.

### Configuration and Monitoring

The **Connector Gallery** (web and mobile) lets administrators browse connectors by category, search and filter by status or certification, enable/disable with one click, and open a configuration modal to set connection details, choose REST or MCP transport, map MCP tools, set sync direction and frequency, and test the connection. Each connector also has a **Certification Evidence** modal for tracking compliance status, audit references, and uploaded evidence documents.

The **Connector Health Dashboard** provides real-time operational visibility with three panels: connector status (health, error rates, circuit breaker state), data freshness (last sync time and staleness per entity), and the conflict resolution queue.

The **Sync Status Panel** embedded in both hub and project galleries shows per-connector sync run history -- total runs, success rate, errors, and last sync timestamp.

### Connector SDK

The connector SDK (`connectors/sdk/`) provides the `BaseConnector` abstract class with lifecycle hooks for authentication, connection testing, and data operations, plus resilience middleware (circuit breakers, retry policies, timeouts), telemetry, and JSON schema validation. The registry (`connectors/registry/connectors.json`) is the canonical manifest for all connector definitions and field mappings.

---

## Coverage Matrix

> Last reviewed: 2026-02-15

This matrix audits the current SPA and backend implementation against the required capability list. Legacy workspace entrypoints (`/workspace`, `/v1/workspace`) are retired; this inventory tracks SPA routes only.

### Route inventory (react-router)

Source: `apps/web/frontend/src/App.tsx`

| Route | Component | Guarding / Notes |
|---|---|---|
| `/login` | `LoginPage` | Public route |
| `/` | `HomePage` | `RequireAuth` + `RequireTenantContext` |
| `/portfolio/:portfolioId`, `/portfolios/:portfolioId` | `WorkspacePage type=portfolio` | Portfolio workspace |
| `/portfolios` | `EntityCollectionRedirect` | Redirects to current selection or `/portfolio/demo` |
| `/program/:programId`, `/programs/:programId` | `WorkspacePage type=program` | Program workspace |
| `/programs` | `EntityCollectionRedirect` | Redirects to current selection or `/program/demo` |
| `/project/:projectId`, `/projects/:projectId` | `WorkspacePage type=project` | Project workspace |
| `/projects` | `EntityCollectionRedirect` | Redirects to current selection or `/project/demo` |
| `/projects/:projectId/config`, `/projects/:projectId/ops/config/:tab` | `ProjectConfigPage` | Project-scoped agents/connectors |
| `/ops/config/agents`, `/ops/config/connectors`, `/ops/config/workflows` | `ConfigPage` | Global config |
| `/ops/config/prompts` | `PromptManager` | Prompt management |
| `/approvals` | `ApprovalsPage` | Approval processing |
| `/workflows/monitoring` | `WorkflowMonitoringPage` | Workflow runs |
| `/workflows/designer` | `WorkflowDesigner` | Workflow authoring |
| `/marketplace/connectors` | `ConnectorMarketplacePage` | Connector registry view |
| `/intake/new` | `IntakeFormPage` | New intake / project initiation |
| `/intake/status/:requestId` | `IntakeStatusPage` | Intake status |
| `/intake/approvals` | `IntakeApprovalsPage` | Intake approval queue |
| `/intake/merge-review` | `MergeReviewPage` | `featureFlags.duplicate_resolution` |
| `/notifications` | `NotificationCenterPage` | `featureFlags.agent_async_notifications` |
| `/knowledge/documents` | `DocumentSearchPage` | Knowledge docs |
| `/knowledge/lessons` | `LessonsLearnedPage` | Lessons learned |
| `/search` | `GlobalSearch` | Global search |
| `/admin/audit` | `AuditLogPage` | `RequireAdminRole` |
| `/admin/agent-runs` | `AgentRunsPage` | `RequireAdminRole` + `featureFlags.agent_run_ui` in nav |
| `/admin/methodology` | `MethodologyEditor` | `RequireAdminRole` |
| `/admin/roles` | `RoleManager` | `RequireAdminRole` |
| `/analytics/dashboard` | `AnalyticsDashboard` | Permission-gated in-page |
| `/demo-run` | `DemoRunPage` | Demo run ledger |

### Capability matrix

| # | Capability | Build status | Demo-safe |
|---|---|---|---|
| 1 | Initial login + session establishment | Implemented | Implemented |
| 2 | Entry view after login with assistant-first launcher | Implemented (partial wording) | Implemented |
| 3 | Create new project (all steps and post-create routing) | Partial — intake-to-workspace routing incomplete | Implemented for intake flow; post-approval routing partial |
| 4 | Access existing portfolio workspace (list/search + open) | Partial — no dedicated list/search page | Implemented for seeded IDs; collection browsing partial |
| 5 | Access existing program workspace (list/search + open) | Partial — no dedicated list/search page | Implemented for seeded IDs; list/search gap present |
| 6 | Access existing project workspace (list/search + open) | Partial — route open works; collection list/search not implemented | Implemented for seeded demo projects |
| 7 | Complete route coverage after create/collection flows | Partial — route map comprehensive but create and list/search gaps remain | Mostly implemented; broad seed data backing |
| 8 | Agent gallery (list, filter, profile, config, test, run) | Partial — list/filter/config exist; profile page and explicit test/run missing | Implemented partial with fallback/mock data |
| 9 | Connector registry (list/category/ops/config/test/enable/certification) | Implemented | Implemented |
| 10 | Methodology navigation (map/detail/monitoring/dashboard) | Implemented (read-only fallback when backend unreachable) | Implemented |
| 11 | Configure user access (roles/permissions + UI RBAC) | Implemented | Implemented |
| 12 | Performance dashboard (filter/drill-down/what-if/export) | Partial — what-if and export pack controls not wired | Partial — same what-if/export gap |
| 13 | Generate artefacts (document/spreadsheet/timeline; edit/review/approve/publish) | Partial — lifecycle dispatch works; publish evidence chain incomplete | Partial |
| 14 | Read/push records to Systems of Record | Implemented (integration surface) | Implemented via demo connector clients and outbox |
| 15 | Approval flows (stage gates/template/publish + audit evidence) | Partial — queues and decisions exist; specialized template/publish views missing | Implemented partial |

### Feature-flagged UI surfaces

| Flag | Surfaces enabled |
|---|---|
| `duplicate_resolution` | `/intake/merge-review` |
| `agent_async_notifications` | `/notifications` route and nav entry |
| `agent_run_ui` | Agent Runs nav visibility |
| `predictive_alerts` | Analytics predictive alerts surface |
| `multi_agent_collab` | Shared insights panel in workspace |
| `multimodal_intake` | Intake upload/extract endpoints |

### Demo readiness summary

- Demo mode seeds workspace and demo UI data at startup.
- Demo fixture tests enforce minimum visible record counts and required navigation backing data.
- Connector and SoR interactions are demo-safe via demo clients and mock connector mappings when `DEMO_MODE=true`.
- All demo write operations (documents, entities, connectors) emit audit events to the demo outbox so publish paths remain observable without external side effects.
- RBAC permission fallback defaults to empty (deny) rather than all-permissions to prevent accidental privilege escalation.

---

## Known Gaps

> Last reviewed: 2026-02-15

This backlog is ordered by impact on the required capabilities and implementation effort.

### Gap 1 — Add dedicated portfolio/program/project collection list and search pages

**Capabilities affected:** 4, 5, 6, 7

**Current gap:** `/portfolios`, `/programs`, `/projects` only redirect to current selection or a hard-coded fallback instead of rendering searchable collections.

**Affected files:**
- `apps/web/frontend/src/App.tsx` (`EntityCollectionRedirect` routes)
- `apps/web/frontend/src/components/layout/LeftPanel.tsx` (nav currently points to redirect routes)
- `apps/web/src/main.py` (add collection list/search endpoints if not already available)

**Acceptance criteria:**
1. Visiting `/portfolios`, `/programs`, `/projects` renders list/search tables.
2. Search supports name/id/status filters and opens the selected workspace route.
3. Works in actual build and demo mode with seeded records.

---

### Gap 2 — Complete "create new project" end-to-end routing after approvals

**Capabilities affected:** 3, 7, 15

**Current gap:** Intake creation routes to the status page, but the SPA does not automatically route to a newly created project workspace when approval is complete.

**Affected files:**
- `apps/web/frontend/src/pages/IntakeFormPage.tsx`
- `apps/web/frontend/src/pages/IntakeStatusPage.tsx`
- `apps/web/frontend/src/pages/IntakeApprovalsPage.tsx`
- `apps/web/src/main.py` (ensure created project identifier is exposed in intake decision/status payload)

**Acceptance criteria:**
1. Approved intake shows target `project_id` in status payload.
2. UI provides "Open project workspace" action that routes to `/projects/:projectId`.
3. Demo seeded approvals can traverse this full path.

---

### Gap 3 — Add full agent profile/test/run experience from Agent Gallery

**Capabilities affected:** 8

**Current gap:** Agent listing/filter/config exists, but there is no dedicated profile route and no explicit test-run flow from agent cards.

**Affected files:**
- `apps/web/frontend/src/components/agentConfig/AgentGallery.tsx`
- `apps/web/frontend/src/components/project/AgentGallery.tsx`
- `apps/web/frontend/src/pages/ProjectConfigPage.tsx`
- `apps/web/src/main.py` (add/confirm agent profile and test-run endpoints as needed)

**Acceptance criteria:**
1. Agent card can open a profile page (or panel) with capabilities and configuration history.
2. "Test agent" executes a backend test endpoint and displays result artifacts.
3. "Run agent" creates a run record visible in Agent Runs and audit trail.

---

### Gap 4 — Wire analytics what-if and export pack controls into SPA

**Capabilities affected:** 12

**Current gap:** Analytics page loads trends and predictive alerts but does not invoke dashboard what-if/export APIs from the UI.

**Affected files:**
- `apps/web/frontend/src/pages/AnalyticsDashboard.tsx`
- `apps/web/src/main.py` (dashboard what-if/export endpoints)

**Acceptance criteria:**
1. Dashboard includes what-if input controls and calls `POST /v1/api/dashboard/{project_id}/what-if`.
2. Dashboard includes export pack trigger/download (or an explicit unsupported state).
3. Demo mode returns safe simulated what-if/export data.

---

### Gap 5 — Strengthen artefact lifecycle UX for review/approve/publish evidence

**Capabilities affected:** 13, 15

**Current gap:** Lifecycle actions are dispatched from methodology runtime, but the UI lacks a consolidated artefact lifecycle board showing review/approval/publish status per artefact type.

**Affected files:**
- `apps/web/frontend/src/components/methodology/MethodologyWorkspaceSurface.tsx`
- `apps/web/frontend/src/pages/ApprovalsPage.tsx`
- `apps/web/frontend/src/pages/AuditLogPage.tsx`
- `apps/web/src/main.py` (runtime action/audit payload fields)

**Acceptance criteria:**
1. Artefact records display lifecycle status (`generated`, `in_review`, `approved`, `published`).
2. Each status transition links to audit evidence/event ID.
3. Publish action is disabled until required approvals are complete.

---

### Gap 6 — Add explicit template-approval and publish-approval views

**Capabilities affected:** 15

**Current gap:** A generic approvals list exists, but stage-gate/template/publish approvals are not split into dedicated queues or views.

**Affected files:**
- `apps/web/frontend/src/pages/ApprovalsPage.tsx`
- `apps/web/frontend/src/components/layout/LeftPanel.tsx`
- `apps/web/src/main.py` (approval type metadata enrichment)

**Acceptance criteria:**
1. Approval list can filter by approval type (`stage_gate`, `template`, `publish`).
2. Distinct detail pane fields are shown per type.
3. Audit log deep-links are present for each decision.

---

### Gap 7 — Close demo parity gaps for workspace collections and post-intake project creation

**Capabilities affected:** 3, 4, 5, 6, 7

**Current gap:** Demo data is broad, but UX parity for collection list/search and intake-to-project routing remains incomplete.

**Affected files:**
- `apps/web/data/demo_seed.json`
- `apps/web/src/demo_seed.py`
- `tests/demo/test_ui_data_completeness.py`

**Acceptance criteria:**
1. Demo seed includes portfolio/program/project collection metadata required by new list/search pages.
2. Demo seed includes intake records that resolve to concrete project IDs after approval.
3. Demo tests assert these routes and data links are present.
