# API Gateway

FastAPI entrypoint for the platform. It exposes health probes, agent query routing, and the
OpenAPI contract used by downstream clients.

## Quickstart

```bash
make run-api
```

## How to verify

```bash
curl http://localhost:8000/healthz
```

Expected response:

```json
{"status":"ok","timestamp":"2024-01-01T12:00:00","version":"0.1.0"}
```

```bash
curl http://localhost:8000/version
```

Expected response:

```json
{"service":"multi-agent-ppm-api","version":"0.1.0","build_sha":"unknown"}
```

## Key files

- `apps/api-gateway/src/api/main.py`: FastAPI app and startup wiring.
- `apps/api-gateway/src/api/routes/`: HTTP route modules.
- `docs/api/openapi.yaml`: source OpenAPI spec.
- `apps/api-gateway/openapi/`: generated OpenAPI summaries.

## Example request

```bash
curl -X POST http://localhost:8000/api/v1/query \\
  -H "Content-Type: application/json" \\
  -d '{"query":"Show me the portfolio overview","context":{"user_id":"demo"}}'
```
