# Multi-Agent PPM Platform

AI-native Project Portfolio Management (PPM) platform blueprint with 25 specialized agents orchestrating portfolio, program, and project delivery.

[![CI/CD](https://github.com/georgeprowse91/multi-agent-ppm-platform/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/georgeprowse91/multi-agent-ppm-platform/actions)
[![codecov](https://codecov.io/gh/georgeprowse91/multi-agent-ppm-platform/branch/main/graph/badge.svg)](https://codecov.io/gh/georgeprowse91/multi-agent-ppm-platform)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Purpose

The repository provides a docs-first, code-light blueprint for an enterprise-grade, multi-agent PPM platform. It includes real schemas, manifests, policies, and orchestration scaffolding so delivery teams can evaluate or extend the design without guessing how components fit together.

## What's inside

- `apps/`: user-facing apps (API gateway, web console, admin console) and Helm packaging.
- `agents/`: 25 domain agents plus runtime scaffolding, prompts, and tests.
- `connectors/`: integration manifests, mappings, SDK, and registry assets.
- `services/`: backend services (audit log, data sync, identity, notification, telemetry).
- `data/`: canonical schemas, lineage, quality rules, and migration specs.
- `docs/`: architecture, methodology, agent catalog, and solution overview.
- `infra/`: Terraform, Kubernetes, observability, and policy assets.
- `packages/`: shared Python packages used by apps/services.
- `tools/` + `scripts/`: local tooling, lint/format, codegen, and CI checks.
- `tests/`: contract, integration, load, security, and E2E test suites.
- `examples/`: scenario and configuration examples.
- `config/`: tenant and environment configuration assets.

## How it's used

- **Non-coders** start with the solution overview and architecture docs in `docs/`.
- **Developers** run the API gateway and web console locally, then extend agents, connectors, and services.
- **Integrators** use connector manifests and mappings to align external systems with the canonical data model.
- **Ops teams** use `infra/` plus `services/` Helm charts to deploy in Kubernetes environments.

## Quickstart (local development)

> Requires Python 3.11+ and Docker Compose.

```bash
make quick-start
```

This will:
- Copy `.env.example` to `.env`.
- Install dependencies.
- Start the local Docker Compose stack.

**Expected services**
- API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs
- Web Console: http://localhost:8501

Run individual components when you need them:

```bash
make run-api
make run-web
```

## Testing

```bash
make test
make test-cov
```

Other useful checks:

```bash
make lint
make check-links
make check-placeholders
```

## Deployment (high level)

- **Terraform**: infrastructure definitions live under `infra/terraform/`.
  ```bash
  make tf-init
  make tf-plan
  make tf-apply
  ```
- **Kubernetes manifests**: see `infra/kubernetes/manifests/`.
- **Helm charts**: each app/service has a `helm/` folder for packaging.

For deeper operational guidance, start with `infra/README.md` and `docs/architecture/`.

## Security & compliance

- Security posture and architecture: `docs/architecture/security-architecture.md`.
- Responsible disclosure: `SECURITY.md`.
- Data policy scaffolding: `infra/policies/` and `services/policy-engine/`.

## Where to find things

- **Agents** → `agents/` and `docs/agents/`.
- **Services** → `services/`.
- **Connectors** → `connectors/` and `docs/connectors/`.
- **Data model** → `data/schemas/` and `docs/data/`.

## How to verify documentation links

```bash
python scripts/check-links.py
python scripts/check-placeholders.py
```

## Related docs

- [Docs hub](docs/README.md)
- [Solution overview](docs/product/solution-overview/README.md)
- [Architecture documentation](docs/architecture/README.md)
- [Agent catalog](docs/agents/README.md)
- [Connector overview](docs/connectors/overview.md)
- [Data model & lineage](docs/data/README.md)
