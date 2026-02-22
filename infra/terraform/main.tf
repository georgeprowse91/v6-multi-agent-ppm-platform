# PPM Platform – Azure Infrastructure (Terraform)
# Production storage, WORM audit, and lifecycle management.

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  backend "azurerm" {
    resource_group_name  = "ppm-tfstate-rg"
    storage_account_name = "ppmtfstate"
    container_name       = "tfstate"
    key                  = "prod.terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
}

# ---------------------------------------------------------------------------
# Resource groups
# ---------------------------------------------------------------------------

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.common_tags
}

# ---------------------------------------------------------------------------
# Storage account for PPM data
# ---------------------------------------------------------------------------

resource "azurerm_storage_account" "ppm" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  min_tls_version          = "TLS1_2"
  blob_properties {
    versioning_enabled  = true
    change_feed_enabled = true
    delete_retention_policy {
      days = 30
    }
  }
  tags = var.common_tags
}

# ---------------------------------------------------------------------------
# Storage containers with classification-based lifecycle rules
# ---------------------------------------------------------------------------

resource "azurerm_storage_management_policy" "lifecycle" {
  storage_account_id = azurerm_storage_account.ppm.id

  rule {
    name    = "public-lifecycle"
    enabled = true
    filters {
      prefix_match = ["public/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = 30
        tier_to_archive_after_days_since_modification_greater_than = 90
        delete_after_days_since_modification_greater_than          = 365
      }
    }
  }

  rule {
    name    = "internal-lifecycle"
    enabled = true
    filters {
      prefix_match = ["internal/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = 60
        tier_to_archive_after_days_since_modification_greater_than = 180
        delete_after_days_since_modification_greater_than          = 730
      }
    }
  }

  rule {
    name    = "confidential-lifecycle"
    enabled = true
    filters {
      prefix_match = ["confidential/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = 90
        tier_to_archive_after_days_since_modification_greater_than = 365
      }
    }
  }

  rule {
    name    = "restricted-lifecycle"
    enabled = true
    filters {
      prefix_match = ["restricted/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = 180
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Audit WORM storage with immutability
# ---------------------------------------------------------------------------

resource "azurerm_storage_container" "audit" {
  name                  = "audit-events"
  storage_account_name  = azurerm_storage_account.ppm.name
  container_access_type = "private"
}

resource "azurerm_storage_blob_immutability_policy" "audit_worm" {
  storage_account_id            = azurerm_storage_account.ppm.id
  immutability_period_in_days   = 2555
  state                         = "Locked"
  protected_append_writes_all_enabled = false
}

resource "azurerm_storage_account_blob_container_sas" "audit" {
  connection_string = azurerm_storage_account.ppm.primary_connection_string
  container_name    = azurerm_storage_container.audit.name
}

# Immutable storage configuration for audit log containers
locals {
  immutable_storage_enabled = true
  immutability_policy = {
    enabled                      = true
    period_since_creation_in_days = 2555
    state                        = "Locked"
  }
}

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "ppm-platform-prod"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "storage_account_name" {
  description = "Name of the Azure Storage account"
  type        = string
  default     = "ppmplatformprod"
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    environment = "production"
    project     = "ppm-platform"
    managed_by  = "terraform"
  }
}
