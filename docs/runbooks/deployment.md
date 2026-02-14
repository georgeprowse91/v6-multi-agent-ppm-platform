# Deployment Runbook

This runbook defines pre-deployment, deployment, and post-deployment procedures for the Multi-Agent PPM platform. It aligns release execution with the operational controls described in the monitoring, incident response, and backup/disaster recovery runbooks.

## Related runbooks and artefacts

- `docs/runbooks/monitoring-dashboards.md`
- `docs/runbooks/incident-response.md`
- `docs/runbooks/backup-recovery.md`
- `docs/runbooks/disaster-recovery.md`
- `docs/runbooks/troubleshooting.md`
- `docs/production-readiness/release-process.md`

## Roles and responsibilities

- **Release manager:** Owns go/no-go decision, scheduling window, and stakeholder comms.
- **Platform engineer:** Executes infrastructure and Helm deployments.
- **Service owner(s):** Validate service-specific smoke tests and business-critical flows.
- **SRE/on-call:** Monitors telemetry during and after rollout, handles escalation.
- **Security/compliance approver:** Confirms required approvals for regulated changes.

## Pre-deployment procedure

### 1. Change and readiness gates

- [ ] Approved change record includes scope, risk, rollback, and validation plan.
- [ ] Release notes include schema changes, config changes, and dependency updates.
- [ ] CI is green for lint, tests, and policy checks on the release commit/tag.
- [ ] Environment freeze windows, blackout dates, and stakeholder notifications confirmed.

### 2. Environment health checks

- [ ] `GET /healthz` and readiness endpoints pass in target environment.
- [ ] Error budget and latency are within SLO bounds before deployment.
- [ ] No unresolved Sev-1/Sev-2 incidents impacting target services.
- [ ] Queue depths, worker lag, and connector sync health are nominal.

### 3. Data and platform safety checks

- [ ] PostgreSQL backup and restore point validated within the last 24 hours.
- [ ] Redis persistence snapshot status verified.
- [ ] Audit log pipeline and immutable storage are healthy.
- [ ] Key Vault secrets and certificate expirations verified.

### 4. Deployment package validation

- [ ] Container images are signed, scanned, and promoted from trusted registry.
- [ ] Helm chart versions and value overrides reviewed for environment parity.
- [ ] Feature flags default states reviewed (especially for high-risk changes).
- [ ] DB migrations reviewed for ordering, lock risk, and rollback compatibility.

## Deployment procedure

### Phase A: Prepare release

1. Create and verify release tag/commit.
2. Announce start of deployment in release channel with owner, scope, and ETA.
3. Enable enhanced monitoring annotations/dashboards for the change window.

### Phase B: Apply infrastructure changes

1. Run `terraform plan` and review drift/risk.
2. Apply Terraform for approved infrastructure changes.
3. Verify cloud resources reach expected provisioning state.

### Phase C: Apply application changes

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
4. Keep old replica set available until smoke tests complete.

### Phase D: Smoke and functional checks

- [ ] API liveness/readiness endpoints pass.
- [ ] Authentication/login succeeds.
- [ ] Core create/read/update workflow succeeds.
- [ ] Audit events and telemetry ingestion succeed.
- [ ] At least one connector sync job completes.

### Phase E: Live monitoring during rollout

- [ ] Watch error rate, p95 latency, saturation, and queue depth.
- [ ] Track deployment-specific alerts and trace anomalies.
- [ ] Record checkpoints at 5, 15, and 30 minutes after cutover.

## Rollback procedure

Initiate rollback if any of the following occur: sustained error budget burn, failed critical user journey, irreversible migration issue, or Sev-1/Sev-2 triggered by the release.

1. Declare rollback in release/incident channel.
2. Halt further rollout waves.
3. Roll back Helm releases to the previous stable revision.
4. Revert feature flags/config toggles changed during rollout.
5. If required, execute DB recovery per `docs/runbooks/backup-recovery.md`.
6. Re-run smoke tests and confirm service stabilization.
7. Capture timeline, impact, and corrective actions in incident report.

## Post-deployment procedure

### Immediate validation (0-60 minutes)

- [ ] All critical dashboards healthy (availability, latency, errors, saturation).
- [ ] No increase in failed workflows, dead letters, or connector backlogs.
- [ ] No authz/authn regressions for core roles.
- [ ] Audit logs and compliance events continue without gap.

### Extended validation (24 hours)

- [ ] No recurring alerts tied to release changes.
- [ ] Business KPIs and throughput remain within expected ranges.
- [ ] Support tickets triaged for release-related trends.
- [ ] Release outcomes documented and shared with stakeholders.

## Deployment checklist (quick reference)

### Pre-deployment
- [ ] Change approved and risk assessed.
- [ ] CI and security gates passed.
- [ ] Backup and restore point verified.
- [ ] Rollback steps rehearsed/confirmed.

### Deployment
- [ ] Infra updates applied.
- [ ] Migrations executed.
- [ ] Services rolled out in dependency order.
- [ ] Smoke tests passed.

### Post-deployment
- [ ] Monitoring stable after rollout.
- [ ] Validation completed at 60 minutes and 24 hours.
- [ ] Stakeholder notification sent.
- [ ] Follow-up actions logged.
