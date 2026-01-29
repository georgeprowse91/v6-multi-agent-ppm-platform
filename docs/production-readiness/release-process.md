# Release Process

## Purpose

Document the end-to-end release workflow for the Multi-Agent PPM Platform, including governance
checks, tagging, and post-release validation.

## Release cadence & ownership

- **Cadence:** monthly minor releases with weekly patch releases as needed.
- **Owners:** Release manager (operations), security lead, product owner.

## Versioning

- Follow **semantic versioning** (`MAJOR.MINOR.PATCH`).
- Update `CHANGELOG.md` before cutting a release tag.

## Pre-release checklist

1. **Backlog readiness**
   - Confirm approved scope and risk sign-offs.
   - Ensure documentation updates are merged.
2. **Quality gates**
   - CI pipeline green (lint, tests, security scans).
   - Coverage ≥ 80% for changed components.
3. **Security & compliance**
   - DPIA and threat model reviewed for material changes.
   - Secrets verified in Key Vault and rotated if required.
4. **Operational readiness**
   - Runbooks updated for new endpoints or workflows.
   - Monitoring dashboards and alerts validated.

## Release steps

1. **Prepare release branch**
   - Create a release branch: `release/vX.Y.Z`.
   - Update `CHANGELOG.md` and version references.
2. **Tag the release**
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```
3. **CI/CD automation**
   - `release.yml` builds artifacts, generates SBOM, signs, and verifies signatures.
   - Artifacts are published to the registry and attached to the release.
4. **Deploy to staging**
   - Use the [Deployment runbook](../runbooks/deployment.md).
   - Run smoke tests and verify dashboards.
5. **Promote to production**
   - Obtain approval from release manager and security lead.
   - Deploy with Helm in the documented service order.

## Post-release validation

- Confirm `/healthz` for API gateway, workflow engine, and core services.
- Verify audit log ingestion and retention policy execution.
- Validate telemetry ingestion and alerting.
- Notify stakeholders in the release channel with summary and rollback plan.

## Rollback guidance

- Identify last known good tag from deployment history.
- Roll back Helm releases to prior chart versions.
- Re-run smoke tests and verify SLO dashboards stabilize.

## Release documentation

- Update `CHANGELOG.md` with release notes.
- Store evidence in `docs/production-readiness/evidence-pack.md`.
