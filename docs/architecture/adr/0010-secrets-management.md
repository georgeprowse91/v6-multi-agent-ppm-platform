# ADR 0010: Secrets Management

## Status

Accepted.

## Context

Services require secrets (JWT keys, API tokens, storage keys) and must avoid storing them in source control. Deployments must support managed secret stores while still enabling local development.

## Decision

Use Azure Key Vault via the Kubernetes SecretProviderClass in Helm charts for production deployments. For local development, use environment variables and `.env` files outside of source control. Helm charts accept Key Vault metadata (`keyVault.name`, `keyVault.tenantId`, `keyVault.clientId`) to mount secrets at runtime.

## Consequences

- Production deployments can use managed identity and centralized secret rotation.
- Local development remains simple without cloud dependencies.
- Charts and Terraform must be configured with the correct Key Vault metadata.

## References

- `services/api-gateway/helm/templates/secretproviderclass.yaml`
- `services/audit-log/helm/templates/secretproviderclass.yaml`
- `ops/infra/kubernetes/secret-provider-class.yaml`
