# Identity Access

## Purpose

Define the Identity Access service responsibilities and how it integrates with the platform.

## Key endpoints

- [healthz](/GET /healthz): Service health check.
- [validate](/POST /v1/auth/validate): Validate a JWT and return tenant/role claims.
- [Users](/POST /v1/scim/v2/Users): Create a user via SCIM.
- [Users](/GET /v1/scim/v2/Users): List users via SCIM.
- [{user_id}](/PATCH /v1/scim/v2/Users/{user_id}): Update a user.
- [Groups](/POST /v1/scim/v2/Groups): Create a group via SCIM.
- [Groups](/GET /v1/scim/v2/Groups): List groups via SCIM.
- [{group_id}](/PATCH /v1/scim/v2/Groups/{group_id}): Update a group via SCIM.
- [{user_id}](/GET /v1/scim/internal/roles/{user_id}): Retrieve resolved roles for a user.

**Default port:** `8080`

## What's inside

- [contracts](/services/identity-access/contracts): Service contracts and schema artifacts.
- [helm](/services/identity-access/helm): Helm chart packaging for Kubernetes deployments.
- [src](/services/identity-access/src): Implementation source for this component.
- [tests](/services/identity-access/tests): Test suites and fixtures.
- [Dockerfile](/services/identity-access/Dockerfile): Container build recipe for local or CI use.
- [main.py](/services/identity-access/main.py): Primary runtime entrypoint for this component.

## How it's used

Services are run via `tools/component_runner` or Docker and are referenced by API and orchestration layers.

## How to run / develop / test

Run the service locally (dry run to inspect the command):

```bash
python -m tools.component_runner run --type service --name identity-access --dry-run
```

## Configuration

Service-specific environment variables should be defined in `.env` and, for production, in secrets managers.

## Troubleshooting

- Missing env vars: review the service README or source code for required settings.
- Port conflicts: adjust `PORT` or Docker/Helm values.
