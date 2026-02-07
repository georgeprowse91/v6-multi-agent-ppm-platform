# Disaster Recovery Scripts

Use these scripts to flip the active region and restore primary deployments.

## Failover

```bash
./infra/terraform/dr/failover.sh <environment> <dr-region>
```

## Restore

```bash
./infra/terraform/dr/restore.sh <environment> <primary-region>
```

Ensure replication and DNS/traffic managers are configured before running.
