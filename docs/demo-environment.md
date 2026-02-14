# Demo environment provisioning and deployment

This guide describes how to provision a low-cost demo environment and deploy the PPM platform with demo-specific Helm values.

## Prerequisites

- Terraform `>= 1.5`
- Helm `>= 3.12`
- Azure CLI authenticated to the target subscription
- `kubectl` configured with cluster access

## 1) Prepare demo environment variables

```bash
cp .env.demo .env
source .env
```

> `.env.demo` contains stub secrets only. Replace them before provisioning shared infrastructure.

## 2) Provision infrastructure with Terraform

```bash
cd infra/terraform/envs/demo
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

The demo stack intentionally uses cost-effective defaults:

- Single-node AKS (`Standard_B2s`, `sku_tier=Free`)
- PostgreSQL burstable SKU (`B_Standard_B1ms`) with no HA
- LRS storage account for artifacts and logs

## 3) Deploy the platform with Helm

```bash
helm upgrade --install ppm-platform-demo \
  infra/kubernetes/helm-charts/ppm-platform \
  --namespace ppm-demo \
  --create-namespace \
  -f infra/kubernetes/helm-charts/ppm-platform/demo-values.yaml
```

The demo values file enables demo mode, points connector services to internal mock connector URLs, and reduces service replica counts for lower cost.

## 4) Verify deployment

```bash
kubectl get pods -n ppm-demo
kubectl get svc -n ppm-demo
```
