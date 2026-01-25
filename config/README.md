# Configuration Files

This directory contains configuration files for the Multi-Agent PPM Platform.

## Structure

```
config/
├── agents/              # Agent-specific configurations
│   ├── orchestration.yaml
│   └── portfolio.yaml
├── connectors/          # External integration configurations
│   └── integrations.yaml
├── environments/        # Environment-specific configs
│   ├── dev.yaml
│   ├── test.yaml
│   └── prod.yaml
├── feature-flags/       # Feature flag definitions
│   └── flags.yaml
├── rbac/                # Role/permission definitions
│   ├── roles.yaml
│   ├── permissions.yaml
│   └── field-level.yaml
├── data-classification/ # Classification mappings
│   └── levels.yaml
└── retention/           # Retention policies
    └── policies.yaml
```

## Configuration Files

### Agent Configurations

- **orchestration.yaml**: Intent Router and Response Orchestration agents
- **portfolio.yaml**: Demand Intake, Business Case, Portfolio Strategy, Program Management
- **delivery.yaml**: Project Definition, Lifecycle, Schedule, Resource, Financial, Vendor agents
- **governance.yaml**: Quality, Risk, Compliance, Change Management agents
- **operations.yaml**: Release, Knowledge, Continuous Improvement, Communications agents
- **platform.yaml**: Analytics, Data Sync, Workflow, System Health agents

### Connector Configurations

- **integrations.yaml**: External system integrations (Jira, SAP, Workday, Slack, etc.)

See [Connector Specifications](../docs/connectors/overview.md) for details.

## Environment Variables

Configuration files support environment variable substitution using `${VAR_NAME}` syntax.

See `.env.example` in the root directory for all available environment variables.

## Usage

Configurations are loaded automatically by the platform based on the `ENVIRONMENT` variable:

```bash
ENVIRONMENT=dev  # Loads dev.yaml
ENVIRONMENT=prod # Loads prod.yaml
```

## Overriding Configurations

You can override configurations using environment variables:

```bash
export AGENT_INTENT_ROUTER_ENABLED=false
export AGENT_MAX_CONCURRENCY=10
```

## Validation

All configuration files are validated against schemas on startup. Invalid configurations will prevent the platform from starting.
