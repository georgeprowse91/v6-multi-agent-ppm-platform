#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT=${1:-}
PRIMARY_REGION=${2:-}
if [[ -z "${ENVIRONMENT}" || -z "${PRIMARY_REGION}" ]]; then
  echo "Usage: $0 <environment> <primary-region>" >&2
  exit 1
fi

echo "Restoring primary region ${PRIMARY_REGION} for ${ENVIRONMENT}"

terraform -chdir=infra/terraform workspace select "${ENVIRONMENT}"
terraform -chdir=infra/terraform apply -var "active_region=${PRIMARY_REGION}" -auto-approve

kubectl config use-context "${ENVIRONMENT}-${PRIMARY_REGION}"

echo "Restore complete. Validate services and switch traffic back."
