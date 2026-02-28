FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app


RUN groupadd --gid 10001 appuser && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin appuser && chown -R 10001:10001 /app

USER appuser

CMD ["python", "-m", "tools.connector_runner", "--connector-root", "/app/integrations/connectors/azure_devops"]
