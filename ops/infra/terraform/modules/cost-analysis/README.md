# Cost Analysis Terraform Module

This module provisions an Azure Cost Management export at subscription scope and configures a dedicated storage container for exported reports.

## Inputs

- `subscription_id`: Azure subscription ID where the cost export is created.
- `export_storage_account_id`: Resource ID of the storage account that will host export files.
- `environment`: Environment label used in naming.
- `resource_prefix`: Prefix applied to resource names.
- `export_storage_container_name` (optional): Blob container for export data. Defaults to `cost-exports`.
- `export_root_folder_path` (optional): Folder path inside the container. Defaults to `cost-management`.
- `recurrence_period_start_date` (optional): RFC3339 start date for export schedule.
- `recurrence_period_end_date` (optional): RFC3339 end date for export schedule.

## Outputs

- `cost_management_export_id`: ID of the created cost management export.
- `cost_export_container_id`: ID of the storage container for exported files.
