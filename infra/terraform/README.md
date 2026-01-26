# Terraform (Azure)

## Audit WORM immutability verification

After `terraform apply`, confirm immutable storage is enabled for audit logs:

```bash
az storage account show --name <storage-account> --resource-group <rg> --query "immutableStorageWithVersioning.enabled"
```

```bash
az storage container immutability-policy show \
  --account-name <storage-account> \
  --container-name audit-events
```

The audit container should show a **Locked** immutability policy with the configured retention period, and storage account versioning should be enabled.

## WAF traffic flow

Application traffic should follow this path:

```
Client -> Application Gateway WAF_v2 -> Kubernetes ingress (NGINX) -> Services
```

Ensure the `ingress_backend_fqdn` variable resolves to the ingress controller endpoint (internal load balancer or private DNS).
