# Secret Initialization Runbook

Operational guide for initializing secrets required by the PPM platform services.

## Key Vault

All production secrets are stored in Azure Key Vault. Each environment (dev, staging, production) has its own Key Vault instance.

### Required Secrets

| Secret Name | Description | Rotation Cadence |
|-------------|-------------|-----------------|
| `database-connection-string` | Primary database connection | 90 days |
| `redis-connection-string` | Redis cache connection | 90 days |
| `jwt-signing-key` | JWT token signing key | 180 days |
| `azure-openai-api-key` | Azure OpenAI API key | 90 days |
| `service-bus-connection` | Azure Service Bus connection | 90 days |

### Initialization Steps

1. Ensure the Key Vault instance exists and RBAC is configured.
2. Grant the service principal `Key Vault Secrets User` role.
3. Populate each secret using the Azure CLI:
   ```bash
   az keyvault secret set --vault-name <vault> --name <secret-name> --value <value>
   ```

## Validation

After initialization, verify all secrets are accessible:

1. Run `make env-validate` to check environment configuration.
2. Deploy a canary pod and verify it starts without secret-related errors.
3. Check application logs for any `KeyVaultError` or `SecretNotFound` messages.

## Troubleshooting

- If a secret is missing, check Key Vault access policies.
- If a secret value is incorrect, rotate it and restart affected pods.
