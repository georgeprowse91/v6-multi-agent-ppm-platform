FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/delivery-management/agent-08-project-definition-scope/src/project_definition_agent.py

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/delivery-management/agent-08-project-definition-scope/src/project_definition_agent.py"]
