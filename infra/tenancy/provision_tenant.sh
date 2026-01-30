#!/usr/bin/env bash
set -euo pipefail

TENANT_ID=${1:-}
if [[ -z "${TENANT_ID}" ]]; then
  echo "Usage: $0 <tenant-id>" >&2
  exit 1
fi

NAMESPACE="tenant-${TENANT_ID}"

kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${NAMESPACE}"

kubectl label namespace "${NAMESPACE}" ppm.platform/tenant="${TENANT_ID}" --overwrite

echo "Provisioned namespace ${NAMESPACE} for tenant ${TENANT_ID}"
