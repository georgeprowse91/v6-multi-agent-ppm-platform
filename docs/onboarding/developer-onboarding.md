# Developer Onboarding Guide

## Purpose

Provide a practical, step-by-step guide for new contributors to set up the Multi-Agent PPM Platform
locally, understand core services, and start contributing safely.

## Prerequisites

- Python 3.11+
- Node.js 18+ with `pnpm`
- Docker Desktop (or Docker Engine + Docker Compose plugin)
- `make`

## Repository tour (fast path)

- `apps/`: API gateway, workflow engine, admin console, and web console.
- `services/`: audit log, data sync, data lineage, identity, policy, telemetry.
- `agents/`: agent prompts, orchestrators, and domain agents.
- `docs/`: architecture, compliance, runbooks, and this guide.
- `infra/`: Terraform, Kubernetes, and observability artifacts.

## Setup checklist

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
3. **Start the local stack**
   ```bash
   make dev-up
   ```
4. **Apply database migrations**
   ```bash
   DATABASE_URL=postgresql://ppm:ppm_password@localhost:5432/ppm alembic upgrade head
   ```
5. **Verify health endpoints**
   ```bash
   curl -sS http://localhost:8000/healthz
   curl -sS http://localhost:8080/healthz
   ```

## Local URLs & endpoints

- API Gateway: `http://localhost:8000`
  - `GET /healthz`
  - `POST /api/v1/query`
  - `GET /api/v1/status`
- Workflow Engine: `http://localhost:8080`
  - `POST /workflows/start`
  - `GET /workflows/{run_id}`
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

## Configuration tips

- Local development uses an auth stub in docker-compose (`AUTH_DEV_MODE=true`).
- Update `.env` for local overrides (LLM provider, credentials, feature flags).
- Service-specific environment variables live in each service README.

## Common issues

- **Port conflicts**: update `PORT` in the service config or stop the conflicting process.
- **Migrations failing**: ensure the Postgres container is healthy and `DATABASE_URL` is correct.
- **Slow startup**: check Docker resource limits and confirm `pnpm install` completed.

## Next steps

- Review the [Architecture docs](../architecture/README.md) for system design.
- Read the [Runbooks](../runbooks/quickstart.md) before touching production infrastructure.
- Use the [Release process](../production-readiness/release-process.md) before cutting tags.
