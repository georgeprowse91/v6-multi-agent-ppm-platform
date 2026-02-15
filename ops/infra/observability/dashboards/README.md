# Dashboards Infrastructure

## Purpose

Document infrastructure resources under infra/observability/dashboards.

## What's inside

- [ppm-platform.json](/infra/observability/dashboards/ppm-platform.json): JSON data asset or configuration.
- [ppm-slo.json](/infra/observability/dashboards/ppm-slo.json): JSON data asset or configuration.
- [ppm-error-budget.json](/infra/observability/dashboards/ppm-error-budget.json): Error budget reporting dashboard.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
