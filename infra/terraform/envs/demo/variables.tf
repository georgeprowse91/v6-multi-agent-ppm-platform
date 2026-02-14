variable "region" {
  description = "Azure region for the demo environment"
  type        = string
  default     = "eastus2"
}

variable "resource_group_name" {
  description = "Name of the resource group for demo resources"
  type        = string
}

variable "name_prefix" {
  description = "Prefix used for naming demo resources"
  type        = string
  default     = "ppm-demo"
}

variable "tags" {
  description = "Tags applied to all demo resources"
  type        = map(string)
  default = {
    environment = "demo"
    managed-by  = "terraform"
    cost-tier   = "low"
  }
}

variable "aks_node_count" {
  description = "Demo AKS node count kept intentionally small for cost control"
  type        = number
  default     = 1
}

variable "postgres_sku_name" {
  description = "Low-cost PostgreSQL SKU for demo workloads"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "postgres_storage_mb" {
  description = "PostgreSQL storage for demo workloads in MB"
  type        = number
  default     = 32768
}
