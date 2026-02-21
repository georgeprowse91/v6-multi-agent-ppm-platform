#!/bin/bash
set -euo pipefail

# Only run in Claude Code remote (web) sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

echo "=== Installing pnpm workspace dependencies ==="
pnpm install

echo "=== Generating CSS module types ==="
pnpm --filter @ppm/web-ui run css-modules:types

echo "=== Installing Python dev tools ==="
pip install --quiet \
  pytest \
  pytest-asyncio \
  pytest-cov \
  pytest-mock \
  pytest-timeout \
  ruff \
  black \
  mypy \
  types-pyyaml \
  starlette \
  fastapi \
  pydantic \
  pydantic-settings \
  PyJWT

echo "=== Starting Vite dev server (UI preview on port 5000) ==="
pnpm --filter @ppm/web-ui run dev &
echo "Vite dev server started in background (port 5000)"

echo "=== Session start complete ==="
