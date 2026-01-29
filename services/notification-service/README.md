# Notification Service

## Purpose

Define the Notification Service service responsibilities and how it integrates with the platform.

## Key endpoints

- `GET /healthz`: Service health check.
- `POST /notifications/send`: Send a notification payload.

**Default port:** `8080`

## What's inside

- `services/notification-service/contracts`: Service contracts and schema artifacts.
- `services/notification-service/helm`: Helm chart packaging for Kubernetes deployments.
- `services/notification-service/src`: Implementation source for this component.
- `services/notification-service/templates`: Templates used by the component (deployment or message content).
- `services/notification-service/tests`: Test suites and fixtures.
- `services/notification-service/Dockerfile`: Container build recipe for local or CI use.

## How it's used

Services are run via `tools/component_runner` or Docker and are referenced by API and orchestration layers.

## How to run / develop / test

Run the service locally (dry run to inspect the command):

```bash
python -m tools.component_runner run --type service --name notification-service --dry-run
```

## Configuration

Service-specific environment variables should be defined in `.env` and, for production, in secrets managers.

## Troubleshooting

- Missing env vars: review the service README or source code for required settings.
- Port conflicts: adjust `PORT` or Docker/Helm values.
