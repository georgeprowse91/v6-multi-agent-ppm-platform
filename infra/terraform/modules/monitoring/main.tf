resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.resource_prefix}-${var.environment}-logs"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30
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

# Alert: High API Error Rate (>5% 5xx errors)
resource "azurerm_monitor_metric_alert" "api_error_rate" {
  name                = "${var.resource_prefix}-${var.environment}-api-error-rate"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_application_insights.main.id]
  description         = "Alert when API error rate exceeds 5%"
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/failed"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = 50
  }

  action {
    action_group_id = azurerm_monitor_action_group.critical.id
  }

  tags = {
    Environment = var.environment
    AlertType   = "error-rate"
  }
}

# Alert: High API Latency (P95 > 2s)
resource "azurerm_monitor_metric_alert" "api_latency" {
  name                = "${var.resource_prefix}-${var.environment}-api-latency"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_application_insights.main.id]
  description         = "Alert when API P95 latency exceeds 2 seconds"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/duration"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 2000
  }

  action {
    action_group_id = azurerm_monitor_action_group.warning.id
  }

  tags = {
    Environment = var.environment
    AlertType   = "latency"
  }
}

# Alert: High Memory Usage (>85%)
resource "azurerm_monitor_metric_alert" "memory_usage" {
  name                = "${var.resource_prefix}-${var.environment}-memory-usage"
  resource_group_name = var.resource_group_name
  scopes              = [var.aks_cluster_id]
  description         = "Alert when container memory usage exceeds 85%"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Insights.Container/pods"
    metric_name      = "memoryWorkingSetPercentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 85
  }

  action {
    action_group_id = azurerm_monitor_action_group.warning.id
  }

  tags = {
    Environment = var.environment
    AlertType   = "resource"
  }
}

# Alert: High CPU Usage (>80%)
resource "azurerm_monitor_metric_alert" "cpu_usage" {
  name                = "${var.resource_prefix}-${var.environment}-cpu-usage"
  resource_group_name = var.resource_group_name
  scopes              = [var.aks_cluster_id]
  description         = "Alert when container CPU usage exceeds 80%"
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Insights.Container/pods"
    metric_name      = "cpuExceededPercentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.warning.id
  }

  tags = {
    Environment = var.environment
    AlertType   = "resource"
  }
}

# Alert: Database Connection Failures
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
    threshold        = 10
  }

  action {
    action_group_id = azurerm_monitor_action_group.critical.id
  }

  tags = {
    Environment = var.environment
    AlertType   = "database"
  }
}

# Alert: Agent Execution Failures
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
      | where FailureCount > 10
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
  }
}

# Alert: Authentication Failures (potential security incident)
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
      | where FailureCount > 100
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
  }
}

# Alert: Service Health (availability < 99.9%)
resource "azurerm_monitor_metric_alert" "availability" {
  name                = "${var.resource_prefix}-${var.environment}-availability"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_application_insights.main.id]
  description         = "Alert when service availability drops below 99.9%"
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "availabilityResults/availabilityPercentage"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 99.9
  }

  action {
    action_group_id = azurerm_monitor_action_group.critical.id
  }

  tags = {
    Environment = var.environment
    AlertType   = "availability"
  }
}
