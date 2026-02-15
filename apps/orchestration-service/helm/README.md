# Orchestration Service Helm Chart

## Purpose

Package Kubernetes deployment manifests for this component.

## What's inside

- [templates](/apps/orchestration-service/helm/templates): Templates used by the component (deployment or message content).
- [Chart.yaml](/apps/orchestration-service/helm/Chart.yaml): Helm chart metadata and versioning.
- [values.yaml](/apps/orchestration-service/helm/values.yaml): Helm values for environment-specific overrides.

## How it's used

Used by deployment pipelines and `helm` to render Kubernetes manifests.

## How to run / develop / test

Lint and render the chart locally:

```bash
helm lint apps/orchestration-service/helm
helm template orchestration-service apps/orchestration-service/helm
```

## Configuration

Edit `values.yaml` for environment-specific overrides.

## Troubleshooting

- Helm lint errors: validate YAML formatting and required values.
- Rendered manifests missing resources: check `templates/` for missing files.
