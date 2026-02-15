# Policies Infrastructure

## Purpose

Document infrastructure resources under infra/policies.

## What's inside

- [dlp](/infra/policies/dlp): Subdirectory containing dlp assets for this area.
- [network](/infra/policies/network): Subdirectory containing network assets for this area.
- [schema](/infra/policies/schema): Schemas or validation rules for component assets.
- [security](/infra/policies/security): Subdirectory containing security assets for this area.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
