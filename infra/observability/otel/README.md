# OpenTelemetry Collector

This chart deploys the OpenTelemetry Collector with Azure Monitor export enabled. Configure the Key
Vault CSI integration to provide `AZURE_MONITOR_CONNECTION_STRING`.

## Deploy
```bash
helm upgrade --install otel-collector infra/observability/otel/helm \
  --set keyVault.name=<kv> \
  --set keyVault.tenantId=<tenant> \
  --set keyVault.clientId=<client>
```
