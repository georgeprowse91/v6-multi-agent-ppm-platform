# Document Service Helm Chart

## Purpose
This chart packages the **document-service** deployment for the Multi-Agent PPM platform when deploying to
Kubernetes. It defines the Deployment, Service, and ConfigMap used by the document-service runtime.

## Responsibilities
- Package the document-service container image and runtime settings.
- Provide a stable Service for inter-service communication on port 8080.
- Externalize runtime configuration via `values.yaml` and `templates/configmap.yaml`.

## Folder structure
```
apps/document-service/helm/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── _helpers.tpl
│   ├── configmap.yaml
│   ├── deployment.yaml
│   └── service.yaml
```

## Conventions
- `Chart.yaml` **name** must match the parent directory name (`document-service`).
- `values.yaml` defines `image.repository`, `image.tag`, and `service.port`.
- All templates use the `name` helper from `_helpers.tpl` for consistent naming.

## How to add a new template
1. Add a new manifest under `apps/document-service/helm/templates/` (e.g. `ingress.yaml`).
2. Reference new values under `values.yaml` and keep defaults minimal.
3. Update this README with the new path and a short usage note.
4. Validate the chart with the command below.

## How to validate/test
```bash
python scripts/validate-helm-charts.py apps/document-service/helm
```

## Example
`values.yaml` excerpt:
```yaml
image:
  repository: ghcr.io/your-org/document-service
  tag: "0.1.0"
service:
  port: 8080
```
