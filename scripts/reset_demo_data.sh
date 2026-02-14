#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_CMD="${COMPOSE_CMD:-docker compose}"
DB_SERVICE="${DB_SERVICE:-db}"
CACHE_SERVICE="${CACHE_SERVICE:-redis}"
APP_SERVICES=("api" "workflow-engine" "web")

REGENERATE=0
GENERATOR_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --regenerate)
      REGENERATE=1
      shift
      ;;
    --size|--seed|--output-dir|--manifest-path)
      GENERATOR_ARGS+=("$1" "$2")
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: scripts/reset_demo_data.sh [--regenerate] [generator args]

Resets demo databases/cache, re-runs migrations, and reloads demo records.

Options:
  --regenerate            Regenerate data/*.json and manifest CSV before loading
  --size N                Base size passed to generate_demo_data.py (with --regenerate)
  --seed N                Seed passed to generate_demo_data.py (with --regenerate)
  --output-dir PATH       Output directory passed to generate_demo_data.py
  --manifest-path PATH    Manifest CSV path passed to generate_demo_data.py
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

echo "[1/7] Stopping app services to release DB connections..."
$COMPOSE_CMD stop "${APP_SERVICES[@]}" >/dev/null 2>&1 || true

echo "[2/7] Ensuring database and cache services are running..."
$COMPOSE_CMD up -d "$DB_SERVICE" "$CACHE_SERVICE"

echo "[3/7] Dropping and recreating demo database..."
$COMPOSE_CMD exec -T "$DB_SERVICE" sh -lc '
set -e
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '"'"'$POSTGRES_DB'"'"'
  AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "'"'$POSTGRES_DB'"'"';
CREATE DATABASE "'"'$POSTGRES_DB'"'"';
SQL
'

echo "[4/7] Clearing Redis cache..."
$COMPOSE_CMD exec -T "$CACHE_SERVICE" redis-cli FLUSHALL >/dev/null

if [[ "$REGENERATE" -eq 1 ]]; then
  echo "[5/7] Regenerating demo JSON/CSV files..."
  python3 scripts/generate_demo_data.py "${GENERATOR_ARGS[@]}"
else
  echo "[5/7] Skipping regeneration (use --regenerate to generate a fresh dataset)."
fi

echo "[6/7] Running database migrations..."
$COMPOSE_CMD run --rm api alembic upgrade head

echo "[7/7] Reloading demo JSON/CSV-backed records..."
python3 scripts/load_demo_data.py

echo "Restarting app services..."
$COMPOSE_CMD up -d "${APP_SERVICES[@]}"

echo "Demo data reset complete."
