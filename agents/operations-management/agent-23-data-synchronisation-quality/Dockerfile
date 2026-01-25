FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/operations-management/agent-23-data-synchronisation-quality/src/data_sync_agent.py

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/operations-management/agent-23-data-synchronisation-quality/src/data_sync_agent.py"]
