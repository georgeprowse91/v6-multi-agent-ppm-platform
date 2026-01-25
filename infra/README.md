# Infrastructure & Deployment

Infrastructure as Code (IaC) and deployment configurations for the Multi-Agent PPM Platform.

## Directory Structure

```
infra/
├── terraform/           # Terraform configurations for Azure
│   └── main.tf         # Main infrastructure definition
├── kubernetes/         # Kubernetes manifests
│   ├── deployment.yaml # Deployment and Service definitions
│   └── secrets.yaml.example  # Secrets template
└── docker/            # Docker-specific configs
```

## Terraform - Azure Infrastructure

### Prerequisites

- [Terraform](https://www.terraform.io/downloads.html) >= 1.5.0
- Azure CLI logged in: `az login`
- Azure subscription with appropriate permissions

### Deploy Infrastructure

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Plan changes
terraform plan -var="environment=dev"

# Apply changes
terraform apply -var="environment=dev"
```

### Resources Created

The Terraform configuration creates:

- **Resource Group**: Container for all resources
- **Container Registry**: For Docker images
- **Container Apps Environment**: For running containers
- **PostgreSQL Flexible Server**: Primary database
- **Azure Cosmos DB**: For scalable document storage
- **Redis Cache**: For caching and sessions
- **Azure OpenAI**: AI/ML capabilities
- **Key Vault**: Secrets management
- **Storage Account**: Data Lake Gen2
- **Service Bus**: Event-driven messaging

### Variables

- `environment`: Environment name (dev, staging, production)
- `location`: Azure region (default: eastus)
- `resource_prefix`: Prefix for resource names (default: ppm)

## Kubernetes - Container Orchestration

### Prerequisites

- Kubernetes cluster (AKS, EKS, GKE, or local)
- kubectl configured
- Docker images built and pushed to registry

### Deploy to Kubernetes

```bash
cd infra/kubernetes

# Create secrets (copy from example first)
cp secrets.yaml.example secrets.yaml
# Edit secrets.yaml with your values

kubectl apply -f secrets.yaml
kubectl apply -f deployment.yaml

# Check deployment status
kubectl get pods -l app=ppm-api
kubectl get svc ppm-api-service
```

### Scaling

The deployment includes a Horizontal Pod Autoscaler (HPA) that automatically scales based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)

Manually scale:
```bash
kubectl scale deployment ppm-api --replicas=5
```

### Monitoring

View logs:
```bash
kubectl logs -f deployment/ppm-api
```

Port forward for local testing:
```bash
kubectl port-forward service/ppm-api-service 8000:80
```

## Docker Compose - Local Development

For local development, use Docker Compose:

```bash
# From repository root
docker-compose up --build

# Access services
# API: http://localhost:8000
# Web: http://localhost:8501
# PostgreSQL: localhost:5432
# Redis: localhost:6379
```

## Environment-Specific Deployments

### Development
```bash
terraform apply -var="environment=dev"
```

### Staging
```bash
terraform apply -var="environment=staging"
```

### Production
```bash
terraform apply -var="environment=production"
```

## Cost Optimization

For development environments, consider:
- Using Basic tier for PostgreSQL
- Reducing Redis capacity
- Using fewer container replicas
- Disabling geo-redundancy

## Security Best Practices

1. **Never commit secrets** - Use Key Vault or Kubernetes Secrets
2. **Enable RBAC** - Role-based access control on all resources
3. **Use Managed Identities** - Avoid storing credentials
4. **Network Isolation** - Use Virtual Networks and Private Endpoints
5. **Enable Monitoring** - Use Azure Monitor and Application Insights

## Disaster Recovery

- **Backup**: PostgreSQL automated backups (7 days retention)
- **Geo-Redundancy**: Cosmos DB multi-region replication
- **State Management**: Terraform state stored in Azure Storage

## Troubleshooting

### Terraform Issues

```bash
# Refresh state
terraform refresh

# Force unlock if stuck
terraform force-unlock <LOCK_ID>

# Destroy and recreate specific resource
terraform taint azurerm_container_app_environment.main
terraform apply
```

### Kubernetes Issues

```bash
# Check pod status
kubectl describe pod <POD_NAME>

# View events
kubectl get events --sort-by='.lastTimestamp'

# Check logs
kubectl logs <POD_NAME> --previous
```

## Additional Resources

- [Architecture Documentation](../docs/architecture/)
- [Deployment Architecture](../docs/architecture/deployment-architecture.md)
- [Security Architecture](../docs/architecture/security-architecture.md)
