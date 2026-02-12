# PostgreSQL Terraform Module

## Secret management architecture

This module no longer exposes plaintext PostgreSQL administrator passwords via outputs. It now uses a controlled secret lifecycle in Azure Key Vault:

1. `random_password.db_password` generates an admin password at provisioning time.
2. The password is only consumed in-module by `azurerm_postgresql_flexible_server.main`.
3. The generated password is persisted as a Key Vault secret (`*-postgres-admin-password`).
4. A full database connection string is generated in-module and stored as a Key Vault secret (`database-url`).
5. Module outputs provide Key Vault secret IDs instead of secret values.

### Security notes about Terraform state

Because Azure PostgreSQL admin credentials are provisioned through Terraform, the generated password value is still present in Terraform state. Use the following controls to reduce exposure risk:

- **Encrypted backend at rest**: Store state in Azure Storage with platform-managed encryption (default) or customer-managed keys.
- **Private network only**: Restrict state storage account access to private endpoints / trusted networks.
- **Strict IAM/RBAC**: Grant least-privilege read/write access to the Terraform state container and Key Vault.
- **State locking and versioning**: Enable blob versioning and soft delete to support tamper detection and recovery.
- **Auditability**: Enable diagnostic logs for the state storage account and Key Vault access; forward to Log Analytics/SIEM.
- **Short-lived operator credentials**: Use workload identity / managed identity instead of static credentials for Terraform runners.

## Operator runbook

### Provision / update

1. Apply Terraform from a trusted runner identity.
2. Confirm secret resources were updated:
   - `${prefix}-${env}-postgres-admin-password`
   - `database-url`
3. Confirm applications read the database URL from Key Vault and not Terraform outputs.

### Credential rotation

1. Generate and apply a new admin password by tainting/replacing `random_password.db_password` and applying Terraform.
2. Validate the new Key Vault secret versions were created.
3. Restart or roll workloads so they pick up the new secret version.
4. Validate database connectivity and revoke stale pooled sessions where applicable.

### Migration plan for previously exposed credentials/state

1. **Immediate rotation**: Rotate PostgreSQL admin password and regenerate the Key Vault `database-url` secret.
2. **Application cutover**: Ensure all consumers use Key Vault-based secrets only.
3. **State snapshot invalidation**:
   - Remove old local state artifacts from CI agents and operator workstations.
   - Expire or archive historical remote blob versions/snapshots per retention policy.
   - Restrict access to historical state versions to incident-response personnel only.
4. **Access review**: Audit who had state read access; revoke unnecessary permissions.
5. **Evidence capture**: Record rotation timestamps, principal IDs, and Terraform run IDs for compliance.
