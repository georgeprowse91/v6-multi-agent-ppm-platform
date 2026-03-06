FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app/vendor/stubs:/app/vendor:/app:/app/packages/common/src:/app/packages/observability/src:/app/packages/security/src:/app/packages/llm/src:/app/packages/workflow/src:/app/packages/event-bus/src:/app/services/agent-config/src

COPY . /app


RUN groupadd --gid 10001 appuser && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin appuser && chown -R 10001:10001 /app

USER appuser

CMD ["python", "-m", "tools.connector_runner", "--connector-root", "/app/connectors/regulatory_compliance"]
