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

variable "oncall_email" {
  description = "Email address for on-call notifications (critical alerts)"
  type        = string
  default     = "platform-oncall@example.com"
}

variable "ops_email" {
  description = "Email address for platform operations (warning alerts)"
  type        = string
  default     = "platform-ops@example.com"
}

variable "pagerduty_webhook_url" {
  description = "PagerDuty webhook URL for critical alerts"
  type        = string
  default     = ""
}

variable "aks_cluster_id" {
  description = "Azure resource ID of the AKS cluster for container metrics"
  type        = string
}

variable "postgresql_server_id" {
  description = "Azure resource ID of the PostgreSQL server for database metrics"
  type        = string
}
