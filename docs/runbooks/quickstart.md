# Quickstart (Local, Deterministic)

## Purpose
This quickstart spins up a local stack (API gateway, orchestration, workflow engine, and backing services)
then runs a deterministic, end-to-end scenario that exercises the intent router, orchestration layer,
three domain agents, and workflow persistence.

## Prerequisites
- Docker Desktop (or Docker Engine + docker compose plugin)
- Python 3.11+ (optional, for running the smoke script locally)
- `make`

## Start the local stack
```bash
make dev-up
```

The default dev stack enables an auth stub and mock LLM response for deterministic routing. The
stack exposes:
- API gateway: http://localhost:8000
- Workflow engine: http://localhost:8080
- Web console: http://localhost:8501

## Run the end-to-end scenario
The scenario uses:
- API gateway auth stub/dev mode
- Intent router + response orchestration
- Portfolio strategy, financial management, and risk management agents
- Workflow engine persistence

### 1) Post a workflow run (workflow engine)
```bash
curl -sS -X POST "http://localhost:8080/workflows/start" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant" \
  -d @examples/demo-scenarios/quickstart-workflow.json | jq
```

Expected output:
- `status` should be `running`
- `workflow_id` should be `portfolio-intake`

### 2) Run the multi-agent query (API gateway)
```bash
curl -sS -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant" \
  -d @examples/demo-scenarios/quickstart-request.json | jq
```

Expected output:
- `success: true`
- `data.execution_summary.total_agents: 3`
- Agent results include:
  - `portfolio-strategy-optimization`
  - `financial-management`
  - `risk-management`

### 3) Verify health endpoints
```bash
curl -sS http://localhost:8000/healthz | jq
curl -sS http://localhost:8080/healthz | jq
```

## Stop the stack
```bash
make dev-down
```

## Notes
- To override the deterministic routing response, set `LLM_MOCK_RESPONSE_PATH` to a custom JSON
  file that matches the intent router response schema.
- Auth stub/dev mode is enabled with `AUTH_DEV_MODE=true` (default in docker-compose for local
  development). In production, disable it and configure JWT validation.
