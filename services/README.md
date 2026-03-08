# Services

## Purpose

Catalog backend services that power data sync, policy enforcement, and telemetry.

## Directory structure

| Folder | Description |
| --- | --- |
| [admin-console/](./admin-console/) | Admin console (platform operator management) |
| [agent-config/](./agent-config/) | Agent configuration management |
| [agent-runtime/](./agent-runtime/) | Agent runtime hosting and orchestration |
| [analytics-service/](./analytics-service/) | Analytics and reporting service |
| [api-gateway/](./api-gateway/) | API gateway (front door for client requests) |
| [audit-log/](./audit-log/) | Immutable audit trail service |
| [auth-service/](./auth-service/) | Authentication (OAuth2/OIDC) |
| [connector-hub/](./connector-hub/) | Integration connector management hub |
| [data-lineage-service/](./data-lineage-service/) | Lineage capture and quality scoring |
| [data-service/](./data-service/) | Canonical schema and entity storage |
| [data-sync-service/](./data-sync-service/) | Connector-driven sync jobs |
| [document-service/](./document-service/) | Document storage and management service |
| [identity-access/](./identity-access/) | SCIM and token validation |
| [memory_service/](./memory_service/) | Conversation context and memory persistence |
| [notification-service/](./notification-service/) | Outbound notifications |
| [orchestration-service/](./orchestration-service/) | Multi-agent workflow coordination |
| [policy-engine/](./policy-engine/) | RBAC/ABAC policy evaluation |
| [realtime-coedit-service/](./realtime-coedit-service/) | Collaborative document editing |
| [scope_baseline/](./scope_baseline/) | Project scope baseline persistence |
| [telemetry-service/](./telemetry-service/) | Metrics/events ingestion |
| [workflow-service/](./workflow-service/) | Workflow persistence and execution engine |

Integration utilities now live under [`integrations/services/integration/`](../integrations/services/integration/).

## Service descriptions & endpoints

Each service runs a FastAPI application (default port `8080`) with health checks at `/healthz`.

| Service | Description | Primary endpoints |
| --- | --- | --- |
| Admin Console | Platform operator management for tenants, agents, connectors, and monitoring. | `GET /v1/admin/tenants`, `GET /v1/admin/agents` |
| Analytics Service | Computes KPI, trend, and utilization metrics for dashboards. | `GET /v1/analytics/kpis`, `GET /v1/analytics/trends` |
| API Gateway | Front door for client requests with auth, rate limiting, and circuit breaking. | `GET /healthz`, `GET /v1/*` (proxied) |
| Audit Log | Immutable audit trail with retention and WORM storage enforcement. | `POST /v1/audit/events`, `GET /v1/audit/events/{event_id}` |
| Auth Service | Exchanges OAuth2/OIDC tokens and validates JWTs. | `POST /v1/auth/login`, `POST /v1/auth/refresh`, `POST /v1/auth/logout`, `POST /v1/auth/validate` |
| Agent Runtime | Hosts agent registry, orchestration, and connector integration for the platform. | `GET /v1/agents`, `POST /v1/agents/{agent_id}/execute`, `POST /v1/orchestration/run` |
| Connector Hub | Manages connector status, sync jobs, field-mapping overrides, and health metrics. | `GET /v1/connectors`, `POST /v1/connectors/sync` |
| Data Sync Service | Runs connector sync jobs, tracks status, and manages conflicts. | `POST /v1/sync/run`, `GET /v1/sync/status/{job_id}`, `GET /v1/sync/conflicts` |
| Data Lineage Service | Captures lineage events and quality summaries. | `POST /v1/lineage/events`, `GET /v1/lineage/graph`, `GET /v1/quality/summary` |
| Data Service | Manages schemas and canonical entities. | `POST /v1/schemas`, `GET /v1/schemas`, `POST /v1/entities/{schema_name}` |
| Identity & Access | Validates auth tokens and supports SCIM provisioning. | `POST /v1/auth/validate`, `POST /v1/scim/v2/Users`, `GET /v1/scim/v2/Groups` |
| Memory Service | Persists and retrieves agent conversation context keyed by correlation ID. | `POST /v1/memory`, `GET /v1/memory/{correlation_id}`, `DELETE /v1/memory/{correlation_id}` |
| Notification Service | Sends email/chat/webhook notifications. | `POST /v1/notifications/send` |
| Policy Engine | Evaluates RBAC/ABAC policy decisions. | `POST /v1/policies/evaluate`, `POST /v1/rbac/evaluate`, `POST /v1/abac/evaluate` |
| Document Service | Document storage, versioning, and policy controls. | `POST /v1/documents`, `GET /v1/documents/{document_id}` |
| Orchestration Service | Multi-agent workflow coordination, routing, and state tracking. | `POST /v1/orchestration/run`, `GET /v1/orchestration/status` |
| Scope Baseline | Persists and versions project scope baseline snapshots. | `POST /v1/baselines`, `GET /v1/baselines/{project_id}`, `GET /v1/baselines/{project_id}/diff` |
| Telemetry Service | Ingests telemetry payloads for observability. | `POST /v1/telemetry/ingest` |
| Realtime Coedit Service | Manages collaborative document editing sessions. | `POST /v1/sessions`, `GET /v1/sessions/{session_id}`, `GET /v1/ws/documents/{document_id}` |
| Workflow Service | Workflow execution, gate evaluation, and audit recording. | `POST /v1/workflows`, `GET /v1/workflows/{workflow_id}` |

## How it's used

Services are discovered by `tools/component_runner` and deployed via Helm and Terraform resources under `ops/infra/`.

## How to run / develop / test

List services and run one locally:

```bash
python -m tools.component_runner list --type service
python -m tools.component_runner run --type service --name audit-log --dry-run
```

## Configuration

Services use shared `.env` settings plus service-specific env vars documented in each service README.

## Troubleshooting

- Service not listed: ensure the service folder exists under `services/`.
- Startup errors: confirm database and external service endpoints are reachable.

## Generated API docs (source of truth)

Service endpoint documentation is generated from FastAPI route decorators and published under [`docs/generated/services/`](../docs/generated/services/).

- Index: [`docs/generated/services/README.md`](../docs/generated/services/README.md)
- Regenerate: `python ops/tools/codegen/generate_docs.py`
