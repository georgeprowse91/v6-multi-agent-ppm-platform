FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/delivery-management/agent-12-financial-management/src/financial_management_agent.py


RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/delivery-management/agent-12-financial-management/src/financial_management_agent.py"]
