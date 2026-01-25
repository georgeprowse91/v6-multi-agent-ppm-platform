FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/portfolio-management/agent-07-program-management/src/program_management_agent.py

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/portfolio-management/agent-07-program-management/src/program_management_agent.py"]
