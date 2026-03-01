# Core Orchestration

## Overview

Core orchestration agents handle the front-door routing of user intents, assembly of multi-agent responses, and governance approval workflows. Together they form the control plane that coordinates all other agents in the platform.

## Directory structure

Each agent directory contains `src/`, `tests/`, a `Dockerfile`, and its own `README.md`.

| Name | Description | Link |
|------|-------------|------|
| `intent-router-agent` | Routes incoming user intents to the appropriate downstream agent(s). | [](/./intent-router-agent/) |
| `response-orchestration-agent` | Assembles and merges responses from multiple agents into a unified output. | [](/./response-orchestration-agent/) |
| `approval-workflow-agent` | Manages multi-step approval workflows and escalation policies. | [](/./approval-workflow-agent/) |
