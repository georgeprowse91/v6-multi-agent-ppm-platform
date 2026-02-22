# Production Evidence Pack

## Purpose
This pack is a single source of truth for how to build, test, scan, deploy, and operate the
Multi-Agent PPM Platform in a production-ready manner.

## Build
```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
python -m build --sdist --wheel
```

## Test
```bash
make lint
make test-cov
python ops/scripts/validate-schemas.py
python ops/scripts/validate-manifests.py
python ops/scripts/quickstart_smoke.py
```

## Security & Compliance Scans
```bash
make secret-scan
python ops/scripts/generate-sbom.py
python ops/scripts/sign-artifact.py
python ops/scripts/verify-signature.py
```

CI also runs:
- Trivy filesystem scan (`.github/workflows/ci.yml`)
- License compliance (`.github/workflows/license-compliance.yml`)
- SAST/SCA workflows (`.github/workflows/security-scan.yml`)

## Release Process (Tag → Build → SBOM → Sign)
1. Update `CHANGELOG.md` and bump the version in `pyproject.toml`.
2. Tag the release: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`.
3. Push tags to trigger the release workflow.
4. `release.yml` builds artifacts, generates SBOM, signs, and verifies signatures.

## Deploy
### Kubernetes + Helm
```bash
helm dependency build ops/infra/kubernetes/helm-charts/ppm-platform
helm lint ops/infra/kubernetes/helm-charts/ppm-platform \
  --set audit-log.keyVault.name=kv-sample \
  --set audit-log.keyVault.tenantId=tenant-sample \
  --set audit-log.keyVault.clientId=client-sample
```

### Terraform
```bash
make tf-init
make tf-plan
make tf-apply
```

## Operate
- **Runbooks**: `docs/runbooks/` (incident response, backup/recovery, on-call, troubleshooting).
- **Monitoring**: `docs/runbooks/monitoring-dashboards.md`.
- **SLO/SLI**: `docs/runbooks/slo-sli.md`.

## Acceptance Criteria Checklist
- [x] CI gates: lint, typecheck, tests with coverage ≥ 80%.
- [x] Deterministic quickstart scenario (see `docs/runbooks/quickstart.md`).
- [x] Auth dev mode for local stack with RBAC enforcement.
- [x] Orchestration resilience (bounded concurrency, retries, timeouts, caching).
- [x] Release pipeline builds, generates SBOM, signs, and verifies artifacts.
- [x] Runbooks for incident response, backup/recovery, and DR.

## Housekeeping
- Legacy uplift trackers with all actions completed were removed:
  - `docs/production-readiness/PROGRAM_TRACKER.md`
  - `docs/production-readiness/FINALIZATION_TRACKER.md`
  - `docs/production-readiness/AGENT_UPGRADE_TRACKER.md`
