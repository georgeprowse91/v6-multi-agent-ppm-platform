resource "azurerm_key_vault" "main" {
  name                = var.key_vault_name
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  enable_rbac_authorization = true
  public_network_access_enabled = false

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
  }

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_user_assigned_identity" "key_vault_workload" {
  name                = "${var.resource_prefix}-${var.environment}-kv-identity"
  resource_group_name = var.resource_group_name
  location            = var.location
}

resource "azurerm_role_assignment" "key_vault_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = var.current_object_id
}

resource "azurerm_role_assignment" "key_vault_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.key_vault_workload.principal_id
}

resource "azurerm_federated_identity_credential" "key_vault" {
  count               = var.workload_identity_subject != "" ? 1 : 0
  name                = "${var.resource_prefix}-${var.environment}-kv-fic"
  resource_group_name = var.resource_group_name
  parent_id           = azurerm_user_assigned_identity.key_vault_workload.id
  issuer              = var.workload_identity_issuer_url
  subject             = var.workload_identity_subject
  audience            = [var.workload_identity_audience]
}

locals {
  secrets = {
    "redis-url"                  = var.redis_url
    "azure-openai-endpoint"      = var.azure_openai_endpoint
    "azure-openai-api-key"       = var.azure_openai_api_key
    "identity-client-secret"     = var.identity_client_secret
    "servicebus-connection"      = var.service_bus_connection_string
    "storage-account-key"        = var.storage_account_key
    "audit-worm-connection-string" = var.audit_worm_connection_string
    "audit-log-encryption-key"   = var.audit_log_encryption_key
    "azure-monitor-connection-string" = var.azure_monitor_connection_string
  }
}

resource "azurerm_key_vault_secret" "secrets" {
  for_each     = { for key, value in local.secrets : key => value if value != "" }
  name         = each.key
  value        = each.value
  key_vault_id = azurerm_key_vault.main.id

  # Set expiration date based on rotation policy
  expiration_date = timeadd(timestamp(), local.secret_rotation_periods[each.key])

  tags = {
    rotation-policy = local.secret_rotation_policies[each.key]
    managed-by      = "terraform"
  }

  lifecycle {
    ignore_changes = [expiration_date, value]
  }
}

# Secret rotation policies
locals {
  # Rotation periods for different secret types
  secret_rotation_policies = {
    "redis-url"                       = "180-days"
    "azure-openai-endpoint"           = "365-days"
    "azure-openai-api-key"            = "90-days"
    "identity-client-secret"          = "90-days"
    "servicebus-connection"           = "180-days"
    "storage-account-key"             = "180-days"
    "audit-worm-connection-string"    = "180-days"
    "audit-log-encryption-key"        = "365-days"
    "azure-monitor-connection-string" = "365-days"
  }

  secret_rotation_periods = {
    "redis-url"                       = "4320h"  # 180 days
    "azure-openai-endpoint"           = "8760h"  # 365 days
    "azure-openai-api-key"            = "2160h"  # 90 days
    "identity-client-secret"          = "2160h"  # 90 days
    "servicebus-connection"           = "4320h"  # 180 days
    "storage-account-key"             = "4320h"  # 180 days
    "audit-worm-connection-string"    = "4320h"  # 180 days
    "audit-log-encryption-key"        = "8760h"  # 365 days
    "azure-monitor-connection-string" = "8760h"  # 365 days
  }
}

# Event Grid subscription for secret expiration notifications
resource "azurerm_eventgrid_system_topic" "keyvault" {
  name                   = "${var.resource_prefix}-${var.environment}-kv-events"
  resource_group_name    = var.resource_group_name
  location               = var.location
  source_arm_resource_id = azurerm_key_vault.main.id
  topic_type             = "Microsoft.KeyVault.vaults"

  tags = {
    Environment = var.environment
  }
}

# Alert action group for secret rotation notifications
resource "azurerm_monitor_action_group" "secret_rotation" {
  name                = "${var.resource_prefix}-${var.environment}-secret-rotation-ag"
  resource_group_name = var.resource_group_name
  short_name          = "SecRotation"

  email_receiver {
    name                    = "platform-ops"
    email_address           = var.ops_email
    use_common_alert_schema = true
  }

  dynamic "webhook_receiver" {
    for_each = var.enable_rotation_webhook ? [1] : []
    content {
      name        = "rotation-webhook"
      service_uri = var.rotation_webhook_url
    }
  }
}

# Event Grid subscription for secret near-expiry events
resource "azurerm_eventgrid_system_topic_event_subscription" "secret_near_expiry" {
  count               = var.enable_rotation_webhook ? 1 : 0
  name                = "${var.resource_prefix}-${var.environment}-secret-expiry-sub"
  system_topic        = azurerm_eventgrid_system_topic.keyvault.name
  resource_group_name = var.resource_group_name

  included_event_types = [
    "Microsoft.KeyVault.SecretNearExpiry",
    "Microsoft.KeyVault.SecretExpired"
  ]

  webhook_endpoint {
    url = var.rotation_webhook_url
  }

  retry_policy {
    max_delivery_attempts = 30
    event_time_to_live    = 1440
  }

  lifecycle {
    precondition {
      condition     = trimspace(var.rotation_webhook_url) != ""
      error_message = "rotation_webhook_url must be provided when enable_rotation_webhook is true."
    }
  }
}
