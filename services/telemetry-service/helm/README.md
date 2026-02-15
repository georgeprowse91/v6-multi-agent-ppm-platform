# Telemetry Service Helm Chart

## Purpose

Package Kubernetes deployment manifests for this component.

## What's inside

- [services/telemetry-service/helm/files](/services/telemetry-service/helm/files): Subdirectory containing files assets for this area.
- [services/telemetry-service/helm/templates](/services/telemetry-service/helm/templates): Templates used by the component (deployment or message content).
- [services/telemetry-service/helm/Chart.yaml](/services/telemetry-service/helm/Chart.yaml): Helm chart metadata and versioning.
- [services/telemetry-service/helm/values.yaml](/services/telemetry-service/helm/values.yaml): Helm values for environment-specific overrides.

## How it's used

Used by deployment pipelines and `helm` to render Kubernetes manifests.

## How to run / develop / test

Lint and render the chart locally:

```bash
helm lint services/telemetry-service/helm
helm template telemetry-service services/telemetry-service/helm
```

## Configuration

Edit `values.yaml` for environment-specific overrides.

## Troubleshooting

- Helm lint errors: validate YAML formatting and required values.
- Rendered manifests missing resources: check `templates/` for missing files.
