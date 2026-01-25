FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY . /app

ENV AGENT_PATH=/app/agents/core-orchestration/agent-03-approval-workflow/src/approval_workflow_agent.py

CMD ["python", "-m", "tools.agent_runner", "--agent-path", "/app/agents/core-orchestration/agent-03-approval-workflow/src/approval_workflow_agent.py"]
