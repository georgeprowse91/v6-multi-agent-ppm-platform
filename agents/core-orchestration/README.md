# Core Orchestration

## Overview

Core orchestration agents handle the front-door routing of user intents, assembly of multi-agent responses, and governance approval workflows. Together they form the control plane that coordinates all other agents in the platform.

## Directory structure

Each agent directory contains `src/`, `tests/`, a `Dockerfile`, and its own `README.md`.

| Name | Description | Link |
|------|-------------|------|
| `agent-01-intent-router` | Routes incoming user intents to the appropriate downstream agent(s). | [./agent-01-intent-router/](/./agent-01-intent-router/) |
| `agent-02-response-orchestration` | Assembles and merges responses from multiple agents into a unified output. | [./agent-02-response-orchestration/](/./agent-02-response-orchestration/) |
| `agent-03-approval-workflow` | Manages multi-step approval workflows and escalation policies. | [./agent-03-approval-workflow/](/./agent-03-approval-workflow/) |
