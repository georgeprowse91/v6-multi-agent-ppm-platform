# Identity Access

## Purpose

Define the Identity Access service responsibilities and how it integrates with the platform.

## Key endpoints

- `GET /healthz`: Service health check.
- `POST /auth/validate`: Validate a JWT and return tenant/role claims.
- `POST /scim/v2/Users`: Create a user via SCIM.
- `GET /scim/v2/Users`: List users via SCIM.
- `PATCH /scim/v2/Users/{user_id}`: Update a user.
- `POST /scim/v2/Groups`: Create a group via SCIM.
- `GET /scim/v2/Groups`: List groups via SCIM.
- `PATCH /scim/v2/Groups/{group_id}`: Update a group.
- `GET /scim/internal/roles/{user_id}`: Retrieve resolved roles for a user.

**Default port:** `8080`

## What's inside

- `services/identity-access/contracts`: Service contracts and schema artifacts.
- `services/identity-access/helm`: Helm chart packaging for Kubernetes deployments.
- `services/identity-access/src`: Implementation source for this component.
- `services/identity-access/tests`: Test suites and fixtures.
- `services/identity-access/Dockerfile`: Container build recipe for local or CI use.
- `services/identity-access/main.py`: Primary runtime entrypoint for this component.

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
