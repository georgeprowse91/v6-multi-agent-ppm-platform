# Multi-Agent PPM Platform

AI-native Project Portfolio Management (PPM) platform with 25 specialized agents orchestrating portfolio, program, and project delivery.

[![CI/CD](https://github.com/georgeprowse91/multi-agent-ppm-platform/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/georgeprowse91/multi-agent-ppm-platform/actions)
[![codecov](https://codecov.io/gh/georgeprowse91/multi-agent-ppm-platform/branch/main/graph/badge.svg)](https://codecov.io/gh/georgeprowse91/multi-agent-ppm-platform)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Purpose

The repository delivers a production-ready, multi-agent PPM platform with validated schemas, manifests, policies, orchestration services, and deployment assets. It includes operational runbooks and evidence to build, test, scan, deploy, and operate the system in client environments.

## Directory structure

| Folder | Description |
| --- | --- |
| [agents/](./agents/) | 25 domain agents plus runtime scaffolding, prompts, and tests |
| [apps/](./apps/) | User-facing applications (API gateway, web console, admin console, mobile) and Helm packaging |
| [ops/config/](./ops/config/) | Tenant, environment, and agent configuration assets |
| [integrations/connectors/](./integrations/connectors/) | Integration manifests, mappings, SDK, and registry assets for external systems |
| [data/](./data/) | Canonical JSON schemas, lineage, quality rules, and migration specs |
| [design-system/](./design-system/) | Design tokens and icon system |
| [docs/](./docs/) | Architecture, methodology, agent catalog, and solution overview |
| [docs/assets/ui/screenshots/](./docs/assets/ui/screenshots/) | Centralized UI screenshot assets for documentation |
| [examples/](./examples/) | Scenario and configuration examples |
| [ops/infra/](./ops/infra/) | Terraform, Kubernetes, observability, and policy assets |
| [packages/](./packages/) | Shared Python and TypeScript packages used by apps, services, and agents |
| [ops/scripts/](./ops/scripts/) | CI checks, validation, and utility scripts |
| [services/](./services/) | Backend services (audit log, data sync, identity, notification, telemetry, and more) |
| [tests/](./tests/) | Contract, integration, load, security, and E2E test suites |
| [ops/tools/](./ops/tools/) | Local tooling for lint, format, codegen, and load testing |

## How it's used

- **Non-coders** start with the solution overview and architecture docs in `docs/`.
- **Developers** run the API gateway and web console locally, then extend agents, connectors, and services.
- **Integrators** use connector manifests and mappings to align external systems with the canonical data model.
- **Ops teams** use `ops/infra/` plus `services/` Helm charts to deploy in Kubernetes environments.

## Quickstart (local development)

> Requires Python 3.11+ and Docker Compose.

```bash
cp .env.example .env
# Optional: update .env values for your machine (dev-only values by default)
make dev-up
```

> ⚠️ `.env.example` contains **dev-only local defaults**. Never reuse these values in CI, staging, or production.

See `docs/runbooks/quickstart.md` for the deterministic, end-to-end scenario that exercises the
API gateway, workflow engine, orchestration service, and agents using the Makefile workflow
(`make dev-up`, `make run-api`, `make run-web`).

**Expected services**
- API: http://localhost:8000
- API Docs: http://localhost:8000/v1/docs
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
| API Gateway | Front door for client requests, auth hand-off, and orchestration fan-out. | `GET /healthz`, `POST /v1/query`, `GET /v1/status` |
| Workflow Engine | Workflow persistence and execution for deterministic flows. | `GET /healthz`, `POST /v1/workflows/start`, `GET /v1/workflows/{workflow_id}` |
| Audit Log | Immutable audit trail with retention enforcement. | `GET /healthz`, `POST /v1/audit/events`, `GET /v1/audit/events/{event_id}` |
| Data Service | Canonical schema and entity storage. | `GET /healthz`, `POST /v1/schemas`, `POST /v1/entities/{schema_name}` |
| Data Sync Service | Connector-driven sync jobs and conflict management. | `GET /healthz`, `POST /v1/sync/run`, `GET /v1/sync/status/{job_id}`, `GET /v1/sync/conflicts` |
| Data Lineage Service | Lineage capture and quality scoring. | `GET /healthz`, `POST /v1/lineage/events`, `GET /v1/lineage/graph`, `GET /v1/quality/summary` |
| Identity & Access | SCIM + token validation for identity management. | `GET /healthz`, `POST /v1/auth/validate`, `POST /v1/scim/v2/Users`, `GET /v1/scim/v2/Groups` |
| Notification Service | Outbound notifications (email/chat/webhook). | `GET /healthz`, `POST /v1/notifications/send` |
| Policy Engine | RBAC/ABAC and policy evaluation. | `GET /healthz`, `POST /v1/policies/evaluate`, `POST /v1/rbac/evaluate`, `POST /v1/abac/evaluate` |
| Telemetry Service | Ingests platform metrics/events for observability. | `GET /healthz`, `POST /v1/telemetry/ingest` |


## Project Definition baseline repository

Agent 08 now supports persistent scope baseline storage and requirement traceability generation:

- Baselines are persisted via SQLAlchemy in `services/scope_baseline/scope_baseline_service.py` (SQLite by default at `data/scope_baselines.db`, configurable with `SCOPE_BASELINE_DB_URL`).
- The Project Definition agent returns `baseline_id` when locking a baseline and supports `get_baseline` retrieval by ID.
- Traceability matrices map requirement IDs to WBS IDs and emit `traceability.matrix.created`; baseline persistence emits `baseline.created`.

## External research (optional)

Several agents can augment their outputs with external web research. The Project Definition & Scope agent
uses public snippets to inform scope, requirements, and WBS proposals. The Risk, Vendor & Procurement, and
Compliance agents can optionally enrich their registers with external signals (market trends, supplier
news, regulatory updates). This feature uses a configured search API to retrieve short, public snippets and
blends them with internal data via the LLM. The goal is to help project managers gather relevant
information faster while preserving the organization's existing baselines and governance workflows.

**Configuration**
- Set `SEARCH_API_ENDPOINT` and `SEARCH_API_KEY` in your environment (see `.env.example`).
- Optional controls:
  - `SEARCH_API_MIN_INTERVAL` to throttle external requests.
  - `SEARCH_RESULT_LIMIT` to cap snippet volume.
- Enable the agent flags only when you are ready for outbound calls:
  - Project Definition & Scope: `enable_external_research`
  - Risk Management: `enable_external_risk_research`
  - Vendor & Procurement: `enable_vendor_research`
  - Compliance & Regulatory: `enable_regulatory_monitoring`

**Security & compliance safeguards**
- Only high-level objectives should be sent to external search providers; never include confidential data,
  personally identifiable information, or customer-specific details in search queries.
- If external search fails or returns no useful results, the agent automatically falls back to internal
  templates.
- External results may be subject to third-party licenses. Review and validate suggested scope items
  or risk/compliance findings before acceptance or inclusion in project artefacts.
- External research is meant to complement, not replace, internal knowledge and human judgment. It relies
  on internet connectivity and third-party APIs, which may introduce latency or additional costs.

## Testing

```bash
make test-all
make test-unit
make test-integration
make test-e2e
make test-security
make test-cov
```

Other useful checks:

```bash
make lint
make check-links
make check-placeholders
python ops/tools/config_validator.py
```

## Deployment (high level)

- **Terraform**: infrastructure definitions live under [ops/infra/terraform/](./ops/infra/terraform/).
  ```bash
  make tf-init
  make tf-plan
  make tf-apply
  ```
- **Kubernetes manifests**: see [ops/infra/kubernetes/manifests/](./ops/infra/kubernetes/manifests/).
- **Helm charts**: each app/service has a `helm/` folder for packaging.

For deeper operational guidance, start with [ops/infra/README.md](./ops/infra/README.md) and [docs/architecture/](./docs/architecture/).

## Security & compliance

- Security posture and architecture: [docs/architecture/security-architecture.md](./docs/architecture/security-architecture.md).
- Responsible disclosure: [SECURITY.md](./SECURITY.md).
- Data policy scaffolding: [ops/infra/policies/](./ops/infra/policies/) and [services/policy-engine/](./services/policy-engine/).

## Where to find things

- **Agents** → [agents/](./agents/) and [docs/agents/](./docs/agents/).
- **Services** → [services/](./services/).
- **Connectors** → [integrations/connectors/](./integrations/connectors/) and [docs/connectors/](./docs/connectors/).
- **Data model** → [data/schemas/](./data/schemas/) and [docs/data/](./docs/data/).

## How to verify documentation links

```bash
python ops/scripts/check-links.py
python ops/scripts/check-placeholders.py
```

## Related docs

- [Docs hub](docs/README.md)
- [Developer onboarding](docs/onboarding/developer-onboarding.md)
- [Versioning strategy](docs/versioning.md)
- [Solution overview](docs/product/solution-overview/README.md)
- [Architecture documentation](docs/architecture/README.md)
- [Agent catalog](docs/agents/README.md)
- [Connector overview](docs/connectors/overview.md)
- [Data model & lineage](docs/data/README.md)
- [Release process](docs/production-readiness/release-process.md)
