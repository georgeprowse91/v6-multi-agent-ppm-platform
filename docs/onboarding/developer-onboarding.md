# Developer Onboarding Guide

## Purpose

Provide a practical, step-by-step guide for new contributors to set up the Multi-Agent PPM Platform
locally, understand core services, and start contributing safely.

## Prerequisites

- Python 3.11+
- Node.js 18+ with `pnpm`
- Docker Desktop (or Docker Engine + Docker Compose plugin)
- `make`
- (Optional) VS Code + Dev Containers extension or the `devcontainer` CLI

## Repository tour (fast path)

- `apps/`: API gateway, workflow engine, admin console, and web console.
- `services/`: audit log, data sync, data lineage, identity, policy, telemetry.
- `agents/`: agent prompts, orchestrators, and domain agents.
- `docs/`: architecture, compliance, runbooks, and this guide.
- `infra/`: Terraform, Kubernetes, and observability artifacts.

## Setup checklist

### Option A: Devcontainer (recommended for simplified local setup)

1. **Fill in required environment variables**
   ```bash
   cp .devcontainer/dev.env .devcontainer/dev.env.local
   ```
   Update `.devcontainer/dev.env.local` with your credentials and endpoints, then set
   `runArgs` in `.devcontainer/devcontainer.json` to use `.devcontainer/dev.env.local`.
2. **Start the devcontainer**
   - VS Code: `Dev Containers: Reopen in Container`
   - CLI: `devcontainer up --workspace-folder . --config .devcontainer/devcontainer.json`
3. **Verify the stack**
   ```bash
   curl -sS http://localhost:8000/healthz
   curl -sS http://localhost:8080/healthz
   ```

### Option B: Host setup

1. **Install Python dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
2. **Install web dependencies**
   ```bash
   pnpm install
   ```
3. **Create local environment file (dev-only defaults)**
   ```bash
   cp .env.example .env
   ```
   > Never reuse `.env.example` values in CI/staging/production.
4. **Start the local stack**
   ```bash
   make dev-up
   ```
5. **Apply database migrations**
   ```bash
   DATABASE_URL=${DATABASE_URL:-postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:5432/$POSTGRES_DB} alembic upgrade head
   ```
6. **Verify health endpoints**
   ```bash
   curl -sS http://localhost:8000/healthz
   curl -sS http://localhost:8080/healthz
   ```

## Local URLs & endpoints

- API Gateway: `http://localhost:8000`
  - `GET /healthz`
  - `POST /v1/query`
  - `GET /v1/status`
- Workflow Engine: `http://localhost:8080`
  - `POST /v1/workflows/start`
  - `GET /v1/workflows/{run_id}`
- Web Console: `http://localhost:8501`

## Development workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-change
   ```
2. **Make changes** in the relevant `apps/`, `services/`, or `agents/` folder.
3. **Run checks**
   ```bash
   make lint
   make test
   ```
4. **Update docs** when you add new endpoints, schemas, or runbooks.

## Versioning updates

When you change API behavior, update the shared API version and changelog:

1. **Edit `packages/version.py`** to bump `API_VERSION` using semantic versioning.
2. **Update `CHANGELOG.md`** under `Unreleased`:
   - Add a **Breaking** section for breaking changes (e.g., removed endpoints, renamed fields).
   - Use **Added**, **Changed**, and **Fixed** for non-breaking updates.
3. **Keep `/v1` routes stable** unless you are intentionally shipping a breaking change.

CI enforces major version bumps when breaking changes are recorded in the changelog.

## Configuration tips

- Local development uses auth dev mode in docker-compose (`AUTH_DEV_MODE=true`).
- `.env.example` is explicitly dev-only; CI and production must use managed secrets and environment-specific values.
- Update `.env` for local overrides (LLM provider, credentials, feature flags).
- Service-specific environment variables live in each service README.
- External research features rely on `SEARCH_API_ENDPOINT`/`SEARCH_API_KEY` and per-agent flags such as
  `enable_external_risk_research`, `enable_vendor_research`, and `enable_regulatory_monitoring`.

## Validation suites

- End-to-end workflow validation lives in `tests/integration/test_end_to_end_workflow.py`.
- Load and performance checks for the event bus live in `tests/performance/test_event_bus_load.py`.
- Security validation of secret resolution and RBAC mappings lives in `tests/security/test_secret_resolution_and_rbac.py`.

## Common issues

- **Port conflicts**: update `PORT` in the service config or stop the conflicting process.
- **Migrations failing**: ensure the Postgres container is healthy and `DATABASE_URL` is correct.
- **Slow startup**: check Docker resource limits and confirm `pnpm install` completed.

## Next steps

- Review the [Architecture docs](../architecture/README.md) for system design.
- Read the [Runbooks](../runbooks/quickstart.md) before touching production infrastructure.
- Use the [Release process](../production-readiness/release-process.md) before cutting tags.
