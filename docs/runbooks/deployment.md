# Deployment Runbook

Operational runbook for deploying the Multi-Agent PPM Platform to production.

## Pre-deployment

1. Verify all CI checks pass on the release branch.
2. Confirm database migrations are up to date (`make migration-check`).
3. Validate environment configuration (`make env-validate`).
4. Review the release notes and changelog.
5. Notify stakeholders of the upcoming deployment window.

## Deployment Steps

1. Tag the release commit following semver conventions.
2. Trigger the CD pipeline via the `cd.yml` workflow.
3. Monitor the rolling update across Kubernetes pods.
4. Verify health endpoints return `status: ok` on all services.
5. Run smoke tests against the staging environment.

## Post-deployment

1. Confirm telemetry dashboards show normal traffic patterns.
2. Check error rates in the observability stack.
3. Validate connector integrations are operational.

## Rollback

If critical issues are detected after deployment:

1. Trigger rollback by re-deploying the previous Helm chart revision:
   ```bash
   helm rollback ppm-platform <previous-revision> -n ppm
   ```
2. Verify rollback health checks pass.
3. If database migrations were applied, run the corresponding downgrade migration.
4. Notify stakeholders of the rollback and open a post-incident review.
