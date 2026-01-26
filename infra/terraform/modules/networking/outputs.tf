output "vnet_id" {
  value = azurerm_virtual_network.main.id
}

output "private_endpoint_subnet_id" {
  value = azurerm_subnet.private_endpoints.id
}

output "aks_subnet_id" {
  value = azurerm_subnet.aks.id
}

output "app_gateway_subnet_id" {
  value = azurerm_subnet.app_gateway.id
}

output "private_dns_zone_ids" {
  value = {
    acr         = azurerm_private_dns_zone.acr.id
    postgres    = azurerm_private_dns_zone.postgres.id
    redis       = azurerm_private_dns_zone.redis.id
    key_vault   = azurerm_private_dns_zone.key_vault.id
    storage_blob = azurerm_private_dns_zone.storage_blob.id
    storage_dfs  = azurerm_private_dns_zone.storage_dfs.id
    service_bus = azurerm_private_dns_zone.service_bus.id
    openai      = azurerm_private_dns_zone.openai.id
    cosmos      = azurerm_private_dns_zone.cosmos.id
    aks         = azurerm_private_dns_zone.aks.id
  }
}
