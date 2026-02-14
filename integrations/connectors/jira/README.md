# Jira Connector

Synchronizes projects and work items with Jira Cloud, including webhook scaffolding for inbound updates.

## Jira authentication

Configure Jira credentials with environment variables before running the connector:

- `JIRA_INSTANCE_URL`: Base URL for your Jira Cloud tenant (for example, `https://your-org.atlassian.net`).
- `JIRA_EMAIL`: Atlassian account email used to generate the API token.
- `JIRA_API_TOKEN`: Jira API token used for connector authentication.

Export these values in your deployment environment so they can be injected into the connector runtime securely.

## Directory structure

| Folder | Description |
| --- | --- |
| [src/](./src/) | Connector implementation |
| [mappings/](./mappings/) | Field mapping definitions |
| [tests/](./tests/) | Test suites and fixtures |

## Key files

- `manifest.yaml` — Connector manifest with metadata and sync configuration
- `Dockerfile` — Container build recipe
- `__init__.py` — Python package marker
