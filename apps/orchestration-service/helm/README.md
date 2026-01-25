# Helm Chart

This folder will contain the Helm chart definition for **orchestration service**. The chart should package the
service deployment, service, config, and secrets templates.

## Expected contents
- `Chart.yaml` and `values.yaml`
- Kubernetes manifests under `templates/`
- Environment-specific overlays managed via CI/CD

Assumption: Helm is the primary packaging method for Kubernetes deployments in this repo.
