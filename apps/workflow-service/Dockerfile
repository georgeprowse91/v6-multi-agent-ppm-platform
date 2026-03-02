# NOTE: This Dockerfile uses Docker BuildKit additional_contexts. It must be
# built via docker-compose (ops/docker/docker-compose.yml) which provides the
# 'repo-root' context pointing to the repository root.
# Standalone build: DOCKER_BUILDKIT=1 docker build --build-context repo-root=../.. .
# syntax=docker/dockerfile:1.6
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY --from=repo-root pyproject.toml ./
COPY --from=repo-root tools ./tools
COPY --from=repo-root config ./config
COPY --from=repo-root packages ./packages
COPY --from=repo-root agents ./agents
COPY . /app/apps/workflow-service

RUN mkdir -p /app/services


RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Healthcheck contract:
# - Endpoint: GET /healthz on port 8080
# - Returns HTTP 200 when critical dependencies are healthy
# - Returns HTTP 503 when service is degraded/unhealthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["curl", "--fail", "--silent", "--show-error", "http://127.0.0.1:8080/healthz"]

RUN groupadd --gid 10001 appuser && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin appuser && chown -R 10001:10001 /app

USER appuser

CMD ["python", "-m", "tools.component_runner", "--component-type", "app", "--component-name", "workflow-service", "--component-root", "/app/apps/workflow-service"]
