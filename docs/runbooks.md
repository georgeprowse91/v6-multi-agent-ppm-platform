# Runbooks

> Operational runbooks for the multi-agent PPM platform — covering deployment, on-call procedures, monitoring, incident response, disaster recovery, secret management, and local development.

## Contents

- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [On-Call Guide](#on-call-guide)
- [Monitoring and Dashboards](#monitoring-and-dashboards)
- [SLOs and SLIs](#slos-and-slis)
- [Incident Response](#incident-response)
- [Troubleshooting](#troubleshooting)
- [LLM Degradation](#llm-degradation)
- [Data Sync Failures](#data-sync-failures)
- [Backup and Recovery](#backup-and-recovery)
- [Disaster Recovery](#disaster-recovery)
- [Secret Initialisation](#secret-initialisation)
- [Secret Rotation](#secret-rotation)
- [Schema Promotion and Rollback](#schema-promotion-and-rollback)
- [Credential Acquisition](#credential-acquisition)
- [Docker Compose Profiles](#docker-compose-profiles)

## Quick Start

This section describes how to spin up a local stack (API gateway, orchestration service, workflow service, and backing services) and run a deterministic end-to-end scenario. The scenario exercises the intent router, orchestration layer, three domain agents, and workflow persistence.

### Prerequisites

- Docker Desktop (or Docker Engine + docker compose plugin)
- Python 3.11+ (optional, for running the smoke script locally)
- `make`

### Preflight checks

- Confirm Docker is running: `docker ps`
- Confirm ports are free: `8000`, `8080`, and `8501`
- Create `.env` from the environment template for local defaults: `cp .env.example .env`

### Start the local stack

```bash
cp .env.example .env
make dev-up
```

> **Warning:** `ops/config/.env.example` is for local development only. Never use these values in CI, staging, or production.

### Startup order and failure behaviour

Docker Compose uses health-gated startup for dependent services:

1. `db` and `redis` start first and must report healthy.
2. `api` waits for healthy `db` and healthy `redis`.
3. `workflow-service` starts independently and must report healthy.
4. `web` waits for both `api` and `workflow-service` to be healthy.

Health checks are intentionally lightweight and deterministic:

- `db`: `pg_isready`
- `redis`: `redis-cli ping`
- `api`, `workflow-service`, `web`: local `GET /healthz` probes from inside each container

Failure behaviour expectations:

- If `db` or `redis` is unhealthy, `api` does not transition to running.
- If `api` or `workflow-service` is unhealthy, `web` does not transition to running.
- A service becoming unhealthy after startup does not automatically restart dependents; use `docker compose ps` and `docker compose logs <service>` for diagnosis.
- Verify dependency health with `docker compose ps` before running migrations or smoke flows.

### Apply database migrations

The orchestration service stores workflow state in Postgres. Apply migrations after the database container is healthy:

```bash
DATABASE_URL=${DATABASE_URL:-postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:5432/$POSTGRES_DB} alembic upgrade head
```

The default dev stack enables auth dev mode and a mock LLM response for deterministic routing. The stack exposes:

- API gateway: `http://localhost:8000`
- Workflow engine: `http://localhost:8080`
- Web console: `http://localhost:8501`

### Run the end-to-end scenario

The scenario uses:

- API gateway auth dev mode
- Intent router + response orchestration
- Portfolio strategy, financial management, and risk management agents
- Workflow engine persistence

#### Step 1 — Post a workflow run (workflow service)

```bash
curl -sS -X POST "http://localhost:8080/v1/workflows/start" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant" \
  -d @examples/demo-scenarios/quickstart-workflow.json | jq
```

Expected output:

- `status` should be `running`
- `workflow_id` should be `portfolio-intake`

#### Step 2 — Run the multi-agent query (API gateway)

```bash
curl -sS -X POST "http://localhost:8000/v1/query" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant" \
  -d @examples/demo-scenarios/quickstart-request.json | jq
```

Expected output:

- `success: true`
- `data.execution_summary.total_agents: 3`
- Agent results include:
  - `portfolio-optimisation-agent`
  - `financial-management-agent`
  - `risk-management-agent`

#### Step 3 — Verify health endpoints

```bash
curl -sS http://localhost:8000/healthz | jq
curl -sS http://localhost:8080/healthz | jq
```

Optional: verify service-level health when running individual services directly by using their configured port and `/healthz` endpoint.

### Stop the stack

```bash
make dev-down
```

### Notes

- To override the deterministic routing response, set `LLM_MOCK_RESPONSE_PATH` to a custom JSON file that matches the intent router response schema.
- Auth dev mode is enabled with `AUTH_DEV_MODE=true` (default in docker-compose for local development). In production, disable it and configure JWT validation. CI/prod must use environment-specific secrets, not local defaults from `ops/config/.env.example`.
- The orchestration service reads `ORCHESTRATION_STATE_BACKEND` (set to `db` in docker-compose) and `ORCHESTRATION_DATABASE_URL`/`DATABASE_URL` to select the durable Postgres store. Ensure database encryption-at-rest features are enabled in your environment and use optional app-level envelope encryption hooks if you integrate them later.

---

## Deployment

This runbook defines pre-deployment, deployment, and post-deployment procedures for the Multi-Agent PPM platform. It aligns release execution with the operational controls described in the monitoring, incident response, and backup/disaster recovery runbooks.

### Related runbooks and artefacts

- Monitoring and Dashboards
- Incident Response
- Backup and Recovery
- Disaster Recovery
- Troubleshooting Guide
- Release Process

### Roles and responsibilities

- **Release manager:** Owns the go/no-go decision, scheduling window, and stakeholder communications.
- **Platform engineer:** Executes infrastructure and Helm deployments.
- **Service owner(s):** Validates service-specific smoke tests and business-critical flows.
- **SRE/on-call:** Monitors telemetry during and after rollout; handles escalation.
- **Security/compliance approver:** Confirms required approvals for regulated changes.

### Pre-deployment procedure

#### 1. Change and readiness gates

- [ ] Approved change record includes scope, risk, rollback, and validation plan.
- [ ] Release notes include schema changes, config changes, and dependency updates.
- [ ] CI is green for lint, tests, and policy checks on the release commit/tag.
- [ ] Environment freeze windows, blackout dates, and stakeholder notifications confirmed.

#### 2. Environment health checks

- [ ] `GET /healthz` and readiness endpoints pass in target environment.
- [ ] Error budget and latency are within SLO bounds before deployment.
- [ ] No unresolved Sev-1/Sev-2 incidents impacting target services.
- [ ] Queue depths, worker lag, and connector sync health are nominal.

#### 3. Data and platform safety checks

- [ ] PostgreSQL backup and restore point validated within the last 24 hours.
- [ ] Redis persistence snapshot status verified.
- [ ] Audit log pipeline and immutable storage are healthy.
- [ ] Key Vault secrets and certificate expirations verified.

#### 4. Deployment package validation

- [ ] Container images are signed, scanned, and promoted from trusted registry.
- [ ] Helm chart versions and value overrides reviewed for environment parity.
- [ ] Feature flag default states reviewed (especially for high-risk changes).
- [ ] DB migrations reviewed for ordering, lock risk, and rollback compatibility.

### Deployment procedure

#### Phase A: Prepare release

1. Create and verify the release tag/commit.
2. Announce the start of deployment in the release channel with owner, scope, and ETA.
3. Enable enhanced monitoring annotations/dashboards for the change window.

#### Phase B: Apply infrastructure changes

1. Run `terraform plan` and review drift/risk.
2. Apply Terraform for approved infrastructure changes.
3. Verify cloud resources reach the expected provisioning state.

#### Phase C: Apply application changes

1. Run database migrations.
2. Deploy services using Helm in dependency order:
   - identity
   - policy/authorization
   - core API services
   - workflow/orchestration
   - agent services
   - connector services
   - edge/API gateway
3. For production, use canary or phased rollout where supported.
4. Keep the old replica set available until smoke tests complete.

#### Phase D: Smoke and functional checks

- [ ] API liveness/readiness endpoints pass.
- [ ] Authentication/login succeeds.
- [ ] Core create/read/update workflow succeeds.
- [ ] Audit events and telemetry ingestion succeed.
- [ ] At least one connector sync job completes.

#### Phase E: Live monitoring during rollout

- [ ] Watch error rate, p95 latency, saturation, and queue depth.
- [ ] Track deployment-specific alerts and trace anomalies.
- [ ] Record checkpoints at 5, 15, and 30 minutes after cutover.

### Rollback procedure

Initiate rollback if any of the following occur: sustained error budget burn, failed critical user journey, irreversible migration issue, or a Sev-1/Sev-2 triggered by the release.

1. Declare rollback in the release/incident channel.
2. Halt further rollout waves.
3. Roll back Helm releases to the previous stable revision.
4. Revert feature flags and config toggles changed during rollout.
5. If required, execute DB recovery per the Backup and Recovery runbook.
6. Re-run smoke tests and confirm service stabilisation.
7. Capture the timeline, impact, and corrective actions in the incident report.

### Post-deployment procedure

#### Immediate validation (0–60 minutes)

- [ ] All critical dashboards healthy (availability, latency, errors, saturation).
- [ ] No increase in failed workflows, dead letters, or connector backlogs.
- [ ] No authz/authn regressions for core roles.
- [ ] Audit logs and compliance events continue without gap.

#### Extended validation (24 hours)

- [ ] No recurring alerts tied to release changes.
- [ ] Business KPIs and throughput remain within expected ranges.
- [ ] Support tickets triaged for release-related trends.
- [ ] Release outcomes documented and shared with stakeholders.

### Deployment checklist (quick reference)

**Pre-deployment**

- [ ] Change approved and risk assessed.
- [ ] CI and security gates passed.
- [ ] Backup and restore point verified.
- [ ] Rollback steps rehearsed/confirmed.

**Deployment**

- [ ] Infra updates applied.
- [ ] Migrations executed.
- [ ] Services rolled out in dependency order.
- [ ] Smoke tests passed.

**Post-deployment**

- [ ] Monitoring stable after rollout.
- [ ] Validation completed at 60 minutes and 24 hours.
- [ ] Stakeholder notification sent.
- [ ] Follow-up actions logged.

---

## On-Call Guide

This section provides detailed guidance for operating the multi-agent PPM platform in production. It covers monitoring and logging, backup and disaster-recovery strategies, and support procedures to ensure smooth, reliable service. It should be used by operations, DevOps, and support teams to manage the platform across SaaS, private-cloud, and on-premises deployments.

### 1. Monitoring and Logging

#### 1.1 Centralised telemetry

**Azure Monitor and Application Insights:** All microservices and agents must emit structured logs and metrics (requests, dependencies, errors, durations) to Azure Monitor. Use Azure Application Insights for distributed tracing across the multi-agent orchestration layer and downstream connectors. Ensure each agent includes correlation IDs so traces can be stitched end-to-end.

**Reliability and resilience:** Azure Monitor's ingestion pipeline validates that each log record is successfully processed before removing it from the pipeline and will buffer and retry sending logs if the Log Analytics workspace is temporarily unavailable. Create Log Analytics workspaces in regions that support availability zones so logs are replicated across independent datacentres; if one zone fails, Azure automatically switches to another without manual intervention. For cross-regional protection, enable workspace replication or continuous export to a geo-redundant storage account.

**Alerting and dashboards:** Define health and performance metrics for each agent (for example, average response time, error rate, queue length, and throughput). Configure Azure Monitor alerts for threshold breaches (for example, >2% error rate, memory >80%, or unprocessed messages). Use real-time dashboards to visualise key indicators such as agent throughput, API latency, and connector health.

**Retention and archival:** Retain operational logs in Log Analytics for at least 30 days for active troubleshooting. Export audit and security logs to a geo-redundant storage account for long-term retention (seven years or more) to meet compliance requirements. Use Azure Data Explorer or Data Factory to analyse archived logs when investigating incidents.

**Data privacy:** Ensure logs do not contain sensitive customer data. Pseudonymise identifiers where possible and enforce proper role-based access for log viewing.

#### 1.2 Synthetic monitoring

**Heartbeat checks:** Implement health endpoints for each microservice and agent. Use Azure Monitor or an external tool (such as Pingdom or New Relic) to perform periodic GET requests to health endpoints. Alerts should trigger if an endpoint returns an error or does not respond.

**End-to-end scenarios:** Configure synthetic transactions that simulate critical user journeys (for example, creating a new project or running portfolio optimisation) through the UI. Run these tests regularly to detect regressions early.

#### 1.3 Audit logging

**Event recording:** Record all administrative actions (for example, configuration changes, role assignments, agent activation/deactivation) and critical user actions (for example, approvals and financial adjustments). Store audit logs in a secure, tamper-evident workspace and maintain at least seven years of retention to satisfy regulatory obligations.

**Log analysis:** Use automated rules to flag suspicious patterns (for example, repeated failed logins or mass data exports). Route high-severity events to Security Operations for investigation.

### 2. Backup and Disaster Recovery

#### 2.1 Backup strategy

**Incremental backups and automation:** Azure Backup performs incremental backups, saving only changes since the last backup and reducing storage costs. Use automated backup management to schedule backups and enforce retention policies. A well-defined strategy should include regular backups, retention rules, and routine testing.

**Retention policies:** Define retention schedules (for example, daily backups retained for 30 days, weekly for 90 days, monthly for 12 months) to balance compliance and cost. Use Azure Policy to enforce consistent backup configurations and automatically remediate non-compliant resources.

**Data encryption and security:** Ensure backup data is encrypted at rest and in transit. If required, use customer-managed keys. Enable multi-factor authentication to protect backup management interfaces and use role-based access control to enforce least-privilege access.

**Geo-redundancy:** Configure geo-redundant or geo-zone-redundant storage for backups so that copies of data are stored in a second region. Azure Backup automatically stores copies in different locations to protect against regional outages.

**Performance optimisation:** Use throttling and parallel processing to ensure that backup operations do not impact production workloads. Enable data deduplication to reduce storage and network utilisation.

#### 2.2 Disaster-recovery planning

**RPO and RTO targets:** Define Recovery Point Objectives (RPO) and Recovery Time Objectives (RTO) for each subsystem (for example, <15 minutes of data loss and 1 hour recovery for critical services). Use these targets to design replication and failover strategies.

**Azure Site Recovery (ASR):** Use ASR to replicate workloads (VMs, databases) to a secondary region, providing automated failover and failback. Regularly test failover procedures to ensure the DR plan works as expected and that staff can execute it under pressure.

**Cross-regional log replication:** For log data, enable workspace replication or continuous export to a geo-replicated storage account, ensuring logs and monitoring continue during a regional outage.

**Service resilience:** Deploy redundant instances of the orchestrator, agents, and connectors across availability zones. Use load balancers with health probes to route traffic to healthy instances. Test failure scenarios to verify that services fail over gracefully.

**Data store replication:** Use managed databases (Azure SQL, Cosmos DB) configured with geo-replication. For on-premises deployments, implement database mirroring or Always On groups.

**Disaster event runbook:** Document steps for declaring a disaster, failing over to the secondary region, communicating with stakeholders, and failing back once the primary region is restored.

### 3. Support Procedures and Runbook Framework

#### 3.1 Runbook principles

**Documented procedures:** A runbook is a documented process that guides teams through performing specific tasks or achieving desired outcomes. Runbooks provide step-by-step instructions for operational tasks such as deploying updates, troubleshooting incidents, or configuring infrastructure. They should be simple, clear, and actionable so that tasks are completed correctly by anyone.

**Reduce operational risk:** Standardised runbooks reduce risk by ensuring that processes are repeatable and consistent, minimising errors during critical tasks such as incident response or system changes.

**Checklists:** Runbooks include checklists to ensure that no step is missed during routine procedures (system maintenance, deployments).

**Coverage areas:** In cloud operations, runbooks should cover infrastructure deployment, incident response, and maintenance tasks. They should also include business continuity tasks such as backup restoration and DR failover.

#### 3.2 Incident management process

**Detection and triage:** Monitoring systems generate alerts when thresholds are breached or anomalies are detected. The support engineer classifies the incident severity and begins triage.

**Response and mitigation:** Follow the relevant runbook to investigate logs, metrics, and traces; reproduce the issue; apply immediate remediation (restart service, scale resources, roll back deployment); and document actions taken.

**Escalation:** If the incident cannot be resolved within the defined response time, involve the on-call engineer, development lead, or vendor support. Use defined escalation paths and include business stakeholders when service level objectives are at risk.

**Communication:** Provide timely, clear, and actionable communications to affected users and management. Use status pages and channels such as Teams or Slack. For major incidents, provide regular updates until resolution.

**Post-incident review:** Within 48 hours, conduct a blameless retrospective to identify root causes and improvement actions. Update runbooks, playbooks, and tests accordingly.

#### 3.3 Roles and responsibilities

**Operations engineer:** Executes runbooks for incident response, system maintenance, and deployments. Contributes to runbook improvements based on operational experience.

**DevOps engineer:** Develops and maintains runbooks for critical infrastructure operations. Automates runbook procedures where possible and ensures documentation is up to date.

**Incident responder:** Uses runbooks during incident response to ensure necessary steps are taken and updates runbooks based on lessons learned.

**Support lead:** Owns the incident management process, coordinates communication, and ensures that service level objectives are met. Responsible for overall service health metrics and continuous improvement.

### 4. Operational Procedures

#### 4.1 Deployments

**Pre-deployment checks:** Validate infrastructure templates, configuration parameters, secrets, and environment readiness. Ensure code has passed all automated tests and that monitoring and alerting are in place.

**Deployment execution:** Use CI/CD pipelines to deploy microservices and agents. Deployments should be automated, version-controlled, and use blue/green or canary strategies to minimise impact. Monitor metrics during deployment and be prepared to roll back if issues arise.

**Post-deployment validation:** Run smoke tests to verify functionality. Confirm that dashboards, alerts, and integrations are functioning. If performance or error rates degrade, initiate rollback.

#### 4.2 Maintenance and patching

Schedule regular maintenance windows (for example, monthly) to apply security patches and update underlying infrastructure. Use automated configuration management (such as Azure Automation or Ansible) to reduce manual work.

Document standard maintenance tasks (for example, scaling database throughput or updating OS patches) in runbooks.

#### 4.3 Backup and restore procedures

**Backup verification:** Use periodic test restores to verify that backups are valid and usable. Conduct at least quarterly full restores in a staging environment.

**On-demand backups:** Prior to major upgrades or schema changes, trigger an on-demand backup. Document the process to request and validate such backups.

**Restore process:** Provide runbooks for restoring individual items (single file, database table) and for full environment recovery. Include steps to validate data integrity and ensure dependencies (indexes, triggers) are restored.

#### 4.4 Disaster-recovery procedures

**Failover:** When a disaster is declared, execute the DR runbook: verify that replication is up to date, switch traffic to the secondary region (DNS or traffic manager), bring up services and applications, and confirm health via synthetic testing.

**Failback:** After the primary region is restored, plan a maintenance window to replicate data back, test primary services, and gradually switch traffic back.

**Testing:** Conduct DR drills at least twice annually to ensure readiness. Review results, adjust procedures, and update runbooks.

### 5. Continuous Improvement and Knowledge Management

**Runbook updates:** Maintain a runbook update log to record changes, reasons, and dates. Encourage team members to propose improvements based on incident learnings and new technologies.

**Training:** Provide regular training on runbooks and DR procedures. Conduct tabletop exercises for critical scenarios.

**Metrics and feedback:** Measure mean time to detect (MTTD), mean time to respond (MTTR), backup success rate, restore time, and incident volume. Use these metrics to prioritise improvements.

**Knowledge base:** Integrate runbooks with a knowledge management system and ensure they are easily discoverable. Document common issues, root causes, and remediation steps.

---

## Monitoring and Dashboards

This section describes the dashboards used to monitor production health.

### Primary dashboards

- **SLO Dashboard:** `ops/infra/observability/dashboards/ppm-slo.json` — latency, error rate, and availability panels.
- **Alert overview:** `ops/infra/observability/alerts/ppm-alerts.yaml` — alert rules tied directly to SLOs.
- **Tracing view:** OpenTelemetry traces for end-to-end workflow execution.
- **Connector health:** Monitors sync lag, error rates, and job throughput across all connectors.

### Usage guidelines

- Validate dashboards before release cutover.
- During incidents, capture dashboard snapshots for the postmortem record.
- Ensure dashboard access is limited to on-call and operations roles.

### Dashboard validation checklist

- [ ] SLO panels show live metrics.
- [ ] Alert rules are enabled and routed to on-call.
- [ ] Trace sampling is configured for critical endpoints.
- [ ] Connector health dashboard shows job success rates.

---

## SLOs and SLIs

### Purpose

Define service-level objectives (SLOs) and the service-level indicators (SLIs) used to monitor the platform.

### Scope

- API Gateway (`services/api-gateway`)
- Orchestration Service (`services/orchestration-service`)
- Workflow Service (`services/workflow-service`)
- Data Sync Service (`services/data-sync-service`)
- Audit Log Service (`services/audit-log`)

### Core SLIs

| SLI | Definition | Source |
| --- | --- | --- |
| Availability | Successful responses / total requests | HTTP request metrics via `packages/observability` |
| Latency (P95) | 95th percentile response time for critical endpoints | Metrics middleware in each service |
| Error rate | 5xx responses / total responses | HTTP request metrics |
| Queue freshness | Age of queued sync jobs | Data Sync Service status store |
| Workflow completion | Completed runs / total runs | Workflow engine status store |

### Suggested SLO targets

These targets are aligned with the SLO template in `docs/templates/quality/slo-alert-definition-cross.yaml` and should be adjusted per deployment.

- **Availability:** 99.9% over 30 days for API Gateway and Workflow Service.
- **Latency (P95):** < 750 ms for `/v1/query` and `/v1/workflows/start` over 7 days.
- **Error rate:** < 0.5% 5xx responses for core APIs.
- **Queue freshness:** 95% of sync jobs start within 5 minutes of enqueue.

### Instrumentation sources

- **HTTP metrics:** `packages/observability` middleware emits request counters and latency histograms.
- **Workflow metrics:** The workflow engine exposes status state; use scheduled checks to compute completion ratios.
- **Audit metrics:** The audit log emits ingestion counters and error counts.

### Operational guidance

1. Create an SLO definition per service using the template at `docs/templates/quality/slo-alert-definition-cross.yaml`.
2. Store the finalised SLO spec in your deployment repository or monitoring system.
3. Link each SLO to the relevant runbooks (incident response, data sync failures, LLM degradation).

### Verification steps

Inspect the SLO template:

```bash
sed -n '1,160p' docs/templates/quality/slo-alert-definition-cross.yaml
```

Confirm metrics middleware is registered:

```bash
rg -n "RequestMetricsMiddleware" apps services | head -n 20
```

### Implementation status

- **Implemented:** Metrics middleware in services and apps.
- **Implemented:** Grafana dashboards and error budget alerts in `ops/infra/observability/dashboards` and `ops/infra/observability/alerts`.

### Related docs

- Observability Architecture
- Runbook: Incident Response
- Runbook: LLM Degradation

---

## Incident Response

This section outlines incident response steps, severity definitions, and escalation procedures for the PPM platform.

### Severity levels

| Severity | Description | Response Time | Escalation |
| --- | --- | --- | --- |
| SEV-1 | Platform outage, data loss, security breach | 15 minutes | Immediate exec notification |
| SEV-2 | Major functionality degraded | 30 minutes | Manager notification within 1 hour |
| SEV-3 | Partial degradation or single service issue | 4 hours | Team lead notification |

### RTO/RPO reference

| Service | RTO | RPO | Priority |
| --- | --- | --- | --- |
| API Gateway | 15 minutes | N/A | Critical |
| Workflow Service | 30 minutes | 5 minutes | Critical |
| Data Service | 1 hour | 15 minutes | High |
| Audit Log | 2 hours | 0 minutes (WORM) | High |
| Analytics | 4 hours | 30 minutes | Medium |

### Escalation matrix

| Role | Contact Method | When to Escalate |
| --- | --- | --- |
| On-call Engineer | PagerDuty | All alerts |
| Platform Lead | Slack + Phone | SEV-1/2 unresolved > 30 min |
| Engineering Manager | Phone | SEV-1 unresolved > 1 hour |
| VP Engineering | Phone | SEV-1 with data loss or security breach |
| Legal/Compliance | Email + Phone | Security breach affecting customer data |

### Immediate response steps

#### 1. Acknowledge the alert (within SLA)

```bash
# Check current alerts
az monitor metrics alert list --resource-group ppm-production

# View Application Insights live metrics
# Navigate to: Azure Portal > Application Insights > Live Metrics
```

- Confirm alert severity and affected service.
- Start an incident bridge (Slack: `#incident-response`).
- Create an incident ticket with initial details.
- Assign an Incident Commander (IC) role.

#### 2. Triage

```bash
# Check service health
kubectl get pods -n ppm-platform
kubectl describe pod <pod-name> -n ppm-platform

# View recent logs
kubectl logs -n ppm-platform -l app=ppm-api --tail=100

# Check Application Insights for errors
az monitor app-insights query --app ppm-production-appinsights \
  --analytics-query "exceptions | where timestamp > ago(15m) | summarize count() by problemId"
```

- Review service dashboards in Grafana/Azure Monitor.
- Confirm tenant impact and scope.
- Document affected services and estimated user impact.

#### 3. Containment

```bash
# Rollback to previous deployment
kubectl rollout undo deployment/ppm-api -n ppm-platform

# Scale down problematic service
kubectl scale deployment/ppm-api --replicas=0 -n ppm-platform

# Enable maintenance mode (if available)
kubectl set env deployment/ppm-api MAINTENANCE_MODE=true -n ppm-platform
```

- Disable failing deployments or rollback.
- Isolate compromised credentials.
- Block malicious IPs if under attack.

#### 4. Mitigation

```bash
# Scale out services
kubectl scale deployment/ppm-api --replicas=10 -n ppm-platform

# Apply hotfix
kubectl set image deployment/ppm-api api=ghcr.io/org/ppm-api:hotfix-v1.2.3 -n ppm-platform

# Verify deployment
kubectl rollout status deployment/ppm-api -n ppm-platform
```

- Apply a hotfix or scale out services.
- Route traffic to a healthy region if needed.
- Implement temporary workarounds.

#### 5. Communication

| Audience | Channel | Frequency |
| --- | --- | --- |
| Internal Team | Slack #incident-response | Every 15 minutes |
| Stakeholders | Email | Every 30 minutes |
| Customers (SEV-1/2) | Status Page | Every 30 minutes |
| Executive | Email + Slack | Major updates only |

**Status update template:**

```
INCIDENT UPDATE - [SEV-X] [Service Name]
Time: [UTC timestamp]
Status: [Investigating/Identified/Monitoring/Resolved]
Impact: [Description of user impact]
Current Actions: [What we're doing]
ETA to Resolution: [Estimate or "Under investigation"]
Next Update: [Time]
```

#### 6. Resolution

```bash
# Verify service health
curl -f https://api.ppm-platform.com/v1/health

# Check error rates returned to normal
az monitor app-insights query --app ppm-production-appinsights \
  --analytics-query "requests | where timestamp > ago(15m) | summarize count() by resultCode"

# Validate data integrity
python ops/scripts/validate-data-integrity.py --tenant-id <affected-tenant>
```

- Confirm metrics return to SLO targets.
- Validate tenant isolation and RBAC integrity.
- Remove any temporary workarounds.
- Update the status page to "Resolved".

#### 7. Post-incident

- [ ] Create a postmortem document within 24 hours.
- [ ] Schedule a postmortem meeting within 5 business days.
- [ ] Identify root cause and contributing factors.
- [ ] Create action items with owners and due dates.
- [ ] Update runbooks based on learnings.
- [ ] Close the incident ticket with a summary.

### Common incident playbooks

#### Database connection pool exhaustion

1. Check current connections: `SELECT count(*) FROM pg_stat_activity;`
2. Identify long-running queries: `SELECT * FROM pg_stat_activity WHERE state = 'active' ORDER BY query_start;`
3. Kill problematic queries if necessary.
4. Scale up the connection pool or add read replicas.
5. Review application connection handling.

#### Agent execution failures

1. Check orchestrator logs for error patterns.
2. Verify LLM provider (Azure OpenAI) status.
3. Check rate limits and quotas.
4. Review recent agent configuration changes.
5. Restart affected agent pods if necessary.

#### Authentication service degradation

1. Verify Azure AD/Okta status.
2. Check JWT signing key validity.
3. Review OIDC discovery endpoint availability.
4. Verify identity service pod health.
5. Check for expired certificates.

#### High memory usage / OOM kills

1. Identify affected pods: `kubectl top pods -n ppm-platform`
2. Check for memory leaks in recent deployments.
3. Review request patterns for unusual load.
4. Increase memory limits temporarily.
5. Roll back if caused by a recent deployment.

### Security incident addendum

#### Immediate actions (within 15 minutes)

1. **Isolate affected systems**

   ```bash
   # Block external access if needed
   kubectl patch networkpolicy deny-all -n ppm-platform
   ```

2. **Preserve evidence**
   - Do not delete or modify logs.
   - Take snapshots of affected systems.
   - Document the timeline of events.

3. **Rotate compromised credentials**

   ```bash
   # Rotate secrets in Key Vault
   az keyvault secret set --vault-name ppm-keyvault --name <secret-name> --value <new-value>

   # Force pod restart to pick up new secrets
   kubectl rollout restart deployment -n ppm-platform
   ```

#### Notification requirements

| Condition | Notify | Timeline |
| --- | --- | --- |
| PII exposure | Legal, DPO | Immediately |
| GDPR data breach | Supervisory Authority | Within 72 hours |
| Customer data access | Affected customers | As required by contract |

#### Post-security incident checklist

- [ ] Conduct forensic analysis.
- [ ] Document attack vector and remediation.
- [ ] Validate audit log integrity and retention policies.
- [ ] Perform tenant impact assessment.
- [ ] Update threat model and security controls.
- [ ] Notify compliance team and complete required filings.

---

## Troubleshooting

This section covers common operational issues and how to resolve them.

### Authentication failures

**Symptoms:** `401`/`403` responses, JWT validation errors.

**Checks:**

- Confirm the Key Vault secret for the JWT signing key.
- Verify `IDENTITY_ISSUER` and `IDENTITY_AUDIENCE` values.
- Validate clock skew between services.

### Workflow failures

**Symptoms:** Workflows stuck in `running` or `failed` state.

**Checks:**

- Inspect workflow service logs for exceptions.
- Ensure Postgres connectivity and that migrations are current.
- Verify queue backlogs are draining.

### Connector sync issues

**Symptoms:** Connector jobs fail, no data ingested.

**Checks:**

- Validate connector credentials in Key Vault.
- Confirm network reachability to external APIs.
- Inspect connector job logs in the telemetry dashboard.

### Elevated latency

**Symptoms:** p95 latency exceeds the SLO.

**Checks:**

- Review the SLO dashboard for error rate spikes.
- Inspect database CPU and connection pool saturation.
- Scale API gateway pods and confirm autoscaling is active.

### Backup/restore anomalies

**Symptoms:** Backup job alerts, restore failures.

**Checks:**

- Verify storage account health and immutability policy.
- Confirm retention job logs for the audit log pipeline.
- Run the DR validation checklist if in doubt.

### Escalation

If an issue persists beyond 30 minutes, engage the on-call lead and open an incident per the [On-Call Guide](#on-call-guide).

---

## LLM Degradation

This section provides a structured framework for gathering feedback, analysing performance, identifying improvement opportunities, and implementing changes in a controlled manner when continuous improvement or LLM-driven processes exhibit degradation. It leverages the Continuous Improvement and Process Mining Agent and the Knowledge and Document Management Agent to create a closed loop of learning and refinement.

### Guiding principles

**Data-driven decision-making:** Collect quantitative and qualitative data to understand how projects, portfolios, and the platform itself perform. Use metrics such as cycle time, on-time completion, resource utilisation, and realised benefits to prioritise improvement initiatives.

**Closed-loop feedback:** Capture feedback from users, agents, and stakeholders through surveys, retrospectives, performance dashboards, and operational metrics. Feed insights into the backlog and change-management processes.

**Process transparency:** Visualise end-to-end processes using process-mining techniques, revealing actual flows, bottlenecks, and deviations from expected paths. Compare against methodology-embedded process flows for adaptive, predictive, and hybrid projects.

**Iterative and incremental:** Prioritise small, high-impact improvements. Use MVP experiments, A/B testing, and feature flags to validate assumptions before wider rollout.

**Cross-functional collaboration:** Involve stakeholders from PMO, technology, finance, risk, and end users in identifying issues and designing solutions. Align improvements with strategic goals and compliance requirements.

### Process mining and analysis

The Continuous Improvement and Process Mining Agent uses event logs, trace data, and agent telemetry to reconstruct actual workflows.

**Event collection:** Capture timestamped events from project activities, agent interactions, approvals, risk escalations, and schedule updates. Use correlation IDs to connect events across agents and systems (as recommended in the observability strategy). Ensure logs are enriched with context (user, project, phase, system).

**Process discovery:** Apply process-mining algorithms (such as Alpha+ or heuristic mining) to derive process models that represent observed flows. Identify frequent patterns, deviations, and outliers.

**Bottleneck detection:** Analyse waiting times and throughput at each stage. Highlight areas where approvals take longest, resources are over-allocated, or tasks frequently return to a previous state.

**Compliance checking:** Compare actual sequences to methodology-defined process flows (adaptive, predictive, hybrid) to detect violations (for example, phase gates skipped or unapproved scope changes). Flag potential governance breaches for review.

**Root-cause analysis:** Correlate issues with contributing factors (team workload, skill gaps, external dependencies, integration failures). Use Pareto analysis to identify the small number of causes driving the majority of delays.

### Continuous improvement cycle

**Identify opportunities:** Through process-mining reports, retrospectives, surveys, and metrics dashboards. Capture improvement ideas in a central backlog managed by the PMO.

**Prioritise:** Evaluate impact, urgency, and feasibility. Align with strategic objectives, compliance requirements, and resource availability.

**Design solutions:** Propose changes to processes, agent behaviours, integrations, or tooling. Engage relevant agents (for example, Project Lifecycle and Governance, Approval Workflow) to understand dependencies and user-experience impacts.

**Plan and implement:** Schedule improvements into sprints or releases. Use feature flags or pilot groups to reduce risk. Update documentation, training materials, and governance artefacts as necessary.

**Validate and measure:** Define success metrics (for example, reduction in cycle time, improvement in on-time delivery, adoption rate). Monitor performance through dashboards and analytics tools. Conduct user surveys and focus groups.

**Document and share:** Capture lessons learned, including what worked and what did not. Update knowledge bases via the Knowledge Management agent to ensure organisational learning.

**Repeat:** Feed results back into the backlog, closing the loop.

### Key metrics and KPIs

To track improvement over time, measure:

- **Cycle time:** Average time from project initiation to completion, broken down by phase.
- **Lead time:** Time from demand submission to approval and resource commitment.
- **Delivery predictability:** Percentage of projects delivered within schedule and budget baselines.
- **Resource utilisation:** Average percentage of resources' capacity used versus planned.
- **Approval turnaround:** Average time for approvals (for example, budget, scope, change) per gate.
- **Risk response time:** Time between risk identification and mitigation action.
- **Quality defects:** Number of defects or non-conformities detected during quality checks.
- **User satisfaction:** Survey scores for user interface, assistance quality, and overall experience.

These metrics should be configured in dashboards accessible to relevant stakeholders. They serve as triggers for deeper analysis when thresholds are exceeded.

### Integration with governance and compliance

Continuous improvement must operate within the boundaries defined by the governance and compliance plan. When implementing changes:

**Assess regulatory impact:** Perform privacy and security impact assessments for changes that affect data processing, access controls, or retention. Ensure compliance with data-classification rules and retention periods.

**Update policies:** Amend relevant policies (for example, change management, incident response) to reflect new processes. Communicate changes via training and governance channels.

**Audit trail:** Record decisions, approvals, and implementation steps. Ensure logs capture feature-flag activations, configuration changes, and deployment details for auditability.

### Tools and automation

**Process-mining tooling:** Integrate off-the-shelf process-mining tools or build custom pipelines leveraging event logs and agent telemetry. Use visual dashboards to present discovered processes and bottlenecks.

**Kanban and backlog management:** Track improvement initiatives in backlog boards (such as Azure DevOps or Jira). Tag items with improvement categories (compliance, performance, UX) and link to metrics.

**Automation and AI:** Use AI capabilities (LLMs, anomaly detection) to suggest process optimisations, detect patterns, and generate improvement ideas automatically. Configure the Continuous Improvement agent to propose potential changes when it identifies recurring inefficiencies.

### Organisational adoption

**Change champions:** Designate champions in each department to advocate for continuous improvement and serve as liaisons between teams and the PMO.

**Training and awareness:** Educate users on how improvement data is collected and how to interpret process-mining visualisations. Encourage participation in retrospectives and feedback sessions.

**Recognition and rewards:** Recognise teams that actively contribute to process improvements and share lessons with the wider organisation.

---

## Data Sync Failures

Restore connector syncs when jobs back up, fail, or produce partial data.

### Scope

- Data Sync Service (`services/data-sync-service`)
- Connector runtimes (`connectors/*/src`)
- Data quality and lineage artifacts (`data/quality/`, `data/lineage/`)

### Symptoms

- `/v1/sync/run` responses remain in `queued` or `planned` status.
- Connector-specific mappings are missing or invalid.
- Lineage artifacts are missing or contain redacted fields unexpectedly.

### Immediate checks

1. **Service health**
   ```bash
   curl -sS http://localhost:8080/healthz
   ```
2. **Inspect job status store**
   ```bash
   cat services/data-sync-service/storage/status.json
   ```
3. **Review configured rules**
   ```bash
   ls services/data-sync-service/rules
   ```

### Diagnostics

#### 1) Validate connector configuration

- Confirm the connector is enabled in `ops/config/connectors/integrations.yaml`.
- Ensure manifest and mapping files exist (e.g., `connectors/jira/manifest.yaml`).

#### 2) Validate mappings

- Check mapping YAML targets against canonical schemas in `data/schemas/`.
- Run a dry-run mapping with the connector runtime (example for Jira):
  ```bash
  python -m integrations.connectors.jira.src.main connectors/jira/tests/fixtures/projects.json --tenant dev-tenant
  ```

#### 3) Validate queue configuration

- If using Azure Service Bus, confirm `SERVICE_BUS_CONNECTION_STRING` and `SERVICE_BUS_QUEUE` are set.
- If not set, the service falls back to an in-memory queue (suitable only for local development).

#### 4) Validate lineage masking

- Lineage payloads are masked by `packages/security` before returning status.
- Confirm masking rules in `packages/security/src/security/lineage.py` align with classification settings.

### Remediation steps

- **Missing mappings:** Create or update mapping YAMLs under `connectors/<name>/mappings/` and re-run the sync.
- **Queue misconfiguration:** Set Service Bus environment variables or use local mode for development.
- **Invalid schema targets:** Update mapping targets to match `data/schemas/*.schema.json`.
- **Backlogged jobs:** Delete stale entries in `services/data-sync-service/storage/status.json` and re-trigger `/v1/sync/run`.

### Verification

- Trigger a sync run:
  ```bash
  curl -sS -X POST http://localhost:8080/v1/sync/run \
    -H "Content-Type: application/json" \
    -H "X-Tenant-ID: dev-tenant" \
    -d '{"connector":"jira","dry_run":true}' | jq
  ```
- Confirm status updates:
  ```bash
  curl -sS http://localhost:8080/v1/sync/status/<job_id> -H "X-Tenant-ID: dev-tenant" | jq
  ```

### Escalation

Escalate to the integration owner if:

- Mapping changes require schema updates.
- Connector auth credentials are invalid and require rotation.
- Service Bus connectivity is unstable or throttling.

### Related docs

- Connector Overview
- Data Quality
- Data Lineage

---

## Backup and Recovery

This section describes backup configuration, retention schedules, and recovery procedures for the Multi-Agent PPM platform.

### Scope

- **PostgreSQL** (primary transactional datastore)
- **Redis** (queue and cache data)
- **Audit Log WORM Storage**
- **Configuration and secrets** (Key Vault)

### Backup schedule and retention

| Component | Backup method | Frequency | Retention | Storage |
| --- | --- | --- | --- | --- |
| PostgreSQL | Azure Database for PostgreSQL automated backups | Continuous + nightly snapshots | 35 days | Geo-redundant storage (GRS) |
| Redis | Azure Redis persistence | Hourly | 7 days | Geo-redundant storage (GRS) |
| Audit Log | WORM storage with retention policies | Real-time ingestion | Per `ops/config/retention/policies.yaml` | Immutable blob container |
| Kubernetes manifests | GitOps (repository) | Per release | Git history | GitHub |

### Automated backups

- **Azure Database for PostgreSQL:** automated backups enabled with point-in-time restore and geo-redundant storage.
- **Redis:** persistence configured with scheduled snapshots.
- **Audit log:** continuous export to immutable storage with retention policies.
- **Validation automation:** `tests/test_backup_runbook.py` validates runbook requirements and retention policies.

### Pre-requisites

- Access to the Azure subscription and resource group.
- Azure Key Vault permissions to retrieve service credentials.
- Terraform backend configured for the target environment.

### Backup verification

1. **PostgreSQL**
   - Confirm backups exist in Azure Portal (Backups > Automated backups).
   - Ensure the latest snapshot is within the last 24 hours.
2. **Redis**
   - Validate persistence status via Redis configuration in Azure Portal.
   - Confirm backups are healthy with the last persistence time.
3. **Audit Log**
   - Validate WORM storage container immutability policy is enabled.
   - Run retention enforcement job and confirm no errors.

### Recovery procedures

#### 1. PostgreSQL restore

##### Option A: Point-in-Time Restore (Preferred)

```bash
# List available restore points
az postgres flexible-server backup list \
  --resource-group ppm-production \
  --name ppm-postgresql

# Restore to a specific point in time
az postgres flexible-server restore \
  --resource-group ppm-production \
  --name ppm-postgresql-restored \
  --source-server ppm-postgresql \
  --restore-time "2024-01-15T10:00:00Z"

# Verify the restored server is ready
az postgres flexible-server show \
  --resource-group ppm-production \
  --name ppm-postgresql-restored \
  --query "state"
```

##### Option B: Geo-Restore (Disaster Recovery)

```bash
# Restore from geo-redundant backup to a different region
az postgres flexible-server geo-restore \
  --resource-group ppm-dr \
  --name ppm-postgresql-dr \
  --source-server /subscriptions/<sub-id>/resourceGroups/ppm-production/providers/Microsoft.DBforPostgreSQL/flexibleServers/ppm-postgresql \
  --location "West US 2"
```

##### Post-Restore Steps

1. Update connection string in Key Vault:
   ```bash
   az keyvault secret set \
     --vault-name ppm-keyvault \
     --name database-url \
     --value "postgresql://user:pass@ppm-postgresql-restored.postgres.database.azure.com:5432/ppm"
   ```

2. Run database migrations:
   ```bash
   alembic upgrade head
   ```

3. Restart services to pick up the new connection:
   ```bash
   kubectl rollout restart deployment -n ppm-platform
   ```

4. Validate data integrity:
   ```bash
   python ops/scripts/validate-data-integrity.py --full-scan
   ```

#### 2. Redis restore

##### Option A: Restore from RDB Snapshot

```bash
# Check available snapshots
az redis export \
  --resource-group ppm-production \
  --name ppm-redis \
  --prefix backup \
  --container "https://ppmbackups.blob.core.windows.net/redis-backups"

# Import from snapshot
az redis import \
  --resource-group ppm-production \
  --name ppm-redis \
  --files "https://ppmbackups.blob.core.windows.net/redis-backups/backup.rdb"
```

##### Option B: Create New Redis Instance

If the Redis instance is corrupted, create a new one:

```bash
# Create new Redis instance
az redis create \
  --resource-group ppm-production \
  --name ppm-redis-new \
  --location "East US" \
  --sku Premium \
  --vm-size P1

# Update connection string in Key Vault
az keyvault secret set \
  --vault-name ppm-keyvault \
  --name redis-url \
  --value "rediss://ppm-redis-new.redis.cache.windows.net:6380?password=<access-key>"
```

##### Post-Restore Validation

```bash
# Test Redis connectivity
redis-cli -h ppm-redis.redis.cache.windows.net -p 6380 -a <password> --tls ping

# Check keyspace info
redis-cli -h ppm-redis.redis.cache.windows.net -p 6380 -a <password> --tls info keyspace
```

Restart dependent services:
```bash
kubectl rollout restart deployment/ppm-api -n ppm-platform
kubectl rollout restart deployment/ppm-data-sync -n ppm-platform
```

#### 3. Audit log restore

Audit logs are stored in WORM (Write Once Read Many) immutable storage and cannot be modified or deleted until the retention period expires.

##### Verify Immutability

```bash
# Check immutability policy
az storage container immutability-policy show \
  --account-name ppmauditlogs \
  --container-name audit-worm

# List audit log blobs
az storage blob list \
  --account-name ppmauditlogs \
  --container-name audit-worm \
  --query "[].{name:name, lastModified:properties.lastModified}" \
  --output table
```

##### Restore Access to Audit Logs

If the audit log service cannot access storage:

1. Verify managed identity permissions:
   ```bash
   az role assignment list \
     --assignee <managed-identity-object-id> \
     --scope /subscriptions/<sub-id>/resourceGroups/ppm-production/providers/Microsoft.Storage/storageAccounts/ppmauditlogs
   ```

2. Re-grant access if needed:
   ```bash
   az role assignment create \
     --role "Storage Blob Data Reader" \
     --assignee <managed-identity-object-id> \
     --scope /subscriptions/<sub-id>/resourceGroups/ppm-production/providers/Microsoft.Storage/storageAccounts/ppmauditlogs
   ```

3. Verify encryption keys in Key Vault are accessible.

#### 4. Kubernetes recovery

##### Full Cluster Recovery

```bash
# Re-apply Terraform infrastructure
cd ops/infra/terraform
terraform init
terraform plan -out=recovery.tfplan
terraform apply recovery.tfplan

# Verify AKS cluster is ready
az aks show \
  --resource-group ppm-production \
  --name ppm-aks \
  --query "provisioningState"

# Get credentials
az aks get-credentials \
  --resource-group ppm-production \
  --name ppm-aks \
  --overwrite-existing
```

##### Deploy Services

```bash
# Apply namespace and security policies
kubectl apply -f ops/infra/kubernetes/manifests/

# Deploy platform services using Helm
helm dependency update ops/infra/kubernetes/helm-charts/ppm-platform
helm upgrade --install ppm-platform ops/infra/kubernetes/helm-charts/ppm-platform \
  --namespace ppm-platform \
  --create-namespace \
  -f ops/infra/kubernetes/helm-charts/ppm-platform/values-production.yaml

# Verify all pods are running
kubectl get pods -n ppm-platform
kubectl wait --for=condition=ready pod -l app=ppm-api -n ppm-platform --timeout=300s
```

#### 5. Complete disaster recovery

For a complete site failure, restore components in this order:

1. **Infrastructure**: Apply Terraform to recreate all Azure resources.
2. **Database**: Geo-restore PostgreSQL from the secondary region.
3. **Redis**: Create a new instance (cache data will rebuild automatically).
4. **Secrets**: Restore Key Vault from backup or recreate secrets.
5. **Kubernetes**: Deploy all services.
6. **DNS**: Update DNS to point to new endpoints.
7. **Validation**: Run full system validation.

```bash
# Full DR recovery script
./ops/scripts/disaster-recovery.sh --region "West US 2" --env production
```

### Post-recovery validation checklist

#### Critical Services
- [ ] API Gateway `/healthz` responds with `200`
- [ ] API Gateway `/v1/health/ready` responds with `200`
- [ ] Workflow engine can resume workflows
- [ ] Orchestration service accepts new requests

#### Data Layer
- [ ] PostgreSQL connections successful from all services
- [ ] Database migrations are current (`alembic current`)
- [ ] Project records can read/write the `benefits_realisation_plan` field
- [ ] Project records can read/write the `regulatory_category` field (`low|medium|high`)
- [ ] Redis connectivity verified
- [ ] Data sync queues are draining

#### Security and Compliance
- [ ] Authentication flow working (test login)
- [ ] RBAC permissions enforced correctly
- [ ] Audit log events are immutable and retrievable
- [ ] Tenant isolation verified

#### Integration
- [ ] Connector sync jobs executing
- [ ] Webhook notifications firing
- [ ] Analytics jobs can list manifests

#### Performance
- [ ] Response times within SLA
- [ ] No elevated error rates
- [ ] HPA scaling correctly

### Backup testing schedule

| Test Type | Frequency | Owner | Last Tested |
| --- | --- | --- | --- |
| PostgreSQL PITR restore | Quarterly | Platform Team | - |
| Redis snapshot restore | Quarterly | Platform Team | - |
| Full DR failover | Annually | Platform + SRE | - |
| Audit log access verification | Monthly | Compliance | - |

### Automation hooks

- **Retention enforcement:** `services/audit-log/src/retention_job.py`
- **Schema validation:** `ops/scripts/validate-schemas.py`
- **Placeholder checks:** `ops/scripts/check-placeholders.py`
- **Data integrity validation:** `ops/scripts/validate-data-integrity.py`
- **Disaster recovery:** `ops/scripts/disaster-recovery.sh`
- **Backup verification:** `tests/test_backup_runbook.py`

---

## Disaster Recovery

This section outlines DR planning, RTO/RPO targets, and recovery steps for the Multi-Agent PPM platform.

### Recovery objectives

| Component | RTO | RPO | Notes |
| --- | --- | --- | --- |
| API Gateway + UI | 1 hour | 15 minutes | Stateless services behind load balancer. |
| Workflow Service | 2 hours | 30 minutes | Requires workflow state DB recovery. |
| Audit Log (WORM) | 4 hours | 0 minutes | Immutable storage with geo-redundancy. |
| Data Sync Service | 2 hours | 30 minutes | Resume from Service Bus checkpoints. |

### Preconditions

- Latest Terraform state available in remote backend.
- Backup snapshots for Postgres, Redis, and blob storage retained per policy.
- DR environment credentials stored in Azure Key Vault.

### Recovery steps

1. **Declare DR event**
   - Notify on-call lead and incident commander.
   - Open DR ticket and record incident timeline.
2. **Assess impact**
   - Confirm region outage or data corruption scope.
   - Identify affected services and data domains.
3. **Restore infrastructure**
   - Apply Terraform in DR region using remote backend.
   - Validate Service Bus, Key Vault, and Storage Accounts.
4. **Restore databases**
   - Restore Postgres snapshot to DR instance.
   - Validate schema using `alembic upgrade head` if required.
5. **Restore workflow state**
   - Validate workflow service DB and resume pending workflows.
   - Replay audit events for in-flight workflows if needed.
6. **Rehydrate audit log**
   - Verify WORM container immutability policies.
   - Validate encryption keys and retention policies.
7. **Cutover traffic**
   - Update DNS or Traffic Manager to DR endpoints.
   - Monitor health checks and SLO dashboards.
8. **Post-recovery validation**
   - Run smoke tests and end-to-end workflows.
   - Confirm telemetry ingestion to Azure Monitor.
9. **Postmortem**
   - Document root cause, remediation steps, and follow-up actions.

### Validation checklist

- [ ] API gateway `/healthz` responds with `200`.
- [ ] Workflow engine can start and resume workflows.
- [ ] Audit log ingestion returns `202` and events are immutable.
- [ ] Telemetry pipeline exports to Azure Monitor.
- [ ] Data sync queue backlog has drained.

### DR testing procedures

Run a DR drill at least twice per year or after major infrastructure changes.

1. Provision a DR sandbox environment in the secondary region.
2. Restore the latest backups to the DR environment.
3. Execute smoke and end-to-end tests (`pytest tests/e2e`).
4. Validate SLAs under load (`pytest tests/load`).
5. Document outcomes, issues, and remediation tasks.

---

## Secret Initialisation

This section documents how to bootstrap secrets for new environments.

### Scope

- Azure Key Vault secrets
- Kubernetes SecretProviderClass configuration
- Service principal credentials for CI/CD

### Initial bootstrap

1. **Create Key Vault**
   - Provision Key Vault via Terraform (`ops/infra/terraform/main.tf`).
2. **Create secret namespace**
   - Use a dedicated prefix per environment (e.g., `prod-`, `staging-`).
3. **Seed baseline secrets**
   - Database connection strings
   - Redis connection strings
   - JWT signing keys and JWKS URL
   - Connector API credentials (Jira, ServiceNow, Azure DevOps)
4. **Configure Kubernetes CSI driver**
   - Apply `ops/infra/kubernetes/secret-provider-class.yaml`.
   - Verify workloads mount secrets at runtime.
   - Ensure the workload identity service account in `ops/infra/kubernetes/service-account.yaml` is annotated with the Key Vault client ID and tenant ID.
   - Confirm pods are labeled with `azure.workload.identity/use: "true"` for AKS workload identity.

### Secret naming and mount conventions

- **Key Vault secret names** should match the filenames expected under `/mnt/secrets-store`.
- **Mount path**: the CSI driver mounts secrets to `/mnt/secrets-store/<secret-name>`.
- **Config references** must use file references, for example:
  - `file:/mnt/secrets-store/identity-client-secret`
  - `file:/mnt/secrets-store/jira-api-token`
- **Local development** can use environment variable placeholders instead of files:
  - `env:IDENTITY_CLIENT_SECRET`
  - `${JIRA_API_TOKEN}`

### Provisioning steps (AKS + Key Vault)

1. **Create/verify Key Vault secrets**
   - Add secrets for endpoints, identity, observability, and connector credentials using the same names referenced in `ops/config/environments/prod.yaml`.
2. **Apply SecretProviderClass**
   - Ensure `ops/infra/kubernetes/secret-provider-class.yaml` lists the secret names to mount.
3. **Deploy workloads**
   - The CSI driver mounts secrets to `/mnt/secrets-store` and optionally syncs them to Kubernetes Secrets via `secretObjects`.

### Validation

- `kubectl describe pod` shows CSI mount ready.
- API gateway `/v1/status` returns `healthy`.
- Identity service can validate JWTs using Key Vault-backed secrets.

### Rotation readiness

- Ensure each secret has an owner, rotation schedule, and alternate version.
- Verify alerting for Key Vault access failures.
- Rotate by updating the Key Vault secret value and restarting pods (or wait for the CSI rotation interval).

---

## Secret Rotation

This section defines procedures for rotating secrets safely across all environments.

### Rotation cadence

- **JWT signing keys:** every 90 days.
- **Database credentials:** every 180 days or upon personnel change.
- **Connector API tokens:** every 90 days.
- **Service principals:** every 180 days.
- **Automated rotation:** a weekly CronJob (`0 3 * * 0`) in the `ppm` namespace rotates all Key Vault secrets and restarts deployments to pick up new values.

### Automation workflow

- **CronJob:** `ops/infra/kubernetes/secret-rotation-cronjob.yaml` runs `mcr.microsoft.com/azure-cli:latest` with the `ppm-admin` service account.
- **Script ConfigMap:** `ops/infra/kubernetes/secret-rotation-scripts.yaml` mounts `rotate_secrets.sh` at `/scripts`.
- **Rotation behaviour:** the script replaces every Key Vault secret with a new 32-byte hex value and triggers rollouts for workflow-service, notification-service, data-service, policy-engine, identity-access, telemetry-service, and audit-log deployments.

### Rotation process

1. **Generate new secret value** in Azure Key Vault.
2. **Stage the new secret** alongside the existing version.
3. **Update configuration** to reference the new version (Key Vault version pin or updated secret name).
4. **Roll deployments** to pick up new secrets.
5. **Validate** authentication, connectors, and workflows.
6. **Revoke old secret** after validation completes.

### Validation checks

- API `/v1/status` returns `healthy`.
- Connector sync jobs authenticate successfully.
- Audit log events continue to ingest.

### Emergency rotation

- Trigger immediate rotation if a compromise is suspected.
- Notify the security team and update the incident record.
- Force logout of all user sessions if JWT signing keys are rotated.

### Tracking

- Record rotation date, owner, and next due date in the secrets inventory.
- Use Key Vault access logs to confirm rotation success.

---

## Schema Promotion and Rollback

Provide a safe, repeatable rollback path when a promoted schema version causes ingestion or downstream processing failures in staging or production environments.

### Triggers

- Spike in `4xx/5xx` responses on data-service ingest endpoints after a schema promotion.
- Validation errors indicating incompatible payloads for recently promoted schema versions.
- Consumer failures in analytics or workflow systems tied to new schema fields.

### Preconditions

1. Identify the impacted schema and promoted version (`<schema>@<bad_version>`).
2. Identify the last known good promoted version (`<schema>@<good_version>`).
3. Confirm blast radius (environments, tenants, connector feeds).

### Rollback procedure

1. **Freeze new promotions and ingesters**
   - Pause promotion pipelines and disable scheduled ingest jobs for impacted connectors.
2. **Re-promote last known good version**
   - Execute:
     - `POST /v1/schemas/<schema>/versions/<good_version>/promote`
     - Body: `{ "environment": "<env>" }`
3. **Validate environment promotion records**
   - Verify `GET /v1/schemas/<schema>/promotions` includes `<good_version>` for `<env>` as the latest effective promotion.
4. **Replay or repair failed ingests**
   - Re-run failed connector sync jobs and inspect validation error counts.
5. **Communicate incident status**
   - Update the incident channel and status page with rollback completion and current ingestion status.

### Verification checklist

- Ingestion for the impacted schema succeeds in `<env>`.
- Error budget burn rate returns to baseline.
- No new incompatible payload errors for `<schema>`.
- Monitoring dashboards reflect healthy throughput and latency.

### Post-incident actions

- Open a follow-up PR to fix the schema change with compatible evolution.
- Update `data/schemas/examples/<schema>.json` with corrective payload snapshots.
- Add or expand compatibility tests in `services/data-service/tests/`.

---

## Credential Acquisition

This section explains how operators obtain credentials required to deploy and operate the platform.

### Azure access

1. Request Azure subscription access through the access management portal.
2. Ensure you have `Contributor` and `Key Vault Secrets Officer` roles for the target resource group.
3. Verify access:
   ```bash
   az account show
   az keyvault secret list --vault-name <vault-name>
   ```

### CI/CD service principal

1. Create a service principal scoped to the resource group:
   ```bash
   az ad sp create-for-rbac \
     --name "ppm-cicd" \
     --role contributor \
     --scopes /subscriptions/<subscription-id>/resourceGroups/<rg>
   ```
2. Store the output in the CI secrets vault (`AZURE_CREDENTIALS`).
3. Grant Key Vault access for secret retrieval.

### Database credentials

- Retrieve database connection strings from Key Vault.
- Validate connectivity using `psql` or application health checks.

### Connector credentials

- **Jira:** create an API token under your Atlassian account and store it in Key Vault.
- **ServiceNow:** create an integration user with read permissions.
- **Azure DevOps:** create a PAT with `Project & Team` read scopes.

### OIDC and SCIM provisioning credentials

1. Register an OIDC application in your IdP (Okta, Entra ID, Auth0, etc.).
2. Configure the redirect URI: `https://<web-host>/oidc/callback`.
3. Add custom claims:
   - `tenant_id` (string) for tenant routing.
   - `roles` (array/string) for RBAC role mapping.
4. Store the client secret in the secrets vault:
   - `OIDC_CLIENT_SECRET` (use an env/file reference in the runtime config).
5. Generate a long-lived SCIM provisioning token and store it in the secrets vault:
   - `SCIM_SERVICE_TOKEN` (use an env/file reference in the runtime config).
6. Distribute the SCIM base URL and token to the IdP provisioning connector:
   - `https://<identity-access-host>/scim/v2`
7. Rotate `SCIM_SERVICE_TOKEN` by issuing a new token, updating the secret reference, restarting `identity-access`, and updating the IdP connector with the new bearer token.

### Least privilege checklist

- [ ] Remove unused credentials after onboarding.
- [ ] Audit access quarterly.
- [ ] Enforce MFA for interactive accounts.

---

## Docker Compose Profiles

This section documents deterministic local stack startup using Compose profiles:

- `demo`: smallest UX-centric stack for product demos.
- `core`: core platform stack for local development.
- `full`: all first-class app and service processes currently implemented in `apps/*/src/main.py` and `services/*/src/main.py`.

### Profile startup order

Compose enforces health-gated `depends_on` links. The effective startup sequence is:

1. `db`, `redis`
2. Foundational APIs: `workflow-service`, `identity-access`, `data-service`
3. Domain/core APIs: `api`, `orchestration-service`, `policy-engine`, `document-service`, `audit-log`, `notification-service`
4. Extended/full APIs (full profile only): `analytics-service`, `data-lineage-service`, `data-sync-service`, `telemetry-service`, `agent-runtime`, `auth-service`, `realtime-coedit-service`
5. `web`

### Services and ports by profile

#### demo profile

| Service | Host port | Container port | Health endpoint |
|---|---:|---:|---|
| api | 8000 | 8000 | `/healthz` |
| workflow-service | 8080 | 8080 | `/healthz` |
| web | 8501 | 8501 | `/healthz` |
| db | 5432 | 5432 | `pg_isready` |
| redis | 6379 | 6379 | `redis-cli ping` |

#### core profile

Includes all `demo` services, plus:

| Service | Host port | Container port | Health endpoint |
|---|---:|---:|---|
| identity-access | 8081 | 8080 | `/healthz` |
| data-service | 8082 | 8080 | `/healthz` |
| policy-engine | 8083 | 8080 | `/healthz` |
| notification-service | 8084 | 8080 | `/healthz` |
| audit-log | 8085 | 8080 | `/healthz` |
| orchestration-service | 8087 | 8080 | `/healthz` |
| document-service | 8088 | 8080 | `/healthz` |

#### full profile

Includes all `core` services, plus:

| Service | Host port | Container port | Health endpoint |
|---|---:|---:|---|
| analytics-service | 8086 | 8080 | `/healthz` |
| data-lineage-service | 8089 | 8080 | `/healthz` |
| data-sync-service | 8090 | 8080 | `/healthz` |
| telemetry-service | 8091 | 8080 | `/healthz` |
| agent-runtime | 8092 | 8080 | `/healthz` |
| auth-service | 8093 | 8080 | `/healthz` |
| realtime-coedit-service | 8094 | 8080 | `/healthz` |

### Startup commands

```bash
# demo stack
COMPOSE_PROFILES=demo docker-compose --profile demo up --build -d

# core stack (default dev target)
make dev-up

# full stack
make dev-up-full
```

### Readiness validation

#### Compose-level health

```bash
docker-compose ps
```

```bash
docker-compose ps --format json | jq -r '. | "\(.Name)\t\(.State)\t\(.Health)"'
```

#### HTTP health checks

```bash
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8080/healthz
curl -fsS http://localhost:8501/healthz
```

Core additions:

```bash
curl -fsS http://localhost:8081/healthz
curl -fsS http://localhost:8082/healthz
curl -fsS http://localhost:8083/healthz
curl -fsS http://localhost:8084/healthz
curl -fsS http://localhost:8085/healthz
curl -fsS http://localhost:8087/healthz
curl -fsS http://localhost:8088/healthz
```

Full additions:

```bash
curl -fsS http://localhost:8086/healthz
curl -fsS http://localhost:8089/healthz
curl -fsS http://localhost:8090/healthz
curl -fsS http://localhost:8091/healthz
curl -fsS http://localhost:8092/healthz
curl -fsS http://localhost:8093/healthz
curl -fsS http://localhost:8094/healthz
```

### Shutdown

```bash
make dev-down
```
