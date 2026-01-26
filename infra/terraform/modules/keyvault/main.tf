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
    "database-url"               = var.database_url
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
  for_each   = { for key, value in local.secrets : key => value if value != "" }
  name       = each.key
  value      = each.value
  key_vault_id = azurerm_key_vault.main.id
}
