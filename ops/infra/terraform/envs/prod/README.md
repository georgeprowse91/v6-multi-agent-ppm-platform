# Prod Infrastructure

## Purpose

Document infrastructure resources under infra/terraform/envs/prod.

## What's inside

- `infra/terraform/envs/prod/backend.tfvars`: File asset used by this component.
- `infra/terraform/envs/prod/terraform.tfvars`: File asset used by this component.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
