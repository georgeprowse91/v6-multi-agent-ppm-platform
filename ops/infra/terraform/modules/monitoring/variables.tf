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

variable "log_retention_in_days" {
  description = "Retention period for Log Analytics data. Default is 90 days to support audit/SOX-style investigations."
  type        = number
  default     = 90
}

variable "api_error_rate_threshold_count" {
  description = "Failed request count in a 5m window before alerting. SLO/SLA mapping: protects API availability SLA by detecting sustained 5xx spikes early."
  type        = number
  default     = 50
}

variable "api_latency_p95_threshold_ms" {
  description = "P95 API latency threshold in milliseconds. SLO/SLA mapping: supports responsiveness SLO (target p95 below this threshold)."
  type        = number
  default     = 2000
}

variable "memory_usage_threshold_percent" {
  description = "Container memory utilization threshold percentage. SLO/SLA mapping: capacity guardrail to avoid latency/availability SLA degradation."
  type        = number
  default     = 85
}

variable "cpu_usage_threshold_percent" {
  description = "Container CPU utilization threshold percentage. SLO/SLA mapping: capacity guardrail to preserve throughput/latency SLOs."
  type        = number
  default     = 80
}

variable "db_connection_failures_threshold_count" {
  description = "Database failed connection count per 5m window. SLO/SLA mapping: protects transaction success SLA for data-plane requests."
  type        = number
  default     = 10
}

variable "agent_failures_threshold_count" {
  description = "Agent execution failures per 5m bucket before alerting. SLO/SLA mapping: supports automation reliability SLO for agent workflows."
  type        = number
  default     = 10
}

variable "auth_failures_threshold_count" {
  description = "Authentication failures per 1m bucket before alerting. SLO/SLA mapping: security SLA guardrail for abuse/credential-stuffing detection."
  type        = number
  default     = 100
}

variable "availability_threshold_percent" {
  description = "Minimum service availability percentage before firing a critical alert. SLO/SLA mapping: direct mapping to external uptime SLA objective."
  type        = number
  default     = 99.9
}

variable "deployment_failures_threshold_count" {
  description = "Deployment pipeline failures per 15m window. SLO/SLA mapping: release reliability SLO for safe, repeatable deployments."
  type        = number
  default     = 1
}

variable "secret_rotation_failures_threshold_count" {
  description = "Secret rotation failures per 60m window. SLO/SLA mapping: security operations SLA for key/secret lifecycle compliance."
  type        = number
  default     = 1
}

variable "cert_expiry_threshold_days" {
  description = "Days-to-expiry threshold for certificate validity alerts. SLO/SLA mapping: prevents certificate-driven downtime and preserves availability SLA."
  type        = number
  default     = 30
}

variable "backup_failures_threshold_count" {
  description = "Backup job failures per 24h window. SLO/SLA mapping: data durability and recoverability SLA guardrail."
  type        = number
  default     = 1
}
