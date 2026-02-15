# Alerts Infrastructure

## Purpose

Document infrastructure resources under infra/observability/alerts.

## What's inside

- [infra/observability/alerts/ppm-alerts.yaml](/infra/observability/alerts/ppm-alerts.yaml): YAML definition or configuration used by this component.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
