# Infrastructure

## Purpose

Document infrastructure resources under `infra/`.

## What's inside

- `infra/kubernetes`: Kubernetes manifests and chart metadata.
- `infra/observability`: Observability dashboards, alerts, and tracing config.
- `infra/policies`: Policy definitions enforced by the platform.
- `infra/terraform`: Terraform root modules and environment stacks.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
