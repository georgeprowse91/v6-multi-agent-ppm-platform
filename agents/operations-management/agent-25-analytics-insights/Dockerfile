FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV AGENT_PATH=/app/agents/operations-management/agent-25-analytics-insights/src/analytics_insights_agent.py

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/operations-management/agent-25-analytics-insights/src/analytics_insights_agent.py"]
