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
- `OIDC_*`: OIDC authentication settings (optional for dev mode)

## Troubleshooting

- **Missing dependencies**: Install dev dependencies with `make install-dev` (Python) or `npm install` (frontend)
- **Startup errors**: Verify required env vars are present in `.env`
- **CORS issues**: Ensure the frontend dev server is running on port 3000 (configured in API gateway CORS)
- **Build errors**: Run `npm run typecheck` to check for TypeScript errors
