# Manifests Infrastructure

## Purpose

Document infrastructure resources under infra/kubernetes/manifests.

## What's inside

- [cert-manager-issuer.yaml](/infra/kubernetes/manifests/cert-manager-issuer.yaml): YAML definition or configuration used by this component.
- [namespace.yaml](/infra/kubernetes/manifests/namespace.yaml): YAML definition or configuration used by this component.
- [network-policies.yaml](/infra/kubernetes/manifests/network-policies.yaml): YAML definition or configuration used by this component.
- [pod-security.yaml](/infra/kubernetes/manifests/pod-security.yaml): YAML definition or configuration used by this component.
- [resource-quotas.yaml](/infra/kubernetes/manifests/resource-quotas.yaml): YAML definition or configuration used by this component.

## How it's used

These assets are referenced during deployment and operational runbooks.

## How to run / develop / test

Use Terraform/Helm/Kubernetes tooling referenced in this directory to apply changes.

## Configuration

Infrastructure configuration lives in the files within this folder and `.env` for local tooling.

## Troubleshooting

- Terraform errors: ensure the correct workspace/env variables are set.
- Kubernetes apply failures: verify cluster access and namespace settings.
