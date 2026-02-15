# Api Gateway

## Purpose

Describe the Api Gateway application and its role in the platform experience layer.

## What's inside

- [apps/api-gateway/helm](/apps/api-gateway/helm): Helm chart packaging for Kubernetes deployments.
- [apps/api-gateway/openapi](/apps/api-gateway/openapi): OpenAPI artifacts and generated summaries.
- [apps/api-gateway/src](/apps/api-gateway/src): Implementation source for this component.
- [apps/api-gateway/tests](/apps/api-gateway/tests): Test suites and fixtures.
- [apps/api-gateway/Dockerfile](/apps/api-gateway/Dockerfile): Container build recipe for local or CI use.

## How it's used

Apps are started via `tools/component_runner` or the Makefile targets that wrap common workflows.

## How to run / develop / test

Run the app locally (dry run to see the command):

```bash
python -m tools.component_runner run --type app --name api-gateway --dry-run
```

## Configuration

Runtime configuration is supplied via `.env` and service URLs in the repo configuration files.

### CORS configuration

CORS is configured per environment with explicit trusted origins. Wildcards (`*`) are rejected because the API enables credentials and therefore requires strict origin controls.

Use the following variables (highest to lowest precedence):

1. `CORS_ALLOWED_ORIGINS_<ENVIRONMENT>` (for example `CORS_ALLOWED_ORIGINS_PRODUCTION`)
2. `CORS_ALLOWED_ORIGINS`
3. `ALLOWED_ORIGINS` (legacy fallback)

If none are set, the API applies environment defaults in `apps/api-gateway/src/api/main.py`:

- Local / development / dev: `http://localhost:3000`, `http://localhost:8501`, `http://localhost:8000`
- Test: `http://localhost:3000`
- Staging: `https://staging.ppm.example.com`
- Production / prod: `https://ppm.example.com`

Approved cross-origin methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`.

Approved cross-origin headers: `Authorization`, `Content-Type`, `Accept`, `X-Tenant-ID`, `X-Dev-User`, `X-Webhook-Secret`, `X-Webhook-Signature`.

## Troubleshooting

- Missing dependencies: install dev dependencies with `make install-dev`.
- Startup errors: verify required env vars are present in `.env`.
