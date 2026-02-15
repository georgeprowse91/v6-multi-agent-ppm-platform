# Modules Infrastructure

## Purpose

Document infrastructure resources under infra/terraform/modules.

## What's inside

- [aks](/infra/terraform/modules/aks): Subdirectory containing aks assets for this area.
- [cost-analysis](/infra/terraform/modules/cost-analysis): Subdirectory containing Azure Cost Management export assets for this area.
- [keyvault](/infra/terraform/modules/keyvault): Subdirectory containing keyvault assets for this area.
- [monitoring](/infra/terraform/modules/monitoring): Subdirectory containing monitoring assets for this area.
- [networking](/infra/terraform/modules/networking): Subdirectory containing networking assets for this area.
- [postgresql](/infra/terraform/modules/postgresql): Subdirectory containing postgresql assets for this area (including secret-management runbook in `postgresql/README.md`).

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
