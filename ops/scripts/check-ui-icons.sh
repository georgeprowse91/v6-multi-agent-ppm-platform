#!/usr/bin/env bash
# Check that frontend icon imports come from the project's icon system.
set -euo pipefail

FRONTEND_DIR="apps/web/frontend/src"

if [ ! -d "$FRONTEND_DIR" ]; then
  echo "Frontend directory not found: $FRONTEND_DIR"
  exit 0
fi

# Check for direct imports from icon libraries that should go through our icon system
OFFENDING=$(grep -rPn "from ['\"]react-icons" \
  "$FRONTEND_DIR" \
  --include='*.tsx' --include='*.ts' \
  --exclude-dir='__tests__' \
  --exclude-dir='icons' \
  || true)

if [ -n "$OFFENDING" ]; then
  echo "UI icon check: direct react-icons imports found."
  echo "Import icons from @/components/icons instead."
  echo "$OFFENDING"
  exit 1
fi

echo "UI icon check passed."
