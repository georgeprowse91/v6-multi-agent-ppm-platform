resource "azurerm_kubernetes_cluster" "main" {
  name                = "${var.resource_prefix}-${var.environment}-aks"
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = var.dns_prefix
  private_cluster_enabled = true
  private_dns_zone_id     = var.private_dns_zone_id

  identity {
    type = "SystemAssigned"
  }

  default_node_pool {
    name                = "system"
    vm_size             = var.system_node_vm_size
    node_count          = var.system_node_count
    vnet_subnet_id      = var.aks_subnet_id
    type                = "VirtualMachineScaleSets"
    mode                = "System"
    enable_auto_scaling = false
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
  }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  azure_active_directory_role_based_access_control {
    managed                = true
    azure_rbac_enabled     = true
    admin_group_object_ids = var.admin_group_object_ids
  }

  role_based_access_control_enabled = true

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "user" {
  name                  = "user"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = var.user_node_vm_size
  node_count            = var.user_node_count
  enable_auto_scaling   = true
  min_count             = var.user_node_min_count
  max_count             = var.user_node_max_count
  mode                  = "User"
  vnet_subnet_id        = var.aks_subnet_id

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
}
