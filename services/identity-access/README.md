# Identity & Access Service

The identity-access service validates JWTs and returns normalized identity claims for downstream
services. It supports dev-mode HS256 secrets and production-mode JWKS validation.

## Contracts

- OpenAPI: `services/identity-access/contracts/openapi.yaml`

## Run locally

```bash
IDENTITY_JWT_SECRET=dev-secret \
python -m tools.component_runner run --type service --name identity-access
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `IDENTITY_JWT_SECRET` | _none_ | HS256 secret for dev validation |
| `IDENTITY_JWKS_URL` | _none_ | JWKS endpoint for RS256 validation |
| `IDENTITY_AUDIENCE` | _none_ | Expected JWT audience |
| `IDENTITY_ISSUER` | _none_ | Expected JWT issuer |
| `LOG_LEVEL` | `info` | Logging verbosity |
| `PORT` | `8080` | HTTP port for the service |

## Example request

```bash
curl -X POST http://localhost:8080/auth/validate \
  -H "Content-Type: application/json" \
  -d '{"token": "<jwt>"}'
```

## Tests

```bash
pytest services/identity-access/tests
```
