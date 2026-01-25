# Jira Field Mappings

## Purpose

Describe how Jira fields map to the platform’s canonical PPM schemas in `data/schemas/`.

## Architecture-level context

Mappings are consumed by the connector runtime to transform Jira payloads into canonical entities and to emit data quality scores during sync.

## Key files

- `project.yaml`: Jira project metadata → canonical project schema.

## Usage example

View the Jira project mapping:

```bash
sed -n '1,160p' connectors/jira/mappings/project.yaml
```

## How to verify

Check that the mapping file exists:

```bash
ls connectors/jira/mappings/project.yaml
```

Expected output: the YAML mapping file path.

## Related docs

- [Connector Overview](../../../docs/connectors/overview.md)
- [Data Schemas](../../../data/schemas/)
