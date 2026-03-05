# Local Dev Tools

## Purpose

Document the local dev tooling used to automate **local development** workflows.

## What's inside

- [dev_down.sh](./dev_down.sh): Stops the local Docker Compose stack.
- [dev_up.sh](./dev_up.sh): Boots the local Docker Compose stack and can initialize `.env` from `ops/config/.env.example`.
- [docker-compose.override.example.yml](./docker-compose.override.example.yml): Optional local override template.

## How it's used

These tools are invoked by local Make targets (for example, `make dev-up` and `make dev-down`).

## Configuration

- Configuration is sourced from repository-level `.env`.
- If `.env` is missing, `dev_up.sh` copies `ops/config/.env.example` and randomizes local password defaults for safer local posture.
- `ops/config/.env.example` values are **dev-only** and must never be reused in CI/staging/production.

## Troubleshooting

- Command not found: ensure Docker Compose is installed (`docker compose version` or `docker-compose --version`).
- Tool errors: inspect logs and verify referenced paths exist.
