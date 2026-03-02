# Quickstart (Local, Deterministic)

## Purpose
This quickstart spins up a local stack (API gateway, orchestration, workflow service, and backing services)
then runs a deterministic, end-to-end scenario that exercises the intent router, orchestration layer,
three domain agents, and workflow persistence.

## Prerequisites
- Docker Desktop (or Docker Engine + docker compose plugin)
- Python 3.11+ (optional, for running the smoke script locally)
- `make`

## Preflight checks

- Confirm Docker is running: `docker ps`
- Confirm ports are free: `8000`, `8080`, and `8501`
- Create `.env` from `ops/config/.env.example` for local defaults: `cp .env.example .env`

## Start the local stack
```bash
cp .env.example .env
make dev-up
```

> ⚠️ `ops/config/.env.example` is for local development only. Never use these values in CI, staging, or production.


## Startup order and failure behavior
Docker Compose now uses health-gated startup for dependent services:

1. `db` and `redis` start first and must report healthy.
2. `api` waits for healthy `db` and healthy `redis`.
3. `workflow-service` starts independently and must report healthy.
4. `web` waits for both `api` and `workflow-service` to be healthy.

Health checks are intentionally lightweight and deterministic:
- `db`: `pg_isready`
- `redis`: `redis-cli ping`
- `api`, `workflow-service`, `web`: local `GET /healthz` probes from inside each container

Failure behavior expectations:
- If `db` or `redis` is unhealthy, `api` does not transition to running.
- If `api` or `workflow-service` is unhealthy, `web` does not transition to running.
- A service becoming unhealthy after startup does not automatically restart dependents; use `docker compose ps` and `docker compose logs <service>` for diagnosis.
- Verify dependency health with `docker compose ps` before running migrations or smoke flows.

## Apply database migrations
The orchestration service stores workflow state in Postgres. Apply migrations after the database
container is healthy:

```bash
DATABASE_URL=${DATABASE_URL:-postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:5432/$POSTGRES_DB} alembic upgrade head
```

The default dev stack enables auth dev mode and a mock LLM response for deterministic routing. The
stack exposes:
- API gateway: http://localhost:8000
- Workflow engine: http://localhost:8080
- Web console: http://localhost:8501

## Run the end-to-end scenario
The scenario uses:
- API gateway auth dev mode
- Intent router + response orchestration
- Portfolio strategy, financial management, and risk management agents
- Workflow engine persistence

### 1) Post a workflow run (workflow service)
```bash
curl -sS -X POST "http://localhost:8080/v1/workflows/start" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant" \
  -d @examples/demo-scenarios/quickstart-workflow.json | jq
```

Expected output:
- `status` should be `running`
- `workflow_id` should be `portfolio-intake`

### 2) Run the multi-agent query (API gateway)
```bash
curl -sS -X POST "http://localhost:8000/v1/query" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant" \
  -d @examples/demo-scenarios/quickstart-request.json | jq
```

Expected output:
- `success: true`
- `data.execution_summary.total_agents: 3`
- Agent results include:
  - `portfolio-optimisation-agent`
  - `financial-management-agent`
  - `risk-management-agent`

### 3) Verify health endpoints
```bash
curl -sS http://localhost:8000/healthz | jq
curl -sS http://localhost:8080/healthz | jq
```

Optional: verify service-level health when running individual services directly by using their
configured port and `/healthz` endpoint.

## Stop the stack
```bash
make dev-down
```

## Notes
- To override the deterministic routing response, set `LLM_MOCK_RESPONSE_PATH` to a custom JSON
  file that matches the intent router response schema.
- Auth dev mode is enabled with `AUTH_DEV_MODE=true` (default in docker-compose for local
  development). In production, disable it and configure JWT validation. CI/prod must use environment-specific secrets, not local defaults from `ops/config/.env.example`.
- The orchestration service reads `ORCHESTRATION_STATE_BACKEND` (set to `db` in docker-compose)
  and `ORCHESTRATION_DATABASE_URL`/`DATABASE_URL` to select the durable Postgres store. Ensure the
  database encryption-at-rest features are enabled in your environment and use optional app-level
  envelope encryption hooks if you integrate them later.
