# Kubernetes

Kubernetes resource definitions, Helm chart packaging, and deployment manifests for the platform.

## Directory structure

| Folder | Description |
|--------|-------------|
| [helm-charts/](./helm-charts/) | Helm chart packaging for the platform |
| [manifests/](./manifests/) | Kubernetes manifests for cluster resources |

## Key files

| File | Description |
|------|-------------|
| `deployment.yaml` | Platform deployment specification |
| `service-account.yaml` | Kubernetes service account definition |
| `db-backup-cronjob.yaml` | CronJob for scheduled database backups |
| `secret-rotation-cronjob.yaml` | CronJob for automated secret rotation |
| `secret-provider-class.yaml` | Secret store CSI driver provider class |
| `secrets.yaml.example` | Example secrets manifest template |
