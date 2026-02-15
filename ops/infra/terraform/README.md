# Terraform Infrastructure

## Purpose

Document infrastructure resources under infra/terraform.

## What's inside

- [infra/terraform/envs](/infra/terraform/envs): Environment-specific overlays.
- [infra/terraform/modules](/infra/terraform/modules): Reusable Terraform modules.
- [infra/terraform/main.tf](/infra/terraform/main.tf): File asset used by this component.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
