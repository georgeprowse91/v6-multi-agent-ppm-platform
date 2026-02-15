# Envs Infrastructure

## Purpose

Document infrastructure resources under infra/terraform/envs.

## What's inside

- [dev](/infra/terraform/envs/dev): Subdirectory containing dev assets for this area.
- [stage](/infra/terraform/envs/stage): Subdirectory containing stage assets for this area.
- [prod](/infra/terraform/envs/prod): Subdirectory containing prod assets for this area.
- [test](/infra/terraform/envs/test): Subdirectory containing test assets for this area.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
