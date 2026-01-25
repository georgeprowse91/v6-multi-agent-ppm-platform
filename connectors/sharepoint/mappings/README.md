# Sharepoint field mappings

This folder defines how external Sharepoint fields map to the platform's canonical
portfolio, program, project, and work-item schemas.

## File expectations
- Keep mappings in YAML files named after the entity (for example, `project.yaml`).
- Use `source_field` for the upstream field name and `target_field` for the platform field.
- Include `transform` when the source format needs normalization.

## Example
```yaml
entity: project
fields:
  - source_field: System.Title
    target_field: title
    transform: string
  - source_field: System.State
    target_field: status
    transform: enum
```
