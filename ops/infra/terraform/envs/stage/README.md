# Stage Environment

Terraform overlay for the stage environment. Use this directory to define stage-specific
variables, backends, and overrides (network CIDRs, scaling parameters, tags).

## Usage

1. Copy required `*.tfvars` files into this directory.
2. Run `terraform init` from `infra/terraform` with the stage backend configuration.
3. Apply with `terraform workspace select stage` and `terraform apply -var-file=envs/stage/stage.tfvars`.
