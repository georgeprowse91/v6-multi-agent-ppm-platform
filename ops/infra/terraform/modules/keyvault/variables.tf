variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_prefix" {
  type = string
}

variable "environment" {
  type = string
}

variable "key_vault_name" {
  type = string
}

variable "tenant_id" {
  type = string
}

variable "current_object_id" {
  type = string
}

variable "workload_identity_subject" {
  type    = string
  default = ""
}

variable "workload_identity_audience" {
  type = string
}

variable "workload_identity_issuer_url" {
  type = string
}

variable "redis_url" {
  type      = string
  sensitive = true
}

variable "azure_openai_endpoint" {
  type = string
}

variable "azure_openai_api_key" {
  type      = string
  sensitive = true
}

variable "identity_client_secret" {
  type      = string
  sensitive = true
}

variable "service_bus_connection_string" {
  type      = string
  sensitive = true
}

variable "storage_account_key" {
  type      = string
  sensitive = true
}

variable "audit_worm_connection_string" {
  type      = string
  sensitive = true
}

variable "audit_log_encryption_key" {
  type      = string
  sensitive = true
}

variable "azure_monitor_connection_string" {
  type      = string
  sensitive = true
}

variable "ops_email" {
  description = "Email address for platform operations notifications"
  type        = string
  default     = "platform-ops@example.com"
}

variable "rotation_webhook_url" {
  description = "Webhook URL for secret rotation automation (required when enable_rotation_webhook is true)"
  type        = string
  default     = ""

  validation {
    condition     = var.rotation_webhook_url == "" || can(regex("^https://", var.rotation_webhook_url))
    error_message = "rotation_webhook_url must be a valid HTTPS URL when provided."
  }
}

variable "enable_rotation_webhook" {
  description = "Enable Event Grid webhook notifications for Key Vault secret expiry events"
  type        = bool
  default     = false
}
