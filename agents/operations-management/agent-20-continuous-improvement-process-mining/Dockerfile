FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/operations-management/agent-20-continuous-improvement-process-mining/src/process_mining_agent.py

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/operations-management/agent-20-continuous-improvement-process-mining/src/process_mining_agent.py"]
