output "cost_management_export_id" {
  description = "Azure resource ID of the cost management export"
  value       = azurerm_subscription_cost_management_export.this.id
}

output "cost_export_container_id" {
  description = "Azure resource ID of the cost export storage container"
  value       = azurerm_storage_container.cost_exports.id
}
