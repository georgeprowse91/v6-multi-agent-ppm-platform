# Tenants Configuration

## Purpose

Describe tenant bootstrap configuration used to seed new tenants and to drive environment-specific defaults.

## What's inside

- `config/tenants/default.yaml`: Default tenant definition consumed by provisioning flows and local development.

## How it's used

Tenant configuration is loaded by API gateway, policy engine, and agent runtime services to set identity providers, default security posture, and enabled platform features.

## Configuration fields (`default.yaml`)

| Field | Description |
| --- | --- |
| `id` | Template tenant identifier used for bootstrapping. |
| `name` | Tenant display name. |
| `region` | Default deployment region for tenant resources. |
| `features.workflow_engine` | Enable the workflow engine for the tenant. |
| `features.data_sync` | Enable connector sync services. |
| `features.audit_logging` | Enable audit log emission. |
| `features.telemetry` | Enable telemetry and metrics. |
| `identity.issuer` | OIDC issuer URL template. |
| `identity.audience` | Audience expected in tokens. |
| `identity.jwks_url` | JWKS endpoint for token verification. |
| `classification_defaults.level` | Default classification label applied to new records. |
| `retention_defaults.policy` | Default retention policy ID. |
| `rbac_defaults.roles` | Default roles to seed in the tenant RBAC store. |
| `provisioning.namespaces` | Kubernetes namespaces to provision for the tenant. |
| `provisioning.resource_groups` | Resource groups to create in the cloud environment. |
| `provisioning.key_vault.name` | Key vault naming template. |
| `provisioning.key_vault.secrets` | Secret names to pre-create in the vault. |

## How to run / develop / test

Review tenant configuration files directly before running services or provisioning new tenants.

## Troubleshooting

- Config not applied: ensure the runtime points to the correct file.
- Schema errors: validate configuration format with `python scripts/check-placeholders.py`.
