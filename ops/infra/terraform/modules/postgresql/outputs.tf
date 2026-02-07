output "administrator_login" {
  value = azurerm_postgresql_flexible_server.main.administrator_login
}

output "administrator_password" {
  value     = random_password.db_password.result
  sensitive = true
}

output "fqdn" {
  value = azurerm_postgresql_flexible_server.main.fqdn
}

output "server_id" {
  value = azurerm_postgresql_flexible_server.main.id
}
