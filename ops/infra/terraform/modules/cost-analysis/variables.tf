variable "environment" {
  description = "Environment name"
  type        = string
}

variable "resource_prefix" {
  description = "Prefix for Azure resources"
  type        = string
}

variable "subscription_id" {
  description = "Azure subscription ID to scope the cost management export"
  type        = string
}

variable "export_storage_account_id" {
  description = "Resource ID of the storage account where cost exports are written"
  type        = string
}

variable "export_storage_container_name" {
  description = "Blob container name that stores cost exports"
  type        = string
  default     = "cost-exports"
}

variable "export_root_folder_path" {
  description = "Root folder path used for exported cost files"
  type        = string
  default     = "cost-management"
}

variable "recurrence_period_start_date" {
  description = "Start date for recurring cost exports in RFC3339 format"
  type        = string
  default     = "2024-01-01T00:00:00Z"
}

variable "recurrence_period_end_date" {
  description = "End date for recurring cost exports in RFC3339 format"
  type        = string
  default     = "2034-01-01T00:00:00Z"
}
