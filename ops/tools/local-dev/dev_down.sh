#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$repo_root"

compose_cmd="docker-compose"
if command -v docker-compose >/dev/null 2>&1; then
  compose_cmd="docker-compose"
elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  compose_cmd="docker compose"
else
  echo "Docker Compose is not available. Install Docker Desktop or the docker-compose plugin."
  exit 1
fi

echo "Stopping local development stack..."
${compose_cmd} down
