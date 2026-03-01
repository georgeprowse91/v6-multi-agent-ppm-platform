FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/delivery-management/quality-management-agent/src/quality_management_agent.py


RUN groupadd --gid 10001 appuser && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin appuser && chown -R 10001:10001 /app

USER appuser

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/delivery-management/quality-management-agent/src/quality_management_agent.py"]
