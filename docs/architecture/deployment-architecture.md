# Deployment Architecture

## Purpose

Explain how the platform is deployed across environments, how releases move through the pipeline, and how disaster recovery (DR) is handled.

## Architecture-level context

The deployment architecture maps the logical components into Azure environments with clear separation between dev, staging, and production. CI/CD uses GitHub Actions to build containers, run tests, and publish artifacts. Infrastructure-as-code lives under `ops/infra/`.

## Environment matrix

| Environment | Purpose | Data handling | Infra path |
| --- | --- | --- | --- |
| Dev | Engineer experimentation | Synthetic/seed data only | `ops/infra/terraform/envs/dev/` |
| Staging | Pre-prod validation | Sanitized data | `ops/infra/terraform/envs/stage/` |
| Production | Customer workloads | Live data with retention policies | `ops/infra/terraform/envs/prod/` |

## Release flow

1. **Build**: GitHub Actions builds Docker images from `apps/api-gateway/Dockerfile`.
2. **Validate**: unit tests + docs checks (`ops/scripts/check-links.py`, `ops/scripts/check-placeholders.py`).
3. **Deploy**: Terraform provisions infra, then Kubernetes manifests roll out services.

## Diagram

```text
PlantUML: docs/architecture/diagrams/deployment-overview.puml
```

## DR strategy

- Active-passive failover in a paired Azure region with scripted region flips.
- RPO target: 15 minutes; RTO target: 2 hours.
- Backups stored in geo-redundant storage with quarterly restore drills.

## Usage example

Show Terraform environments:

```bash
ls ops/infra/terraform
```

## How to verify

Inspect the Kubernetes deployment manifest:

```bash
sed -n '1,160p' ops/infra/kubernetes/deployment.yaml
```

Expected output: deployment spec with container image and env vars.

## Implementation status

- **Implemented**: CI pipeline, Dockerfiles, Terraform environment overlays, and DR failover scripts.

## Related docs

- [Container Runtime Identity Policy](container-runtime-identity-policy.md)
- [Physical Architecture](physical-architecture.md)
- [Runbooks](../runbooks/)
- [Infrastructure README](../../ops/infra/README.md)
