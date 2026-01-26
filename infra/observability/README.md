# Observability Infrastructure

## Purpose

Document infrastructure resources under infra/observability.

## What's inside

- `infra/observability/alerts`: Alert definitions and thresholds.
- `infra/observability/dashboards`: Dashboard definitions for monitoring.
- `infra/observability/otel`: OpenTelemetry collector configs and docs.
- `infra/observability/slo`: Subdirectory containing slo assets for this area.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
