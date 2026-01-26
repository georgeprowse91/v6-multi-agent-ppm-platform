FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app


RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "tools.component_runner", "--component-type", "service", "--component-name", "policy-engine", "--component-root", "/app/services/policy-engine"]
