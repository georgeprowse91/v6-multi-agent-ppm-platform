FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

CMD ["python", "-m", "tools.component_runner", "--component-type", "app", "--component-name", "workflow-engine", "--component-root", "/app/apps/workflow-engine"]
