# UI Gaps Backlog (Ordered)

This backlog is ordered by impact on the required capabilities and implementation effort.

## 1) Add dedicated portfolio/program/project collection list + search pages
- **Capabilities:** 4, 5, 6, 7.
- **Current gap:** `/portfolios`, `/programs`, `/projects` only redirect to current selection or hard-coded fallback instead of rendering searchable collections.
- **Affected files:**
  - `apps/web/frontend/src/App.tsx` (`EntityCollectionRedirect` routes)
  - `apps/web/frontend/src/components/layout/LeftPanel.tsx` (nav currently points to redirect routes)
  - `apps/web/src/main.py` (add collection list/search endpoints if not already available)
- **Acceptance criteria:**
  1. Visiting `/portfolios`, `/programs`, `/projects` renders list/search tables.
  2. Search supports name/id/status filters and opens selected workspace route.
  3. Works in actual build and demo mode with seeded records.

## 2) Complete “create new project” end-to-end routing after approvals
- **Capabilities:** 3, 7, 15.
- **Current gap:** Intake creation routes to status page, but SPA does not automatically route to a newly created project workspace when approval is complete.
- **Affected files:**
  - `apps/web/frontend/src/pages/IntakeFormPage.tsx`
  - `apps/web/frontend/src/pages/IntakeStatusPage.tsx`
  - `apps/web/frontend/src/pages/IntakeApprovalsPage.tsx`
  - `apps/web/src/main.py` (ensure created project identifier is exposed in intake decision/status payload)
- **Acceptance criteria:**
  1. Approved intake shows target `project_id` in status payload.
  2. UI provides “Open project workspace” action that routes to `/projects/:projectId`.
  3. Demo seeded approvals can traverse this full path.

## 3) Add full agent profile/test/run experience from Agent Gallery
- **Capabilities:** 8.
- **Current gap:** Agent listing/filter/config exists, but no dedicated profile route and no explicit test-run flow from agent cards.
- **Affected files:**
  - `apps/web/frontend/src/components/agentConfig/AgentGallery.tsx`
  - `apps/web/frontend/src/components/project/AgentGallery.tsx`
  - `apps/web/frontend/src/pages/ProjectConfigPage.tsx`
  - `apps/web/src/main.py` (add/confirm agent profile + test-run endpoints as needed)
- **Acceptance criteria:**
  1. Agent card can open a profile page (or panel) with capabilities and configuration history.
  2. “Test agent” executes a backend test endpoint and displays result artifacts.
  3. “Run agent” creates a run record visible in Agent Runs/audit trail.

## 4) Wire analytics what-if and export pack controls into SPA
- **Capabilities:** 12.
- **Current gap:** Analytics page loads trends/predictive alerts but does not invoke dashboard what-if/export APIs from the UI.
- **Affected files:**
  - `apps/web/frontend/src/pages/AnalyticsDashboard.tsx`
  - `apps/web/src/main.py` (dashboard what-if/export endpoints)
- **Acceptance criteria:**
  1. Dashboard includes what-if input controls and calls `POST /v1/api/dashboard/{project_id}/what-if`.
  2. Dashboard includes export pack trigger/download (or explicit unsupported state).
  3. Demo mode returns safe simulated what-if/export data.

## 5) Strengthen artifact lifecycle UX for review/approve/publish evidence
- **Capabilities:** 13, 15.
- **Current gap:** Lifecycle actions are dispatched from methodology runtime, but UI lacks a consolidated artifact lifecycle board showing review/approval/publish status per artifact type.
- **Affected files:**
  - `apps/web/frontend/src/components/methodology/MethodologyWorkspaceSurface.tsx`
  - `apps/web/frontend/src/pages/ApprovalsPage.tsx`
  - `apps/web/frontend/src/pages/AuditLogPage.tsx`
  - `apps/web/src/main.py` (runtime action/audit payload fields)
- **Acceptance criteria:**
  1. Artifact records display lifecycle status (`generated`, `in_review`, `approved`, `published`).
  2. Each status transition links to audit evidence/event id.
  3. Publish action is disabled until required approvals are complete.

## 6) Add explicit template-approval and publish-approval views
- **Capabilities:** 15.
- **Current gap:** Generic approvals list exists, but stage-gate/template/publish approvals are not split into dedicated queues/views.
- **Affected files:**
  - `apps/web/frontend/src/pages/ApprovalsPage.tsx`
  - `apps/web/frontend/src/components/layout/LeftPanel.tsx`
  - `apps/web/src/main.py` (approval type metadata enrichment)
- **Acceptance criteria:**
  1. Approval list can filter by approval type (`stage_gate`, `template`, `publish`).
  2. Distinct detail pane fields are shown per type.
  3. Audit log deep-links are present for each decision.

## 7) Close demo parity gaps for workspace collections and post-intake project creation
- **Capabilities:** 3, 4, 5, 6, 7.
- **Current gap:** Demo data is broad, but UX parity for collection list/search and intake-to-project routing remains incomplete.
- **Affected files:**
  - `apps/web/data/demo_seed.json`
  - `apps/web/src/demo_seed.py`
  - `tests/demo/test_ui_data_completeness.py`
- **Acceptance criteria:**
  1. Demo seed includes portfolio/program/project collection metadata required by new list/search pages.
  2. Demo seed includes intake records that resolve to concrete project ids after approval.
  3. Demo tests assert these routes and data links are present.
