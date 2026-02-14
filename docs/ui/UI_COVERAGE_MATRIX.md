# UI Coverage Matrix

This matrix audits the current SPA + backend implementation against the required capability list.

## Route Inventory (react-router)

Source: `apps/web/frontend/src/App.tsx`.

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
| `/projects/:projectId/config`, `/projects/:projectId/config/:tab` | `ProjectConfigPage` | Project-scoped agents/connectors |
| `/config/agents`, `/config/connectors`, `/config/workflows` | `ConfigPage` | Global config |
| `/config/prompts` | `PromptManager` | Prompt management |
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

## Page/Component Inventory under `apps/web/frontend/src/pages`

`AgentRunsPage`, `AnalyticsDashboard`, `ApprovalsPage`, `AuditLogPage`, `ConfigPage`, `ConnectorMarketplacePage`, `DemoRunPage`, `DocumentSearchPage`, `GlobalSearch`, `HomePage`, `IntakeApprovalsPage`, `IntakeFormPage`, `IntakeStatusPage`, `LessonsLearnedPage`, `LoginPage`, `MergeReviewPage`, `MethodologyEditor`, `NotificationCenterPage`, `ProjectConfigPage`, `PromptManager`, `RoleManager`, `WorkflowDesigner`, `WorkflowMonitoringPage`, `WorkspacePage`.

---

## Capability Matrix

### Capability 1: Initial login + session establishment
- **Entry routes:** `/login`, then guarded app routes.
- **UI components:** `LoginPage`, `RequireAuth`, `RequireTenantContext`.
- **Backend endpoints used:**
  - `GET /session` (login page pre-check)
  - `GET /login?return_to=/` (start OIDC)
  - `GET /v1/session` (guard bootstrap)
  - `GET /v1/api/roles` (role catalog for permission derivation)
- **Feature-flagged:** No.
- **Actual build:** **Implemented**.
- **Demo-safe/demo-seeded:** **Implemented**. Demo mode uses same flow; seed data includes users in `apps/web/data/demo_seed.json` and startup seeding via `seed_demo_data(...)`.

### Capability 2: Entry view after login with assistant-first launcher
- **Entry routes:** `/`.
- **UI components:** `HomePage`, `OnboardingTour`, persistent `AssistantPanel` in `AppLayout`.
- **Backend endpoints used:**
  - `GET /v1/config` (loads feature flags)
  - `POST /api/assistant` and `POST /api/assistant/suggestions` from assistant panel/hooks
- **Feature-flagged:** Assistant is not flagged; specific assistant-related surfaces depend on feature flags from `/v1/config`.
- **Actual build:** **Implemented (partial wording)**: launcher has “Log new intake” and demo project launchers; assistant is always visible in layout.
- **Demo-safe/demo-seeded:** **Implemented** via demo conversation payloads and demo-aware assistant behavior.

### Capability 3: Create new project (all steps and post-create routing)
- **Entry routes:** `/intake/new`.
- **UI components:** `IntakeFormPage` multi-step intake, `IntakeStatusPage`.
- **Backend endpoints used:**
  - `POST /v1/api/intake/uploads` (feature-gated)
  - `POST /v1/api/intake/extract` (feature-gated)
  - `POST /v1/api/intake`
  - `GET /v1/api/intake/{request_id}`
- **Feature-flagged:** Upload/extract depend on `multimodal_intake`.
- **Actual build:** **Partial**. Intake creation is implemented and routes to `/intake/status/:requestId`; explicit “new project workspace auto-open” after approval is not wired in SPA.
- **Demo-safe/demo-seeded:** **Implemented for intake flow**; demo fixtures provide requests/approvals, but full end-to-end promotion to project workspace is partial.

### Capability 4: Access existing portfolio workspace (list/search + open)
- **Entry routes:** `/portfolios` (redirect), `/portfolio/:portfolioId`, `/portfolios/:portfolioId`.
- **UI components:** `LeftPanel` nav links, `WorkspacePage type=portfolio`.
- **Backend endpoints used:**
  - `GET /api/portfolios/{portfolioId}`
  - `GET /api/pipeline/portfolio/{portfolioId}`
  - `PATCH /api/pipeline/portfolio/{portfolioId}/items/{itemId}`
- **Feature-flagged:** Scenario cards depend on `scenario_modeling`; shared insights depend on `multi_agent_collab`.
- **Actual build:** **Partial**. Open works; list/search UX for portfolio collection is redirect-based and lacks dedicated list/search page.
- **Demo-safe/demo-seeded:** **Implemented** for opening seeded IDs; collection browsing remains partial in demo too.

### Capability 5: Access existing program workspace (list/search + open)
- **Entry routes:** `/programs` (redirect), `/program/:programId`, `/programs/:programId`.
- **UI components:** `LeftPanel` nav links, `WorkspacePage type=program`.
- **Backend endpoints used:**
  - `GET /api/programs/{programId}`
  - `GET /api/pipeline/program/{programId}`
  - `PATCH /api/pipeline/program/{programId}/items/{itemId}`
- **Feature-flagged:** Same as workspace feature flags above.
- **Actual build:** **Partial**. Open route works; no dedicated list/search page for programs.
- **Demo-safe/demo-seeded:** **Implemented** for seeded IDs with same partial list/search gap.

### Capability 6: Access existing project workspace (list/search + open)
- **Entry routes:** `/projects` (redirect), `/project/:projectId`, `/projects/:projectId`.
- **UI components:** `LeftPanel`, `HomePage` demo project buttons, `WorkspacePage type=project`.
- **Backend endpoints used:**
  - `GET /api/projects/{projectId}`
  - `GET /api/workspace/{projectId}` (methodology/workspace state hydration)
- **Feature-flagged:** Scenario/modeling and collaboration cards are flagged.
- **Actual build:** **Partial**. Route open works; list/search collection page not implemented.
- **Demo-safe/demo-seeded:** **Implemented** for seeded demo projects and workspace state.

### Capability 7: Each subsequent screen for each of those 4 options (complete route coverage)
- **Entry routes:** `Home -> intake/new`, `Home -> demo projects`, `LeftPanel -> config/work/insights/admin`, project workspace sub-nav links.
- **UI components:** `LeftPanel`, `AppLayout`, `MainCanvas`, page components listed above.
- **Backend endpoints used:** Mixed per page; see each capability row.
- **Feature-flagged:** `/intake/merge-review`, `/notifications`, scenario/predictive/admin-nav visibility flags.
- **Actual build:** **Partial**. Route map is comprehensive for implemented pages, but route-level coverage after “create new project” and “collection list/search pages” is incomplete.
- **Demo-safe/demo-seeded:** **Mostly implemented**; seeded data backs many screens (`approvals`, `connectors`, `audit_log`, `dashboards`, `notifications`, `demo_run_log`).

### Capability 8: Agent gallery (list, filter, open profile, capabilities, config, test, run)
- **Entry routes:** `/projects/:projectId/config` (agents tab), `/config/agents`.
- **UI components:**
  - Project scoped: `components/project/AgentGallery`
  - Global scoped: `components/agentConfig/AgentGallery`, `ConfigPage` agents tab
- **Backend endpoints used:**
  - `GET /api/projects/{projectId}/agents`
  - `GET /v1/agents/config`
  - `PATCH /v1/agents/config/{catalog_id}`
  - `GET /v1/projects/{projectId}/agents/config`
  - `PATCH /v1/projects/{projectId}/agents/config/{agent_id}`
- **Feature-flagged:** No hard flag on gallery routes.
- **Actual build:** **Partial**. List/filter/config and capability chips exist; dedicated profile page, explicit “test agent”, and explicit “run agent from gallery” are missing.
- **Demo-safe/demo-seeded:** **Implemented partial** with fallback/mock data and seeded registry.

### Capability 9: Connector registry (list/category/config/test/enable per project/certification)
- **Entry routes:** `/marketplace/connectors`, `/config/connectors`, `/projects/:projectId/config/connectors`.
- **UI components:** `ConnectorGallery`, `ProjectConnectorGallery`, connector config/certification modals, `ProjectMcpSidebar`.
- **Backend endpoints used:**
  - `GET /v1/connectors`, `GET /api/projects/{projectId}/connectors`
  - `GET /v1/connectors/categories`
  - `PUT /v1/connectors/{id}/config`, `PUT /api/projects/{projectId}/connectors/{id}/config`
  - `POST /v1/connectors/{id}/test`, `POST /api/projects/{projectId}/connectors/{id}/test`
  - `POST /v1/connectors/{id}/enable|disable`, project-scoped enable/disable variants
  - `GET /v1/certifications`, `PATCH /v1/certifications/{id}`, `POST /v1/certifications/{id}/documents`
  - `POST|PUT /api/projects/{projectId}/connectors/{system}/mcp`, `GET /v1/mcp/servers/{system}/tools`
- **Feature-flagged:** MCP behavior depends on backend MCP flags.
- **Actual build:** **Implemented**.
- **Demo-safe/demo-seeded:** **Implemented** using demo connector clients and demo-safe outbox in demo mode.

### Capability 10: Methodology navigation (left index/map/detail/monitoring/dashboard)
- **Entry routes:** Project workspace routes (`/project/:id`, `/projects/:id`) with project-workspace sidebar mode.
- **UI components:** `LeftPanel` methodology block, `MethodologyNav`, `MethodologyMapCanvas`, `ActivityDetailPanel`, `MethodologyWorkspaceSurface`.
- **Backend endpoints used:**
  - `GET /api/workspace/{project_id}`
  - `POST /api/workspace/{project_id}/select`
  - `GET /api/methodology/runtime/actions`
  - `GET /api/methodology/runtime/resolve`
  - `POST /api/methodology/runtime/action`
- **Feature-flagged:** Not hard-flagged at route level.
- **Actual build:** **Implemented** (with read-only fallback when backend unreachable).
- **Demo-safe/demo-seeded:** **Implemented** (demo seed initializes workspace/methodology stores).

### Capability 11: Configure user access (roles/permissions + UI RBAC enforcement)
- **Entry routes:** `/admin/roles`; indirect enforcement across nav/routes.
- **UI components:** `RoleManager`, `RouteGuards`, permission utilities in `auth/permissions`, permission-driven nav in `LeftPanel`.
- **Backend endpoints used:**
  - `GET|POST /v1/api/roles`
  - `PUT|DELETE /v1/api/roles/{role_id}`
  - `GET|POST /v1/api/roles/assignments`
  - `GET /v1/session` (role bootstrap)
- **Feature-flagged:** No.
- **Actual build:** **Implemented** for role CRUD/assign + route/nav gating.
- **Demo-safe/demo-seeded:** **Implemented** with seeded roles and assignments.

### Capability 12: Performance dashboard (open/filter/drill-down/what-if/export pack)
- **Entry routes:** `/analytics/dashboard`; workspace “View full dashboard” affordance.
- **UI components:** `AnalyticsDashboard`, workspace summary cards.
- **Backend endpoints used:**
  - Used by SPA: `GET /v1/api/analytics/trends`, `GET /v1/api/analytics/predictive-alerts`
  - Available backend but not wired to SPA page: `POST /v1/api/dashboard/{project_id}/what-if` and other dashboard endpoints
- **Feature-flagged:** `predictive_alerts` controls alert panel badges.
- **Actual build:** **Partial**. Open/filter and trend drill-down cards exist; explicit what-if execution and export pack controls are not wired in SPA.
- **Demo-safe/demo-seeded:** **Partial**. Demo dashboard payloads exist; same what-if/export gap remains.

### Capability 13: Generate files/artifacts (document/spreadsheet/timeline/dashboard; edit/review/approve/publish)
- **Entry routes:** Project workspace methodology actions + artifact/canvas APIs.
- **UI components:** `MethodologyWorkspaceSurface`, `ActivityDetailPanel`, canvas/editor components.
- **Backend endpoints used:**
  - `POST /api/methodology/runtime/action` lifecycle events (`generate`, `update`, `review`, `approve`, `publish`)
  - `POST /api/document-canvas/documents`, spreadsheet/timeline/tree APIs under `/api/spreadsheets`, `/api/timeline`, `/api/tree`
- **Feature-flagged:** No hard route flag; runtime actions depend on backend runtime contract resolution.
- **Actual build:** **Partial**. Lifecycle action dispatch exists and opens artifacts; explicit end-user publish workflow visibility/evidence across all artifact types is incomplete in SPA.
- **Demo-safe/demo-seeded:** **Partial**. Safe demo behavior exists; full publish evidence chain remains partial.

### Capability 14: Read/push records to Systems of Record (SoRs)
- **Entry routes:** Connector galleries and project connector config.
- **UI components:** `ConnectorGallery`, `ProjectConnectorGallery`, `SyncStatusPanel`, `ProjectMcpSidebar`.
- **Backend endpoints used:** Connector enable/config/test and MCP mapping endpoints listed in capability 9.
- **Feature-flagged:** MCP and connector behavior can be narrowed by feature flags; mock connector mapping enables demo safety.
- **Actual build:** **Implemented (integration surface)**. Real calls happen through non-demo connector clients.
- **Demo-safe/demo-seeded:** **Implemented**. Demo mode switches to demo connector/data/document clients and records actions in demo outbox instead of real pushes.

### Capability 15: Approval flows (stage gates/template/publish approvals + audit evidence)
- **Entry routes:** `/approvals`, `/intake/approvals`, methodology runtime actions, `/admin/audit`.
- **UI components:** `ApprovalsPage`, `IntakeApprovalsPage`, methodology lifecycle actions, `AuditLogPage`.
- **Backend endpoints used:**
  - `GET /v1/workflows/approvals`, `GET /v1/workflows/approvals/{id}`, `POST /v1/workflows/approvals/{id}/decision`
  - `GET /v1/api/intake?status=pending`, `POST /v1/api/intake/{requestId}/decision`
  - `GET /v1/audit/events`, `GET /v1/audit/events/{eventId}`
- **Feature-flagged:** Merge-review approval route is gated by `duplicate_resolution`.
- **Actual build:** **Partial**. Approval queues and decisions exist with audit log browsing; explicit template-approval and publish-approval specialized screens are not fully separated.
- **Demo-safe/demo-seeded:** **Implemented partial** with seeded approvals and audit records.

---

## Feature-flagged UI surfaces relevant to this matrix
- `duplicate_resolution`: enables `/intake/merge-review`.
- `agent_async_notifications`: enables `/notifications` route/nav.
- `agent_run_ui`: controls visibility of Agent Runs nav entry.
- `predictive_alerts`: analytics predictive alerts surface.
- `multi_agent_collab`: shared insights panel in workspace.
- `multimodal_intake`: intake upload/extract endpoints.

## Demo Readiness Summary
- Demo mode seeds workspace and demo UI data at startup.
- Demo fixture tests enforce minimum visible record counts and required navigation backing data.
- Connector + SoR interactions are demo-safe via demo clients and mock connector mappings when `DEMO_MODE=true`.
