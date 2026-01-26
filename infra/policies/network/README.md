# Network Infrastructure

## Purpose

Document infrastructure resources under infra/policies/network.

## What's inside

- `infra/policies/network/bundles`: Subdirectory containing bundles assets for this area.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
