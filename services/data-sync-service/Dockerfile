FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

CMD ["python", "-m", "tools.component_runner", "--component-type", "service", "--component-name", "data-sync-service", "--component-root", "/app/services/data-sync-service"]
