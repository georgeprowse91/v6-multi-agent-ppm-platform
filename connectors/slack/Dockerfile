FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

CMD ["python", "-m", "tools.connector_runner", "--connector-root", "/app/connectors/slack"]
