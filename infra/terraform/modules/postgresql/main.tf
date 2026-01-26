resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                = "${var.resource_prefix}-${var.environment}-psql"
  resource_group_name = var.resource_group_name
  location            = var.location

  sku_name   = var.postgres_sku_name
  storage_mb = var.postgres_storage_mb
  version    = "15"

  administrator_login    = "ppmadmin"
  administrator_password = random_password.db_password.result

  backup_retention_days        = var.postgres_backup_retention_days
  geo_redundant_backup_enabled = var.postgres_geo_redundant_backup_enabled
  public_network_access_enabled = false
  zone                          = var.postgres_primary_zone

  dynamic "high_availability" {
    for_each = var.postgres_ha_mode == "Disabled" ? [] : [var.postgres_ha_mode]
    content {
      mode                      = high_availability.value
      standby_availability_zone = var.postgres_standby_zone
    }
  }

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_postgresql_flexible_server_configuration" "minimum_tls_version" {
  name      = "ssl_minimum_tls_version"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = var.postgres_minimum_tls_version
}

resource "azurerm_private_endpoint" "postgres" {
  name                = "${var.resource_prefix}-${var.environment}-postgres-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.resource_prefix}-${var.environment}-postgres-psc"
    private_connection_resource_id = azurerm_postgresql_flexible_server.main.id
    subresource_names              = ["postgresqlServer"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "postgres-dns"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }
}
