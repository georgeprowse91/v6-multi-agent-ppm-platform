# NOTE: This Dockerfile uses Docker BuildKit additional_contexts. It must be
# built via docker-compose (ops/docker/docker-compose.yml) which provides the
# 'repo-root' context pointing to the repository root.
# Standalone build: DOCKER_BUILDKIT=1 docker build --build-context repo-root=../.. .
# syntax=docker/dockerfile:1.6
# Multi-Agent PPM Platform - policy-engine Dockerfile

# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY --from=repo-root requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 10001 appuser && \
    useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin appuser && \
    chown -R 10001:10001 /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code and shared tooling
COPY --chown=10001:10001 --from=repo-root pyproject.toml ./
COPY --chown=10001:10001 --from=repo-root tools ./tools
COPY --chown=10001:10001 --from=repo-root config ./config
COPY --chown=10001:10001 --from=repo-root packages ./packages
COPY --chown=10001:10001 . ./services/policy-engine

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/home/appuser/.local/bin:${PATH}"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--app-dir", "services/policy-engine/src", "--host", "0.0.0.0", "--port", "8000"]
