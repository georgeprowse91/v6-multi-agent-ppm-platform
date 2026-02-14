variable "subscription_id" {
  description = "Azure subscription ID for the dev environment"
  type        = string
}

module "cost_analysis" {
  source = "../../modules/cost-analysis"

  environment               = "dev"
  resource_prefix           = "ppm"
  subscription_id           = var.subscription_id
  export_storage_account_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/ppm-dev-shared-rg/providers/Microsoft.Storage/storageAccounts/ppmdevcostexports"
  export_root_folder_path   = "dev/cost-management"
}
