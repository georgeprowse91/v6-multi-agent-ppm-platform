environment = "prod"
location    = "eastus"
resource_prefix = "ppm"

# AKS configuration
aks_dns_prefix             = "ppm-aks"
aks_system_node_vm_size    = "Standard_DS3_v2"
aks_system_node_count      = 3
aks_user_node_vm_size      = "Standard_DS3_v2"
aks_user_node_count        = 3
aks_user_node_min_count    = 3
aks_user_node_max_count    = 10
aks_admin_group_object_ids = ["00000000-0000-0000-0000-000000000000"]

# Application Gateway WAF settings
ingress_backend_fqdn = "ingress.internal"
app_gateway_capacity = 2

# PostgreSQL production sizing
postgres_sku_name                     = "GP_Standard_D4s_v3"
postgres_storage_mb                   = 262144
postgres_backup_retention_days        = 35
postgres_geo_redundant_backup_enabled = true
postgres_ha_mode                      = "ZoneRedundant"
postgres_primary_zone                 = "1"
postgres_standby_zone                 = "2"
postgres_minimum_tls_version          = "TLS1_2"

# Redis production sizing
redis_sku_name                 = "Premium"
redis_family                   = "P"
redis_capacity                 = 2
redis_persistence_enabled      = true
redis_backup_frequency         = 60
redis_backup_max_snapshot_count = 5
redis_maxmemory_policy         = "allkeys-lru"

# Storage
storage_replication_type = "GZRS"
storage_minimum_tls_version = "TLS1_2"
audit_immutability_days = 2555

# Key Vault naming (reference only)
key_vault_name = "ppm-prod-kv"

# Workload identity subject for Key Vault CSI
workload_identity_subject = "system:serviceaccount:ppm-platform:audit-log-kv"

# Azure Monitor connection string (populate via CI/TF Cloud for production)
azure_monitor_connection_string = "REPLACE_ME"
