# Shared Template Schema Guidance

Canonical template YAML files in `docs/templates/core/**.yaml` and `docs/templates/extensions/**.yaml` must follow this shared shape.

## Required top-level keys

Every canonical template file MUST include the following top-level keys:

- `metadata`
- `inputs`
- `sections`
- `guidance`
- `placeholders`

Extensions may include additional patch keys (`extends`, `add_sections`, `add_fields`, `add_tiles`, `replace`) but the five keys above are always required.

## Field typing and enum conventions

Use explicit type descriptors for all input and section field definitions:

- `string`, `integer`, `number`, `boolean`, `date`, `datetime`, `array`, `object`, `enum`

For enum fields:

- Set `type: enum`.
- Provide allowed values in a `values` array.
- Enum values should be lowercase kebab-case unless domain standards require otherwise.

Recommended field object shape:

```yaml
- name: status
  type: enum
  values: [not-started, in-progress, blocked, complete]
  required: true
```

## Rules for multiline narrative blocks

When a template includes narrative guidance or sample prose:

1. Use YAML block scalars with `|` (literal) for multiline text.
2. Keep each narrative block focused on one topic (purpose, instructions, assumptions, etc.).
3. Use complete sentences; avoid comma-separated fragments.
4. Wrap at natural sentence boundaries and preserve readable indentation.
5. Do not mix markdown headings inside scalar blocks; headings belong to structured keys.

Example:

```yaml
guidance:
  authoring_notes: |
    Summarize current-state context before detailing next steps.
    Keep content role-based and action-oriented.
```
