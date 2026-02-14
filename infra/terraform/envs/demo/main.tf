locals {
  normalized_prefix = lower(replace(var.name_prefix, "_", "-"))
}

resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
}

resource "azurerm_resource_group" "demo" {
  name     = var.resource_group_name
  location = var.region
  tags     = var.tags
}

resource "azurerm_storage_account" "demo" {
  name                            = substr(replace("${local.normalized_prefix}${random_string.suffix.result}", "-", ""), 0, 24)
  resource_group_name             = azurerm_resource_group.demo.name
  location                        = azurerm_resource_group.demo.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  tags                            = var.tags
}

resource "azurerm_postgresql_flexible_server" "demo" {
  name                   = "${local.normalized_prefix}-pg-${random_string.suffix.result}"
  resource_group_name    = azurerm_resource_group.demo.name
  location               = azurerm_resource_group.demo.location
  version                = "15"
  administrator_login    = "ppmadmin"
  administrator_password = "ChangeMe-DemoOnly-123!"
  zone                   = "1"
  sku_name               = var.postgres_sku_name
  storage_mb             = var.postgres_storage_mb

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false
  high_availability {
    mode = "Disabled"
  }

  tags = var.tags
}

resource "azurerm_kubernetes_cluster" "demo" {
  name                = "${local.normalized_prefix}-aks"
  location            = azurerm_resource_group.demo.location
  resource_group_name = azurerm_resource_group.demo.name
  dns_prefix          = "${local.normalized_prefix}-dns"

  default_node_pool {
    name       = "system"
    vm_size    = "Standard_B2s"
    node_count = var.aks_node_count
  }

  identity {
    type = "SystemAssigned"
  }

  sku_tier = "Free"
  tags     = var.tags
}
