# Local Dev Tools

## Purpose

Document the local dev tooling used to automate **local development** workflows.

## What's inside

- [ops/tools/local-dev/dev_down.sh](/ops/tools/local-dev/dev_down.sh): Stops the local Docker Compose stack.
- [ops/tools/local-dev/dev_up.sh](/ops/tools/local-dev/dev_up.sh): Boots the local Docker Compose stack and can initialize `.env` from `.env.example`.
- [ops/tools/local-dev/docker-compose.override.example.yml](/ops/tools/local-dev/docker-compose.override.example.yml): Optional local override template.

## How it's used

These tools are invoked by local Make targets (for example, `make dev-up` and `make dev-down`).

## Configuration

- Configuration is sourced from repository-level `.env`.
- If `.env` is missing, `dev_up.sh` copies `.env.example` and randomizes local password defaults for safer local posture.
- `.env.example` values are **dev-only** and must never be reused in CI/staging/production.

## Troubleshooting

- Command not found: ensure Docker Compose is installed (`docker compose version` or `docker-compose --version`).
- Tool errors: inspect logs and verify referenced paths exist.
