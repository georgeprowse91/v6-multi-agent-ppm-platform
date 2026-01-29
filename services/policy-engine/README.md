# Policy Engine

## Purpose

Define the Policy Engine service responsibilities and how it integrates with the platform.

## Key endpoints

- `GET /healthz`: Service health check.
- `POST /policies/evaluate`: Evaluate policy decisions against inputs.
- `POST /rbac/evaluate`: Evaluate RBAC policies.
- `POST /abac/evaluate`: Evaluate ABAC policies.

**Default port:** `8080`

## What's inside

- `services/policy-engine/contracts`: Service contracts and schema artifacts.
- `services/policy-engine/helm`: Helm chart packaging for Kubernetes deployments.
- `services/policy-engine/policies`: Policy definitions enforced by the platform.
- `services/policy-engine/src`: Implementation source for this component.
- `services/policy-engine/tests`: Test suites and fixtures.
- `services/policy-engine/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Services are run via `tools/component_runner` or Docker and are referenced by API and orchestration layers.

## How to run / develop / test

Run the service locally (dry run to inspect the command):

```bash
python -m tools.component_runner run --type service --name policy-engine --dry-run
```

## Configuration

Service-specific environment variables should be defined in `.env` and, for production, in secrets managers.

## Troubleshooting

- Missing env vars: review the service README or source code for required settings.
- Port conflicts: adjust `PORT` or Docker/Helm values.
