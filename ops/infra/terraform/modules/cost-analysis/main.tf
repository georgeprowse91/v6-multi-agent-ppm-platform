resource "azurerm_storage_container" "cost_exports" {
  name                  = var.export_storage_container_name
  storage_account_id    = var.export_storage_account_id
  container_access_type = "private"
}

resource "azurerm_subscription_cost_management_export" "this" {
  name                                 = "${var.resource_prefix}-${var.environment}-cost-export"
  subscription_id                      = var.subscription_id
  recurrence_type                      = "Monthly"
  recurrence_period_start_date         = var.recurrence_period_start_date
  recurrence_period_end_date           = var.recurrence_period_end_date

  export_data_options {
    type       = "ActualCost"
    time_frame = "MonthToDate"
  }

  export_data_storage_location {
    container_id     = azurerm_storage_container.cost_exports.id
    root_folder_path = var.export_root_folder_path
  }
}
