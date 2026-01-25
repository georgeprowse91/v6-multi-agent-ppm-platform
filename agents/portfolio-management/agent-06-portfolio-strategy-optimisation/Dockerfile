FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/portfolio-management/agent-06-portfolio-strategy-optimisation/src/portfolio_strategy_agent.py"]
