# Resilience Architecture

## Purpose

Describe the failure modes, fallback strategies, and recovery mechanisms for the platform.

## Architecture-level context

Resilience covers agent orchestration, connector sync, data availability, and AI model dependencies. It informs runbooks in `docs/runbooks/` and the System Health agent’s alerting policies.

## Failure modes and mitigations

| Failure mode | Mitigation | Owner |
| --- | --- | --- |
| Connector API outage | Circuit breakers open after repeated failures; fallback response returned | API Gateway |
| LLM service degradation | Use cached responses; require human approval | Orchestrator (02) |
| Data store failure | Scheduled backups + restore procedures; read-only mode | Platform Ops |
| Queue backlog | Shed non-critical jobs; prioritize gates | Workflow Engine (24) |

## LLM degradation modes

- **Degraded**: disable optional agent calls, return summaries.
- **Read-only**: prevent writes and require manual approvals.
- **Offline**: pause orchestration and rely on runbooks.

## Active-passive failover

The API gateway and orchestration service run two replicas in Kubernetes with active-passive semantics. A ConfigMap-backed leader election loop assigns one pod as the active leader, while the passive replica remains hot-standby. Readiness probes point to leader-aware endpoints so only the active pod receives traffic.

- **Leader election:** ConfigMap lock (`*-leader`) updated by the service pods.
- **Failover:** If the leader stops renewing, the passive pod acquires the lock and becomes active.
- **Probe behavior:** Passive pods return non-ready status to keep them out of service endpoints.

## Circuit breakers

Connector interactions are protected by an in-memory circuit breaker in the API gateway. Repeated connector failures open the circuit for the configured recovery window, returning a fallback response until a successful probe closes the circuit again.

- **Failure threshold:** 3 consecutive failures (configurable).
- **Recovery timeout:** 60 seconds (configurable).
- **Fallback:** `circuit_open` response for connector tests and webhooks.

## DR and backup strategy

PostgreSQL and Redis backups run as Kubernetes CronJobs with encrypted object storage uploads (see `ops/infra/kubernetes/manifests/backup-jobs.yaml`). The jobs create an on-demand dump and push it to a secured bucket using credentials stored in Kubernetes Secrets (`postgres-credentials`, `redis-credentials`, `backup-credentials`).

| Store | Schedule (UTC) | CronJob | Storage |
| --- | --- | --- | --- |
| PostgreSQL | 02:00 daily | `postgres-backup` | S3-compatible bucket with server-side encryption |
| Redis | 03:00 daily | `redis-backup` | S3-compatible bucket with server-side encryption |

### Restore procedure

1. **Fetch backup artifacts** from the secure bucket (e.g., `s3://<bucket>/<prefix>/postgres/<date>/ppm-platform.dump` and `s3://<bucket>/<prefix>/redis/<date>/redis.rdb`).
2. **Restore PostgreSQL** with `pg_restore --clean --dbname=<db> ppm-platform.dump`.
3. **Restore Redis** by stopping Redis, replacing the `dump.rdb` file, and restarting the service.
4. **Validate** application connectivity and run smoke tests from the deployment runbook.

## Usage example

Review the LLM degradation runbook:

```bash
sed -n '1,160p' docs/runbooks/llm-degradation.md
```

## How to verify

Confirm resilience runbooks exist:

```bash
ls docs/runbooks
```

Expected output includes `incident-response.md` and `disaster-recovery.md`.

## Implementation status

- **Implemented**: active-passive failover, circuit breakers, and scheduled backups.

## Related docs

- [Observability Architecture](observability-architecture.md)
- [Performance Architecture](performance-architecture.md)
- [Incident Response Runbook](../runbooks/incident-response.md)
