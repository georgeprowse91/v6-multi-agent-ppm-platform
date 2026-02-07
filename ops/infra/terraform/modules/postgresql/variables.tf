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

variable "postgres_sku_name" {
  type = string
}

variable "postgres_storage_mb" {
  type = number
}

variable "postgres_backup_retention_days" {
  type = number
}

variable "postgres_geo_redundant_backup_enabled" {
  type = bool
}

variable "postgres_ha_mode" {
  type = string
}

variable "postgres_primary_zone" {
  type = string
}

variable "postgres_standby_zone" {
  type = string
}

variable "postgres_minimum_tls_version" {
  type = string
}

variable "private_endpoint_subnet_id" {
  type = string
}

variable "private_dns_zone_id" {
  type = string
}
