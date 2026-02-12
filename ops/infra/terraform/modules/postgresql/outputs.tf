output "administrator_login" {
  value     = local.administrator_login
  sensitive = true
}

output "fqdn" {
  value     = azurerm_postgresql_flexible_server.main.fqdn
  sensitive = true
}

output "server_id" {
  value = azurerm_postgresql_flexible_server.main.id
}

output "database_url_secret_id" {
  value     = azurerm_key_vault_secret.postgres_database_url.versionless_id
  sensitive = true
}

output "administrator_password_secret_id" {
  value     = azurerm_key_vault_secret.postgres_admin_password.versionless_id
  sensitive = true
}
