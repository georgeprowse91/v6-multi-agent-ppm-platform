output "resource_group_name" {
  description = "Resource group name for demo environment"
  value       = azurerm_resource_group.demo.name
}

output "aks_cluster_name" {
  description = "AKS cluster name for demo environment"
  value       = azurerm_kubernetes_cluster.demo.name
}

output "postgres_server_name" {
  description = "PostgreSQL server name for demo environment"
  value       = azurerm_postgresql_flexible_server.demo.name
}

output "storage_account_name" {
  description = "Storage account for demo logs and artifacts"
  value       = azurerm_storage_account.demo.name
}
