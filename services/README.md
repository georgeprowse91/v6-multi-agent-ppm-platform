# Services

## Purpose
This directory contains supporting services that run alongside the core applications. Each service
is deployable independently and ships its own Helm chart, tests, and implementation code.

## Responsibilities
- Provide cross-cutting platform capabilities (audit logging, telemetry, policy evaluation).
- Expose API and event interfaces consumed by the apps in `apps/`.
- Maintain deployment artifacts for Kubernetes releases.

## Included services
- **audit-log**: Long-term audit trail and retention storage for platform events.
- **data-sync-service**: Background synchronisation for connector data and reconciliation rules.
- **identity-access**: IAM, RBAC enforcement, and tenant identity integration.
- **notification-service**: Email/chat notifications and templated communications.
- **policy-engine**: Policy evaluation and enforcement for compliance rules.
- **telemetry-service**: Central ingestion and processing of logs, metrics, and traces.

## Folder structure
```
services/
├── audit-log/helm/Chart.yaml
├── data-sync-service/helm/values.yaml
├── identity-access/helm/templates/deployment.yaml
├── notification-service/helm/templates/service.yaml
├── policy-engine/policies/bundles/default-policy-bundle.yaml
└── telemetry-service/helm/templates/configmap.yaml
```

## Conventions
- Service directories are kebab-case and match the service name.
- Each service includes a Helm chart under `<service>/helm/`.
- Policy bundles for the policy engine live under `policy-engine/policies/`.

## How to add a new service
1. Create a new folder under `services/<service-name>`.
2. Add a Helm chart in `services/<service-name>/helm/` (see existing charts).
3. Add service code under `services/<service-name>/src/` and tests under `services/<service-name>/tests/`.
4. Update this README to list the new service.

## How to validate/test
```bash
python scripts/validate-helm-charts.py services/<service-name>/helm
python scripts/validate-policies.py services/policy-engine/policies/bundles/default-policy-bundle.yaml
```

## Example
```yaml
apiVersion: v2
name: audit-log
version: 0.1.0
appVersion: "0.1.0"
```
