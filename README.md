# Multi-Agent PPM Platform

AI-native Project Portfolio Management (PPM) platform with 25 specialized agents orchestrating portfolio, program, and project delivery.

[![CI/CD](https://github.com/georgeprowse91/multi-agent-ppm-platform/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/georgeprowse91/multi-agent-ppm-platform/actions)
[![codecov](https://codecov.io/gh/georgeprowse91/multi-agent-ppm-platform/branch/main/graph/badge.svg)](https://codecov.io/gh/georgeprowse91/multi-agent-ppm-platform)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Purpose

The repository delivers a production-ready, multi-agent PPM platform with validated schemas, manifests, policies, orchestration services, and deployment assets. It includes operational runbooks and evidence to build, test, scan, deploy, and operate the system in client environments.

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
make dev-up
```

See the detailed runbook in `docs/runbooks/quickstart.md` for the deterministic, end-to-end
scenario that exercises the API gateway, workflow engine, orchestration service, and agents.

**Expected services**
- API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs
- Web Console: http://localhost:8501

Run individual components when you need them:

```bash
make run-api
make run-web
```

## Service catalog & endpoints

The platform ships with dedicated backend services. Use the table below to understand responsibilities and
their primary endpoints when run locally (each service defaults to port `8080` unless noted).

| Service | Description | Primary endpoints |
| --- | --- | --- |
| API Gateway | Front door for client requests, auth hand-off, and orchestration fan-out. | `GET /healthz`, `POST /api/v1/query`, `GET /api/v1/status` |
| Workflow Engine | Workflow persistence and execution for deterministic flows. | `GET /healthz`, `POST /workflows/start`, `GET /workflows/{workflow_id}` |
| Audit Log | Immutable audit trail with retention enforcement. | `GET /healthz`, `POST /audit/events`, `GET /audit/events/{event_id}` |
| Data Service | Canonical schema and entity storage. | `GET /healthz`, `POST /schemas`, `POST /entities/{schema_name}` |
| Data Sync Service | Connector-driven sync jobs and conflict management. | `GET /healthz`, `POST /sync/run`, `GET /sync/status/{job_id}`, `GET /sync/conflicts` |
| Data Lineage Service | Lineage capture and quality scoring. | `GET /healthz`, `POST /lineage/events`, `GET /lineage/graph`, `GET /quality/summary` |
| Identity & Access | SCIM + token validation for identity management. | `GET /healthz`, `POST /auth/validate`, `POST /scim/v2/Users`, `GET /scim/v2/Groups` |
| Notification Service | Outbound notifications (email/chat/webhook). | `GET /healthz`, `POST /notifications/send` |
| Policy Engine | RBAC/ABAC and policy evaluation. | `GET /healthz`, `POST /policies/evaluate`, `POST /rbac/evaluate`, `POST /abac/evaluate` |
| Telemetry Service | Ingests platform metrics/events for observability. | `GET /healthz`, `POST /telemetry/ingest` |

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
- [Developer onboarding](docs/onboarding/developer-onboarding.md)
- [Solution overview](docs/product/solution-overview/README.md)
- [Architecture documentation](docs/architecture/README.md)
- [Agent catalog](docs/agents/README.md)
- [Connector overview](docs/connectors/overview.md)
- [Data model & lineage](docs/data/README.md)
- [Release process](docs/production-readiness/release-process.md)
