# Deployment Runbook

This runbook covers deployment procedures for the Multi-Agent PPM platform, including pre-flight checks,
release steps, and rollback guidance.

## Preconditions
- CI pipeline green (lint, unit/integration/e2e, coverage >= 80%).
- Change ticket approved and release notes published.
- Feature flags and configuration changes reviewed.
- Secrets present in Azure Key Vault and synced to Kubernetes.

## Pre-deployment checklist
- [ ] Confirm target environment is healthy (`/healthz`, SLO dashboards).
- [ ] Validate Terraform plan for infrastructure changes.
- [ ] Confirm Key Vault, Service Bus, and database connectivity.
- [ ] Ensure backup snapshot completed within last 24 hours.
- [ ] Confirm SBOM/signature workflow has completed for the release tag.

## Deployment steps
1. **Tag release**
   - Create a Git tag and attach release notes.
2. **Apply infrastructure updates**
   - Run Terraform in the target environment.
3. **Deploy services**
   - Use Helm to upgrade services in order: identity, policy engine, core services, API gateway, workflow engine, agents, connectors.
4. **Run smoke tests**
   - Execute `/healthz` and `/api/v1/status` checks.
   - Confirm `POST /audit/events` and `POST /telemetry/ingest` respond with success.
5. **Validate monitoring**
   - Confirm metrics, traces, and alerts are flowing in Azure Monitor.
6. **Notify stakeholders**
   - Share deployment completion in the release channel with a rollback plan.

## Rollback steps
1. Identify last known good release tag.
2. Roll back Helm releases to prior chart versions.
3. Revert configuration changes if necessary.
4. Re-run smoke tests and verify SLO dashboards stabilize.
5. Capture incident notes if rollback was required.

## Post-deployment validation
- [ ] E2E workflow tests pass.
- [ ] Key service dashboards show steady error rate/latency.
- [ ] Audit log ingestion verified.
- [ ] Incident channel notified of completion.
