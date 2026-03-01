# Core Orchestration

## Overview

Core orchestration agents handle the front-door routing of user intents, assembly of multi-agent responses, and governance approval workflows. Together they form the control plane that coordinates all other agents in the platform.

## Directory structure

Each agent directory contains `src/`, `tests/`, a `Dockerfile`, and its own `README.md`.

| Name | Description | Link |
|------|-------------|------|
| `intent-router-agent` | Routes incoming user intents to the appropriate downstream agent(s). | [](/./intent-router-agent/) |
| `response-orchestration-agent` | Assembles and merges responses from multiple agents into a unified output. | [](/./response-orchestration-agent/) |
| `approval-workflow-agent` | Unified workflow and approval engine — orchestrates long-running workflows, approval chains, task inboxes, and process automation. | [](/./approval-workflow-agent/) |
| `workspace-setup-agent` | Manages project workspace initialisation, connector configuration gating, external provisioning, and methodology bootstrap. | [](/./workspace-setup-agent/) |
