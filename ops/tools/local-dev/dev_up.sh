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

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env

    random_password=""
    if command -v openssl >/dev/null 2>&1; then
      random_password="$(openssl rand -hex 16)"
    else
      random_password="$(LC_ALL=C tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 32)"
    fi

    sed -i "s/replace_me_local_password/${random_password}/g" .env
    echo "Created .env from .env.example with randomized local dev credentials."
  else
    echo ".env is missing and .env.example was not found."
    exit 1
  fi
fi

echo "Starting local development stack..."
${compose_cmd} up --build
