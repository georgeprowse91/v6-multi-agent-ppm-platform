#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT=${1:-}
REGION=${2:-}
if [[ -z "${ENVIRONMENT}" || -z "${REGION}" ]]; then
  echo "Usage: $0 <environment> <dr-region>" >&2
  exit 1
fi

echo "Starting DR failover for ${ENVIRONMENT} to ${REGION}"

terraform -chdir=infra/terraform workspace select "${ENVIRONMENT}"
terraform -chdir=infra/terraform apply -var "active_region=${REGION}" -auto-approve

kubectl config use-context "${ENVIRONMENT}-${REGION}"

echo "Failover complete. Verify traffic routing and data replication."
