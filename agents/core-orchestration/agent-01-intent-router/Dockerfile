FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/core-orchestration/agent-01-intent-router/src/intent_router_agent.py


RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/core-orchestration/agent-01-intent-router/src/intent_router_agent.py"]
