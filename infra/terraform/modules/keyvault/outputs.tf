output "key_vault_id" {
  value = azurerm_key_vault.main.id
}

output "vault_uri" {
  value = azurerm_key_vault.main.vault_uri
}

output "workload_identity_client_id" {
  value     = azurerm_user_assigned_identity.key_vault_workload.client_id
  sensitive = true
}
