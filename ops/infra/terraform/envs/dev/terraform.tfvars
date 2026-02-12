environment     = "dev"
location        = "eastus"
resource_prefix = "ppm"

# Monitoring overrides (dev)
monitoring_log_retention_in_days                    = 30
monitoring_api_error_rate_threshold_count           = 100
monitoring_api_latency_p95_threshold_ms             = 3000
monitoring_memory_usage_threshold_percent           = 90
monitoring_cpu_usage_threshold_percent              = 90
monitoring_db_connection_failures_threshold_count   = 25
monitoring_agent_failures_threshold_count           = 25
monitoring_auth_failures_threshold_count            = 200
monitoring_availability_threshold_percent           = 99.0
monitoring_deployment_failures_threshold_count      = 3
monitoring_secret_rotation_failures_threshold_count = 2
monitoring_cert_expiry_threshold_days               = 14
monitoring_backup_failures_threshold_count          = 2
