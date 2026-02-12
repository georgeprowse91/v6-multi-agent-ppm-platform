environment     = "stage"
location        = "eastus"
resource_prefix = "ppm"

# Monitoring overrides (stage)
monitoring_log_retention_in_days                    = 60
monitoring_api_error_rate_threshold_count           = 75
monitoring_api_latency_p95_threshold_ms             = 2500
monitoring_memory_usage_threshold_percent           = 88
monitoring_cpu_usage_threshold_percent              = 85
monitoring_db_connection_failures_threshold_count   = 15
monitoring_agent_failures_threshold_count           = 15
monitoring_auth_failures_threshold_count            = 150
monitoring_availability_threshold_percent           = 99.5
monitoring_deployment_failures_threshold_count      = 2
monitoring_secret_rotation_failures_threshold_count = 1
monitoring_cert_expiry_threshold_days               = 21
monitoring_backup_failures_threshold_count          = 1
