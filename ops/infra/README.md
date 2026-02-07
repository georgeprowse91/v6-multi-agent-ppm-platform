# Infrastructure

Infrastructure resources for deploying and operating the platform, including Kubernetes manifests, Terraform modules, observability configuration, policies, and tenant provisioning.

## Directory structure

| Folder | Description |
|--------|-------------|
| [kubernetes/](./kubernetes/) | Kubernetes manifests, Helm charts, and cluster resource definitions |
| [observability/](./observability/) | Observability dashboards, alerts, and tracing configuration |
| [policies/](./policies/) | Policy definitions enforced by the platform |
| [tenancy/](./tenancy/) | Tenant provisioning and deprovisioning scripts |
| [terraform/](./terraform/) | Terraform root modules and environment stacks |

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
