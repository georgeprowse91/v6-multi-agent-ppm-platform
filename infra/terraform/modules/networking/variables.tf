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

variable "vnet_address_space" {
  type = list(string)
}

variable "private_endpoint_subnet_address_prefixes" {
  type = list(string)
}

variable "aks_subnet_address_prefixes" {
  type = list(string)
}

variable "app_gateway_subnet_address_prefixes" {
  type = list(string)
}
