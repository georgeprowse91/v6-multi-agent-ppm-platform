# Secret Rotation Runbook

Procedures for rotating secrets used by the PPM platform.

## Rotation cadence

| Secret Category | Rotation cadence | Owner |
|----------------|-----------------|-------|
| Database credentials | 90 days | Platform team |
| API keys (OpenAI, connectors) | 90 days | Platform team |
| JWT signing keys | 180 days | Security team |
| Service Bus connections | 90 days | Platform team |
| Connector OAuth tokens | Per provider policy | Integration team |

## Standard Rotation Procedure

1. Generate the new secret value.
2. Add the new secret version to Azure Key Vault:
   ```bash
   az keyvault secret set --vault-name <vault> --name <secret> --value <new-value>
   ```
3. Trigger in-process cache refresh via SIGUSR1:
   ```bash
   kubectl exec -n ppm <pod> -- kill -USR1 1
   ```
4. Verify the service is using the new secret (check logs for `llm_key_rotation_triggered`).
5. After confirming all pods have rotated, disable the old secret version.

## Emergency rotation

In case of a suspected secret compromise:

1. Immediately rotate the compromised secret in Key Vault.
2. Force restart all affected pods:
   ```bash
   kubectl rollout restart deployment/<service> -n ppm
   ```
3. Audit access logs for unauthorized usage of the old secret.
4. Notify the security team and open an incident.
5. Review and update rotation cadence if needed.

## Verification

After rotation:

1. Check service health endpoints.
2. Verify no authentication errors in logs.
3. Run integration tests to confirm connectivity.
