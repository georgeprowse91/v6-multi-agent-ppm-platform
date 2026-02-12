# Multi-Agent PPM Platform - Azure Infrastructure
# Terraform configuration for deploying to Azure

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "ppm-prod-tfstate-rg"
    storage_account_name = "ppmtfstateprod"
    container_name       = "tfstate"
    key                  = "ppm-platform/prod/terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
}

# Variables
variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "resource_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "ppm"
}

variable "key_vault_name" {
  description = "Optional override for the Key Vault name"
  type        = string
  default     = ""
}

variable "postgres_database_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "ppm"
}

variable "identity_client_secret" {
  description = "OIDC identity client secret"
  type        = string
  sensitive   = true
}

variable "service_bus_connection_string" {
  description = "Azure Service Bus connection string"
  type        = string
  sensitive   = true
}

variable "azure_openai_api_key" {
  description = "Azure OpenAI API key"
  type        = string
  sensitive   = true
}

variable "azure_monitor_connection_string" {
  description = "Azure Monitor connection string for OpenTelemetry exporter"
  type        = string
  sensitive   = true
  default     = ""
}

variable "workload_identity_issuer_url" {
  description = "OIDC issuer URL for AKS workload identity"
  type        = string
  default     = ""
}

variable "workload_identity_subject" {
  description = "Workload identity subject (service account) for Key Vault access"
  type        = string
  default     = ""
}

variable "workload_identity_audience" {
  description = "Workload identity audience"
  type        = string
  default     = "api://AzureADTokenExchange"
}

variable "vnet_address_space" {
  description = "Address space for the virtual network"
  type        = list(string)
  default     = ["10.20.0.0/16"]
}

variable "aks_subnet_address_prefixes" {
  description = "Address prefixes for the AKS subnet"
  type        = list(string)
  default     = ["10.20.2.0/23"]
}

variable "app_gateway_subnet_address_prefixes" {
  description = "Address prefixes for the Application Gateway subnet"
  type        = list(string)
  default     = ["10.20.4.0/24"]
}

variable "private_endpoint_subnet_address_prefixes" {
  description = "Address prefixes for the private endpoint subnet"
  type        = list(string)
  default     = ["10.20.1.0/24"]
}

variable "postgres_sku_name" {
  description = "PostgreSQL Flexible Server SKU"
  type        = string
  default     = "GP_Standard_D4s_v3"

  validation {
    condition     = length(var.postgres_sku_name) > 0
    error_message = "postgres_sku_name must be set to a valid PostgreSQL Flexible Server SKU."
  }
}

variable "postgres_storage_mb" {
  description = "PostgreSQL storage size in MB"
  type        = number
  default     = 131072

  validation {
    condition     = var.postgres_storage_mb >= 32768
    error_message = "postgres_storage_mb must be at least 32768 MB."
  }
}

variable "postgres_backup_retention_days" {
  description = "PostgreSQL backup retention in days"
  type        = number
  default     = 35

  validation {
    condition     = var.postgres_backup_retention_days >= 7 && var.postgres_backup_retention_days <= 35
    error_message = "postgres_backup_retention_days must be between 7 and 35 days."
  }
}

variable "postgres_geo_redundant_backup_enabled" {
  description = "Enable geo-redundant backups for PostgreSQL"
  type        = bool
  default     = true
}

variable "postgres_ha_mode" {
  description = "PostgreSQL high availability mode (ZoneRedundant, SameZone, Disabled)"
  type        = string
  default     = "ZoneRedundant"

  validation {
    condition     = contains(["ZoneRedundant", "SameZone", "Disabled"], var.postgres_ha_mode)
    error_message = "postgres_ha_mode must be one of ZoneRedundant, SameZone, or Disabled."
  }
}

variable "postgres_primary_zone" {
  description = "Primary availability zone for PostgreSQL"
  type        = string
  default     = "1"
}

variable "postgres_standby_zone" {
  description = "Standby availability zone for PostgreSQL"
  type        = string
  default     = "2"
}

variable "postgres_minimum_tls_version" {
  description = "Minimum TLS version enforced by PostgreSQL"
  type        = string
  default     = "TLS1_2"

  validation {
    condition     = contains(["TLS1_0", "TLS1_1", "TLS1_2"], var.postgres_minimum_tls_version)
    error_message = "postgres_minimum_tls_version must be TLS1_0, TLS1_1, or TLS1_2."
  }
}

variable "storage_replication_type" {
  description = "Storage account replication type"
  type        = string
  default     = "GRS"

  validation {
    condition     = contains(["LRS", "GRS", "RAGRS", "ZRS", "GZRS", "RAGZRS"], var.storage_replication_type)
    error_message = "storage_replication_type must be a valid Azure replication option."
  }
}

variable "storage_minimum_tls_version" {
  description = "Minimum TLS version for storage accounts"
  type        = string
  default     = "TLS1_2"
}

variable "redis_sku_name" {
  description = "Redis SKU name (Basic, Standard, Premium)"
  type        = string
  default     = "Premium"

  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.redis_sku_name)
    error_message = "redis_sku_name must be Basic, Standard, or Premium."
  }
}

variable "redis_family" {
  description = "Redis SKU family (C or P)"
  type        = string
  default     = "P"

  validation {
    condition     = contains(["C", "P"], var.redis_family)
    error_message = "redis_family must be C or P."
  }
}

variable "redis_capacity" {
  description = "Redis cache capacity"
  type        = number
  default     = 2

  validation {
    condition     = var.redis_capacity >= 0
    error_message = "redis_capacity must be zero or greater."
  }
}

variable "redis_persistence_enabled" {
  description = "Enable Redis persistence backups"
  type        = bool
  default     = true
}

variable "redis_backup_frequency" {
  description = "Redis RDB backup frequency in minutes"
  type        = number
  default     = 60

  validation {
    condition     = contains([15, 60], var.redis_backup_frequency)
    error_message = "redis_backup_frequency must be 15 or 60 minutes."
  }
}

variable "redis_backup_max_snapshot_count" {
  description = "Redis RDB backup max snapshot count"
  type        = number
  default     = 5

  validation {
    condition     = var.redis_backup_max_snapshot_count >= 1
    error_message = "redis_backup_max_snapshot_count must be at least 1."
  }
}

variable "redis_maxmemory_policy" {
  description = "Redis maxmemory policy"
  type        = string
  default     = "allkeys-lru"
}

variable "aks_dns_prefix" {
  description = "DNS prefix for the AKS cluster"
  type        = string
  default     = "ppm-aks"
}

variable "aks_system_node_vm_size" {
  description = "VM size for the AKS system node pool"
  type        = string
  default     = "Standard_DS3_v2"
}

variable "aks_system_node_count" {
  description = "Node count for the AKS system pool"
  type        = number
  default     = 2
}

variable "aks_user_node_vm_size" {
  description = "VM size for the AKS user node pool"
  type        = string
  default     = "Standard_DS3_v2"
}

variable "aks_user_node_count" {
  description = "Node count for the AKS user pool"
  type        = number
  default     = 2
}

variable "aks_user_node_min_count" {
  description = "Minimum nodes for the AKS user pool"
  type        = number
  default     = 2
}

variable "aks_user_node_max_count" {
  description = "Maximum nodes for the AKS user pool"
  type        = number
  default     = 6
}

variable "aks_admin_group_object_ids" {
  description = "AAD group object IDs to grant cluster admin access"
  type        = list(string)
  default     = []
}

variable "audit_immutability_days" {
  description = "Retention window for immutable audit blobs (in days)"
  type        = number
  default     = 2555
}

variable "ingress_backend_fqdn" {
  description = "Ingress endpoint FQDN behind the WAF (e.g., ingress internal load balancer)"
  type        = string
  default     = "ingress.internal"
}

variable "app_gateway_capacity" {
  description = "Instance count for the Application Gateway WAF_v2"
  type        = number
  default     = 2
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${var.resource_prefix}-${var.environment}-rg"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = "Multi-Agent PPM Platform"
  }
}

module "monitoring" {
  source = "./modules/monitoring"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  resource_prefix     = var.resource_prefix
  environment         = var.environment
}

module "networking" {
  source = "./modules/networking"

  resource_group_name                  = azurerm_resource_group.main.name
  location                             = azurerm_resource_group.main.location
  resource_prefix                      = var.resource_prefix
  environment                          = var.environment
  vnet_address_space                   = var.vnet_address_space
  private_endpoint_subnet_address_prefixes = var.private_endpoint_subnet_address_prefixes
  aks_subnet_address_prefixes          = var.aks_subnet_address_prefixes
  app_gateway_subnet_address_prefixes  = var.app_gateway_subnet_address_prefixes
}

# Azure Container Registry
resource "azurerm_container_registry" "acr" {
  name                = "${var.resource_prefix}${var.environment}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
  admin_enabled       = false
  public_network_access_enabled = false

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_public_ip" "app_gateway" {
  name                = "${var.resource_prefix}-${var.environment}-agw-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_web_application_firewall_policy" "main" {
  name                = "${var.resource_prefix}-${var.environment}-waf"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  policy_settings {
    enabled = true
    mode    = "Prevention"
  }

  managed_rules {
    managed_rule_set {
      type    = "OWASP"
      version = "3.2"
    }
  }
}

resource "azurerm_application_gateway" "main" {
  name                = "${var.resource_prefix}-${var.environment}-agw"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  sku {
    name     = "WAF_v2"
    tier     = "WAF_v2"
    capacity = var.app_gateway_capacity
  }

  gateway_ip_configuration {
    name      = "gateway-ip-config"
    subnet_id = module.networking.app_gateway_subnet_id
  }

  frontend_port {
    name = "http"
    port = 80
  }

  frontend_ip_configuration {
    name                 = "public"
    public_ip_address_id = azurerm_public_ip.app_gateway.id
  }

  backend_address_pool {
    name  = "aks-ingress"
    fqdns = [var.ingress_backend_fqdn]
  }

  backend_http_settings {
    name                  = "http-settings"
    cookie_based_affinity = "Disabled"
    port                  = 80
    protocol              = "Http"
    request_timeout       = 30
  }

  http_listener {
    name                           = "http-listener"
    frontend_ip_configuration_name = "public"
    frontend_port_name             = "http"
    protocol                       = "Http"
  }

  request_routing_rule {
    name                       = "default-route"
    rule_type                  = "Basic"
    http_listener_name         = "http-listener"
    backend_address_pool_name  = "aks-ingress"
    backend_http_settings_name = "http-settings"
  }

  firewall_policy_id = azurerm_web_application_firewall_policy.main.id

  tags = {
    Environment = var.environment
  }
}

module "aks" {
  source = "./modules/aks"

  resource_group_name   = azurerm_resource_group.main.name
  location              = azurerm_resource_group.main.location
  resource_prefix       = var.resource_prefix
  environment           = var.environment
  dns_prefix            = var.aks_dns_prefix
  aks_subnet_id         = module.networking.aks_subnet_id
  private_dns_zone_id   = module.networking.private_dns_zone_ids["aks"]
  system_node_vm_size   = var.aks_system_node_vm_size
  system_node_count     = var.aks_system_node_count
  user_node_vm_size     = var.aks_user_node_vm_size
  user_node_count       = var.aks_user_node_count
  user_node_min_count   = var.aks_user_node_min_count
  user_node_max_count   = var.aks_user_node_max_count
  admin_group_object_ids = var.aks_admin_group_object_ids
  acr_id                = azurerm_container_registry.acr.id
}

module "postgresql" {
  source = "./modules/postgresql"

  resource_group_name                = azurerm_resource_group.main.name
  location                           = azurerm_resource_group.main.location
  resource_prefix                     = var.resource_prefix
  environment                         = var.environment
  postgres_sku_name                   = var.postgres_sku_name
  postgres_storage_mb                 = var.postgres_storage_mb
  postgres_backup_retention_days      = var.postgres_backup_retention_days
  postgres_geo_redundant_backup_enabled = var.postgres_geo_redundant_backup_enabled
  postgres_ha_mode                    = var.postgres_ha_mode
  postgres_primary_zone               = var.postgres_primary_zone
  postgres_standby_zone               = var.postgres_standby_zone
  postgres_minimum_tls_version        = var.postgres_minimum_tls_version
  private_endpoint_subnet_id          = module.networking.private_endpoint_subnet_id
  private_dns_zone_id                 = module.networking.private_dns_zone_ids["postgres"]
  key_vault_id                        = module.keyvault.key_vault_id
  key_vault_secret_name_prefix        = "${var.resource_prefix}-${var.environment}"
  postgres_database_name              = var.postgres_database_name
}

# Azure Cosmos DB (optional - for production scale)
resource "azurerm_cosmosdb_account" "main" {
  name                = "${var.resource_prefix}-${var.environment}-cosmos"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"
  public_network_access_enabled = false
  minimum_tls_version           = "Tls12"
  is_virtual_network_filter_enabled = true

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }

  tags = {
    Environment = var.environment
  }
}

# Azure Cache for Redis
resource "azurerm_redis_cache" "main" {
  name                = "${var.resource_prefix}-${var.environment}-redis"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  capacity            = var.redis_capacity
  family              = var.redis_family
  sku_name            = var.redis_sku_name

  enable_non_ssl_port = false
  minimum_tls_version = "1.2"
  public_network_access_enabled = false

  redis_configuration {
    maxmemory_policy            = var.redis_maxmemory_policy
    rdb_backup_enabled          = var.redis_persistence_enabled
    rdb_backup_frequency        = var.redis_backup_frequency
    rdb_backup_max_snapshot_count = var.redis_backup_max_snapshot_count
    rdb_storage_connection_string = var.redis_persistence_enabled ? azurerm_storage_account.redis_backup.primary_blob_connection_string : null
  }

  tags = {
    Environment = var.environment
  }
}

# Azure OpenAI Service
resource "azurerm_cognitive_account" "openai" {
  name                = "${var.resource_prefix}-${var.environment}-openai"
  resource_group_name = azurerm_resource_group.main.name
  location            = "eastus"  # OpenAI is only available in certain regions
  kind                = "OpenAI"
  sku_name            = "S0"
  public_network_access_enabled = false

  tags = {
    Environment = var.environment
  }
}

data "azurerm_client_config" "current" {}

locals {
  redis_url = "rediss://:${azurerm_redis_cache.main.primary_access_key}@${azurerm_redis_cache.main.hostname}:${azurerm_redis_cache.main.ssl_port}/0"
}

resource "random_password" "audit_log_encryption_key" {
  length  = 64
  special = false
}

module "keyvault" {
  source = "./modules/keyvault"

  resource_group_name            = azurerm_resource_group.main.name
  location                       = azurerm_resource_group.main.location
  resource_prefix                = var.resource_prefix
  environment                    = var.environment
  key_vault_name                 = var.key_vault_name != "" ? var.key_vault_name : "${var.resource_prefix}-${var.environment}-kv"
  tenant_id                      = data.azurerm_client_config.current.tenant_id
  current_object_id              = data.azurerm_client_config.current.object_id
  workload_identity_subject      = var.workload_identity_subject
  workload_identity_audience     = var.workload_identity_audience
  workload_identity_issuer_url   = coalesce(nullif(var.workload_identity_issuer_url, ""), module.aks.oidc_issuer_url)
  redis_url                      = local.redis_url
  azure_openai_endpoint          = azurerm_cognitive_account.openai.endpoint
  azure_openai_api_key           = var.azure_openai_api_key
  identity_client_secret         = var.identity_client_secret
  service_bus_connection_string  = var.service_bus_connection_string
  storage_account_key            = azurerm_storage_account.main.primary_access_key
  audit_worm_connection_string   = azurerm_storage_account.main.primary_connection_string
  audit_log_encryption_key       = random_password.audit_log_encryption_key.result
  azure_monitor_connection_string = var.azure_monitor_connection_string
}

# Storage Account for Data Lake
resource "azurerm_storage_account" "main" {
  name                     = "${var.resource_prefix}${var.environment}storage"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.storage_replication_type
  is_hns_enabled           = true  # Enable Data Lake Gen2
  allow_blob_public_access = false
  enable_https_traffic_only = true
  min_tls_version           = var.storage_minimum_tls_version
  public_network_access_enabled = false
  immutable_storage_enabled      = true

  blob_properties {
    versioning_enabled = true
  }

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_storage_account" "redis_backup" {
  name                     = "${var.resource_prefix}${var.environment}redisbk"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.storage_replication_type
  allow_blob_public_access = false
  enable_https_traffic_only = true
  min_tls_version           = var.storage_minimum_tls_version
  public_network_access_enabled = false

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_storage_container" "redis_backups" {
  name                  = "redis-backups"
  storage_account_name  = azurerm_storage_account.redis_backup.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "audit_events" {
  name                  = "audit-events"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"

  immutability_policy {
    period_since_creation_in_days = var.audit_immutability_days
    state                         = "Locked"
  }

  legal_hold = true
}

# Storage lifecycle policies for retention enforcement
resource "azurerm_storage_management_policy" "retention" {
  storage_account_id = azurerm_storage_account.main.id

  rule {
    name    = "public-retention"
    enabled = true
    filters {
      prefix_match = ["public/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 30
      }
    }
  }

  rule {
    name    = "internal-retention"
    enabled = true
    filters {
      prefix_match = ["internal/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 365
      }
    }
  }

  rule {
    name    = "confidential-retention"
    enabled = true
    filters {
      prefix_match = ["confidential/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 1825
      }
    }
  }

  rule {
    name    = "restricted-retention"
    enabled = true
    filters {
      prefix_match = ["restricted/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 2555
      }
    }
  }
}

# Service Bus Namespace (for event-driven architecture)
resource "azurerm_servicebus_namespace" "main" {
  name                = "${var.resource_prefix}-${var.environment}-sb"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
  minimum_tls_version = "1.2"
  public_network_access_enabled = false

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_servicebus_queue" "data_sync" {
  name         = "data-sync"
  namespace_id = azurerm_servicebus_namespace.main.id

  enable_partitioning = true
  max_delivery_count  = 10
}


resource "azurerm_private_endpoint" "acr" {
  name                = "${var.resource_prefix}-${var.environment}-acr-pe"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = module.networking.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.resource_prefix}-${var.environment}-acr-psc"
    private_connection_resource_id = azurerm_container_registry.acr.id
    subresource_names              = ["registry"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "acr-dns"
    private_dns_zone_ids = [module.networking.private_dns_zone_ids["acr"]]
  }
}


resource "azurerm_private_endpoint" "redis" {
  name                = "${var.resource_prefix}-${var.environment}-redis-pe"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = module.networking.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.resource_prefix}-${var.environment}-redis-psc"
    private_connection_resource_id = azurerm_redis_cache.main.id
    subresource_names              = ["redisCache"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "redis-dns"
    private_dns_zone_ids = [module.networking.private_dns_zone_ids["redis"]]
  }
}

resource "azurerm_private_endpoint" "key_vault" {
  name                = "${var.resource_prefix}-${var.environment}-kv-pe"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = module.networking.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.resource_prefix}-${var.environment}-kv-psc"
    private_connection_resource_id = module.keyvault.key_vault_id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "kv-dns"
    private_dns_zone_ids = [module.networking.private_dns_zone_ids["key_vault"]]
  }
}

resource "azurerm_private_endpoint" "storage_blob" {
  name                = "${var.resource_prefix}-${var.environment}-storage-blob-pe"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = module.networking.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.resource_prefix}-${var.environment}-storage-blob-psc"
    private_connection_resource_id = azurerm_storage_account.main.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "storage-blob-dns"
    private_dns_zone_ids = [module.networking.private_dns_zone_ids["storage_blob"]]
  }
}

resource "azurerm_private_endpoint" "storage_dfs" {
  name                = "${var.resource_prefix}-${var.environment}-storage-dfs-pe"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = module.networking.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.resource_prefix}-${var.environment}-storage-dfs-psc"
    private_connection_resource_id = azurerm_storage_account.main.id
    subresource_names              = ["dfs"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "storage-dfs-dns"
    private_dns_zone_ids = [module.networking.private_dns_zone_ids["storage_dfs"]]
  }
}

resource "azurerm_private_endpoint" "redis_backup_blob" {
  name                = "${var.resource_prefix}-${var.environment}-redisbk-blob-pe"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = module.networking.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.resource_prefix}-${var.environment}-redisbk-blob-psc"
    private_connection_resource_id = azurerm_storage_account.redis_backup.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "redisbk-blob-dns"
    private_dns_zone_ids = [module.networking.private_dns_zone_ids["storage_blob"]]
  }
}

resource "azurerm_private_endpoint" "service_bus" {
  name                = "${var.resource_prefix}-${var.environment}-sb-pe"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = module.networking.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.resource_prefix}-${var.environment}-sb-psc"
    private_connection_resource_id = azurerm_servicebus_namespace.main.id
    subresource_names              = ["namespace"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "sb-dns"
    private_dns_zone_ids = [module.networking.private_dns_zone_ids["service_bus"]]
  }
}

resource "azurerm_private_endpoint" "openai" {
  name                = "${var.resource_prefix}-${var.environment}-openai-pe"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = module.networking.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.resource_prefix}-${var.environment}-openai-psc"
    private_connection_resource_id = azurerm_cognitive_account.openai.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "openai-dns"
    private_dns_zone_ids = [module.networking.private_dns_zone_ids["openai"]]
  }
}

resource "azurerm_private_endpoint" "cosmos" {
  name                = "${var.resource_prefix}-${var.environment}-cosmos-pe"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = module.networking.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.resource_prefix}-${var.environment}-cosmos-psc"
    private_connection_resource_id = azurerm_cosmosdb_account.main.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "cosmos-dns"
    private_dns_zone_ids = [module.networking.private_dns_zone_ids["cosmos"]]
  }
}

# Azure Monitor Diagnostics
resource "azurerm_monitor_diagnostic_setting" "key_vault" {
  name                       = "${var.resource_prefix}-${var.environment}-kv-diag"
  target_resource_id         = module.keyvault.key_vault_id
  log_analytics_workspace_id = module.monitoring.workspace_id

  enabled_log {
    category_group = "allLogs"
  }

  metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "storage_main" {
  name                       = "${var.resource_prefix}-${var.environment}-storage-diag"
  target_resource_id         = azurerm_storage_account.main.id
  log_analytics_workspace_id = module.monitoring.workspace_id

  enabled_log {
    category_group = "allLogs"
  }

  metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "storage_redis" {
  name                       = "${var.resource_prefix}-${var.environment}-redis-storage-diag"
  target_resource_id         = azurerm_storage_account.redis_backup.id
  log_analytics_workspace_id = module.monitoring.workspace_id

  enabled_log {
    category_group = "allLogs"
  }

  metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "service_bus" {
  name                       = "${var.resource_prefix}-${var.environment}-servicebus-diag"
  target_resource_id         = azurerm_servicebus_namespace.main.id
  log_analytics_workspace_id = module.monitoring.workspace_id

  enabled_log {
    category_group = "allLogs"
  }

  metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "container_registry" {
  name                       = "${var.resource_prefix}-${var.environment}-acr-diag"
  target_resource_id         = azurerm_container_registry.acr.id
  log_analytics_workspace_id = module.monitoring.workspace_id

  enabled_log {
    category_group = "allLogs"
  }

  metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "aks" {
  name                       = "${var.resource_prefix}-${var.environment}-aks-diag"
  target_resource_id         = module.aks.cluster_id
  log_analytics_workspace_id = module.monitoring.workspace_id

  enabled_log {
    category_group = "allLogs"
  }

  metric {
    category = "AllMetrics"
  }
}

# Outputs
output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "container_registry_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "app_gateway_public_ip" {
  value = azurerm_public_ip.app_gateway.ip_address
}

output "aks_name" {
  value = module.aks.name
}

output "aks_oidc_issuer_url" {
  value = module.aks.oidc_issuer_url
}

output "postgresql_fqdn" {
  value     = module.postgresql.fqdn
  sensitive = true
}

output "redis_hostname" {
  value     = azurerm_redis_cache.main.hostname
  sensitive = true
}

output "cosmos_endpoint" {
  value     = azurerm_cosmosdb_account.main.endpoint
  sensitive = true
}

output "openai_endpoint" {
  value     = azurerm_cognitive_account.openai.endpoint
  sensitive = true
}

output "key_vault_uri" {
  value = module.keyvault.vault_uri
}

output "key_vault_workload_identity_client_id" {
  value     = module.keyvault.workload_identity_client_id
  sensitive = true
}
