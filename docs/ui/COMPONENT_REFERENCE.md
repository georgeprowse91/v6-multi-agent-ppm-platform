# UI Component Reference

> Last reviewed: 2026-02-23

This reference documents every UI component in the platform: the React SPA (`apps/web/frontend`) and the Streamlit standalone demo (`apps/demo_streamlit`). It is intended for developers extending either surface, QA engineers verifying component behaviour, and product stakeholders reading capability coverage.

Related docs:
- [UI Coverage Matrix](./UI_COVERAGE_MATRIX.md) — route/capability mapping
- [UI Gaps Backlog](./UI_GAPS.md) — ordered list of remaining gaps

---

## Table of Contents

1. [SPA Shell Components](#1-spa-shell-components)
2. [Assistant Panel Components](#2-assistant-panel-components)
3. [Methodology Components](#3-methodology-components)
4. [Dashboard / Analytics Components](#4-dashboard--analytics-components)
5. [Primitive / Shared UI Components](#5-primitive--shared-ui-components)
6. [Icon System](#6-icon-system)
7. [Page Components](#7-page-components)
8. [Routing & Auth Guards](#8-routing--auth-guards)
9. [Streamlit Demo Panels](#9-streamlit-demo-panels)

---

## 1. SPA Shell Components

Source root: `apps/web/frontend/src/components/layout/`

### `AppLayout`

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

### `Header`

**File:** `Header.tsx`

Top application bar. Displays the platform wordmark, global search trigger, user avatar, and notification badge. Reads auth session from the app store.

---

### `LeftPanel`

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

### `MainCanvas`

**File:** `MainCanvas.tsx`

Scrollable content region that hosts the active page component. Provides an `id="main-content"` skip-link target and applies `role="main"`.

---

## 2. Assistant Panel Components

Source root: `apps/web/frontend/src/components/assistant/`

### `AssistantPanel`

**File:** `AssistantPanel.tsx`

The persistent right-hand conversational assistant. It is always rendered by `AppLayout` and collapses to an icon-only rail when `rightPanelCollapsed` is true.

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

**LLM model selection:**

Fetches `GET /v1/api/llm/models` to populate a provider/model `<select>`. Users with `config.manage` or `llm.manage` permission can save a project-scoped default via `POST /v1/api/llm/preferences`.

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

### `AssistantHeader`

**File:** `AssistantHeader.tsx`

Title row for the assistant panel. Displays the panel title, an AI state badge (`idle` / `thinking` / `streaming`), and the collapse toggle button.

---

### `ContextBar`

**File:** `ContextBar.tsx`

Collapsible context breadcrumb rendered immediately below `AssistantHeader`. Shows `stage > activity` breadcrumb, a sync-pulse chip that animates for 900 ms on each context change, and a stage-progress percentage badge.

Expanded view reveals: Project name, Methodology name, Stage progress %, Activity lock state.

**Props:**
| Prop | Type | Description |
|---|---|---|
| `context` | `AssistantContext` | Current workspace context snapshot |
| `contextSyncLabel?` | `string` | Triggers a pulse animation when this string value changes |

---

### `MessageList`

**File:** `MessageList.tsx`

Scrollable transcript. Renders each message as a bubble (user, assistant, or system). Assistant messages may include inline `ActionChip` buttons. Shows a typing indicator when `typingStatus` is active. Supports `aiState` to display a loading skeleton when streaming.

---

### `QuickActions`

**File:** `QuickActions.tsx`

Horizontal chip rail rendered below `MessageList`. Each chip maps to an `ActionChip` from the assistant store. Chips can be enabled or disabled; disabled chips render visually muted and block the `handleChipClick` handler.

---

### `ChatInput`

**File:** `ChatInput.tsx`

Textarea-based message input. Features:
- Auto-resize on content growth
- Submit on `Enter` (Shift+Enter inserts newline)
- `/research` scope button as a secondary CTA
- Displays `error` string from `useAssistantChat` when the backend returns an error

---

## 3. Methodology Components

Source root: `apps/web/frontend/src/components/methodology/`

### `MethodologyWorkspaceSurface`

**File:** `MethodologyWorkspaceSurface.tsx`

The main content area when a project workspace is active. Composes the methodology map (stage/activity navigation) with the activity detail panel.

**Canvas type mapping** (`canvasMap`):

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

### `MethodologyNav`

**File:** `MethodologyNav.tsx`

Tree-structured stage/activity navigator rendered inside `LeftPanel` when in `project-workspace` mode. Stages can be expanded/collapsed. Selecting an activity calls `setCurrentActivity` on the methodology store.

**Props:**
| Prop | Type | Description |
|---|---|---|
| `collapsed` | `boolean` | When true (panel is icon-only), renders icon-only stage nodes |

---

### `MethodologyMapCanvas`

**File:** `MethodologyMapCanvas.tsx`

Full-canvas stage/activity grid rendered in the main workspace area. Each stage is a column; each activity is a card. Cards display status indicators (not started / in progress / complete / locked). Clicking a card sets it as the current activity.

---

### `ActivityDetailPanel`

**File:** `ActivityDetailPanel.tsx`

Detail pane shown alongside `MethodologyMapCanvas` when an activity is selected. Displays:
- Activity name, stage label, status
- Description text
- Missing prerequisite names (when locked)
- Lock indicator
- Lifecycle action buttons (filtered to `runtimeActionsAvailable`)
- Approvals inbox (`reviewQueue`) with accept/reject/modify decision controls

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

## 4. Dashboard / Analytics Components

Source root: `apps/web/frontend/src/components/dashboard/`

### `KpiWidget`

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

### `StatusIndicator`

**File:** `StatusIndicator.tsx`

Inline status badge used on pipeline cards and activity rows. Maps a status string to a colour-coded dot + label.

---

## 5. Primitive / Shared UI Components

Source root: `apps/web/frontend/src/components/ui/`

### `EmptyState`

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

### `Skeleton`

**File:** `Skeleton.tsx`

Animated loading placeholder. Accepts `width`, `height`, and `borderRadius` style overrides. Used by `WorkspacePage` and `AnalyticsDashboard` while entity data is loading.

---

### `FadeIn`

**File:** `FadeIn.tsx`

Lightweight animation wrapper that applies a CSS keyframe fade from `opacity: 0` to `opacity: 1` on mount. Used by `EmptyState` and other components for perceived performance.

---

### `OnboardingTour`

Source: `apps/web/frontend/src/components/tours/`

Step-by-step guided tour driven by `TourProvider` context. Tour steps are keyed to `data-tour` attributes on target elements (set by `LeftPanel` and `AssistantPanel`). Tour state (started, current step, dismissed) is persisted in `localStorage`.

---

## 6. Icon System

Source root: `apps/web/frontend/src/components/icon/`

### `Icon`

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

## 7. Page Components

Source root: `apps/web/frontend/src/pages/`

All page components are lazy-loaded by `App.tsx` through `React.lazy` / `Suspense`.

| Component | Route(s) | Summary |
|---|---|---|
| `LoginPage` | `/login` | OIDC login launcher; calls `GET /session` pre-check |
| `HomePage` | `/` | Entry view with KPI summary cards, demo project launchers, and onboarding tour trigger |
| `WorkspacePage` | `/portfolio/:id`, `/program/:id`, `/project/:id` (and `/portfolios/:id`, `/programs/:id`, `/projects/:id` variants) | Unified entity workspace: loads pipeline board (`GET /api/pipeline/:type/:id`), KPI widgets (`KpiWidget`), and drag-and-drop pipeline item management. `type` prop selects `portfolio`, `program`, or `project` context. |
| `IntakeFormPage` | `/intake/new` | Multi-step intake form. Steps: Concept → Details → Attachments → Submit. Optional `multimodal_intake` flag enables `POST /v1/api/intake/uploads` and `POST /v1/api/intake/extract`. |
| `IntakeStatusPage` | `/intake/status/:requestId` | Polls `GET /v1/api/intake/:requestId`; shows approval status and "Open project workspace" CTA once `approved`. |
| `IntakeApprovalsPage` | `/intake/approvals` | Queue of pending intake decisions from `GET /v1/api/intake?status=pending`. |
| `MergeReviewPage` | `/intake/merge-review` | Feature-flagged (`duplicate_resolution`). Displays conflicting intake requests for de-duplication. |
| `ApprovalsPage` | `/approvals` | General approval queue from `GET /v1/workflows/approvals`. Supports approve/reject decisions. |
| `AnalyticsDashboard` | `/analytics/dashboard` | Trend charts, predictive alert badges (flag: `predictive_alerts`), KPI table. What-if controls and export pack button are not yet wired to the API (see UI Gaps #4). |
| `ConnectorMarketplacePage` | `/marketplace/connectors` | Paginated connector registry with category filter, enable/disable toggle, and test action. |
| `ConfigPage` | `/ops/config/agents`, `/ops/config/connectors`, `/ops/config/workflows` | Hub-level configuration tabs for agents, connectors, and workflow routing rules. |
| `PromptManager` | `/ops/config/prompts` | CRUD list of prompt templates used by agent invocations. |
| `ProjectConfigPage` | `/projects/:id/config`, `/projects/:id/ops/config/:tab` | Project-scoped agents and connectors configuration. |
| `WorkflowMonitoringPage` | `/workflows/monitoring` | Live workflow run list from `GET /v1/api/workflows/runs`. |
| `WorkflowDesigner` | `/workflows/designer` | Visual workflow authoring canvas. |
| `AuditLogPage` | `/admin/audit` | Paginated audit event log from `GET /v1/audit/events`. Requires `audit.view` permission. |
| `AgentRunsPage` | `/admin/agent-runs` | Feature-flagged (`agent_run_ui`). Lists agent execution records with duration and output artifact links. |
| `MethodologyEditor` | `/admin/methodology` | Admin-only methodology stage/activity editor. |
| `RoleManager` | `/admin/roles`, `/admin/roles/assignments` | CRUD for roles and user-role assignments. Requires `roles.manage` permission. |
| `NotificationCenterPage` | `/notifications` | Feature-flagged (`agent_async_notifications`). Real-time notification inbox. |
| `DocumentSearchPage` | `/knowledge/documents` | Full-text search over AI-indexed project documents. |
| `LessonsLearnedPage` | `/knowledge/lessons` | Lessons learned repository with filter/tag controls. |
| `GlobalSearch` | `/search` | Cross-entity search (projects, documents, agents). |
| `DemoRunPage` | `/demo-run` | Sequential 25-agent demo run ledger. |

---

## 8. Routing & Auth Guards

Source root: `apps/web/frontend/src/routing/`

### `RequireAuth`

Redirects unauthenticated users to `/login`. Reads session state from the app store (`session.user`). Preserves `return_to` query parameter so users land on their intended page after login.

### `RequireTenantContext`

Checks that the session has a resolved tenant context. Renders a fallback spinner while the session is being hydrated.

### `RequireAdminRole`

Restricts access to admin-only pages (`AuditLogPage`, `AgentRunsPage`, `MethodologyEditor`, `RoleManager`). Returns a `403 Forbidden` inline notice if the user lacks the required permission.

### `EntityCollectionRedirect`

Handles the bare collection routes (`/portfolios`, `/programs`, `/projects`). Redirects to the currently selected entity or a hardcoded `demo` fallback. This is a **known gap** (see UI Gaps #1): a dedicated list/search page should replace this redirect.

---

## 9. Streamlit Demo Panels

Source: `apps/demo_streamlit/app.py`

The Streamlit demo is a self-contained local mirror of the web console for offline and sales demos. It requires no backend services and makes no external calls. All writes go to `apps/demo_streamlit/storage/demo_outbox.json`.

### Architecture

| Class / Function | Role |
|---|---|
| `DemoDataHub` | Central data access layer. Loads JSON fixtures on first access (cached); exposes `normalized_*` methods that merge and shape fixture data into display-ready rows. |
| `DemoOutbox` | Append-only JSON store for all write events emitted during the demo session (assistant actions, agent runs, audit events, artifact generation). |
| `DemoRunEngine` | Stateless step-sequencer for the 25-agent demo run playback. `progress(step)` slices completed vs queued agents; `play_step(step)` emits run + audit events to the outbox. |

### Panel Functions

| Function | Streamlit page | Description |
|---|---|---|
| `render_home(hub)` | Home | Portfolio KPI counts, parity status table vs web console. |
| `render_workspace(hub)` | Workspace | Project selector, methodology navigator table, stage/activity filter, activity detail (description, artifacts, attributes), walkthrough completion tracker. |
| `render_dashboard(hub)` | Dashboard | KPI records metric, workflow run count, KPI and run tables; predictive alerts section when flag is enabled. |
| `render_approvals(hub)` | Approvals | Flat approval list from seed + approvals fixtures. |
| `render_approvals_advanced(hub)` | Approvals (advanced) | Approval type filter (`all` / `stage_gate` / `template` / `publish`), decision detail pane with audit deep-link. |
| `render_artifact_lifecycle(hub)` | Artifact Lifecycle | Full artifact board with status filter; highlights artifacts blocking publish (missing required approvals). |
| `render_intake(hub)` | Intake | Intake request list, JSON detail pane, "Open project workspace" button for approved requests. |
| `render_collections(hub)` | Collections | Segmented control for portfolio/program/project; search by id/name/status/owner; "Open workspace" action. |
| `render_agent_gallery(hub, outbox)` | Agent Gallery | Metric count, filter, agent profile JSON, "Test agent" (emits `agent.tested` event), "Run agent" (emits `agent.run` + audit event). |
| `render_analytics_advanced(hub, outbox)` | Analytics What-If | KPI table, budget/scope delta sliders, "Run what-if scenario" (composite score forecast), "Export dashboard pack" download. |
| `render_connectors(hub)` | Connector Registry | Registered connector count, dataframe, connector detail JSON. |
| `render_audit(hub, outbox)` | Audit | Seed audit log merged with outbox `audit_events`. |
| `render_notifications(hub)` | Notifications | Seed + storage notification rows (visible when `agent_async_notifications` flag is enabled). |
| `render_demo_run(hub, engine, outbox)` | Demo Run | Run ID, progress bar, step playback controls, agent execution table, methodology walkthrough coverage, outbox event counts. |
| `render_agent_runs(hub, engine)` | Agent Runs | Completed/queued agent run counts and last-10 completed rows (visible when `agent_run_ui` flag is enabled). |

### Shared Sidebar Panels

| Function | Description |
|---|---|
| `render_scenario_selectors_sidebar(hub)` | Selectboxes for Methodology, Stage, and Activity that drive the global context bar. |
| `render_feature_flags_panel()` | Checkboxes for each feature flag; changes are written back to `st.session_state['feature_flags']`. |
| `render_global_context_bar()` | Caption bar at page top showing current Project / Methodology / Stage / Activity / Outcome. |
| `render_provenance(hub, view_name)` | Data provenance table showing which JSON fixtures backed the current view. |

### Assistant Panel (Streamlit)

Implemented inline in `assistant_panel(hub, outbox)`:

| Control | Behaviour |
|---|---|
| Context columns | Shows selected project, stage, activity, outcome (2-column layout). |
| Action chips | Four quick-action buttons: Go to Dashboard, Open selected activity, Complete current activity, Generate status report. |
| Scenario outcome selector | `on_track` / `at_risk` / `off_track`; used by `choose_assistant_response` to select the matching response entry. |
| Demo scenario selector | Selectbox over conversation scenario files in `apps/web/data/demo_conversations/`. |
| Restart / Play next step | Replays or advances the scripted conversation. |
| Invoke agent selector | Selectbox over agent catalog; "Generate" sends a prompt and emits an invocation response. |
| "Run all 25 agents" | Appends invocation responses for all agents; emits `assistant.agent_invocation.bulk` to outbox. |
| Artifact download | Appears after `GENERATE_ARTIFACT` chip action; provides content as `.md`, `.csv`, or `.txt`. |
| Transcript | Renders all `assistant_messages` with role label and provenance source. |

### Data Sources

All fixture paths relative to repo root:

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

Agent capability metadata is parsed directly from `agents/AGENT_CATALOG.md`. Connector metadata is parsed from `connectors/*/manifest.yaml`.

### Outbox Event Types

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

## Appendix: Agent Catalog (25 agents)

Agents are registered in `agents/AGENT_CATALOG.md` and surfaced in the Agent Gallery and Streamlit demo.

| Agent ID | Name | Domain |
|---|---|---|
| `intent-router-agent` | Intent Router | Core Orchestration |
| `response-orchestration-agent` | Response Orchestration | Core Orchestration |
| `approval-workflow-agent` | Approval Workflow | Core Orchestration |
| `demand-intake-agent` | Demand Intake | Portfolio Management |
| `business-case-agent` | Business Case Investment | Portfolio Management |
| `portfolio-optimisation-agent` | Portfolio Strategy Optimisation | Portfolio Management |
| `program-management-agent` | Program Management | Portfolio Management |
| `scope-definition-agent` | Project Definition Scope | Delivery Management |
| `lifecycle-governance-agent` | Lifecycle Governance | Delivery Management |
| `schedule-planning-agent` | Schedule Planning | Delivery Management |
| `resource-management-agent` | Resource Capacity | Delivery Management |
| `financial-management-agent` | Financial Management | Delivery Management |
| `vendor-procurement-agent` | Vendor Procurement | Delivery Management |
| `quality-management-agent` | Quality Management | Delivery Management |
| `risk-management-agent` | Risk Issue Management | Delivery Management |
| `compliance-governance-agent` | Compliance Regulatory | Delivery Management |
| `change-control-agent` | Change Configuration | Operations Management |
| `release-deployment-agent` | Release Deployment | Operations Management |
| `knowledge-management-agent` | Knowledge Document Management | Operations Management |
| `continuous-improvement-agent` | Continuous Improvement Process Mining | Operations Management |
| `stakeholder-communications-agent` | Stakeholder Comms | Operations Management |
| `analytics-insights-agent` | Analytics Insights | Operations Management |
| `data-synchronisation-agent` | Data Synchronisation Quality | Operations Management |
| `workspace-setup-agent` | Workspace Setup | Core Orchestration |
| `system-health-agent` | System Health Monitoring | Operations Management |
