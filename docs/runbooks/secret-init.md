# Secret Initialization Runbook

This runbook documents how to bootstrap secrets for new environments.

## Scope
- Azure Key Vault secrets
- Kubernetes SecretProviderClass configuration
- Service principal credentials for CI/CD

## Initial bootstrap
1. **Create Key Vault**
   - Provision Key Vault via Terraform (`ops/infra/terraform/main.tf`).
2. **Create secret namespace**
   - Use a dedicated prefix per environment (e.g., `prod-`, `staging-`).
3. **Seed baseline secrets**
   - Database connection strings
   - Redis connection strings
   - JWT signing keys and JWKS URL
   - Connector API credentials (Jira, ServiceNow, Azure DevOps)
4. **Configure Kubernetes CSI driver**
   - Apply `ops/infra/kubernetes/secret-provider-class.yaml`.
   - Verify workloads mount secrets at runtime.
   - Ensure the workload identity service account in `ops/infra/kubernetes/service-account.yaml` is annotated with the Key Vault client ID and tenant ID.
   - Confirm pods are labeled with `azure.workload.identity/use: "true"` for AKS workload identity.

## Secret naming and mount conventions
- **Key Vault secret names** should match the filenames expected under `/mnt/secrets-store`.
- **Mount path**: the CSI driver mounts secrets to `/mnt/secrets-store/<secret-name>`.
- **Config references** must use file references, for example:
  - `file:/mnt/secrets-store/identity-client-secret`
  - `file:/mnt/secrets-store/jira-api-token`
- **Local development** can use env placeholders instead of files:
  - `env:IDENTITY_CLIENT_SECRET`
  - `${JIRA_API_TOKEN}`

## Provisioning steps (AKS + Key Vault)
1. **Create/verify Key Vault secrets**
   - Add secrets for endpoints, identity, observability, and connector credentials using the same names referenced in `ops/config/environments/prod.yaml`.
2. **Apply SecretProviderClass**
   - Ensure `ops/infra/kubernetes/secret-provider-class.yaml` lists the secret names to mount.
3. **Deploy workloads**
   - The CSI driver mounts secrets to `/mnt/secrets-store` and optionally syncs them to Kubernetes Secrets via `secretObjects`.

## Validation
- `kubectl describe pod` shows CSI mount ready.
- API gateway `/v1/status` returns `healthy`.
- Identity service can validate JWTs using Key Vault-backed secrets.

## Rotation readiness
- Ensure each secret has an owner, rotation schedule, and alternate version.
- Verify alerting for Key Vault access failures.
- Rotate by updating the Key Vault secret value and restarting pods (or wait for CSI rotation interval).
