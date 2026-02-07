#!/bin/bash
set -euo pipefail
TIMESTAMP=$(date +"%Y%m%d%H%M%S")
BACKUP_FILE="/backups/db-${TIMESTAMP}.sql.gz"
pg_dump "$DB_URL" | gzip > "$BACKUP_FILE"
az storage blob upload --account-name "$STORAGE_ACCOUNT" \
  --container-name "$CONTAINER" \
  --file "$BACKUP_FILE" \
  --name "$(basename "$BACKUP_FILE")"
