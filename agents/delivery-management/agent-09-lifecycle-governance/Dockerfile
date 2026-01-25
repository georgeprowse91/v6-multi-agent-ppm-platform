FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/delivery-management/agent-09-lifecycle-governance/src/project_lifecycle_agent.py

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/delivery-management/agent-09-lifecycle-governance/src/project_lifecycle_agent.py"]
