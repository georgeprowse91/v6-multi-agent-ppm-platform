# Workflow Engine Helm Chart

## Purpose
This chart packages the **workflow-engine** deployment for the Multi-Agent PPM platform when deploying to
Kubernetes. It defines the Deployment, Service, and ConfigMap used by the workflow-engine runtime.

## Responsibilities
- Package the workflow-engine container image and runtime settings.
- Provide a stable Service for inter-service communication on port 8080.
- Externalize runtime configuration via `values.yaml` and `templates/configmap.yaml`.

## Folder structure
```
apps/workflow-engine/helm/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── _helpers.tpl
│   ├── configmap.yaml
│   ├── deployment.yaml
│   └── service.yaml
```

## Conventions
- `Chart.yaml` **name** must match the parent directory name (`workflow-engine`).
- `values.yaml` defines `image.repository`, `image.tag`, and `service.port`.
- All templates use the `name` helper from `_helpers.tpl` for consistent naming.

## How to add a new template
1. Add a new manifest under `apps/workflow-engine/helm/templates/` (e.g. `ingress.yaml`).
2. Reference new values under `values.yaml` and keep defaults minimal.
3. Update this README with the new path and a short usage note.
4. Validate the chart with the command below.

## How to validate/test
```bash
python scripts/validate-helm-charts.py apps/workflow-engine/helm
```

## Example
`values.yaml` excerpt:
```yaml
image:
  repository: ghcr.io/your-org/workflow-engine
  tag: "0.1.0"
service:
  port: 8080
```
