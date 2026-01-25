FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

CMD ["python", "-m", "tools.component_runner", "--component-type", "service", "--component-name", "telemetry-service", "--component-root", "/app/services/telemetry-service"]
