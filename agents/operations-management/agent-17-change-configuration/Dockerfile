FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/operations-management/agent-17-change-configuration/src/change_configuration_agent.py

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/operations-management/agent-17-change-configuration/src/change_configuration_agent.py"]
