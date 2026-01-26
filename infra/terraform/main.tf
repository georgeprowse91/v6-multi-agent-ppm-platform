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

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${var.resource_prefix}-${var.environment}-rg"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = "Multi-Agent PPM Platform"
  }
}

# Azure Container Registry
resource "azurerm_container_registry" "acr" {
  name                = "${var.resource_prefix}${var.environment}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
  admin_enabled       = false

  tags = {
    Environment = var.environment
  }
}

# Azure Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  name                = "${var.resource_prefix}-${var.environment}-env"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

# PostgreSQL Flexible Server
resource "azurerm_postgresql_flexible_server" "main" {
  name                = "${var.resource_prefix}-${var.environment}-psql"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  sku_name   = "B_Standard_B1ms"
  storage_mb = 32768
  version    = "15"

  administrator_login    = "ppmadmin"
  administrator_password = random_password.db_password.result

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  tags = {
    Environment = var.environment
  }
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Azure Cosmos DB (optional - for production scale)
resource "azurerm_cosmosdb_account" "main" {
  name                = "${var.resource_prefix}-${var.environment}-cosmos"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

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
  capacity            = 0
  family              = "C"
  sku_name            = "Basic"

  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  redis_configuration {
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

  tags = {
    Environment = var.environment
  }
}

# Azure Key Vault
resource "azurerm_key_vault" "main" {
  name                = "${var.resource_prefix}-${var.environment}-kv"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  enable_rbac_authorization = true

  tags = {
    Environment = var.environment
  }
}

data "azurerm_client_config" "current" {}

locals {
  database_url = "postgresql://${azurerm_postgresql_flexible_server.main.administrator_login}:${random_password.db_password.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${var.postgres_database_name}"
  redis_url    = "rediss://:${azurerm_redis_cache.main.primary_access_key}@${azurerm_redis_cache.main.hostname}:${azurerm_redis_cache.main.ssl_port}/0"
}

resource "azurerm_user_assigned_identity" "key_vault_workload" {
  name                = "${var.resource_prefix}-${var.environment}-kv-identity"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

resource "azurerm_role_assignment" "key_vault_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "key_vault_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.key_vault_workload.principal_id
}

resource "azurerm_federated_identity_credential" "key_vault" {
  count               = var.workload_identity_issuer_url != "" && var.workload_identity_subject != "" ? 1 : 0
  name                = "${var.resource_prefix}-${var.environment}-kv-fic"
  resource_group_name = azurerm_resource_group.main.name
  parent_id           = azurerm_user_assigned_identity.key_vault_workload.id
  issuer              = var.workload_identity_issuer_url
  subject             = var.workload_identity_subject
  audience            = [var.workload_identity_audience]
}

# Storage Account for Data Lake
resource "azurerm_storage_account" "main" {
  name                     = "${var.resource_prefix}${var.environment}storage"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true  # Enable Data Lake Gen2
  allow_blob_public_access = false

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_storage_container" "audit_events" {
  name                  = "audit-events"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
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

resource "azurerm_key_vault_secret" "database_url" {
  name         = "database-url"
  value        = local.database_url
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "redis_url" {
  name         = "redis-url"
  value        = local.redis_url
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "azure_openai_endpoint" {
  name         = "azure-openai-endpoint"
  value        = azurerm_cognitive_account.openai.endpoint
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "azure_openai_api_key" {
  name         = "azure-openai-api-key"
  value        = var.azure_openai_api_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "identity_client_secret" {
  name         = "identity-client-secret"
  value        = var.identity_client_secret
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "service_bus_connection" {
  name         = "servicebus-connection"
  value        = var.service_bus_connection_string
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "storage_account_key" {
  name         = "storage-account-key"
  value        = azurerm_storage_account.main.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
}

# Outputs
output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "container_registry_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "postgresql_fqdn" {
  value     = azurerm_postgresql_flexible_server.main.fqdn
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
  value = azurerm_key_vault.main.vault_uri
}

output "key_vault_workload_identity_client_id" {
  value     = azurerm_user_assigned_identity.key_vault_workload.client_id
  sensitive = true
}
