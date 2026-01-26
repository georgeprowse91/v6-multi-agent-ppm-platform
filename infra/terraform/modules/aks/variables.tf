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

variable "dns_prefix" {
  type = string
}

variable "aks_subnet_id" {
  type = string
}

variable "private_dns_zone_id" {
  type = string
}

variable "system_node_vm_size" {
  type = string
}

variable "system_node_count" {
  type = number
}

variable "user_node_vm_size" {
  type = string
}

variable "user_node_count" {
  type = number
}

variable "user_node_min_count" {
  type = number
}

variable "user_node_max_count" {
  type = number
}

variable "admin_group_object_ids" {
  type = list(string)
}

variable "acr_id" {
  type = string
}
