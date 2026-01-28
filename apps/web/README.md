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

- `apps/web/data`: Data assets and fixtures for this component
- `apps/web/e2e`: End-to-end test specs or tooling
- `apps/web/frontend`: React + TypeScript frontend application
  - `frontend/src/components`: Reusable UI components
  - `frontend/src/pages`: Route-level page components
  - `frontend/src/store`: Zustand state management
  - `frontend/src/styles`: CSS tokens and global styles
- `apps/web/helm`: Helm chart packaging for Kubernetes deployments
- `apps/web/public`: Static assets served by the app
- `apps/web/scripts`: Scripts that support this component or workflow
- `apps/web/src`: Python backend source
- `apps/web/static`: Built frontend assets (production)

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
uvicorn src.main:app --host 0.0.0.0 --port 8501 --reload
```

Then open `http://localhost:8501/workspace?project_id=demo-1&methodology=hybrid`.

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
| `/workspace` | Static workspace shell layout (navigation, canvas tabs, assistant panel) |
| `/portfolio/:id` | Portfolio workspace |
| `/program/:id` | Program workspace |
| `/project/:id` | Project workspace |
| `/config/agents` | AI agent configuration |
| `/config/connectors` | Integration connector settings |
| `/config/templates` | Project/workflow templates |

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

The workspace shell expects a `project_id` query parameter (for example, `/workspace?project_id=demo-1`).

> **Dev auth mode:** Tests and local development can use `AUTH_DEV_MODE=true` with `ENVIRONMENT=dev|test` to bypass OIDC, and `AUTH_DEV_TENANT_ID` to set the tenant used by the workspace state APIs.

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

The workspace shell supports a methodology-driven navigation model. Methodologies can be provided via the
`methodology` query parameter (for example, `/workspace?project_id=demo-1&methodology=hybrid`) or persisted
through `/api/workspace/{project_id}/select`.

Key behaviours:

- **Methodology activities** follow prerequisite gating. An activity is allowed only when all of its
  prerequisite activity IDs are marked complete in `activity_completion`.
- **Monitoring activities** are never gated. They remain selectable regardless of completion state.
- The API returns gating metadata in `gating.current_activity_access` and the next prerequisite to resolve
  in `gating.next_required_activity_id`.

See `apps/web/src/methodologies.py` for the canonical activity maps and `apps/web/src/gating.py` for the
deterministic gating logic.

### Assistant panel (static workspace shell)

The `/workspace` shell includes an Assistant panel for the currently selected activity. It provides:

- **Activity context** (name + "What this is for" description).
- **Next-best-action prompt chips** drawn from each activity's `assistant_prompts` list.
- **Prompt box** that is empty by default; selecting a chip replaces the text.
- **Copy** action to copy the prompt text to the clipboard, with a user-visible message if the box is empty.
- **Clear** action to reset the prompt box.

The Assistant panel is guidance only. It does **not** send prompts to any orchestrator or LLM execution
service, and no chat transcript is stored by the static shell.

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
- `WORKFLOW_ENGINE_URL`: URL of the workflow engine (default: `http://localhost:8082`)
- `DOCUMENT_SERVICE_URL`: URL of the document service (default: `http://document-service:8080`)
- `OIDC_*`: OIDC authentication settings (optional for dev mode)

## Troubleshooting

- **Missing dependencies**: Install dev dependencies with `make install-dev` (Python) or `npm install` (frontend)
- **Startup errors**: Verify required env vars are present in `.env`
- **CORS issues**: Ensure the frontend dev server is running on port 3000 (configured in API gateway CORS)
- **Build errors**: Run `npm run typecheck` to check for TypeScript errors
