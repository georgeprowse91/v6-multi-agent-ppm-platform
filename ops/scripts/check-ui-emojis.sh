#!/usr/bin/env bash
# Check that frontend source files do not contain raw emoji characters.
# UI text should use named icon components instead.
set -euo pipefail

FRONTEND_DIR="apps/web/frontend/src"

if [ ! -d "$FRONTEND_DIR" ]; then
  echo "Frontend directory not found: $FRONTEND_DIR"
  exit 0
fi

# Match common emoji Unicode ranges in .tsx/.ts files
# Allow emojis in test files and markdown
OFFENDING=$(grep -rPn '[\x{1F300}-\x{1F9FF}\x{2600}-\x{26FF}\x{2700}-\x{27BF}]' \
  "$FRONTEND_DIR" \
  --include='*.tsx' --include='*.ts' \
  --exclude-dir='__tests__' \
  --exclude-dir='__mocks__' \
  || true)

if [ -n "$OFFENDING" ]; then
  echo "UI emoji check: raw emojis found in frontend source files."
  echo "Use named icon components instead of raw emoji characters."
  echo "$OFFENDING"
  exit 1
fi

echo "UI emoji check passed."
