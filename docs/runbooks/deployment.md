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
   - Execute `/healthz` and `/v1/status` checks.
   - Confirm `POST /v1/audit/events` and `POST /v1/telemetry/ingest` respond with success.
5. **Validate monitoring**
   - Confirm metrics, traces, and alerts are flowing in Azure Monitor.
6. **Notify stakeholders**
   - Share deployment completion in the release channel with a rollback plan.

## Environment-specific deployment plan

### Development
- Deploy during business hours to allow quick validation.
- Run smoke tests (`/healthz`, `/v1/status`) and verify connector registry UI loads.
- Validate MCP connector routing against a non-production MCP server endpoint.

### Staging
- Use production-like configuration, secrets, and OAuth credentials.
- Run full regression suite and MCP routing tests before promotion.
- Validate monitoring dashboards, alert rules, and MCP fallback metrics.

### Production
- Obtain release manager + security lead approval and change ticket closure.
- Follow canary or phased rollout for MCP-enabled connectors when possible.
- Monitor error budgets, MCP request latency, and fallback counts during the rollout window.

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
