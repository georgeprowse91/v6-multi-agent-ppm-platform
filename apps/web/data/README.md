# Web App Data

Static data files and database used by the web console application.

## Directory structure

| Folder | Description |
| --- | --- |
| [workflows/](./workflows/) | Workflow data files |

## Key files

| File | Description |
| --- | --- |
| `projects.json` | Project definitions |
| `requirements.json` | Requirement records |
| `agents.json` | Agent configuration data |
| `templates.json` | Template definitions |
| `ppm.db` | SQLite database for PPM data |
| `roles.json` | Role definitions |
| `seed.json` | Seed data for initial setup |

## Agent metadata generation

The `agents.json` file is generated from the agent README files alongside the
catalog markdown. Regenerate it after updating any
`agents/**/*-agent/README.md` file:

```bash
python scripts/generate_agent_metadata.py
```

To verify the committed `agents.json` file is current:

```bash
python scripts/generate_agent_metadata.py --check
```
