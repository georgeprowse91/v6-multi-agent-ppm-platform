# Multi-Agent PPM Platform - auth-service Dockerfile

# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt pyproject.toml ./

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
COPY --chown=10001:10001 pyproject.toml ./
COPY --chown=10001:10001 tools ./tools
COPY --chown=10001:10001 config ./config
COPY --chown=10001:10001 services/auth-service ./services/auth-service

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/vendor/stubs:/app/vendor:/app:/app/packages/common/src:/app/packages/observability/src:/app/packages/security/src:/app/packages/llm/src:/app/packages/workflow/src:/app/packages/event-bus/src:/app/services/agent-config/src \
    PATH="/home/appuser/.local/bin:${PATH}"

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run the application
CMD ["sh", "-c", "uvicorn main:app --app-dir services/auth-service/src --host 0.0.0.0 --port 8080 --workers ${WEB_CONCURRENCY:-2}"]
