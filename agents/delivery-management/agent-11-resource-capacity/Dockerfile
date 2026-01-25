FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/delivery-management/agent-11-resource-capacity/src/resource_capacity_agent.py

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/delivery-management/agent-11-resource-capacity/src/resource_capacity_agent.py"]
