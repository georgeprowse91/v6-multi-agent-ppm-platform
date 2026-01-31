# Services

## Purpose

Catalog backend services that power data sync, policy enforcement, and telemetry.

## What's inside

- `services/audit-log`: Subdirectory containing audit log assets for this area.
- `services/data-sync-service`: Subdirectory containing data sync service assets for this area.
- `services/data-lineage-service`: Subdirectory containing data lineage service assets for this area.
- `services/data-service`: Subdirectory containing data service assets for this area.
- `services/identity-access`: Subdirectory containing identity access assets for this area.
- `services/notification-service`: Subdirectory containing notification service assets for this area.
- `services/agent-runtime`: Subdirectory containing agent runtime assets for this area.
- `services/policy-engine`: Subdirectory containing policy engine assets for this area.
- `services/telemetry-service`: Subdirectory containing telemetry service assets for this area.
- `services/realtime-coedit-service`: Subdirectory containing real-time co-editing assets for this area.

## Service descriptions & endpoints

Each service runs a FastAPI application (default port `8080`) with health checks at `/healthz`.

| Service | Description | Primary endpoints |
| --- | --- | --- |
| Audit Log | Immutable audit trail with retention and WORM storage enforcement. | `POST /audit/events`, `GET /audit/events/{event_id}` |
| Agent Runtime | Hosts agent registry, orchestration, and connector integration for the platform. | `GET /agents`, `POST /agents/{agent_id}/execute`, `POST /orchestration/run` |
| Data Sync Service | Runs connector sync jobs, tracks status, and manages conflicts. | `POST /sync/run`, `GET /sync/status/{job_id}`, `GET /sync/conflicts` |
| Data Lineage Service | Captures lineage events and quality summaries. | `POST /lineage/events`, `GET /lineage/graph`, `GET /quality/summary` |
| Data Service | Manages schemas and canonical entities. | `POST /schemas`, `GET /schemas`, `POST /entities/{schema_name}` |
| Identity & Access | Validates auth tokens and supports SCIM provisioning. | `POST /auth/validate`, `POST /scim/v2/Users`, `GET /scim/v2/Groups` |
| Notification Service | Sends email/chat/webhook notifications. | `POST /notifications/send` |
| Policy Engine | Evaluates RBAC/ABAC policy decisions. | `POST /policies/evaluate`, `POST /rbac/evaluate`, `POST /abac/evaluate` |
| Telemetry Service | Ingests telemetry payloads for observability. | `POST /telemetry/ingest` |
| Realtime Coedit Service | Manages collaborative document editing sessions. | `POST /sessions`, `GET /sessions/{session_id}`, `GET /ws/documents/{document_id}` |

## How it's used

Services are discovered by `tools/component_runner` and deployed via Helm and Terraform resources under `infra/`.

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
