FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/portfolio-management/agent-05-business-case-investment/src/business_case_investment_agent.py


RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/portfolio-management/agent-05-business-case-investment/src/business_case_investment_agent.py"]
