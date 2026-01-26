# Manifests Infrastructure

## Purpose

Document infrastructure resources under infra/kubernetes/manifests.

## What's inside

- `infra/kubernetes/manifests/cert-manager-issuer.yaml`: YAML definition or configuration used by this component.
- `infra/kubernetes/manifests/namespace.yaml`: YAML definition or configuration used by this component.
- `infra/kubernetes/manifests/network-policies.yaml`: YAML definition or configuration used by this component.
- `infra/kubernetes/manifests/pod-security.yaml`: YAML definition or configuration used by this component.
- `infra/kubernetes/manifests/resource-quotas.yaml`: YAML definition or configuration used by this component.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
