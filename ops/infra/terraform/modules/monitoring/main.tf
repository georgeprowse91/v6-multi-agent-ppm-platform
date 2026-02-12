resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.resource_prefix}-${var.environment}-logs"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_in_days
}

# Application Insights for application monitoring
resource "azurerm_application_insights" "main" {
  name                = "${var.resource_prefix}-${var.environment}-appinsights"
  location            = var.location
  resource_group_name = var.resource_group_name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = {
    Environment = var.environment
  }
}

# Action group for critical alerts
resource "azurerm_monitor_action_group" "critical" {
  name                = "${var.resource_prefix}-${var.environment}-critical-ag"
  resource_group_name = var.resource_group_name
  short_name          = "Critical"

  email_receiver {
    name                    = "platform-oncall"
    email_address           = var.oncall_email
    use_common_alert_schema = true
  }

  dynamic "webhook_receiver" {
    for_each = var.pagerduty_webhook_url != "" ? [1] : []
    content {
      name        = "pagerduty"
      service_uri = var.pagerduty_webhook_url
    }
  }
}

# Action group for warning alerts
resource "azurerm_monitor_action_group" "warning" {
  name                = "${var.resource_prefix}-${var.environment}-warning-ag"
  resource_group_name = var.resource_group_name
  short_name          = "Warning"

  email_receiver {
    name                    = "platform-ops"
    email_address           = var.ops_email
    use_common_alert_schema = true
  }
}

# Alert: High API Error Rate
# SLO/SLA mapping: Detects sustained 5xx spikes before they breach customer-facing availability/error-budget targets.
resource "azurerm_monitor_metric_alert" "api_error_rate" {
  name                = "${var.resource_prefix}-${var.environment}-api-error-rate"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_application_insights.main.id]
  description         = "Alert when API failed request count exceeds the configured threshold"
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/failed"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = var.api_error_rate_threshold_count
  }

  action {
    action_group_id = azurerm_monitor_action_group.critical.id
  }

  tags = {
    Environment = var.environment
    AlertType   = "error-rate"
    SLOMapping  = "Availability error-budget protection"
  }
}

# Alert: High API Latency
# SLO/SLA mapping: Enforces the API latency SLO by monitoring p95 response time.
resource "azurerm_monitor_metric_alert" "api_latency" {
  name                = "${var.resource_prefix}-${var.environment}-api-latency"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_application_insights.main.id]
  description         = "Alert when API P95 latency exceeds configured threshold"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/duration"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = var.api_latency_p95_threshold_ms
  }

  action {
    action_group_id = azurerm_monitor_action_group.warning.id
  }

  tags = {
    Environment = var.environment
    AlertType   = "latency"
    SLOMapping  = "Latency p95 objective"
  }
}

# Alert: High Memory Usage
# SLO/SLA mapping: Early signal for pod resource saturation that can cause user-visible latency/availability degradation.
resource "azurerm_monitor_metric_alert" "memory_usage" {
  name                = "${var.resource_prefix}-${var.environment}-memory-usage"
  resource_group_name = var.resource_group_name
  scopes              = [var.aks_cluster_id]
  description         = "Alert when container memory usage exceeds configured threshold"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Insights.Container/pods"
    metric_name      = "memoryWorkingSetPercentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = var.memory_usage_threshold_percent
  }

  action {
    action_group_id = azurerm_monitor_action_group.warning.id
  }

  tags = {
    Environment = var.environment
    AlertType   = "resource"
    SLOMapping  = "Capacity safeguard for latency/availability"
  }
}

# Alert: High CPU Usage
# SLO/SLA mapping: Capacity signal for workload throttling risk that impacts throughput and latency commitments.
resource "azurerm_monitor_metric_alert" "cpu_usage" {
  name                = "${var.resource_prefix}-${var.environment}-cpu-usage"
  resource_group_name = var.resource_group_name
  scopes              = [var.aks_cluster_id]
  description         = "Alert when container CPU usage exceeds configured threshold"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Insights.Container/pods"
    metric_name      = "cpuExceededPercentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = var.cpu_usage_threshold_percent
  }

  action {
    action_group_id = azurerm_monitor_action_group.warning.id
  }

  tags = {
    Environment = var.environment
    AlertType   = "resource"
    SLOMapping  = "Capacity safeguard for latency/throughput"
  }
}

# Alert: Database Connection Failures
# SLO/SLA mapping: Preserves transaction success SLO by detecting database connectivity regressions.
resource "azurerm_monitor_metric_alert" "db_connection_failures" {
  name                = "${var.resource_prefix}-${var.environment}-db-connection-failures"
  resource_group_name = var.resource_group_name
  scopes              = [var.postgresql_server_id]
  description         = "Alert when database connection failures occur"
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.DBforPostgreSQL/flexibleServers"
    metric_name      = "connections_failed"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = var.db_connection_failures_threshold_count
  }

  action {
    action_group_id = azurerm_monitor_action_group.critical.id
  }

  tags = {
    Environment = var.environment
    AlertType   = "database"
    SLOMapping  = "Transaction success objective"
  }
}

# Alert: Agent Execution Failures
# SLO/SLA mapping: Protects automation execution reliability SLO.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "agent_failures" {
  name                = "${var.resource_prefix}-${var.environment}-agent-failures"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "Alert when agent execution failure rate is high"
  severity            = 2

  scopes                   = [azurerm_application_insights.main.id]
  evaluation_frequency     = "PT5M"
  window_duration          = "PT15M"
  target_resource_types    = ["microsoft.insights/components"]

  criteria {
    query = <<-QUERY
      customEvents
      | where name == "agent_execution"
      | where customDimensions.outcome == "error"
      | summarize FailureCount = count() by bin(timestamp, 5m)
      | where FailureCount > ${var.agent_failures_threshold_count}
    QUERY

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.warning.id]
  }

  tags = {
    Environment = var.environment
    AlertType   = "agent"
    SLOMapping  = "Agent workflow reliability"
  }
}

# Alert: Authentication Failures (potential security incident)
# SLO/SLA mapping: Security operations SLA for attack/fraud response.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "auth_failures" {
  name                = "${var.resource_prefix}-${var.environment}-auth-failures"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "Alert on high authentication failure rate (potential attack)"
  severity            = 1

  scopes                   = [azurerm_application_insights.main.id]
  evaluation_frequency     = "PT1M"
  window_duration          = "PT5M"
  target_resource_types    = ["microsoft.insights/components"]

  criteria {
    query = <<-QUERY
      requests
      | where resultCode == "401" or resultCode == "403"
      | summarize FailureCount = count() by bin(timestamp, 1m)
      | where FailureCount > ${var.auth_failures_threshold_count}
    QUERY

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.critical.id]
  }

  tags = {
    Environment = var.environment
    AlertType   = "security"
    SLOMapping  = "Security incident detection"
  }
}

# Alert: Service Health
# SLO/SLA mapping: Directly tied to the customer-facing uptime SLA.
resource "azurerm_monitor_metric_alert" "availability" {
  name                = "${var.resource_prefix}-${var.environment}-availability"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_application_insights.main.id]
  description         = "Alert when service availability drops below configured SLA threshold"
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "availabilityResults/availabilityPercentage"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = var.availability_threshold_percent
  }

  action {
    action_group_id = azurerm_monitor_action_group.critical.id
  }

  tags = {
    Environment = var.environment
    AlertType   = "availability"
    SLOMapping  = "Uptime SLA"
  }
}

# Alert: Deployment Failures
# SLO/SLA mapping: Protects release reliability SLO and change-failure-rate objectives.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "deployment_failures" {
  name                = "${var.resource_prefix}-${var.environment}-deployment-failures"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "Alert on deployment failures"
  severity            = 1

  scopes                = [azurerm_application_insights.main.id]
  evaluation_frequency  = "PT5M"
  window_duration       = "PT15M"
  target_resource_types = ["microsoft.insights/components"]

  criteria {
    query = <<-QUERY
      customEvents
      | where name == "deployment"
      | where tostring(customDimensions.status) == "failed"
      | summarize FailureCount = count() by bin(timestamp, 15m)
      | where FailureCount >= ${var.deployment_failures_threshold_count}
    QUERY

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.critical.id]
  }

  tags = {
    Environment = var.environment
    AlertType   = "deployment"
    SLOMapping  = "Release reliability"
  }
}

# Alert: Secret Rotation Failures
# SLO/SLA mapping: Protects security lifecycle SLA for secret/key hygiene.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "secret_rotation_failures" {
  name                = "${var.resource_prefix}-${var.environment}-secret-rotation-failures"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "Alert on secret rotation failures"
  severity            = 1

  scopes                = [azurerm_application_insights.main.id]
  evaluation_frequency  = "PT15M"
  window_duration       = "PT1H"
  target_resource_types = ["microsoft.insights/components"]

  criteria {
    query = <<-QUERY
      customEvents
      | where name == "secret_rotation"
      | where tostring(customDimensions.status) == "failed"
      | summarize FailureCount = count() by bin(timestamp, 1h)
      | where FailureCount >= ${var.secret_rotation_failures_threshold_count}
    QUERY

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.critical.id]
  }

  tags = {
    Environment = var.environment
    AlertType   = "security"
    SLOMapping  = "Secret lifecycle compliance"
  }
}

# Alert: Certificate Expiry Risk
# SLO/SLA mapping: Prevents certificate expiration outages that violate uptime SLA.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "certificate_expiry" {
  name                = "${var.resource_prefix}-${var.environment}-certificate-expiry"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "Alert when certificates are near expiry"
  severity            = 1

  scopes                = [azurerm_application_insights.main.id]
  evaluation_frequency  = "PT1H"
  window_duration       = "P1D"
  target_resource_types = ["microsoft.insights/components"]

  criteria {
    query = <<-QUERY
      customEvents
      | where name == "certificate_health"
      | extend DaysUntilExpiry = toint(customDimensions.days_until_expiry)
      | where DaysUntilExpiry <= ${var.cert_expiry_threshold_days}
      | summarize ExpiringCerts = count() by bin(timestamp, 1d)
      | where ExpiringCerts > 0
    QUERY

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.warning.id]
  }

  tags = {
    Environment = var.environment
    AlertType   = "certificate"
    SLOMapping  = "Certificate validity for uptime SLA"
  }
}

# Alert: Backup Failures
# SLO/SLA mapping: Protects backup/recovery SLA and recovery-point objective commitments.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "backup_failures" {
  name                = "${var.resource_prefix}-${var.environment}-backup-failures"
  resource_group_name = var.resource_group_name
  location            = var.location
  description         = "Alert on backup failures"
  severity            = 1

  scopes                = [azurerm_application_insights.main.id]
  evaluation_frequency  = "PT1H"
  window_duration       = "P1D"
  target_resource_types = ["microsoft.insights/components"]

  criteria {
    query = <<-QUERY
      customEvents
      | where name == "backup_job"
      | where tostring(customDimensions.status) == "failed"
      | summarize FailureCount = count() by bin(timestamp, 1d)
      | where FailureCount >= ${var.backup_failures_threshold_count}
    QUERY

    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.critical.id]
  }

  tags = {
    Environment = var.environment
    AlertType   = "backup"
    SLOMapping  = "Data durability and recoverability"
  }
}
