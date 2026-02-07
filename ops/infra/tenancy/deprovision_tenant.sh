#!/usr/bin/env bash
set -euo pipefail

TENANT_ID=${1:-}
if [[ -z "${TENANT_ID}" ]]; then
  echo "Usage: $0 <tenant-id>" >&2
  exit 1
fi

NAMESPACE="tenant-${TENANT_ID}"

kubectl delete namespace "${NAMESPACE}" --ignore-not-found

echo "Deprovisioned namespace ${NAMESPACE} for tenant ${TENANT_ID}"
