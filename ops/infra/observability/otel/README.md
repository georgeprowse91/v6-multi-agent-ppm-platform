# Otel Infrastructure

## Purpose

Document infrastructure resources under infra/observability/otel.

## What's inside

- [helm](/infra/observability/otel/helm): Helm chart packaging for Kubernetes deployments.
- [collector.yaml](/infra/observability/otel/collector.yaml): YAML definition or configuration used by this component.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
