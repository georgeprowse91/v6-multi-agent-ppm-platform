# Infrastructure

Infrastructure-as-code and deployment assets for the Multi-Agent PPM Platform.

## Structure
- **terraform/**: Terraform modules and environment configurations.
- **kubernetes/**: Raw manifests and shared Helm charts.
- **observability/**: Alert rules, dashboards, and OpenTelemetry configs.
- **policies/**: Security, network, and DLP policy artifacts.

## Usage
Terraform and Kubernetes usage is driven from the root Makefile targets (`make tf-init`,
`make tf-plan`, `make tf-apply`). Update this directory as infrastructure requirements evolve.
