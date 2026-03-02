# Web

## Purpose

The PPM Platform web application provides the primary user interface for managing portfolios, programs, and projects. It features a three-panel layout with methodology navigation, a main workspace canvas, and an AI assistant panel.

## Architecture

The web application consists of:

- **Backend**: FastAPI server (`src/main.py`) handling authentication, API proxying, and static file serving
- **Frontend**: React + TypeScript SPA (`frontend/`) with Vite build tooling

### Frontend Stack

- **React 18** with TypeScript for UI components
- **React Router 6** for client-side routing
- **Zustand** for global state management
- **Vite** for fast development and optimized builds
- **Vitest** for unit testing

## What's inside

- [data](/apps/web/data): Data assets and fixtures for this component
- [e2e](/apps/web/e2e): End-to-end test specs or tooling
- [frontend](/apps/web/frontend): React + TypeScript frontend application
  - [components](/frontend/src/components): Reusable UI components
  - [pages](/frontend/src/pages): Route-level page components
  - [store](/frontend/src/store): Zustand state management
  - [styles](/frontend/src/styles): CSS tokens and global styles
- [helm](/apps/web/helm): Helm chart packaging for Kubernetes deployments
- [public](/apps/web/public): Static assets served by the app
- [scripts](/apps/web/scripts): Scripts that support this component or workflow
- [src](/apps/web/src): Python backend source
- [static](/apps/web/static): Built frontend assets (production)

## UI screenshots

Store new UI screenshots for this app in `docs/assets/ui/screenshots/` so documentation assets stay centralized. See the README in that folder for naming and capture guidance.

## How to run / develop / test

### Prerequisites

- Node.js 20+ (for frontend)
- Python 3.11+ (for backend)
- npm or pnpm

### Frontend Development

1. Install frontend dependencies:

```bash
cd apps/web/frontend
npm install
```

2. Start the development server:

```bash
npm run dev
```

The frontend dev server runs at `http://localhost:3000` and proxies API requests to the backend.

3. Run tests:

```bash
npm test
```

4. Type checking:

```bash
npm run typecheck
```

5. Linting:

```bash
npm run lint
```

### Legacy workspace artifact guard

Run this check before opening a PR to ensure deprecated workspace entrypoints/assets are not reintroduced:

```bash
python apps/web/scripts/check_legacy_workspace_artifacts.py
```

The guard blocks these patterns by default: `@api_router.get("/workspace")`, `/workspace?`, `_workspace_redirect_to_spa`, and legacy shell bundle references (for example `workspace[.]js`, `workspace[.]css`).

If a historical mention is intentional (for example in migration tests or changelog notes), add a narrowly scoped exception in `apps/web/scripts/legacy_workspace_guard_allowlist.txt` using the `path|check_id|contains` format.

### Backend Development

1. Start the FastAPI backend:

```bash
cd apps/web
uvicorn src.main:app --host 0.0.0.0 --port 8501 --reload
```

Or use the component runner:

```bash
python -m tools.component_runner run --type app --name web
```

#### Backend environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DOCUMENT_SERVICE_URL` | `http://document-service:8080` | Document service API base URL. |
| `ANALYTICS_SERVICE_URL` | `http://analytics-service:8080` | Analytics service API base URL for the dashboard canvas. |
| `DATA_LINEAGE_SERVICE_URL` | `http://data-lineage-service:8080` | Data lineage service API base URL for quality dashboards. |
| `API_GATEWAY_URL` | `http://api-gateway:8000` | API gateway base URL for assistant orchestration. |
| `ASSISTANT_TIMEOUT_S` | `20` | Timeout (seconds) for assistant proxy requests. |
| `CONNECTOR_HUB_URL` | `http://connector-hub:8080` | Connector hub API base URL for the connector gallery. |

### Document canvas local run

To exercise the Document canvas end-to-end, run the document service and point the web app to it:

```bash
cd apps/document-service
uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
```

In another terminal, run the web app with the document service URL configured:

```bash
cd apps/web
export DOCUMENT_SERVICE_URL=http://localhost:8080
export ANALYTICS_SERVICE_URL=http://localhost:8080
uvicorn src.main:app --host 0.0.0.0 --port 8501 --reload
```

Then open `http://localhost:8501/app/projects/demo-1`. The SPA hydrates methodology and canvas state from `/api/workspace/demo-1`.

### Dashboard canvas local run

To exercise the Dashboard canvas end-to-end, run the analytics service and point the web app to it:

```bash
cd apps/analytics-service
uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
```

In another terminal, run the web app with the analytics service URL configured:

```bash
cd apps/web
export ANALYTICS_SERVICE_URL=http://localhost:8080
uvicorn src.main:app --host 0.0.0.0 --port 8501 --reload
```

Then open `http://localhost:8501/app/projects/demo-1` and select the Dashboard tab.

### Connector gallery local run

To exercise the Connector Gallery in the SPA workspace, run connector-hub alongside the web app:

```bash
cd integrations/apps/connector-hub
uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
```

In another terminal, run the web app with the connector hub URL configured:

```bash
cd apps/web
export CONNECTOR_HUB_URL=http://localhost:8080
uvicorn src.main:app --host 0.0.0.0 --port 8501 --reload
```

Then open `http://localhost:8501/app/projects/demo-1` and select **Connectors** in the right panel.

> **Limitations:** The connector gallery only manages instance lifecycle and health status in this PR. Credentials are not stored or submitted through the UI, sync jobs are not executed, and webhook configuration is not included.

### Workspace methodology smoke check

Run a single local smoke check for workspace methodology wiring (YAML map loading, backend workspace payload validation for predictive/adaptive/hybrid, gate presence checks, and frontend hydration wiring assertions):

```bash
make smoke-workspace-wiring
# or
cd apps/web/frontend && npm run smoke:workspace-wiring
```

### Full Stack Development

For full-stack development, run both servers:

1. **Terminal 1** - Backend (port 8501):
   ```bash
   cd apps/web && uvicorn src.main:app --port 8501 --reload
   ```

2. **Terminal 2** - Frontend (port 3000):
   ```bash
   cd apps/web/frontend && npm run dev
   ```

Access the app at `http://localhost:3000`.

### Production Build

Build the frontend for production:

```bash
cd apps/web/frontend
npm run build
```

This outputs to `apps/web/static/dist/`. The FastAPI backend can then serve the built assets.

## Routes

| Path | Description |
|------|-------------|
| `/` | Home page with quick access to portfolios, programs, projects |
| `/app` | SPA shell root. Redirects into project-scoped SPA routes (for example `/app/projects/:projectId`) that render methodology, canvas, and assistant panels. |
| `/app/projects/:projectId` | Canonical SPA project workspace route. Use this route for all workspace deep links and local testing. |
| `/portfolio/:id` | SPA portfolio workspace |
| `/program/:id` | SPA program workspace |
| `/project/:id` | SPA project workspace |
| `/config/agents` | AI agent configuration |
| `/config/connectors` | Integration connector settings |
| `/config/workflows` | Workflow routing configuration |

## Workspace State APIs

Workspace state is persisted per `(tenant_id, project_id)` in:

```
apps/web/storage/workspace_state.json
```

Endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/workspace/{project_id}` | Fetch or create workspace state for the current tenant. |
| `POST` | `/api/workspace/{project_id}/select` | Persist canvas tab + selection metadata. |
| `POST` | `/api/workspace/{project_id}/activity-completion` | Persist activity completion status. |

The SPA project routes (for example, `/app/projects/demo-1`) hydrate workspace state via `/api/workspace/{project_id}` without relying on `/workspace` HTML routes or query-string entrypoints.

Legacy workspace entrypoints (`/workspace`, `/v1/workspace`) are retired and unsupported.

> **Dev auth mode:** Tests and local development can use `AUTH_DEV_MODE=true` with `ENVIRONMENT=dev|test` to bypass OIDC, and `AUTH_DEV_TENANT_ID` to set the tenant used by the workspace state APIs.

## Agent Gallery (project-scoped)

The SPA workspace includes an Agent Gallery panel that lists the platform agent catalogue, per-project enablement, and configuration state. Settings are tenant-aware and scoped to a project.

**Storage location**

```
apps/web/storage/agent_settings.json
```

**Role rules**

- **Admins**: roles containing `tenant_owner` or `portfolio_admin` can enable/disable agents and update configuration.
- **Non-admins**: read-only access to the registry and project settings.

**Endpoints**

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/agent-gallery/agents` | List the available agent registry entries. |
| `GET` | `/api/agent-gallery/{project_id}` | Fetch or initialize project agent settings. |
| `PATCH` | `/api/agent-gallery/{project_id}/agents/{agent_id}` | Update enablement and/or configuration for an agent (admin only). |
| `POST` | `/api/agent-gallery/{project_id}/reset-defaults` | Reset project agent settings to registry defaults (admin only). |

**Defaults management**

Agent defaults are derived from `agents/runtime/src/agent_catalog.py` (with descriptions/outputs enriched from `docs/agents/agent-catalog.md`). To adjust defaults, edit the registry sources and re-fetch the gallery to initialize new agents.

## Template gallery

The workspace includes a canonical template catalog and instantiation gallery. Canonical template retrieval is sourced from:

- `docs/templates/index.json` (source of truth for canonical IDs and metadata)
- `docs/templates/migration/legacy-to-canonical.csv` (legacy alias mapping)
- `apps/web/src/canonical_template_registry.py` (API adapter for canonical retrieval and migration)

Instantiation payload templates remain defined in:

- `apps/web/src/template_models.py` (Pydantic models + placeholder rendering)
- `apps/web/src/template_registry.py` (static registry of template definitions)

### Template placeholders

Templates support simple string substitution (no code execution) for the following placeholders:

- `{{project_id}}`
- `{{tenant_id}}`
- `{{date}}` (YYYY-MM-DD)
- `{{user}}` (derived from the authenticated subject or passed via parameters; defaults to `unknown`)

Custom parameters passed during instantiation are merged into the placeholder context.

### API endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/templates` | List template summaries; canonical catalog mode supports `gallery=true` plus `artefact`, `methodology`, `compliance_tag`, and `q` filters (`type`/`tag` remain backwards-compatible aliases). |
| `GET` | `/api/templates/{template_id}` | Fetch a canonical template definition (when `gallery=true` or canonical/legacy ID is provided) or a project template definition (supports `version`). |
| `POST` | `/api/templates/{template_id}/instantiate` | Instantiate a template into a document or spreadsheet. |
| `POST` | `/api/templates/{template_id}/apply` | Apply a project template; accepts optional `version` to pin the configuration. |

> **Note:** `/api/templates` is shared with project template configuration. Use `gallery=true` to explicitly request canonical template catalog responses for the workspace selector.

Example instantiate request:

```json
{
  "project_id": "demo-1",
  "parameters": { "user": "Alex" }
}
```

### Adding new templates

1. Add a new `Template` entry in `apps/web/src/template_registry.py`.
2. Set `template_id` to a stable identifier and increment `schema_version` if you change the schema.
3. Use `defaults` for document templates (classification + retention) and specify payload templates with placeholder tokens.

## Assistant proxy

The assistant panel sends requests to the web backend, which forwards them to the API gateway orchestrator endpoint.

### Endpoint

```
POST /api/assistant/send
{
  "project_id": "<project-id>",
  "message": "<user prompt>"
}
```

### Next-best-action suggestions

```
POST /api/assistant/suggestions
{
  "project_id": "<project-id>",
  "activity_id": "<activity-id>",
  "activity_name": "<activity name>",
  "stage_id": "<stage-id>",
  "stage_name": "<stage name>",
  "activity_status": "in_progress",
  "canvas_type": "document",
  "incomplete_prerequisites": []
}
```

The response includes structured action chips generated by the LLM (with a heuristic fallback), plus the context used during generation.

### Context forwarded

The proxy forwards the authenticated tenant identifier along with workspace context:

- `tenant_id` (derived from auth/session)
- `project_id`
- `correlation_id` (generated server-side)
- `methodology`, `current_stage_id`, `current_activity_id`, `current_canvas_tab`
- `open_ref` IDs only (`document_id`, `sheet_id`, `milestone_id` when available)

Document content is **not** sent automatically—only identifiers.

### Limitations

- Session-only transcript (no persistence across refreshes)
- No streaming responses
- No automatic artifact content forwarding

## Tree Canvas APIs

Tree canvas data is stored per tenant/project in:

```
apps/web/storage/trees.json
```

Endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/tree/{project_id}` | List tree nodes for the project. |
| `POST` | `/api/tree/{project_id}/nodes` | Create a node (folder, document, sheet, milestone, note). |
| `PATCH` | `/api/tree/{project_id}/nodes/{node_id}` | Update node title, ref, or sort order. |
| `POST` | `/api/tree/{project_id}/nodes/{node_id}/move` | Move a node to a new parent/sort order. |
| `DELETE` | `/api/tree/{project_id}/nodes/{node_id}` | Delete a node and its subtree. |
| `GET` | `/api/tree/{project_id}/export` | Export tree nodes as JSON. |

### Cross-canvas linking

To open a linked artifact from the Tree canvas, call the workspace selection endpoint with `open_ref`:

```json
POST /api/workspace/{project_id}/select
{
  "current_canvas_tab": "document",
  "current_stage_id": null,
  "current_activity_id": null,
  "methodology": null,
  "open_ref": { "document_id": "doc-123" }
}
```

## Timeline canvas APIs

Timeline milestones are persisted per `(tenant_id, project_id)` in:

```
apps/web/storage/timelines.json
```

Endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/timeline/{project_id}` | List milestones for the current tenant/project. |
| `POST` | `/api/timeline/{project_id}/milestones` | Create a milestone. |
| `PATCH` | `/api/timeline/{project_id}/milestones/{milestone_id}` | Update a milestone. |
| `DELETE` | `/api/timeline/{project_id}/milestones/{milestone_id}` | Delete a milestone. |
| `GET` | `/api/timeline/{project_id}/export` | Export timeline JSON for the project. |

## Spreadsheet canvas APIs

Spreadsheet sheets and rows are persisted per `(tenant_id, project_id)` in:

```
apps/web/storage/spreadsheets.json
```

Sheets:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/spreadsheets/{project_id}/sheets` | List spreadsheet sheets for the current tenant/project. |
| `POST` | `/api/spreadsheets/{project_id}/sheets` | Create a new sheet with typed columns. |
| `GET` | `/api/spreadsheets/{project_id}/sheets/{sheet_id}` | Fetch a sheet with its rows. |

Rows:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/spreadsheets/{project_id}/sheets/{sheet_id}/rows` | Add a row to a sheet. |
| `PATCH` | `/api/spreadsheets/{project_id}/sheets/{sheet_id}/rows/{row_id}` | Update row values (partial updates are allowed). |
| `DELETE` | `/api/spreadsheets/{project_id}/sheets/{sheet_id}/rows/{row_id}` | Delete a row. |

CSV:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/spreadsheets/{project_id}/sheets/{sheet_id}/export.csv` | Export a sheet as CSV. |
| `POST` | `/api/spreadsheets/{project_id}/sheets/{sheet_id}/import.csv` | Import rows from CSV (`text/csv` body). |

### CSV format

- Header row uses column names from the sheet (case-sensitive).
- Required columns must be included and populated.
- Column types:
  - `text` -> string
  - `number` -> numeric (coerced to float)
  - `date` -> `YYYY-MM-DD`
  - `bool` -> `true` / `false`
- Unknown columns or invalid values return `422`.

### Methodology selection and gating

Workspace APIs support methodology-driven navigation. Methodology can be set via `GET /api/workspace/{project_id}?methodology=<id>` and persisted through `/api/workspace/{project_id}/select`, independent of which SPA route is used.

Key behaviours:

- **Methodology activities** follow prerequisite gating. An activity is allowed only when all of its
  prerequisite activity IDs are marked complete in `activity_completion`.
- **Monitoring activities** are never gated. They remain selectable regardless of completion state.
- The API returns gating metadata in `gating.current_activity_access` and the next prerequisite to resolve
  in `gating.next_required_activity_id`.

See `apps/web/src/methodologies.py` for the canonical activity maps and `apps/web/src/gating.py` for the
deterministic gating logic.

### Assistant panel (SPA workspace)

The SPA workspace includes an Assistant panel for the currently selected activity. It provides:

- **Activity context** (name + "What this is for" description).
- **Next-best-action prompt chips** drawn from each activity's `assistant_prompts` list.
- **Prompt box** that is empty by default; selecting a chip replaces the text.
- **Copy** action to copy the prompt text to the clipboard, with a user-visible message if the box is empty.
- **Clear** action to reset the prompt box.

The Assistant panel is guidance only. It does **not** send prompts to any orchestrator or LLM execution
service, and no chat transcript is stored by the SPA workspace.

## Global State

The application uses Zustand for state management. Key state slices:

- **Session**: User authentication state
- **Current Selection**: Active portfolio/program/project
- **Current Activity**: Selected methodology phase
- **Open Tabs**: Canvas tab management
- **Chat Messages**: Assistant conversation history
- **UI State**: Panel collapse states

## Configuration

Runtime configuration is supplied via `.env` and service URLs in the repo configuration files.

Key environment variables:
- `API_GATEWAY_URL`: URL of the API gateway (default: `http://localhost:8000`)
- `WORKFLOW_SERVICE_URL`: URL of the workflow service (default: `http://localhost:8082`)
- `DOCUMENT_SERVICE_URL`: URL of the document service (default: `http://document-service:8080`)
- `OIDC_*`: OIDC authentication settings (optional for dev mode)

## Troubleshooting

- **Missing dependencies**: Install dev dependencies with `make install-dev` (Python) or `npm install` (frontend)
- **Startup errors**: Verify required env vars are present in `.env`
- **CORS issues**: Ensure the frontend dev server is running on port 3000 (configured in API gateway CORS)
- **Build errors**: Run `npm run typecheck` to check for TypeScript errors

## Ownership and support

- Owner: Platform Engineering
- Support: #ppm-platform-support
